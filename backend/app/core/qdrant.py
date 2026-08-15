"""Qdrant vector database client and collection initialization."""

import logging
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest_models

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)


def get_qdrant_client(
    url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> QdrantClient:
    """Create a Qdrant client instance using configured settings or custom arguments."""
    settings = get_settings()
    target_url = url or settings.QDRANT_URL
    target_api_key = api_key if api_key is not None else settings.QDRANT_API_KEY
    if target_url.startswith("http://") or target_url.startswith("https://"):
        return QdrantClient(url=target_url, api_key=target_api_key or None, timeout=10.0)
    return QdrantClient(location=target_url)


def init_qdrant_collection(
    client: QdrantClient,
    collection_name: Optional[str] = None,
    vector_size: Optional[int] = None,
) -> bool:
    """Ensure the Qdrant knowledge collection exists with correct dimension and distance."""
    settings = get_settings()
    name = collection_name or settings.QDRANT_COLLECTION
    dim = vector_size or settings.EMBEDDING_DIMENSION

    try:
        collections = client.get_collections().collections
        exists = any(c.name == name for c in collections)
        if not exists:
            logger.info("Creating Qdrant collection %s with vector size %d", name, dim)
            client.create_collection(
                collection_name=name,
                vectors_config=rest_models.VectorParams(
                    size=dim,
                    distance=rest_models.Distance.COSINE,
                ),
            )
            # Create payload index for fast filtering
            client.create_payload_index(
                collection_name=name,
                field_name="source_type",
                field_schema=rest_models.PayloadSchemaType.KEYWORD,
            )
            client.create_payload_index(
                collection_name=name,
                field_name="product_id",
                field_schema=rest_models.PayloadSchemaType.INTEGER,
            )
        return True
    except Exception as exc:
        logger.warning("Failed to initialize Qdrant collection %s: %s", name, exc)
        return False
