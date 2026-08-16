"""Hybrid Product Recommendation Service combining MySQL hard constraints and Qdrant semantic ranking."""

import logging
from typing import List, Optional, Tuple
from backend.app.repositories.product_repository import ProductRepository
from backend.app.rag.retriever import QdrantRetriever
from backend.app.schemas.product import ProductCard, ProductSearchParams

logger = logging.getLogger(__name__)


class RecommendationService:
    """Combines authoritative MySQL filter constraints with Qdrant preference scoring."""

    def __init__(
        self,
        product_repo: ProductRepository,
        retriever: Optional[QdrantRetriever] = None,
    ):
        self.product_repo = product_repo
        self.retriever = retriever or QdrantRetriever()

    def recommend(
        self,
        category: Optional[str] = None,
        origin: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        price_unit: str = "PACKAGE",
        preferences: Optional[str] = None,
        in_stock: bool = True,
        top_k: int = 3,
    ) -> Tuple[List[ProductCard], bool]:
        """Perform hybrid recommendation and return top products and a flag indicating if semantic retrieval was used."""
        # 1. Step 1: Hard constraint filtering via MySQL
        search_params = ProductSearchParams(
            category=category,
            origin=origin,
            brand=brand,
            min_price=min_price,
            max_price=max_price,
            price_unit=price_unit or "PACKAGE",
            in_stock=in_stock,
            limit=10,
        )
        mysql_candidates = self.product_repo.search_products(search_params)

        if not mysql_candidates:
            logger.info("No MySQL candidates met the hard constraints.")
            return [], False

        candidate_map = {p.id: p for p in mysql_candidates}
        semantic_applied = False

        # 2. Step 2: Semantic preference matching via Qdrant
        pref_query = (preferences or "").strip()
        if pref_query:
            try:
                retrieved_chunks = self.retriever.retrieve(
                    query=pref_query,
                    limit=10,
                    source_type="product",
                )
                if retrieved_chunks:
                    # Create score map for candidate products only (Hard constraint intersection)
                    scored_candidates = []
                    matched_ids = set()

                    for chunk in retrieved_chunks:
                        pid = chunk.get("product_id")
                        if pid and pid in candidate_map and pid not in matched_ids:
                            cand = candidate_map[pid]
                            cand.reason = f"Phù hợp tiêu chí '{pref_query}' ({chunk.get('title')})"
                            scored_candidates.append((chunk.get("score", 0.0), cand))
                            matched_ids.add(pid)

                    # Add remaining candidates that did not get a direct semantic match
                    for pid, cand in candidate_map.items():
                        if pid not in matched_ids:
                            if not cand.reason:
                                cand.reason = "Đáp ứng ngân sách và danh mục yêu cầu"
                            scored_candidates.append((0.0, cand))

                    # Sort by semantic score descending
                    scored_candidates.sort(key=lambda x: x[0], reverse=True)
                    ranked_products = [c[1] for c in scored_candidates]
                    semantic_applied = True
                    return ranked_products[: max(1, min(top_k, 5))], semantic_applied
            except Exception as exc:
                logger.warning("Semantic recommendation ranking failed (%s), degrading to MySQL candidates.", exc)

        # Fallback to MySQL candidates when no preferences or Qdrant fails
        for p in mysql_candidates:
            if not p.reason:
                p.reason = "Đáp ứng ngân sách và danh mục yêu cầu"
        return mysql_candidates[: max(1, min(top_k, 5))], False
