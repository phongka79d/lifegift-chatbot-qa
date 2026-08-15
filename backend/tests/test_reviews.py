"""Tests for customer reviews filtering (APPROVED only)."""

import pytest
from sqlalchemy.orm import Session
from backend.app.repositories.review_repository import ReviewRepository


def test_approved_reviews_only(db_session: Session):
    """Verify only APPROVED reviews are returned; PENDING/REJECTED are filtered out."""
    repo = ReviewRepository(db_session)
    result = repo.get_product_reviews(product_id=1, limit=10)

    assert result["product_id"] == 1
    assert result["review_count"] == 2  # Product 1 has 2 approved, 1 pending, 1 rejected
    assert result["average_rating"] == 5.0
    assert len(result["reviews"]) == 2

    for rev in result["reviews"]:
        assert rev["rating"] == 5
        assert "Spam" not in rev["title"]
        assert "Chờ duyệt" not in rev["title"]
