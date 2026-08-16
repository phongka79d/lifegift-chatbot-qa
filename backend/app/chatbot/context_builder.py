"""Context Builder assembling compact, normalized, customer-safe context for LLM generation."""

import json
from typing import List, Dict, Any, Optional

from backend.app.chatbot.prompts import LABELS
from backend.app.schemas.product import ProductCard, ProductDetailResponse
from backend.app.schemas.chat import OrderStatusResponse


def format_currency_vnd(amount: float) -> str:
    """Format number to Vietnamese Dong string."""
    return f"{amount:,.0f}đ".replace(",", ".")


def build_chat_context(
    products: Optional[List[ProductCard]] = None,
    product_detail: Optional[ProductDetailResponse] = None,
    knowledge_chunks: Optional[List[Dict[str, Any]]] = None,
    reviews: Optional[Dict[str, Any]] = None,
    order: Optional[OrderStatusResponse] = None,
    comparison_products: Optional[List[ProductDetailResponse]] = None,
    applied_filters: Optional[Dict[str, Any]] = None,
    empty_reason: Optional[str] = None,
    available_categories: Optional[List[str]] = None,
) -> str:
    """Build a compact, clean text representation of factual data for grounding LLM answers."""
    blocks = []

    if applied_filters:
        parts = []
        for key in ("category", "origin", "brand", "min_price", "max_price", "price_unit", "query"):
            val = applied_filters.get(key)
            if val is not None and val != "":
                parts.append(f"{key}={val}")
        if parts:
            blocks.append(f"{LABELS['APPLIED_FILTERS']} " + ", ".join(parts))

    # 1. Product list / Search / Recommendation results
    if products:
        prod_lines = [LABELS["PRODUCTS_FOUND"]]
        for p in products:
            price_str = format_currency_vnd(p.effective_price)
            if p.sale_price and p.sale_price < p.price:
                price_str += f" (list: {format_currency_vnd(p.price)}, on sale)"
            price_extra = " | Price basis: package/box"
            if getattr(p, "price_per_kg", None) is not None:
                price_extra += f" | Est. /kg: {format_currency_vnd(p.price_per_kg)}"
            if getattr(p, "weight", None):
                price_extra += f" | Wt: {p.weight:g}g"
            stock_str = (
                f"In stock {p.available_quantity}" if p.is_available else "Out of stock"
            )
            reason_str = f" - Recommend reason: {p.reason}" if p.reason else ""
            cat_name = getattr(p, "category_name", None)
            cat_str = f" | Category: {cat_name}" if cat_name else ""
            prod_lines.append(
                f"- [ID: {p.id}] {p.name}{cat_str} | Package price: {price_str}{price_extra} | "
                f"Origin: {p.origin or 'Vietnam'} | Status: {stock_str}{reason_str}"
            )
        blocks.append("\n".join(prod_lines))
    elif empty_reason:
        empty_lines = [
            LABELS["NO_MATCH"],
            f"{LABELS['EMPTY_REASON']} {empty_reason}.",
            LABELS["EMPTY_GUIDANCE"],
        ]
        if available_categories:
            empty_lines.append(
                f"{LABELS['AVAILABLE_CATEGORIES']} " + ", ".join(available_categories)
            )
        blocks.append("\n".join(empty_lines))

    # 2. Product Detail
    if product_detail:
        d = product_detail
        price_str = format_currency_vnd(d.effective_price)
        if d.sale_price and d.sale_price < d.price:
            price_str += f" (list: {format_currency_vnd(d.price)})"
        stock_str = f"In stock {d.available_quantity}" if d.is_available else "Temporarily out of stock"
        cert_names = [c["name"] for c in d.certificates if c.get("status") == "ACTIVE"]
        cert_str = ", ".join(cert_names) if cert_names else "No listed certificates"

        detail_lines = [
            f"{LABELS['PRODUCT_DETAIL']} {d.name}",
            f"- Category: {d.category_name or 'Produce'}",
            f"- Brand: {d.brand_name or 'LifeGift'}",
            f"- Current price: {price_str}",
            f"- Stock: {stock_str}",
            f"- Origin: {d.origin or d.production_area or 'Vietnam'}",
            f"- Quality certificates: {cert_str}",
        ]
        if d.ingredients:
            detail_lines.append(f"- Ingredients: {d.ingredients}")
        if d.taste_profile:
            detail_lines.append(f"- Taste: {d.taste_profile}")
        if d.key_benefits:
            detail_lines.append(f"- Benefits: {d.key_benefits}")
        if d.suitable_for:
            detail_lines.append(f"- Suitable for: {d.suitable_for}")
        if d.usage_instructions:
            detail_lines.append(f"- Usage: {d.usage_instructions}")
        if d.storage_instructions:
            detail_lines.append(f"- Storage: {d.storage_instructions}")
        if d.product_story:
            detail_lines.append(f"- Story: {d.product_story}")

        blocks.append("\n".join(detail_lines))

    # 3. Product Comparison
    if comparison_products:
        comp_lines = [LABELS["COMPARISON"]]
        for p in comparison_products:
            price_str = format_currency_vnd(p.effective_price)
            stock_str = f"In stock {p.available_quantity}" if p.is_available else "Out of stock"
            comp_lines.append(
                f"Product: {p.name}\n"
                f"  + Price: {price_str}\n"
                f"  + Origin: {p.origin}\n"
                f"  + Stock: {stock_str}\n"
                f"  + Taste: {p.taste_profile or 'Characteristic'}\n"
                f"  + Suitable for: {p.suitable_for or 'General'}\n"
                f"  + Usage: {p.usage_instructions or 'Standard preparation'}"
            )
        blocks.append("\n\n".join(comp_lines))

    # 4. Knowledge chunks from Qdrant
    if knowledge_chunks:
        k_lines = [LABELS["KNOWLEDGE"]]
        for idx, k in enumerate(knowledge_chunks, 1):
            title = k.get("title", "Agricultural knowledge")
            content = k.get("content", "")
            k_lines.append(f"[{idx}] {title}:\n{content}")
        blocks.append("\n\n".join(k_lines))

    # 5. Customer Reviews
    if reviews and reviews.get("reviews"):
        rev_lines = [
            f"{LABELS['REVIEWS_HEADER']} — average {reviews.get('average_rating')}/5 from {reviews.get('review_count')} reviews):"
        ]
        for r in reviews["reviews"]:
            rev_lines.append(
                f"- ⭐ {r['rating']}/5 sao | {r['reviewer_name']}: \"{r['title']}\" - {r['content']}"
            )
        blocks.append("\n".join(rev_lines))

    # 6. Order Status
    if order:
        ord_lines = [
            f"{LABELS['ORDER']} {order.order_code}",
            f"- Order status: {order.order_status}",
            f"- Payment: {order.payment_status}",
            f"- Ordered: {order.created_at}",
            "- Status history:",
        ]
        for h in order.status_history:
            ord_lines.append(f"  + [{h['created_at']}] {h['status']}: {h['notes']}")
        blocks.append("\n".join(ord_lines))

    if not blocks:
        return LABELS["NO_SPECIAL_DATA"]

    return "\n\n====================\n\n".join(blocks)
