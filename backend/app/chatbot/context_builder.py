"""Context Builder assembling compact, normalized, customer-safe context for LLM generation."""

import json
from typing import List, Dict, Any, Optional

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
            blocks.append("BỘ LỌC ĐÃ ÁP DỤNG: " + ", ".join(parts))

    # 1. Product list / Search / Recommendation results
    if products:
        prod_lines = ["DANH SÁCH SẢN PHẨM TÌM THẤY (DỮ LIỆU TỪ MYSQL):"]
        for p in products:
            price_str = format_currency_vnd(p.effective_price)
            if p.sale_price and p.sale_price < p.price:
                price_str += f" (Giá gốc: {format_currency_vnd(p.price)}, Đang giảm giá)"
            basis = getattr(p, "price_basis", None) or "package"
            price_extra = f" | Cơ sở giá: gói/hộp"
            if getattr(p, "price_per_kg", None) is not None:
                price_extra += f" | Ước tính /kg: {format_currency_vnd(p.price_per_kg)}"
            if getattr(p, "weight", None):
                price_extra += f" | KL: {p.weight:g}g"
            stock_str = f"Còn {p.available_quantity} sản phẩm" if p.is_available else "Hết hàng"
            reason_str = f" - Lý do gợi ý: {p.reason}" if p.reason else ""
            cat_name = getattr(p, "category_name", None)
            cat_str = f" | Danh mục: {cat_name}" if cat_name else ""
            prod_lines.append(
                f"- [ID: {p.id}] {p.name}{cat_str} | Giá gói: {price_str}{price_extra} | "
                f"Xuất xứ: {p.origin or 'Việt Nam'} | Tình trạng: {stock_str}{reason_str}"
            )
        blocks.append("\n".join(prod_lines))
    elif empty_reason:
        empty_lines = [
            "KHÔNG CÓ SẢN PHẨM KHỚP BỘ LỌC (DỮ LIỆU MYSQL).",
            f"Lý do: {empty_reason}.",
            "Không được bịa sản phẩm. Hãy thông báo rõ ràng và gợi ý nới tiêu chí nếu hợp lý.",
        ]
        if available_categories:
            empty_lines.append(
                "Danh mục đang có hàng: " + ", ".join(available_categories)
            )
        blocks.append("\n".join(empty_lines))

    # 2. Product Detail
    if product_detail:
        d = product_detail
        price_str = format_currency_vnd(d.effective_price)
        if d.sale_price and d.sale_price < d.price:
            price_str += f" (Giá gốc: {format_currency_vnd(d.price)})"
        stock_str = f"Còn {d.available_quantity} sản phẩm" if d.is_available else "Tạm hết hàng"
        cert_names = [c["name"] for c in d.certificates if c.get("status") == "ACTIVE"]
        cert_str = ", ".join(cert_names) if cert_names else "Chưa có chứng chỉ niêm yết"

        detail_lines = [
            f"THÔNG TIN CHI TIẾT SẢN PHẨM: {d.name}",
            f"- Danh mục: {d.category_name or 'Nông sản'}",
            f"- Thương hiệu: {d.brand_name or 'LifeGift'}",
            f"- Giá bán hiện tại: {price_str}",
            f"- Tình trạng tồn kho: {stock_str}",
            f"- Xuất xứ: {d.origin or d.production_area or 'Việt Nam'}",
            f"- Chứng nhận chất lượng: {cert_str}",
        ]
        if d.ingredients:
            detail_lines.append(f"- Thành phần: {d.ingredients}")
        if d.taste_profile:
            detail_lines.append(f"- Hương vị: {d.taste_profile}")
        if d.key_benefits:
            detail_lines.append(f"- Công dụng: {d.key_benefits}")
        if d.suitable_for:
            detail_lines.append(f"- Phù hợp: {d.suitable_for}")
        if d.usage_instructions:
            detail_lines.append(f"- Hướng dẫn pha chế/sử dụng: {d.usage_instructions}")
        if d.storage_instructions:
            detail_lines.append(f"- Bảo quản: {d.storage_instructions}")
        if d.product_story:
            detail_lines.append(f"- Câu chuyện sản phẩm: {d.product_story}")

        blocks.append("\n".join(detail_lines))

    # 3. Product Comparison
    if comparison_products:
        comp_lines = ["SO SÁNH CÁC SẢN PHẨM ĐƯỢC YÊU CẦU:"]
        for p in comparison_products:
            price_str = format_currency_vnd(p.effective_price)
            stock_str = f"Còn {p.available_quantity} sp" if p.is_available else "Hết hàng"
            comp_lines.append(
                f"Sản phẩm: {p.name}\n"
                f"  + Giá: {price_str}\n"
                f"  + Xuất xứ: {p.origin}\n"
                f"  + Tồn kho: {stock_str}\n"
                f"  + Hương vị: {p.taste_profile or 'Đặc trưng'}\n"
                f"  + Phù hợp: {p.suitable_for or 'Mọi người'}\n"
                f"  + Pha chế: {p.usage_instructions or 'Pha thông thường'}"
            )
        blocks.append("\n\n".join(comp_lines))

    # 4. Knowledge chunks from Qdrant
    if knowledge_chunks:
        k_lines = ["KIẾN THỨC NÔNG SẢN VÀ THÔNG TIN BÀI VIẾT (TỪ VECTOR RAG):"]
        for idx, k in enumerate(knowledge_chunks, 1):
            title = k.get("title", "Kiến thức nông sản")
            content = k.get("content", "")
            k_lines.append(f"[{idx}] {title}:\n{content}")
        blocks.append("\n\n".join(k_lines))

    # 5. Customer Reviews
    if reviews and reviews.get("reviews"):
        rev_lines = [
            f"ĐÁNH GIÁ CỦA KHÁCH HÀNG (ĐÃ PHÊ DUYỆT - Trung bình {reviews.get('average_rating')}/5 sao từ {reviews.get('review_count')} đánh giá):"
        ]
        for r in reviews["reviews"]:
            rev_lines.append(
                f"- ⭐ {r['rating']}/5 sao | {r['reviewer_name']}: \"{r['title']}\" - {r['content']}"
            )
        blocks.append("\n".join(rev_lines))

    # 6. Order Status
    if order:
        ord_lines = [
            f"THÔNG TIN ĐƠN HÀNG: {order.order_code}",
            f"- Trạng thái đơn: {order.order_status}",
            f"- Thanh toán: {order.payment_status}",
            f"- Ngày đặt: {order.created_at}",
            "- Lịch sử trạng thái:",
        ]
        for h in order.status_history:
            ord_lines.append(f"  + [{h['created_at']}] {h['status']}: {h['notes']}")
        blocks.append("\n".join(ord_lines))

    if not blocks:
        return "Không có dữ liệu đặc biệt nào từ cơ sở dữ liệu."

    return "\n\n====================\n\n".join(blocks)
