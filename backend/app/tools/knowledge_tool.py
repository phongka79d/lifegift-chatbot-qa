"""Knowledge RAG tool adapter."""

from typing import List, Dict, Any, Optional
from backend.app.rag.retriever import QdrantRetriever


def search_knowledge_tool(
    retriever: QdrantRetriever,
    query: str,
    limit: int = 4,
    product_id: Optional[int] = None,
    source_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve grounded knowledge chunks from Qdrant."""
    return retriever.retrieve(
        query=query,
        limit=limit,
        product_id=product_id,
        source_type=source_type,
    )
