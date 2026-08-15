"""Tests for authoritative ProductRepository search and filtering."""

import pytest
from sqlalchemy.orm import Session
from backend.app.repositories.product_repository import ProductRepository
from backend.app.schemas.product import ProductSearchParams


def test_effective_price_precedence(db_session: Session):
    """Verify sale price takes precedence over regular price in effective_price."""
    repo = ProductRepository(db_session)
    params = ProductSearchParams(category="cà phê", max_price=240000, in_stock=True)
    products = repo.search_products(params)

    assert len(products) > 0
    # Arabica Cầu Đất regular price is 260k, sale price is 239k -> should be returned under 240k
    arabica = next((p for p in products if p.id == 1), None)
    assert arabica is not None
    assert arabica.effective_price == 239000.0
    assert arabica.sale_price == 239000.0
    assert arabica.price == 260000.0


def test_inactive_and_out_of_stock_filtering(db_session: Session):
    """Verify out of stock products are excluded when in_stock=True."""
    repo = ProductRepository(db_session)
    # Product 16 is OUT_OF_STOCK with stock = 0
    params_in_stock = ProductSearchParams(query="Honey Process", in_stock=True)
    results = repo.search_products(params_in_stock)
    assert len(results) == 0

    # When in_stock=False, inactive or out-of-stock might still be excluded by status = 'ACTIVE'
    params_all = ProductSearchParams(query="Honey Process", in_stock=False)
    results_all = repo.search_products(params_all)
    # Status is OUT_OF_STOCK so status = 'ACTIVE' filters it out
    assert len(results_all) == 0


def test_category_and_origin_filter(db_session: Session):
    """Verify filtering by category and origin."""
    repo = ProductRepository(db_session)
    params = ProductSearchParams(category="trà", origin="hà giang")
    products = repo.search_products(params)

    assert len(products) == 1
    assert products[0].id == 5
    assert "Shan Tuyết" in products[0].name
    assert "Hà Giang" in products[0].origin


def test_price_range_filter(db_session: Session):
    """Verify min_price and max_price bounds."""
    repo = ProductRepository(db_session)
    params = ProductSearchParams(min_price=500000, max_price=900000)
    products = repo.search_products(params)

    assert len(products) >= 2
    for p in products:
        assert 500000 <= p.effective_price <= 900000
