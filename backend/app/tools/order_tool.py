"""Authenticated order tool adapter."""

from typing import Optional
from backend.app.repositories.order_repository import OrderRepository
from backend.app.schemas.chat import OrderStatusResponse


def get_order_status_tool(
    repo: OrderRepository,
    user_id: int,
    order_code: str,
) -> Optional[OrderStatusResponse]:
    """Retrieve order status strictly enforcing user ownership."""
    return repo.get_order_status(user_id=user_id, order_code=order_code)
