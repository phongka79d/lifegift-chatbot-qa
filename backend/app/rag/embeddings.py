"""Provider-neutral embedding client wrapper."""

import hashlib
import logging
from typing import List, Optional
from langchain_core.embeddings import Embeddings

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)


class MockDeterministicEmbeddings(Embeddings):
    """Deterministic fallback embeddings for offline testing and environments without API keys."""

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    def _embed_text(self, text: str) -> List[float]:
        # Generate stable, pseudo-random float vector from md5 hash
        hasher = hashlib.sha256(text.encode("utf-8"))
        digest = hasher.digest()
        # Create deterministic normalized vector
        vec = []
        for i in range(self.dimension):
            byte_val = digest[i % len(digest)]
            val = (float(byte_val) / 255.0) - 0.5
            vec.append(val)
        # Normalize
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_text(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_text(text)


def get_embedding_client(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Embeddings:
    """Return an initialized OpenAI-compatible embeddings client or deterministic fallback."""
    settings = get_settings()
    key = api_key or settings.EMBEDDING_API_KEY
    url = base_url or settings.EMBEDDING_BASE_URL
    model_name = model or settings.EMBEDDING_MODEL

    if not key or key.strip() in ("", "your_embedding_api_key_here", "test_key"):
        logger.info("No valid EMBEDDING_API_KEY provided; using deterministic mock embeddings.")
        return MockDeterministicEmbeddings(dimension=settings.EMBEDDING_DIMENSION)

    try:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=model_name,
            api_key=key,
            base_url=url,
            dimensions=settings.EMBEDDING_DIMENSION if "text-embedding-3" in model_name else None,
        )
    except Exception as exc:
        logger.warning("Failed to initialize remote embeddings client (%s), falling back to mock.", exc)
        return MockDeterministicEmbeddings(dimension=settings.EMBEDDING_DIMENSION)
