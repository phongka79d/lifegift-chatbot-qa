"""Customer review tool adapter."""

from typing import Dict, Any
from backend.app.repositories.review_repository import ReviewRepository


def get_product_reviews_tool(
    repo: ReviewRepository, product_id: int, limit: int = 5
) -> Dict[str, Any]:
    """Fetch verified approved reviews for a product."""
    return repo.get_product_reviews(product_id=product_id, limit=limit)
