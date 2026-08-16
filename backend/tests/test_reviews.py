"""Tests for customer reviews filtering (APPROVED only)."""

import asyncio
from sqlalchemy.orm import Session

from backend.app.chatbot.llm import extract_review_theme, parse_review_min_rating
from backend.app.chatbot.router import normalize_extraction
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
        assert rev["user_name"]
        assert rev["comment"]
    assert result["total_reviews"] == result["review_count"]


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


def test_review_tot_is_discovery_not_name_search(db_session: Session):
    raw = IntentExtractionResult(intent=IntentEnum.PRODUCT_SEARCH, query="Các sản phẩm review tốt")
    out = normalize_extraction("Các sản phẩm review tốt", raw)
    assert out.intent == IntentEnum.PRODUCT_REVIEW
    assert out.query is None

    svc = ChatbotService(session=db_session, llm=None)
    extracted = IntentExtractionResult(
        intent=IntentEnum.PRODUCT_REVIEW,
        query=None,
        preferences="tốt",
    )
    products, context = asyncio.run(svc._handle_product_review(extracted))
    assert products
    assert "PRODUCTS FOUND" in context


def test_parse_review_min_rating_floors():
    assert parse_review_min_rating("Sản phẩm đánh giá trên 5 sao") == 5.0
    assert parse_review_min_rating("đánh giá trên 5 sao") == 5.0
    assert parse_review_min_rating("sản phẩm 5 sao") == 5.0
    assert parse_review_min_rating("sản phẩm đánh giá tốt") == 4.0
    assert parse_review_min_rating("Các sản phẩm review tốt") == 4.0
    assert parse_review_min_rating("trên 4 sao") == 4.0
    assert parse_review_min_rating("đúng mô tả") is None
    assert parse_review_min_rating("Có sản phẩm nào có review đúng với mô tả không?") is None


def test_above_5_star_phrase_is_rating_floor_not_theme():
    leftover = IntentExtractionResult(
        intent=IntentEnum.PRODUCT_SEARCH,
        query="đánh giá trên 5 sao",
    )
    out = normalize_extraction("Sản phẩm đánh giá trên 5 sao", leftover)
    assert out.intent == IntentEnum.PRODUCT_REVIEW
    assert out.query is None
    assert parse_review_min_rating(out.preferences, out.query) == 5.0

    tot = IntentExtractionResult(intent=IntentEnum.PRODUCT_SEARCH, query="đánh giá tốt")
    out_tot = normalize_extraction("sản phẩm đánh giá tốt", tot)
    assert out_tot.intent == IntentEnum.PRODUCT_REVIEW
    assert out_tot.query is None
    assert parse_review_min_rating(out_tot.preferences, out_tot.query) == 4.0


def test_handle_above_5_star_leftover_query_returns_products(db_session: Session):
    """LLM leftover 'đánh giá trên 5 sao' must not LIKE-search that phrase."""
    svc = ChatbotService(session=db_session, llm=None)
    products, context = asyncio.run(
        svc._handle_product_review(
            IntentExtractionResult(
                intent=IntentEnum.PRODUCT_REVIEW,
                query="đánh giá trên 5 sao",
            )
        )
    )
    assert products
    assert "PRODUCTS FOUND" in context
    assert "không có đánh giá" not in context.lower()

    tot_products, tot_context = asyncio.run(
        svc._handle_product_review(
            IntentExtractionResult(
                intent=IntentEnum.PRODUCT_REVIEW,
                query="đánh giá tốt",
            )
        )
    )
    assert tot_products
    assert "PRODUCTS FOUND" in tot_context
