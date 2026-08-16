"""Export product catalog from LifeGift FINAL Excel into importable JSON.

Only product-related data is exported:
  categories, brands, warehouses, products, images, inventories, product_details

Usage:
  python -m backend.scripts.export_excel_to_json
  python -m backend.scripts.export_excel_to_json --final PATH --out PATH
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "pandas + openpyxl are required. Install with:\n"
        "  python -m pip install pandas openpyxl"
    ) from exc


DEFAULT_FINAL = Path.home() / "Downloads" / "lifegift_database_FINAL_150_products_clean.xlsx"
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "lifegift_catalog_import.json"


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat(sep=" ") if isinstance(value, (datetime, pd.Timestamp)) else value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return value


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    cleaned = _clean(value)
    if cleaned is None:
        return default
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    cleaned = _clean(value)
    if cleaned is None:
        return default
    try:
        return int(float(cleaned))
    except (TypeError, ValueError):
        return default


def _slugify(text: str, fallback: str = "item") -> str:
    text = (text or "").strip().lower()
    replacements = {
        "à": "a", "á": "a", "ạ": "a", "ả": "a", "ã": "a",
        "â": "a", "ầ": "a", "ấ": "a", "ậ": "a", "ẩ": "a", "ẫ": "a",
        "ă": "a", "ằ": "a", "ắ": "a", "ặ": "a", "ẳ": "a", "ẵ": "a",
        "è": "e", "é": "e", "ẹ": "e", "ẻ": "e", "ẽ": "e",
        "ê": "e", "ề": "e", "ế": "e", "ệ": "e", "ể": "e", "ễ": "e",
        "ì": "i", "í": "i", "ị": "i", "ỉ": "i", "ĩ": "i",
        "ò": "o", "ó": "o", "ọ": "o", "ỏ": "o", "õ": "o",
        "ô": "o", "ồ": "o", "ố": "o", "ộ": "o", "ổ": "o", "ỗ": "o",
        "ơ": "o", "ờ": "o", "ớ": "o", "ợ": "o", "ở": "o", "ỡ": "o",
        "ù": "u", "ú": "u", "ụ": "u", "ủ": "u", "ũ": "u",
        "ư": "u", "ừ": "u", "ứ": "u", "ự": "u", "ử": "u", "ữ": "u",
        "ỳ": "y", "ý": "y", "ỵ": "y", "ỷ": "y", "ỹ": "y",
        "đ": "d",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or fallback


def _unique_slug(base: str, used: Set[str]) -> str:
    slug = _slugify(base)
    if slug not in used:
        used.add(slug)
        return slug
    i = 2
    while f"{slug}-{i}" in used:
        i += 1
    final = f"{slug}-{i}"
    used.add(final)
    return final


def _map_status(raw: Any, stock_status: Any = None, stock_qty: Optional[int] = None) -> str:
    text = str(raw or "ACTIVE").strip().upper()
    if text not in {"ACTIVE", "INACTIVE", "OUT_OF_STOCK"}:
        text = "ACTIVE"
    stock_text = str(stock_status or "").strip().upper()
    if stock_text == "OUT_OF_STOCK" or (stock_qty is not None and stock_qty <= 0 and text == "ACTIVE"):
        if stock_qty is not None and stock_qty <= 0:
            return "OUT_OF_STOCK"
    return text


def build_payload(final_path: Path) -> Dict[str, Any]:
    if not final_path.exists():
        raise FileNotFoundError(f"Excel not found: {final_path}")

    categories_df = pd.read_excel(final_path, sheet_name="categories")
    brands_df = pd.read_excel(final_path, sheet_name="brands")
    products_df = pd.read_excel(final_path, sheet_name="products")
    images_df = pd.read_excel(final_path, sheet_name="product_images")
    inventories_df = pd.read_excel(final_path, sheet_name="inventories")
    warehouses_df = pd.read_excel(final_path, sheet_name="warehouses")

    brand_names = {
        _safe_int(r["id"]): _clean(r.get("name"))
        for r in brands_df.to_dict(orient="records")
        if _clean(r.get("id")) is not None
    }

    categories = [
        {
            "id": _safe_int(r.get("id")),
            "name": _clean(r.get("name")),
            "slug": _clean(r.get("slug")) or _slugify(str(r.get("name") or "category")),
            "status": (_clean(r.get("status")) or "ACTIVE").upper(),
        }
        for r in categories_df.to_dict(orient="records")
        if _clean(r.get("name"))
    ]

    brands = [
        {
            "id": _safe_int(r.get("id")),
            "name": _clean(r.get("name")),
            "status": (_clean(r.get("status")) or "ACTIVE").upper(),
        }
        for r in brands_df.to_dict(orient="records")
        if _clean(r.get("name"))
    ]

    warehouses = [
        {
            "id": _safe_int(r.get("id")),
            "name": _clean(r.get("name")),
            "status": (_clean(r.get("status")) or "ACTIVE").upper(),
        }
        for r in warehouses_df.to_dict(orient="records")
        if _clean(r.get("name"))
    ]
    if not warehouses:
        warehouses = [{"id": 1, "name": "Kho Tổng", "status": "ACTIVE"}]

    stock_by_product: Dict[int, int] = {}
    inventories: List[Dict[str, Any]] = []
    for r in inventories_df.to_dict(orient="records"):
        product_id = _safe_int(r.get("product_id"))
        warehouse_id = _safe_int(r.get("warehouse_id"), 1)
        qty = _safe_int(r.get("quantity") if "quantity" in r else r.get("available_quantity"))
        reserved = _safe_int(r.get("reserved_quantity"))
        stock_by_product[product_id] = stock_by_product.get(product_id, 0) + qty
        inventories.append(
            {
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "available_quantity": qty,
                "reserved_quantity": reserved,
            }
        )

    images_by_product: Dict[int, List[Dict[str, Any]]] = {}
    for r in images_df.to_dict(orient="records"):
        product_id = _safe_int(r.get("product_id"))
        url = _clean(r.get("image_url"))
        if not url:
            continue
        images_by_product.setdefault(product_id, []).append(
            {
                "image_url": url,
                "is_primary": bool(_clean(r.get("is_primary"))),
                "sort_order": _safe_int(r.get("sort_order")),
            }
        )
    for imgs in images_by_product.values():
        imgs.sort(key=lambda x: (0 if x["is_primary"] else 1, x["sort_order"]))

    slug_used: Set[str] = set()
    products: List[Dict[str, Any]] = []
    skipped_zero_price = 0

    for r in products_df.to_dict(orient="records"):
        product_id = _safe_int(r.get("id"))
        name = _clean(r.get("name"))
        if not name:
            continue

        price = _safe_float(r.get("price"), 0.0) or 0.0
        if price <= 0:
            skipped_zero_price += 1
            continue

        sale_raw = _clean(r.get("sale_price"))
        sale_price = _safe_float(sale_raw) if sale_raw is not None else None
        if sale_price is not None and (sale_price <= 0 or sale_price > price):
            sale_price = None

        stock = stock_by_product.get(product_id, 0)
        status = _map_status(r.get("status"), r.get("stock_status"), stock)

        slug = _clean(r.get("slug"))
        if not slug or slug in slug_used:
            slug = _unique_slug(name, slug_used)
        else:
            slug_used.add(slug)

        brand_id = _clean(r.get("brand_id"))
        brand_id = _safe_int(brand_id) if brand_id is not None else None
        category_id = _clean(r.get("category_id"))
        category_id = _safe_int(category_id) if category_id is not None else None

        short_description = _clean(r.get("short_description"))
        description = _clean(r.get("description")) or short_description
        unit = _clean(r.get("unit"))
        weight = _safe_float(r.get("weight"))
        sku = _clean(r.get("sku"))
        pricing_type = _clean(r.get("pricing_type")) or "FIXED_PRICE"
        stock_status = _clean(r.get("stock_status")) or ("IN_STOCK" if stock > 0 else "OUT_OF_STOCK")
        is_featured = bool(_clean(r.get("is_featured")))

        products.append(
            {
                "id": product_id,
                "category_id": category_id,
                "brand_id": brand_id,
                "sku": sku,
                "name": name,
                "slug": slug,
                "description": description,
                "short_description": short_description,
                "price": price,
                "sale_price": sale_price,
                "unit": unit,
                "weight": weight,
                "origin": _clean(r.get("origin")),
                "pricing_type": pricing_type,
                "stock_status": stock_status,
                "is_featured": is_featured,
                "status": status,
                "images": images_by_product.get(product_id, []),
                "stock": stock,
                "details": {
                    "ingredients": short_description or (description[:500] if description else None),
                    "taste_profile": None,
                    "key_benefits": short_description,
                    "suitable_for": None,
                    "usage_instructions": f"Dùng theo hướng dẫn trên bao bì. Đơn vị: {unit}." if unit else None,
                    "storage_instructions": "Bảo quản nơi khô ráo, thoáng mát, tránh ánh nắng trực tiếp.",
                    "shelf_life": None,
                    "producer_name": brand_names.get(brand_id) if brand_id else None,
                    "production_area": _clean(r.get("origin")),
                    "product_story": description,
                    "extra_attributes": {
                        "sku": sku,
                        "unit": unit,
                        "weight": weight,
                        "pricing_type": pricing_type,
                        "stock_status": stock_status,
                        "is_featured": is_featured,
                    },
                },
            }
        )

    # Keep inventories only for exported products
    product_ids = {p["id"] for p in products}
    inventories = [i for i in inventories if i["product_id"] in product_ids]

    return {
        "meta": {
            "generated_at": datetime.now().isoformat() + "Z",
            "source": str(final_path),
            "scope": "products_only",
            "counts": {
                "categories": len(categories),
                "brands": len(brands),
                "warehouses": len(warehouses),
                "products": len(products),
                "inventories": len(inventories),
                "images": sum(len(p["images"]) for p in products),
                "skipped_zero_price": skipped_zero_price,
            },
            "notes": [
                "Product catalog only: categories, brands, warehouses, products, images, inventories, product_details.",
                "No reviews, blogs, users, sample chatbot sheet, or synthetic data.",
                "Excel inventory.quantity is mapped to available_quantity.",
            ],
        },
        "categories": categories,
        "brands": brands,
        "warehouses": warehouses,
        "products": products,
        "inventories": inventories,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export product catalog Excel → JSON")
    parser.add_argument("--final", type=Path, default=DEFAULT_FINAL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    if not args.final.exists():
        print(f"ERROR: Excel not found: {args.final}", file=sys.stderr)
        return 1

    payload = build_payload(args.final)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    print("counts:", json.dumps(payload["meta"]["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
