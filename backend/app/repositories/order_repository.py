"""Order Repository enforcing authenticated user ownership in SQL."""

from typing import Optional, Dict, Any, List
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.schemas.chat import OrderStatusResponse


class OrderRepository:
    """Repository managing customer order status lookups with strict ownership predicates."""

    def __init__(self, session: Session):
        self.session = session

    def get_order_status(
        self, user_id: int, order_code: str
    ) -> Optional[OrderStatusResponse]:
        """Look up order status enforcing `user_id` match directly in the SQL WHERE clause."""
        sql = """
            SELECT
                id,
                order_code,
                user_id,
                total_amount,
                order_status,
                payment_status,
                created_at
            FROM orders
            WHERE order_code = :order_code AND user_id = :user_id
            LIMIT 1
        """
        row = self.session.execute(
            text(sql), {"order_code": order_code.strip(), "user_id": user_id}
        ).fetchone()

        if not row:
            return None

        # Fetch status history
        hist_sql = """
            SELECT
                status,
                notes,
                created_at
            FROM order_status_history
            WHERE order_id = :order_id
            ORDER BY created_at ASC
        """
        hist_rows = self.session.execute(text(hist_sql), {"order_id": row.id}).fetchall()
        history_list = [
            {
                "status": h.status,
                "notes": h.notes,
                "created_at": str(h.created_at),
            }
            for h in hist_rows
        ]

        return OrderStatusResponse(
            order_code=row.order_code,
            order_status=row.order_status,
            payment_status=row.payment_status,
            created_at=row.created_at,
            status_history=history_list,
        )
