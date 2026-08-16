"""Apply catalog consistency fixes against live MySQL (idempotent)."""
from sqlalchemy import text

from backend.app.core.database import get_db_context

CATEGORY_FALLBACK_IMAGES = {
    4: "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=600&auto=format&fit=crop&q=80",
    5: "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=600&auto=format&fit=crop&q=80",
    6: "https://images.unsplash.com/photo-1508061253366-f7da158b6d46?w=600&auto=format&fit=crop&q=80",
    7: "https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=600&auto=format&fit=crop&q=80",
    8: "https://images.unsplash.com/photo-1513885535751-8b9238bd345a?w=600&auto=format&fit=crop&q=80",
}
DEFAULT_FALLBACK = (
    "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=600&auto=format&fit=crop&q=80"
)


def main() -> None:
    statements = [
        """
        UPDATE categories
        SET status = 'INACTIVE'
        WHERE id IN (1, 2, 3)
          AND NOT EXISTS (
              SELECT 1 FROM products p
              WHERE p.category_id = categories.id AND p.status = 'ACTIVE'
          )
        """,
        """
        UPDATE product_certificates
        SET product_id = 2
        WHERE id IN (1, 2) AND product_id <> 2
        """,
        """
        UPDATE product_certificates
        SET product_id = 3
        WHERE id = 3
          AND (name LIKE '%Shan Tuyết%' OR description LIKE '%Shan Tuyết%' OR description LIKE '%trà%')
        """,
        """
        UPDATE product_certificates
        SET status = 'REVOKED'
        WHERE id = 4
          AND (name LIKE '%U Minh%' OR description LIKE '%U Minh%')
        """,
        """
        UPDATE products
        SET name = 'Nấm hương rừng khô 300g'
        WHERE id = 31 AND weight = 300 AND name = 'Nấm hương rừng khô 250g'
        """,
        """
        UPDATE products
        SET name = 'Trà Shan Tuyết cổ thụ 200g Hà Giang'
        WHERE id = 3 AND origin = 'Hà Giang' AND name = 'Trà Shan Tuyết cổ thụ 200g'
        """,
        """
        UPDATE products
        SET name = 'Trà Shan Tuyết cổ thụ 200g Sơn La'
        WHERE id = 57 AND origin = 'Sơn La' AND name = 'Trà Shan Tuyết cổ thụ 200g'
        """,
    ]

    with get_db_context() as session:
        for stmt in statements:
            session.execute(text(stmt))
        session.commit()

        products = session.execute(
            text("SELECT id, category_id FROM products WHERE status='ACTIVE'")
        ).fetchall()
        updated = 0
        for p in products:
            http = session.execute(
                text(
                    """
                    SELECT id FROM product_images
                    WHERE product_id = :pid AND image_url LIKE 'http%'
                    ORDER BY is_primary DESC, id ASC
                    LIMIT 1
                    """
                ),
                {"pid": p.id},
            ).fetchone()
            if http:
                session.execute(
                    text("UPDATE product_images SET is_primary = 0 WHERE product_id = :pid"),
                    {"pid": p.id},
                )
                session.execute(
                    text("UPDATE product_images SET is_primary = 1 WHERE id = :id"),
                    {"id": http.id},
                )
                updated += 1
                continue
            fallback = CATEGORY_FALLBACK_IMAGES.get(int(p.category_id or 0), DEFAULT_FALLBACK)
            primary = session.execute(
                text(
                    """
                    SELECT id FROM product_images
                    WHERE product_id = :pid
                    ORDER BY is_primary DESC, id ASC
                    LIMIT 1
                    """
                ),
                {"pid": p.id},
            ).fetchone()
            if primary:
                session.execute(
                    text("UPDATE product_images SET image_url = :url, is_primary = 1 WHERE id = :id"),
                    {"url": fallback, "id": primary.id},
                )
            else:
                session.execute(
                    text(
                        """
                        INSERT INTO product_images (product_id, image_url, is_primary, sort_order)
                        VALUES (:pid, :url, 1, 0)
                        """
                    ),
                    {"pid": p.id, "url": fallback},
                )
            updated += 1
        session.commit()

        print("sql statements", len(statements))
        print("image rows adjusted", updated)
        rows = session.execute(
            text(
                """
                SELECT c.id, p.name, c.name AS cert, c.status
                FROM product_certificates c
                JOIN products p ON p.id = c.product_id
                ORDER BY c.id
                """
            )
        ).fetchall()
        for r in rows:
            print(dict(r._mapping))
        print(
            "empty active cats",
            session.execute(
                text(
                    """
                    SELECT COUNT(*) FROM categories c
                    WHERE c.status='ACTIVE'
                      AND NOT EXISTS (
                        SELECT 1 FROM products p
                        WHERE p.category_id=c.id AND p.status='ACTIVE'
                      )
                    """
                )
            ).scalar(),
        )
        print(
            "dup names",
            session.execute(
                text("SELECT COUNT(*) FROM (SELECT name FROM products GROUP BY name HAVING COUNT(*)>1) t")
            ).scalar(),
        )
        print(
            "http primaries",
            session.execute(
                text(
                    "SELECT COUNT(*) FROM product_images WHERE is_primary=1 AND image_url LIKE 'http%'"
                )
            ).scalar(),
        )


if __name__ == "__main__":
    main()
