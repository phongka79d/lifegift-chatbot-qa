"""Import product catalog JSON into LifeGift MySQL.

Scope: categories, brands, warehouses, products (+ new catalog columns),
product_images, inventories, product_details.

Usage:
  python -m backend.scripts.import_catalog_json
  python -m backend.scripts.import_catalog_json --json backend/data/lifegift_catalog_import.json
  python -m backend.scripts.import_catalog_json --purge-other-products
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from backend.app.core.database import get_db_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_JSON = Path(__file__).resolve().parent.parent / "data" / "lifegift_catalog_import.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _exec_many(session, sql: str, rows: List[Dict[str, Any]], label: str) -> int:
    for row in rows:
        session.execute(text(sql), row)
    logger.info("Upserted %s %s", len(rows), label)
    return len(rows)


def import_catalog(payload: Dict[str, Any], *, purge_other_products: bool = False) -> Dict[str, int]:
    categories = payload.get("categories") or []
    brands = payload.get("brands") or []
    warehouses = payload.get("warehouses") or []
    products = payload.get("products") or []
    inventories = payload.get("inventories") or []
    stats: Dict[str, int] = {}

    with get_db_context() as session:
        stats["categories"] = _exec_many(
            session,
            """
            INSERT INTO categories (id, name, slug, status)
            VALUES (:id, :name, :slug, :status)
            ON DUPLICATE KEY UPDATE name=VALUES(name), slug=VALUES(slug), status=VALUES(status)
            """,
            categories,
            "categories",
        )

        stats["brands"] = _exec_many(
            session,
            """
            INSERT INTO brands (id, name, status)
            VALUES (:id, :name, :status)
            ON DUPLICATE KEY UPDATE name=VALUES(name), status=VALUES(status)
            """,
            brands,
            "brands",
        )

        stats["warehouses"] = _exec_many(
            session,
            """
            INSERT INTO warehouses (id, name, status)
            VALUES (:id, :name, :status)
            ON DUPLICATE KEY UPDATE name=VALUES(name), status=VALUES(status)
            """,
            warehouses,
            "warehouses",
        )

        product_rows = []
        for p in products:
            product_rows.append(
                {
                    "id": p["id"],
                    "category_id": p.get("category_id"),
                    "brand_id": p.get("brand_id"),
                    "sku": p.get("sku"),
                    "name": p["name"],
                    "slug": p["slug"],
                    "description": p.get("description"),
                    "short_description": p.get("short_description"),
                    "price": p["price"],
                    "sale_price": p.get("sale_price"),
                    "unit": p.get("unit"),
                    "weight": p.get("weight"),
                    "origin": p.get("origin"),
                    "pricing_type": p.get("pricing_type") or "FIXED_PRICE",
                    "stock_status": p.get("stock_status"),
                    "is_featured": 1 if p.get("is_featured") else 0,
                    "status": p.get("status") or "ACTIVE",
                }
            )

        stats["products"] = _exec_many(
            session,
            """
            INSERT INTO products (
                id, category_id, brand_id, sku, name, slug, description, short_description,
                price, sale_price, unit, weight, origin, pricing_type, stock_status, is_featured, status
            ) VALUES (
                :id, :category_id, :brand_id, :sku, :name, :slug, :description, :short_description,
                :price, :sale_price, :unit, :weight, :origin, :pricing_type, :stock_status, :is_featured, :status
            )
            ON DUPLICATE KEY UPDATE
                category_id=VALUES(category_id),
                brand_id=VALUES(brand_id),
                sku=VALUES(sku),
                name=VALUES(name),
                slug=VALUES(slug),
                description=VALUES(description),
                short_description=VALUES(short_description),
                price=VALUES(price),
                sale_price=VALUES(sale_price),
                unit=VALUES(unit),
                weight=VALUES(weight),
                origin=VALUES(origin),
                pricing_type=VALUES(pricing_type),
                stock_status=VALUES(stock_status),
                is_featured=VALUES(is_featured),
                status=VALUES(status)
            """,
            product_rows,
            "products",
        )

        image_count = 0
        for p in products:
            images = p.get("images") or []
            if not images:
                continue
            session.execute(
                text("DELETE FROM product_images WHERE product_id = :product_id"),
                {"product_id": p["id"]},
            )
            for idx, img in enumerate(images):
                session.execute(
                    text(
                        """
                        INSERT INTO product_images (product_id, image_url, is_primary, sort_order)
                        VALUES (:product_id, :image_url, :is_primary, :sort_order)
                        """
                    ),
                    {
                        "product_id": p["id"],
                        "image_url": img["image_url"],
                        "is_primary": 1 if img.get("is_primary") or idx == 0 else 0,
                        "sort_order": img.get("sort_order", idx),
                    },
                )
                image_count += 1
        stats["product_images"] = image_count
        logger.info("Upserted %s product_images", image_count)

        inv_rows = []
        if inventories:
            for inv in inventories:
                inv_rows.append(
                    {
                        "product_id": inv["product_id"],
                        "warehouse_id": inv.get("warehouse_id") or 1,
                        "available_quantity": inv.get("available_quantity", 0),
                        "reserved_quantity": inv.get("reserved_quantity", 0),
                    }
                )
        else:
            for p in products:
                inv_rows.append(
                    {
                        "product_id": p["id"],
                        "warehouse_id": 1,
                        "available_quantity": p.get("stock", 0),
                        "reserved_quantity": 0,
                    }
                )

        stats["inventories"] = _exec_many(
            session,
            """
            INSERT INTO inventories (product_id, warehouse_id, available_quantity, reserved_quantity)
            VALUES (:product_id, :warehouse_id, :available_quantity, :reserved_quantity)
            ON DUPLICATE KEY UPDATE
                available_quantity=VALUES(available_quantity),
                reserved_quantity=VALUES(reserved_quantity)
            """,
            inv_rows,
            "inventories",
        )

        detail_rows = []
        for p in products:
            d = p.get("details") or {}
            extra = d.get("extra_attributes") or {}
            detail_rows.append(
                {
                    "product_id": p["id"],
                    "ingredients": d.get("ingredients"),
                    "taste_profile": d.get("taste_profile"),
                    "key_benefits": d.get("key_benefits"),
                    "suitable_for": d.get("suitable_for"),
                    "usage_instructions": d.get("usage_instructions"),
                    "storage_instructions": d.get("storage_instructions"),
                    "shelf_life": d.get("shelf_life"),
                    "producer_name": d.get("producer_name"),
                    "production_area": d.get("production_area"),
                    "product_story": d.get("product_story"),
                    "extra_attributes": json.dumps(extra, ensure_ascii=False),
                }
            )

        stats["product_details"] = _exec_many(
            session,
            """
            INSERT INTO product_details (
                product_id, ingredients, taste_profile, key_benefits, suitable_for,
                usage_instructions, storage_instructions, shelf_life, producer_name,
                production_area, product_story, extra_attributes
            ) VALUES (
                :product_id, :ingredients, :taste_profile, :key_benefits, :suitable_for,
                :usage_instructions, :storage_instructions, :shelf_life, :producer_name,
                :production_area, :product_story, :extra_attributes
            )
            ON DUPLICATE KEY UPDATE
                ingredients=VALUES(ingredients),
                taste_profile=VALUES(taste_profile),
                key_benefits=VALUES(key_benefits),
                suitable_for=VALUES(suitable_for),
                usage_instructions=VALUES(usage_instructions),
                storage_instructions=VALUES(storage_instructions),
                shelf_life=VALUES(shelf_life),
                producer_name=VALUES(producer_name),
                production_area=VALUES(production_area),
                product_story=VALUES(product_story),
                extra_attributes=VALUES(extra_attributes)
            """,
            detail_rows,
            "product_details",
        )

        if purge_other_products:
            imported_ids = {p["id"] for p in products}
            existing = [
                int(r[0])
                for r in session.execute(text("SELECT id FROM products")).fetchall()
            ]
            deleted = 0
            for pid in existing:
                if pid not in imported_ids:
                    session.execute(text("DELETE FROM products WHERE id = :id"), {"id": pid})
                    deleted += 1
            stats["purged_products"] = deleted
            logger.info("Purged %s products not in import file", deleted)

        for table in ("products", "categories", "brands", "inventories", "product_details"):
            row = session.execute(text(f"SELECT COUNT(*) AS c FROM {table}")).mappings().first()
            stats[f"db_{table}"] = int(row["c"]) if row else 0

    return stats


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Import product catalog JSON into DB")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument(
        "--purge-other-products",
        action="store_true",
        help="Delete DB products whose id is not in the import JSON",
    )
    args = parser.parse_args(argv)

    try:
        payload = _load_json(args.json)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        logger.error("Run: python -m backend.scripts.export_excel_to_json")
        return 1

    logger.info("Importing products from %s", args.json)
    logger.info("Meta: %s", json.dumps(payload.get("meta", {}).get("counts", {}), ensure_ascii=False))

    try:
        stats = import_catalog(payload, purge_other_products=args.purge_other_products)
    except Exception:
        logger.exception("Import failed")
        return 1

    logger.info("Import complete: %s", json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
