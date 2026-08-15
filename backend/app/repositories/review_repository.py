"""Review Repository filtering strictly for approved customer reviews."""

from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session


class ReviewRepository:
    """Repository managing customer product reviews."""

    def __init__(self, session: Session):
        self.session = session

    def get_product_reviews(
        self, product_id: int, limit: int = 5
    ) -> Dict[str, Any]:
        """Fetch only APPROVED reviews with customer-safe fields and summary ratings."""
        bounded_limit = max(1, min(limit, 10))

        sql = """
            SELECT
                r.id,
                r.rating,
                r.title,
                r.content,
                r.created_at,
                u.full_name AS reviewer_name
            FROM reviews r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.product_id = :product_id AND r.status = 'APPROVED'
            ORDER BY r.created_at DESC
            LIMIT :limit
        """
        rows = self.session.execute(
            text(sql), {"product_id": product_id, "limit": bounded_limit}
        ).fetchall()

        reviews_list = [
            {
                "id": r.id,
                "rating": r.rating,
                "title": r.title,
                "content": r.content,
                "created_at": str(r.created_at),
                "reviewer_name": r.reviewer_name or "Khách hàng",
            }
            for r in rows
        ]

        # Calculate summary statistics
        agg_sql = """
            SELECT
                COUNT(*) AS total_count,
                COALESCE(AVG(rating), 0.0) AS avg_rating
            FROM reviews
            WHERE product_id = :product_id AND status = 'APPROVED'
        """
        agg_row = self.session.execute(text(agg_sql), {"product_id": product_id}).fetchone()
        total_count = int(agg_row.total_count) if agg_row else 0
        avg_rating = round(float(agg_row.avg_rating), 1) if agg_row else 0.0

        return {
            "product_id": product_id,
            "average_rating": avg_rating,
            "review_count": total_count,
            "reviews": reviews_list,
        }
