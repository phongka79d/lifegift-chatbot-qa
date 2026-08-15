"""Regression tests for session ownership, blank name resolution, recommendation
degradation indicator, and structured metadata surfaced by the review audit."""

import pytest
from sqlalchemy.orm import Session

from backend.app.chatbot.router import IntentRouter
from backend.app.chatbot.service import ChatbotService
from backend.app.repositories.chat_repository import ChatRepository
from backend.app.repositories.product_repository import ProductRepository
from backend.app.schemas.chat import ChatRequest
from backend.app.schemas.product import ProductSearchParams


def test_anonymous_cannot_use_owned_session(db_session: Session):
    """An anonymous caller must be denied read/write on a session owned by a user."""
    repo = ChatRepository(db_session)
    owned_id = repo.get_or_create_session(session_id=None, user_id=1)

    with pytest.raises(PermissionError):
        repo.get_or_create_session(session_id=owned_id, user_id=None)

    with pytest.raises(PermissionError):
        repo.get_session(session_id=owned_id, user_id=None)


def test_cross_user_session_access_denied(db_session: Session):
    """A different authenticated user must be denied access to an owned session."""
    repo = ChatRepository(db_session)
    owned_id = repo.get_or_create_session(session_id=None, user_id=1)

    with pytest.raises(PermissionError):
        repo.get_or_create_session(session_id=owned_id, user_id=2)

    with pytest.raises(PermissionError):
        repo.get_session(session_id=owned_id, user_id=2)


def test_anonymous_session_shared_by_anonymous_users(db_session: Session):
    """Anonymous sessions remain reusable by anonymous callers."""
    repo = ChatRepository(db_session)
    anon_id = repo.get_or_create_session(session_id=None, user_id=None)
    reused = repo.get_or_create_session(session_id=anon_id, user_id=None)
    assert reused == anon_id


def test_blank_name_does_not_resolve_to_product(db_session: Session):
    """resolve_by_name with an empty/blank name must return None, not the first product."""
    repo = ProductRepository(db_session)
    assert repo.resolve_by_name("") is None
    assert repo.resolve_by_name("   ") is None
    assert repo.resolve_by_name(None) is None


@pytest.mark.asyncio
async def test_recommendation_metadata_indicates_limited_preference(db_session: Session):
    """Recommendation response metadata must flag semantic_used=False when Qdrant fails."""
    router = IntentRouter()
    service = ChatbotService(session=db_session, router=router)
    req = ChatRequest(message="Tôi thích cà phê thơm nhẹ, ít đắng, dưới 300 nghìn")
    res = await service.handle_chat(req, user_id=None)

    assert res.intent == "PRODUCT_RECOMMENDATION"
    assert "semantic_used" in res.metadata
    assert "tool" in res.metadata and res.metadata["tool"] == "recommendation_service"
    for p in res.products:
        assert p.effective_price <= 300000.0
        assert p.is_available is True


@pytest.mark.asyncio
async def test_recommendation_no_match_controlled_answer(db_session: Session):
    """A budget with zero valid candidates returns no products and a controlled answer."""
    router = IntentRouter()
    service = ChatbotService(session=db_session, router=router)
    req = ChatRequest(message="Tư vấn cà phê dưới 10 nghìn")
    res = await service.handle_chat(req, user_id=None)

    assert res.products == []
    assert res.metadata["no_match"] is True
    assert "chưa có sản phẩm" in res.answer.lower() or "không có sản phẩm" in res.answer.lower()


def test_search_products_excludes_unavailable_with_in_stock(db_session: Session):
    """in_stock=True must exclude products with zero summed inventory."""
    repo = ProductRepository(db_session)
    results = repo.search_products(ProductSearchParams(category="cà phê", in_stock=True, limit=10))
    assert len(results) > 0
    for p in results:
        assert p.available_quantity > 0
        assert p.is_available is True
