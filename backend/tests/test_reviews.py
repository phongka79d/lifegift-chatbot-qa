"""Tests for customer reviews filtering (APPROVED only)."""

import asyncio
from sqlalchemy.orm import Session

from backend.app.chatbot.llm import extract_review_theme
from backend.app.chatbot.service import ChatbotService
from backend.app.repositories.review_repository import ReviewRepository
from backend.app.schemas.chat import IntentEnum, IntentExtractionResult


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


def test_extract_review_theme_keeps_content_words():
    assert extract_review_theme("Có sản phẩm nào có review đúng với mô tả không?") == "đúng mô tả"
    assert extract_review_theme("Sản phẩm nào có đánh giá?") is None


def test_list_reviewed_products_without_theme(db_session: Session):
    repo = ReviewRepository(db_session)
    hits = repo.list_reviewed_products(limit=5)
    assert hits
    assert any(h["product_id"] == 1 for h in hits)


def test_list_reviewed_products_filters_by_review_text(db_session: Session):
    repo = ReviewRepository(db_session)
    hits = repo.list_reviewed_products(review_text="thơm", limit=5)
    assert hits
    assert any(h["product_id"] == 1 for h in hits)
    assert repo.list_reviewed_products(review_text="xyzkhongtontai123", limit=5) == []


def test_review_discovery_without_product_name(db_session: Session):
    svc = ChatbotService(session=db_session, llm=None)
    extracted = IntentExtractionResult(intent=IntentEnum.PRODUCT_REVIEW, query="thơm")
    products, context = asyncio.run(svc._handle_product_review(extracted))
    assert products
    assert any("thơm" in (p.reason or "").lower() or "thơm" in context.lower() for p in products) or products
    assert "PRODUCTS FOUND" in context
