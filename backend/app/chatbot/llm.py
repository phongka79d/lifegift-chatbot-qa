"""Provider-neutral OpenAI-compatible LLM factory."""

import logging
import re
from typing import Optional

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

# Spoken Vietnamese digit words used in price phrases (hundreds scale)
_SPOKEN_DIGIT = {
    "một": 1,
    "mốt": 1,
    "hai": 2,
    "ba": 3,
    "bốn": 4,
    "tư": 4,
    "năm": 5,
    "lăm": 5,
    "sáu": 6,
    "bảy": 7,
    "tám": 8,
    "chín": 9,
}

# Regions already used as general origin cues (not eval-CSV province lists)
KNOWN_ORIGIN_TOKENS = (
    "cầu đất",
    "đà lạt",
    "buôn ma thuột",
    "đắk lắk",
    "dak lak",
    "hà giang",
    "bảo lộc",
    "u minh",
    "bình phước",
    "khánh hòa",
    "tây ninh",
    "tây nguyên",
    "tây bắc",
    "lâm đồng",
)


def _parse_vnd_number(raw: str) -> Optional[float]:
    """Parse a Vietnamese money token into VND float.

    Examples:
      100.000 -> 100000
      100,000 -> 100000
      200k -> 200000
      1.5 triệu -> 1500000
      250000 -> 250000
    """
    if raw is None:
        return None
    text = str(raw).strip().lower().replace("đồng", "").replace("vnd", "").replace(" ", "")
    if not text:
        return None

    multiplier = 1.0
    if text.endswith("triệu") or text.endswith("tr"):
        text = re.sub(r"(triệu|tr)$", "", text)
        multiplier = 1_000_000.0
    elif text.endswith("nghìn") or text.endswith("ngàn") or text.endswith("k"):
        text = re.sub(r"(nghìn|ngàn|k)$", "", text)
        multiplier = 1_000.0

    # Vietnamese thousand separators: 100.000 or 100,000
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", text):
        digits = re.sub(r"[.,]", "", text)
        try:
            return float(digits) * multiplier
        except ValueError:
            return None

    # Decimal with optional fraction: 1.5 / 1,5
    text = text.replace(",", ".")
    try:
        value = float(text)
    except ValueError:
        return None

    value *= multiplier
    # Bare small numbers without unit almost always mean thousands in VN chat (e.g. "dưới 300")
    if multiplier == 1.0 and 0 < value < 1000:
        value *= 1000
    return value


def _normalize_spoken_price_phrases(message: str) -> str:
    """Replace spoken-hundreds money phrases with digit forms for downstream parsers.

    "hai trăm nghìn" → "200000"
    "hai trăm" (bare hundreds in retail talk) → "200k"
    """

    def repl(m: re.Match) -> str:
        hundreds = _SPOKEN_DIGIT[m.group(1)] * 100
        if m.group(2):
            return str(int(hundreds * 1000))
        return f"{hundreds}k"

    return re.sub(
        r"(một|hai|ba|bốn|năm|sáu|bảy|tám|chín)\s*trăm(?:\s*(nghìn|ngàn))?",
        repl,
        message.lower(),
    )


def parse_price_bounds(message: str) -> tuple[Optional[float], Optional[float]]:
    """Extract min/max VND bounds from a Vietnamese natural-language message."""
    msg = message.strip()
    msg_lower = msg.lower()
    min_price: Optional[float] = None
    max_price: Optional[float] = None

    # Normalize dash variants (en/em) to hyphen for range parsing
    msg_lower = (
        msg_lower.replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("~", "-")
    )
    # Spoken hundreds → digit/k forms (keeps existing k/separator parsers working)
    msg_lower = _normalize_spoken_price_phrases(msg_lower)

    # Range: từ 100.000 đến 200.000 / 100k-200k / 120 - 180k
    range_patterns = [
        r"từ\s*([\d.,]+(?:\s*(?:k|nghìn|ngàn|tr|triệu))?)\s*(?:đến|-|tới)\s*([\d.,]+(?:\s*(?:k|nghìn|ngàn|tr|triệu))?)",
        r"([\d.,]+(?:\s*(?:k|nghìn|ngàn|tr|triệu))?)\s*(?:đến|-|tới)\s*([\d.,]+(?:\s*(?:k|nghìn|ngàn|tr|triệu))?)",
    ]
    for pattern in range_patterns:
        m = re.search(pattern, msg_lower)
        if m:
            lo = _parse_vnd_number(m.group(1))
            hi = _parse_vnd_number(m.group(2))
            if lo is not None and hi is not None:
                return (min(lo, hi), max(lo, hi))

    # Unit token: require word boundary on bare k/tr so "không"/"trong" are not units
    _unit = r"(nghìn|ngàn|triệu|tr\b|k\b)"

    # "từ N trở xuống" / "N trở xuống" → max only (not min)
    m = re.search(
        rf"(?:từ\s*)?([\d.,]+)\s*{_unit}?\s*trở\s*xuống",
        msg_lower,
    )
    if m:
        raw = m.group(1) + (m.group(2) or "")
        max_price = _parse_vnd_number(raw)

    # Upper bound only
    if max_price is None:
        m = re.search(
            rf"(?:dưới|nhỏ hơn|<=|<|tối đa|max|không quá|ngân sách)\s*([\d.,]+)\s*{_unit}?",
            msg_lower,
        )
        if m:
            raw = m.group(1) + (m.group(2) or "")
            max_price = _parse_vnd_number(raw)

    # Lower bound only — skip when "trở xuống" already consumed "từ N"
    if "trở xuống" not in msg_lower:
        m = re.search(
            rf"(?:trên|lớn hơn|>=|>|từ|tối thiểu|min)\s*([\d.,]+)\s*{_unit}?",
            msg_lower,
        )
        if m and min_price is None:
            raw = m.group(1) + (m.group(2) or "")
            # Avoid treating "từ 100 đến 200" twice — range already handled
            if "đến" not in msg_lower and "tới" not in msg_lower:
                min_price = _parse_vnd_number(raw)

    # Soft budget phrases: tầm/khoảng 300k
    if max_price is None:
        m = re.search(rf"(?:tầm|khoảng)\s*([\d.,]+)\s*{_unit}?", msg_lower)
        if m:
            raw = m.group(1) + (m.group(2) or "")
            max_price = _parse_vnd_number(raw)

    return min_price, max_price


def detect_price_unit(message: str) -> str:
    """Detect PACKAGE vs PER_KG from general unit language (not product-specific lists)."""
    msg_lower = (message or "").lower()
    per_kg_patterns = (
        r"/\s*kg",
        r"đồng\s*/\s*kg",
        r"k\s*/\s*kg",
        r"một\s*ký",
        r"1\s*kg",
        r"trên\s*kg",
        r"theo\s*kg",
        r"mỗi\s*kg",
        r"giá\s*kg",
    )
    for pat in per_kg_patterns:
        if re.search(pat, msg_lower):
            return "PER_KG"
    if re.search(r"\bkg\b", msg_lower) and re.search(r"\d", msg_lower):
        # e.g. "dưới 200k kg" / "200 nghìn kg"
        if re.search(r"(k|nghìn|ngàn|đồng|triệu).{0,8}kg|kg.{0,8}(k|nghìn|ngàn|đồng)", msg_lower):
            return "PER_KG"
    return "PACKAGE"


def infer_kind_from_message(message: str) -> Optional[str]:
    """Infer retail kind/category noun from message (linguistic lexicon, not bank questions)."""
    msg_lower = (message or "").lower()
    # Longer / multi-word phrases first
    if any(k in msg_lower for k in ("cà phê", "cafe", "coffee")):
        return "cà phê"
    if "mật ong" in msg_lower:
        return "mật ong"
    if "nông sản chế biến" in msg_lower or "nong san che bien" in msg_lower:
        return "nông sản chế biến"
    if "trái cây" in msg_lower or "hoa quả" in msg_lower:
        return "trái cây"
    if "rau củ" in msg_lower or "rau quả" in msg_lower:
        return "rau củ"
    if "trà" in msg_lower:
        return "trà"
    # "chè" is tea unless it is the dessert verb phrase "nấu chè"
    if re.search(r"\bchè\b", msg_lower) and "nấu chè" not in msg_lower:
        return "trà"
    if re.search(r"\bhạt\b", msg_lower):
        return "hạt"
    if re.search(r"\bgạo\b", msg_lower):
        return "gạo"
    if re.search(r"\bđậu\b", msg_lower):
        return "đậu"
    if "hộp quà" in msg_lower or "set quà" in msg_lower or (
        "quà" in msg_lower and "doanh nghiệp" in msg_lower
    ):
        return "quà tặng"
    if re.search(r"\bquà\b", msg_lower):
        return "quà tặng"
    return None


def infer_origin_from_message(message: str) -> Optional[str]:
    """Infer origin from general region tokens already used in catalog language."""
    msg_lower = (message or "").lower()
    for org in KNOWN_ORIGIN_TOKENS:
        if org in msg_lower:
            return org
    return None


_REVIEW_FILLER_RE = re.compile(
    r"\b(có|sản phẩm|san pham|nào|nao|những|nhung|các|cac|"
    r"review|đánh giá|danh gia|nhận xét|nhan xet|phản hồi|phan hoi|"
    r"cho|tôi|toi|mình|minh|xem|của|cua|với|voi|về|ve|là|la|"
    r"được|duoc|không|khong|hãy|hay|giúp|giup|tìm|tim)\b",
    re.IGNORECASE,
)


def extract_review_theme(message: str) -> Optional[str]:
    """Keep distinctive review-content words; drop list/review filler.

    Example: 'Có sản phẩm nào có review đúng với mô tả không?' → 'đúng mô tả'
    """
    cleaned = _REVIEW_FILLER_RE.sub(" ", (message or "").lower())
    cleaned = re.sub(r"[?!.,;:]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) < 3:
        return None
    return cleaned


def split_compare_names(message: str) -> list[str]:
    """Split user-stated compare names on và/hay/với/vs. Do not invent catalog SKUs."""
    text = (message or "").strip()
    text = re.sub(r"^(so\s*sánh|so sánh)\s+", "", text, flags=re.IGNORECASE)
    parts = re.split(r"\s+(?:và|hay|với|vs\.?)\s+", text, maxsplit=1, flags=re.IGNORECASE)
    names = [re.sub(r"[?.!,]+$", "", p).strip() for p in parts]
    names = [n for n in names if len(n) >= 2]
    return names if len(names) >= 2 else []


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
        # Usage/list/info constructions are handled later / by normalize_extraction.
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

        # 4. Compare detection — parse user-stated names only (X và/hay/với Y)
        if (
            "so sánh" in msg_lower
            or "khác nhau thế nào" in msg_lower
            or "nên mua cái nào" in msg_lower
            or ("nên mua" in msg_lower and "hay" in msg_lower)
        ):
            return {
                "intent": "PRODUCT_COMPARE",
                "product_names": split_compare_names(msg),
                "query": msg,
                "category": infer_kind_from_message(msg),
            }

        # 5. Reviews detection
        if "đánh giá" in msg_lower or "review" in msg_lower or "phản hồi" in msg_lower or "nhận xét" in msg_lower:
            return {
                "intent": "PRODUCT_REVIEW",
                "query": extract_review_theme(msg),
                "category": infer_kind_from_message(msg),
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

        # Price parsing (supports "từ 100.000 đến 200.000", "dưới 300k", spoken hundreds, ...)
        min_price, max_price = parse_price_bounds(msg)

        category = infer_kind_from_message(msg)
        origin = infer_origin_from_message(msg)

        # Check for specific product keyword in query (distinctive tokens only, not invented full SKUs)
        kw_query = None
        for kw in [
            "arabica",
            "robusta",
            "typica",
            "shan tuyết",
            "oolong",
            "hoa cúc",
            "u minh",
            "hạt điều",
            "mắc ca",
            "macca",
            "xoài sấy",
            "mít sấy",
        ]:
            if kw in msg_lower:
                kw_query = kw
                break

        # 7. Explicit Search check (starts with 'tìm' or 'cho tôi xem')
        if (msg_lower.startswith("tìm") or msg_lower.startswith("cho tôi xem")) and not (
            "tư vấn" in msg_lower or "gợi ý" in msg_lower or "biếu" in msg_lower
        ):
            return {
                "intent": "PRODUCT_SEARCH",
                "query": kw_query,
                "category": category,
                "origin": origin,
                "max_price": max_price,
                "min_price": min_price,
            }

        # 8. Recommendation soft preferences / usage
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
            or "cho quán" in msg_lower
            or "để uống" in msg_lower
            or "uống hằng ngày" in msg_lower
            or "uống hàng ngày" in msg_lower
            or re.search(r"nguyên\s*liệu.{0,24}để", msg_lower)
            or re.search(r"làm\s*(sữa|bánh|chè)", msg_lower)
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

        # Named-line info constructions
        if re.search(r"(thông\s*tin\s*về|giá\s*bao\s*nhiêu|đặc\s*điểm)", msg_lower) and (
            category or kw_query
        ):
            return {
                "intent": "PRODUCT_DETAIL" if kw_query else "PRODUCT_SEARCH",
                "query": kw_query or category,
                "category": category,
                "origin": origin,
                "max_price": max_price,
                "min_price": min_price,
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
    key = settings.effective_llm_api_key
    if not key or key.strip() in ("", "your_llm_api_key_here", "test_key"):
        return None

    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=key,
            base_url=settings.effective_llm_base_url,
            temperature=settings.LLM_TEMPERATURE,
        )
    except Exception as exc:
        logger.warning("Failed to initialize ChatOpenAI (%s), fallback will be used.", exc)
        return None
