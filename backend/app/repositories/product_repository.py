"""Authoritative MySQL Product Repository with parameterized queries."""

import json
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.schemas.product import ProductCard, ProductDetailResponse, ProductSearchParams


class ProductRepository:
    """Repository handling all product and inventory database access."""

    def __init__(self, session: Session):
        self.session = session

    def search_products(self, params: ProductSearchParams) -> List[ProductCard]:
        """Search active products with bounded filters, effective price and inventory check."""
        conditions = ["p.status = 'ACTIVE'"]
        bind_params: Dict[str, Any] = {}

        if params.category:
            # Match the category table only; a product-name fallback pass runs
            # separately so name mentions never leak other categories in.
            conditions.append(
                "(LOWER(c.name) LIKE :category OR LOWER(c.slug) LIKE :category_slug)"
            )
            cat_clean = f"%{params.category.strip().lower()}%"
            bind_params["category"] = cat_clean
            bind_params["category_slug"] = cat_clean

        if params.brand:
            conditions.append("LOWER(b.name) LIKE :brand")
            bind_params["brand"] = f"%{params.brand.strip().lower()}%"

        if params.origin:
            conditions.append("LOWER(p.origin) LIKE :origin")
            bind_params["origin"] = f"%{params.origin.strip().lower()}%"

        if params.query:
            conditions.append("(LOWER(p.name) LIKE :query OR LOWER(p.description) LIKE :query)")
            bind_params["query"] = f"%{params.query.strip().lower()}%"

        if params.min_price is not None:
            conditions.append("COALESCE(p.sale_price, p.price) >= :min_price")
            bind_params["min_price"] = params.min_price

        if params.max_price is not None:
            conditions.append("COALESCE(p.sale_price, p.price) <= :max_price")
            bind_params["max_price"] = params.max_price

        having_clause = ""
        if params.in_stock:
            having_clause = "HAVING available_quantity > 0"

        limit = max(1, min(params.limit, 10))
        bind_params["limit"] = limit

        where_str = " AND ".join(conditions)

        sql = f"""
            SELECT
                p.id,
                p.name,
                p.price,
                p.sale_price,
                COALESCE(p.sale_price, p.price) AS effective_price,
                p.origin,
                COALESCE(img.image_url, '') AS image_url,
                COALESCE(SUM(inv.available_quantity), 0) AS available_quantity
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN brands b ON p.brand_id = b.id
            LEFT JOIN product_images img ON p.id = img.product_id AND img.is_primary = 1
            LEFT JOIN inventories inv ON p.id = inv.product_id
            WHERE {where_str}
            GROUP BY p.id, p.name, p.price, p.sale_price, p.origin, img.image_url
            {having_clause}
            ORDER BY effective_price ASC
            LIMIT :limit
        """

        rows = self.session.execute(text(sql), bind_params).fetchall()
        results = []
        for r in rows:
            qty = int(r.available_quantity)
            results.append(
                ProductCard(
                    id=r.id,
                    name=r.name,
                    price=float(r.price),
                    sale_price=float(r.sale_price) if r.sale_price is not None else None,
                    effective_price=float(r.effective_price),
                    origin=r.origin,
                    available_quantity=qty,
                    is_available=qty > 0,
                    image_url=r.image_url or None,
                )
            )
        return results

    def get_by_id(self, product_id: int) -> Optional[ProductDetailResponse]:
        """Fetch full product details, active certificates and inventory."""
        sql = """
            SELECT
                p.id,
                p.name,
                p.slug,
                p.description,
                p.category_id,
                c.name AS category_name,
                p.brand_id,
                b.name AS brand_name,
                p.price,
                p.sale_price,
                COALESCE(p.sale_price, p.price) AS effective_price,
                p.origin,
                COALESCE(img.image_url, '') AS image_url,
                COALESCE(SUM(inv.available_quantity), 0) AS available_quantity,
                pd.ingredients,
                pd.taste_profile,
                pd.key_benefits,
                pd.suitable_for,
                pd.usage_instructions,
                pd.storage_instructions,
                pd.shelf_life,
                pd.producer_name,
                pd.production_area,
                pd.product_story,
                pd.extra_attributes
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN brands b ON p.brand_id = b.id
            LEFT JOIN product_images img ON p.id = img.product_id AND img.is_primary = 1
            LEFT JOIN inventories inv ON p.id = inv.product_id
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.id = :product_id AND p.status = 'ACTIVE'
            GROUP BY
                p.id, p.name, p.slug, p.description, p.category_id, c.name,
                p.brand_id, b.name, p.price, p.sale_price, p.origin, img.image_url,
                pd.ingredients, pd.taste_profile, pd.key_benefits, pd.suitable_for,
                pd.usage_instructions, pd.storage_instructions, pd.shelf_life,
                pd.producer_name, pd.production_area, pd.product_story, pd.extra_attributes
        """
        row = self.session.execute(text(sql), {"product_id": product_id}).fetchone()
        if not row:
            return None

        # Fetch only ACTIVE certificates
        cert_sql = """
            SELECT
                id,
                name,
                issuer,
                certificate_code,
                issued_at,
                expires_at,
                description,
                status
            FROM product_certificates
            WHERE product_id = :product_id AND status = 'ACTIVE'
            ORDER BY id ASC
        """
        cert_rows = self.session.execute(text(cert_sql), {"product_id": product_id}).fetchall()
        certs = [
            {
                "id": c.id,
                "name": c.name,
                "issuer": c.issuer,
                "certificate_code": c.certificate_code,
                "issued_at": str(c.issued_at) if c.issued_at else None,
                "expires_at": str(c.expires_at) if c.expires_at else None,
                "description": c.description,
                "status": c.status,
            }
            for c in cert_rows
        ]

        extra = None
        if row.extra_attributes:
            extra = json.loads(row.extra_attributes) if isinstance(row.extra_attributes, str) else row.extra_attributes

        qty = int(row.available_quantity)
        return ProductDetailResponse(
            id=row.id,
            name=row.name,
            slug=row.slug,
            description=row.description,
            category_id=row.category_id,
            category_name=row.category_name,
            brand_id=row.brand_id,
            brand_name=row.brand_name,
            price=float(row.price),
            sale_price=float(row.sale_price) if row.sale_price is not None else None,
            effective_price=float(row.effective_price),
            origin=row.origin,
            image_url=row.image_url or None,
            available_quantity=qty,
            is_available=qty > 0,
            ingredients=row.ingredients,
            taste_profile=row.taste_profile,
            key_benefits=row.key_benefits,
            suitable_for=row.suitable_for,
            usage_instructions=row.usage_instructions,
            storage_instructions=row.storage_instructions,
            shelf_life=row.shelf_life,
            producer_name=row.producer_name,
            production_area=row.production_area,
            product_story=row.product_story,
            extra_attributes=extra,
            certificates=certs,
        )

    def get_stock(self, product_id: int) -> Dict[str, Any]:
        """Compute available inventory stock for a product."""
        sql = """
            SELECT COALESCE(SUM(available_quantity), 0) AS total_stock
            FROM inventories
            WHERE product_id = :product_id
        """
        row = self.session.execute(text(sql), {"product_id": product_id}).fetchone()
        qty = int(row.total_stock) if row else 0
        return {
            "product_id": product_id,
            "available_quantity": qty,
            "is_available": qty > 0,
        }

    def resolve_by_name(self, name: str) -> Optional[ProductCard]:
        """Resolve a product by approximate/substring name search."""
        target = (name or "").strip().lower()
        if not target:
            return None
        # Fetch active products and score by token overlap or exact substring
        sql = """
            SELECT
                p.id,
                p.name,
                p.price,
                p.sale_price,
                COALESCE(p.sale_price, p.price) AS effective_price,
                p.origin,
                COALESCE(img.image_url, '') AS image_url,
                COALESCE(SUM(inv.available_quantity), 0) AS available_quantity
            FROM products p
            LEFT JOIN product_images img ON p.id = img.product_id AND img.is_primary = 1
            LEFT JOIN inventories inv ON p.id = inv.product_id
            WHERE p.status = 'ACTIVE'
            GROUP BY p.id, p.name, p.price, p.sale_price, p.origin, img.image_url
        """
        rows = self.session.execute(text(sql)).fetchall()
        best_card = None
        best_score = 0

        target_tokens = set(target.split())
        for row in rows:
            prod_name_lower = row.name.lower()
            if target in prod_name_lower:
                qty = int(row.available_quantity)
                return ProductCard(
                    id=row.id,
                    name=row.name,
                    price=float(row.price),
                    sale_price=float(row.sale_price) if row.sale_price is not None else None,
                    effective_price=float(row.effective_price),
                    origin=row.origin,
                    available_quantity=qty,
                    is_available=qty > 0,
                    image_url=row.image_url or None,
                )

            # Score token overlap
            prod_tokens = set(prod_name_lower.split())
            overlap = len(target_tokens.intersection(prod_tokens))
            if overlap > best_score:
                best_score = overlap
                qty = int(row.available_quantity)
                best_card = ProductCard(
                    id=row.id,
                    name=row.name,
                    price=float(row.price),
                    sale_price=float(row.sale_price) if row.sale_price is not None else None,
                    effective_price=float(row.effective_price),
                    origin=row.origin,
                    available_quantity=qty,
                    is_available=qty > 0,
                    image_url=row.image_url or None,
                )

        return best_card if best_score > 0 else None

    def get_by_ids(self, product_ids: List[int]) -> List[ProductCard]:
        """Fetch multiple products by explicit ID list."""
        if not product_ids:
            return []
        placeholders = ", ".join(f":id_{i}" for i in range(len(product_ids)))
        bind_params = {f"id_{i}": pid for i, pid in enumerate(product_ids)}
        sql = f"""
            SELECT
                p.id,
                p.name,
                p.price,
                p.sale_price,
                COALESCE(p.sale_price, p.price) AS effective_price,
                p.origin,
                COALESCE(img.image_url, '') AS image_url,
                COALESCE(SUM(inv.available_quantity), 0) AS available_quantity
            FROM products p
            LEFT JOIN product_images img ON p.id = img.product_id AND img.is_primary = 1
            LEFT JOIN inventories inv ON p.id = inv.product_id
            WHERE p.id IN ({placeholders}) AND p.status = 'ACTIVE'
            GROUP BY p.id, p.name, p.price, p.sale_price, p.origin, img.image_url
        """
        rows = self.session.execute(text(sql), bind_params).fetchall()
        id_map = {}
        for r in rows:
            qty = int(r.available_quantity)
            id_map[r.id] = ProductCard(
                id=r.id,
                name=r.name,
                price=float(r.price),
                sale_price=float(r.sale_price) if r.sale_price is not None else None,
                effective_price=float(r.effective_price),
                origin=r.origin,
                available_quantity=qty,
                is_available=qty > 0,
                image_url=r.image_url or None,
            )
        # Preserve input ordering
        return [id_map[pid] for pid in product_ids if pid in id_map]
