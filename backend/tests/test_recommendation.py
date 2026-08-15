"""Tests for hybrid recommendation preserving MySQL hard filters."""

import pytest
from sqlalchemy.orm import Session
from backend.app.repositories.product_repository import ProductRepository
from backend.app.services.recommendation_service import RecommendationService


def test_recommendation_preserves_budget(db_session: Session):
    """Verify hybrid recommendation strictly respects max_price."""
    repo = ProductRepository(db_session)
    service = RecommendationService(repo)

    products, _ = service.recommend(
        category="cà phê",
        max_price=200000,
        preferences="thơm ngon đặc biệt",
        in_stock=True,
    )

    assert len(products) >= 1
    for p in products:
        assert p.effective_price <= 200000.0


def test_recommendation_preserves_in_stock(db_session: Session):
    """Verify hybrid recommendation excludes out of stock products."""
    repo = ProductRepository(db_session)
    service = RecommendationService(repo)

    products, _ = service.recommend(
        category="cà phê",
        in_stock=True,
    )

    for p in products:
        assert p.available_quantity > 0
        assert p.is_available is True
        assert p.id != 16  # 16 is OUT_OF_STOCK


def test_recommendation_empty_when_no_candidates(db_session: Session):
    """Verify recommendation returns empty list when budget is too low."""
    repo = ProductRepository(db_session)
    service = RecommendationService(repo)

    products, _ = service.recommend(
        category="cà phê",
        max_price=50000,  # No coffee under 50k
        in_stock=True,
    )
    assert len(products) == 0
