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
        vec = [0.0] * self.dimension
        words = text.lower().split()
        if not words:
            return vec
        for word in words:
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
            vec[idx] += sign

        for i in range(len(words) - 1):
            bigram = f"{words[i]}_{words[i+1]}"
            h = int(hashlib.md5(bigram.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
            vec[idx] += sign * 1.5

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
    key = api_key or settings.effective_embedding_api_key
    url = base_url or settings.effective_embedding_base_url
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
