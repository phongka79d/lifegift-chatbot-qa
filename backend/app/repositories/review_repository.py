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

        reviews_list = []
        for r in rows:
            name = r.reviewer_name or "Khách hàng"
            body = r.content or r.title or ""
            reviews_list.append(
                {
                    "id": r.id,
                    "rating": r.rating,
                    "title": r.title,
                    "content": r.content,
                    "comment": body,
                    "created_at": str(r.created_at),
                    "reviewer_name": name,
                    "user_name": name,
                    "is_verified_purchase": True,
                }
            )

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
            "total_reviews": total_count,
            "reviews": reviews_list,
        }

    def list_reviewed_products(
        self,
        review_text: Optional[str] = None,
        category_id: Optional[int] = None,
        min_avg_rating: Optional[float] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Active products that have APPROVED reviews, optionally matching review text."""
        bounded_limit = max(1, min(limit, 10))
        conditions = [
            "p.status = 'ACTIVE'",
            "r.status = 'APPROVED'",
        ]
        params: Dict[str, Any] = {"limit": bounded_limit}
        if category_id is not None:
            conditions.append("p.category_id = :category_id")
            params["category_id"] = category_id
        theme = (review_text or "").strip()
        if theme:
            conditions.append(
                "(LOWER(r.title) LIKE :theme OR LOWER(r.content) LIKE :theme)"
            )
            params["theme"] = f"%{theme.lower()}%"

        having = ""
        if min_avg_rating is not None:
            having = "HAVING AVG(r.rating) >= :min_avg_rating"
            params["min_avg_rating"] = float(min_avg_rating)

        where_sql = " AND ".join(conditions)
        id_sql = f"""
            SELECT p.id AS product_id,
                   COUNT(r.id) AS review_count,
                   AVG(r.rating) AS avg_rating
            FROM products p
            INNER JOIN reviews r ON r.product_id = p.id
            WHERE {where_sql}
            GROUP BY p.id
            {having}
            ORDER BY avg_rating DESC, review_count DESC, p.id ASC
            LIMIT :limit
        """
        id_rows = self.session.execute(text(id_sql), params).fetchall()
        results: List[Dict[str, Any]] = []
        for row in id_rows:
            sample_params: Dict[str, Any] = {"product_id": int(row.product_id)}
            sample_where = "product_id = :product_id AND status = 'APPROVED'"
            if theme:
                sample_where += " AND (LOWER(title) LIKE :theme OR LOWER(content) LIKE :theme)"
                sample_params["theme"] = params["theme"]
            sample = self.session.execute(
                text(
                    f"""
                    SELECT rating, title, content
                    FROM reviews
                    WHERE {sample_where}
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                sample_params,
            ).fetchone()
            results.append(
                {
                    "product_id": int(row.product_id),
                    "review_count": int(row.review_count),
                    "avg_rating": round(float(row.avg_rating or 0), 2),
                    "sample_rating": int(sample.rating) if sample else None,
                    "sample_title": sample.title if sample else None,
                    "sample_content": sample.content if sample else None,
                }
            )
        return results
