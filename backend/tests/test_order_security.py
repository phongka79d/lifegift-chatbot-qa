"""Tests for order status lookup and authenticated ownership security."""

import pytest
from sqlalchemy.orm import Session
from backend.app.repositories.order_repository import OrderRepository


def test_authenticated_order_lookup_success(db_session: Session):
    """Verify owner can successfully retrieve their own order with status history."""
    repo = OrderRepository(db_session)
    order = repo.get_order_status(user_id=1, order_code="ORD-20260812-0001")

    assert order is not None
    assert order.order_code == "ORD-20260812-0001"
    assert order.order_status == "SHIPPING"
    assert order.payment_status == "PAID"
    assert len(order.status_history) == 3


def test_cross_user_order_denial(db_session: Session):
    """Verify user 2 cannot access user 1's order (returns None)."""
    repo = OrderRepository(db_session)
    # Order ORD-20260812-0001 belongs to User 1
    unauthorized_lookup = repo.get_order_status(user_id=2, order_code="ORD-20260812-0001")
    assert unauthorized_lookup is None


def test_nonexistent_order_returns_none(db_session: Session):
    """Verify non-existent order returns None safely."""
    repo = OrderRepository(db_session)
    result = repo.get_order_status(user_id=1, order_code="ORD-FAKE-9999")
    assert result is None
