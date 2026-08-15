"""Tests for inventory calculation, product details, and active certificates."""

import pytest
from sqlalchemy.orm import Session
from backend.app.repositories.product_repository import ProductRepository


def test_inventory_summing(db_session: Session):
    """Verify stock is computed from inventories.available_quantity."""
    repo = ProductRepository(db_session)
    stock_info = repo.get_stock(product_id=1)
    assert stock_info["product_id"] == 1
    assert stock_info["available_quantity"] == 85
    assert stock_info["is_available"] is True


def test_product_detail_with_active_certificates(db_session: Session):
    """Verify product detail returns active certificates and full metadata."""
    repo = ProductRepository(db_session)
    detail = repo.get_by_id(product_id=1)

    assert detail is not None
    assert detail.name == "Cà phê Arabica Cầu Đất 500g"
    assert detail.available_quantity == 85
    assert detail.is_available is True
    assert detail.ingredients is not None
    assert detail.taste_profile is not None
    assert len(detail.certificates) == 2

    # Check certificate status is ACTIVE
    for cert in detail.certificates:
        assert cert["status"] == "ACTIVE"
        assert cert["certificate_code"] is not None


def test_unknown_product_returns_none(db_session: Session):
    """Verify unknown product ID returns None safely without raising errors."""
    repo = ProductRepository(db_session)
    detail = repo.get_by_id(product_id=9999)
    assert detail is None


def test_resolve_product_by_name(db_session: Session):
    """Verify substring resolution of product names."""
    repo = ProductRepository(db_session)
    card = repo.resolve_by_name("Arabica")
    assert card is not None
    assert card.id == 1

    card2 = repo.resolve_by_name("Robusta")
    assert card2 is not None
    assert card2.id == 2
