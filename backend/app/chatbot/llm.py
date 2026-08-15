"""Provider-neutral OpenAI-compatible LLM factory."""

import json
import logging
import re
from typing import Optional, Any, Type, TypeVar
from pydantic import BaseModel

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class FallbackStructuredLLM:
    """Rule-based heuristic fallback extractor for offline testing or when LLM API key is absent."""

    def extract_intent(self, message: str) -> dict:
        msg = message.strip()
        msg_lower = msg.lower()

        # 1. Greetings & general chitchat
        if (
            msg_lower.startswith("xin chào")
            or msg_lower.startswith("chào")
            or msg_lower.startswith("hello")
            or msg_lower.startswith("hi")
            or "cảm ơn" in msg_lower
            or "bạn là ai" in msg_lower
            or ("giúp gì" in msg_lower and "cà phê" not in msg_lower and "trà" not in msg_lower)
        ):
            return {
                "intent": "GENERAL",
                "query": msg,
            }

        # 2. Order code pattern: ORD-YYYYMMDD-XXXX or similar
        order_match = re.search(r"ORD-[\w\-]+", msg, re.IGNORECASE)
        if order_match or "đơn hàng" in msg_lower or "tra cứu đơn" in msg_lower or "tình trạng đơn" in msg_lower:
            return {
                "intent": "ORDER_STATUS",
                "order_code": order_match.group(0).upper() if order_match else None,
            }

        # 3. Knowledge detection (educational, botanical, health, standards, guide queries)
        if (
            "cách chọn" in msg_lower
            or "nhận biết" in msg_lower
            or "lợi ích" in msg_lower
            or "hướng dẫn" in msg_lower
            or "bảo quản" in msg_lower
            or "nguyên chất" in msg_lower
            or "đặc tính sinh học" in msg_lower
            or "xu hướng" in msg_lower
            or "quy trình" in msg_lower
            or "tiêu chuẩn" in msg_lower
            or "vietgap" in msg_lower
            or "có nên sử dụng" in msg_lower
            or "sức khỏe" in msg_lower
        ):
            return {
                "intent": "KNOWLEDGE",
                "query": msg,
            }

        # 4. Compare detection
        if (
            "so sánh" in msg_lower
            or "khác nhau thế nào" in msg_lower
            or "nên mua cái nào" in msg_lower
            or ("nên mua" in msg_lower and "hay" in msg_lower)
        ):
            products = []
            if "arabica" in msg_lower:
                products.append("Arabica Cầu Đất")
            if "robusta" in msg_lower:
                products.append("Robusta Buôn Ma Thuột")
            if "shan tuyết" in msg_lower:
                products.append("Trà Shan Tuyết")
            if "oolong" in msg_lower:
                products.append("Trà Oolong")
            if "u minh" in msg_lower:
                products.append("Mật ong U Minh")
            if "hoa cà phê" in msg_lower or "hoa cafe" in msg_lower:
                products.append("Mật ong hoa cà phê")
            if "hạt điều" in msg_lower or "điều bình phước" in msg_lower:
                products.append("Hạt điều Bình Phước")
            if "mắc ca" in msg_lower or "macca" in msg_lower:
                products.append("Hạt mắc ca Lâm Đồng")
            if "xoài" in msg_lower:
                products.append("Xoài sấy dẻo")
            if "mít" in msg_lower:
                products.append("Mít sấy giòn")

            return {
                "intent": "PRODUCT_COMPARE",
                "product_names": products,
                "query": msg,
            }

        # 5. Reviews detection
        if "đánh giá" in msg_lower or "review" in msg_lower or "phản hồi" in msg_lower or "nhận xét" in msg_lower:
            return {
                "intent": "PRODUCT_REVIEW",
                "query": msg,
            }

        # 6. Specific stock or detail
        if (
            "còn hàng" in msg_lower
            or "tồn kho" in msg_lower
            or "hết hàng" in msg_lower
            or "còn đủ" in msg_lower
            or "giao ngay không" in msg_lower
            or "còn bao nhiêu" in msg_lower
        ):
            return {
                "intent": "PRODUCT_DETAIL",
                "query": msg,
            }

        # Price parsing
        max_price = None
        min_price = None
        if "dưới" in msg_lower or "nhỏ hơn" in msg_lower or "<" in msg_lower or "tầm" in msg_lower or "khoảng" in msg_lower or "ngân sách" in msg_lower:
            num_match = re.search(r"(?:dưới|tầm|khoảng|ngân sách|<)\s*(\d+)\s*(k|nghìn|ngàn|tr|triệu)?", msg_lower)
            if num_match:
                val = float(num_match.group(1))
                unit = num_match.group(2) or ""
                if unit in ("k", "nghìn", "ngàn") or val < 1000:
                    max_price = val * 1000
                elif unit in ("tr", "triệu"):
                    max_price = val * 1000000
                else:
                    max_price = val

        # Category parsing
        category = None
        if "cà phê" in msg_lower or "cafe" in msg_lower or "coffee" in msg_lower:
            category = "cà phê"
        elif "trà" in msg_lower or "chè" in msg_lower:
            category = "trà"
        elif "mật ong" in msg_lower:
            category = "mật ong"
        elif "hạt" in msg_lower:
            category = "hạt"
        elif "sấy" in msg_lower or "hoa quả" in msg_lower:
            category = "nông sản sấy"
        elif "hộp quà" in msg_lower or "set quà" in msg_lower or ("quà" in msg_lower and "doanh nghiệp" in msg_lower):
            category = "hộp quà tặng"

        # Origin parsing
        origin = None
        for org in ["cầu đất", "đà lạt", "buôn ma thuột", "đắk lắk", "hà giang", "bảo lộc", "u minh", "bình phước", "khánh hòa", "tây ninh"]:
            if org in msg_lower:
                origin = org
                break

        # Check for specific product keyword in query
        kw_query = None
        for kw in ["arabica", "robusta", "typica", "shan tuyết", "oolong", "hoa cúc", "u minh", "hạt điều", "mắc ca", "xoài sấy", "mít sấy", "dưỡng lành", "tinh hoa"]:
            if kw in msg_lower:
                kw_query = kw
                break

        # 7. Explicit Search check (starts with 'tìm' or 'cho tôi xem')
        if (msg_lower.startswith("tìm") or msg_lower.startswith("cho tôi xem")) and not ("tư vấn" in msg_lower or "gợi ý" in msg_lower or "biếu" in msg_lower):
            return {
                "intent": "PRODUCT_SEARCH",
                "query": kw_query,
                "category": category,
                "origin": origin,
                "max_price": max_price,
                "min_price": min_price,
            }

        # 8. Recommendation soft preferences
        if (
            "thơm" in msg_lower
            or "ít đắng" in msg_lower
            or "đậm đà" in msg_lower
            or "pha phin" in msg_lower
            or "ngọt hậu" in msg_lower
            or "gợi ý" in msg_lower
            or "tư vấn" in msg_lower
            or "phù hợp" in msg_lower
            or "quà biếu" in msg_lower
            or "tặng" in msg_lower
            or "bà bầu" in msg_lower
            or "văn phòng" in msg_lower
            or "ốm dậy" in msg_lower
            or "người lớn tuổi" in msg_lower
            or "thanh lọc" in msg_lower
            or "specialty" in msg_lower
        ):
            return {
                "intent": "PRODUCT_RECOMMENDATION",
                "query": kw_query,
                "category": category,
                "origin": origin,
                "max_price": max_price,
                "min_price": min_price,
                "preferences": msg,
            }

        # 9. General Product Search
        if category or origin or max_price or "tìm" in msg_lower or "có" in msg_lower or "cho tôi xem" in msg_lower:
            return {
                "intent": "PRODUCT_SEARCH",
                "query": kw_query,
                "category": category,
                "origin": origin,
                "max_price": max_price,
                "min_price": min_price,
            }

        return {
            "intent": "GENERAL",
            "query": msg,
        }


def get_chat_model():
    """Create configured ChatOpenAI instance or return fallback when no valid API key."""
    settings = get_settings()
    key = settings.LLM_API_KEY
    if not key or key.strip() in ("", "your_llm_api_key_here", "test_key"):
        return None

    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=key,
            base_url=settings.LLM_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
        )
    except Exception as exc:
        logger.warning("Failed to initialize ChatOpenAI (%s), fallback will be used.", exc)
        return None
