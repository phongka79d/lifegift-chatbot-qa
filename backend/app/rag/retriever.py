"""Qdrant Knowledge Retriever with filters and controlled error handling."""

import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest_models

from backend.app.core.config import get_settings
from backend.app.rag.embeddings import get_embedding_client

logger = logging.getLogger(__name__)


class KnowledgeChunk(dict):
    """Retrieved knowledge chunk with text, score, and payload metadata."""


class QdrantRetriever:
    """Semantic retriever querying the Qdrant lifegift_knowledge collection."""

    def __init__(
        self,
        client: Optional[QdrantClient] = None,
        collection_name: Optional[str] = None,
        embedding_client=None,
    ):
        settings = get_settings()
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.embedding_client = embedding_client or get_embedding_client()
        self._client = client

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            from backend.app.core.qdrant import get_qdrant_client
            self._client = get_qdrant_client()
        return self._client

    def retrieve(
        self,
        query: str,
        limit: int = 4,
        product_id: Optional[int] = None,
        source_type: Optional[str] = None,
        score_threshold: float = 0.25,
    ) -> List[Dict[str, Any]]:
        """Retrieve top semantic documents from Qdrant with optional metadata filters."""
        if not query or not query.strip():
            return []

        bounded_limit = max(1, min(limit, 10))

        try:
            # Generate query embedding
            query_vector = self.embedding_client.embed_query(query.strip())

            # Build optional metadata filter
            filter_conditions = []
            if product_id is not None:
                filter_conditions.append(
                    rest_models.FieldCondition(
                        key="product_id",
                        match=rest_models.MatchValue(value=product_id),
                    )
                )
            if source_type is not None:
                filter_conditions.append(
                    rest_models.FieldCondition(
                        key="source_type",
                        match=rest_models.MatchValue(value=source_type),
                    )
                )

            query_filter = None
            if filter_conditions:
                query_filter = rest_models.Filter(must=filter_conditions)

            if hasattr(self.client, "query_points"):
                search_results = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=bounded_limit,
                    score_threshold=score_threshold,
                ).points
            elif hasattr(self.client, "search"):
                search_results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=bounded_limit,
                    score_threshold=score_threshold,
                )
            else:
                search_results = []

            chunks = []
            for hit in search_results:
                payload = hit.payload or {}
                chunks.append(
                    {
                        "id": hit.id,
                        "score": round(float(hit.score), 4),
                        "content": payload.get("text", ""),
                        "source_type": payload.get("source_type", ""),
                        "source_id": payload.get("source_id"),
                        "product_id": payload.get("product_id"),
                        "title": payload.get("title", ""),
                        "metadata": payload,
                    }
                )
            return chunks

        except Exception as exc:
            logger.warning(
                "Qdrant retrieval error for query '%s': %s. Returning degraded empty result.",
                query,
                exc,
            )
            return []
