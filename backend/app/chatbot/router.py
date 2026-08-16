"""Deterministic Intent Router and Structured Extraction."""

import logging
import re
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage

from backend.app.chatbot.llm import (
    get_chat_model,
    FallbackStructuredLLM,
    parse_price_bounds,
    detect_price_unit,
    infer_kind_from_message,
    infer_origin_from_message,
    extract_review_theme,
    split_compare_names,
)
from backend.app.chatbot.prompts import INTENT_EXTRACTION_SYSTEM_PROMPT
from backend.app.schemas.chat import IntentExtractionResult, IntentEnum, PriceUnitEnum

logger = logging.getLogger(__name__)

_GENERIC_QUERY_RE = re.compile(
    r"^(cà\s*phê|cafe|coffee|trà|chè|mật\s*ong|hạt|gạo|đậu|quà|sản\s*phẩm|nông\s*sản|"
    r"tìm|tìm\s*kiếm).*$",
    re.IGNORECASE,
)

# Generic labels that mean "produce" not a catalog aisle (origin-only talk).
# Keep specific kinds such as "nông sản chế biến" so they remain a hard kind filter.
_GENERIC_CATEGORY_LABELS = frozenset(
    {
        "nông sản",
        "nong san",
        "sản phẩm",
        "san pham",
    }
)

# General list/discovery signals (not evaluation-bank phrases)
_DISCOVERY_RE = re.compile(
    r"(có\s+.+\s+nào|những\s+.+\s+nào|liệt\s*kê|tìm\s+(giúp\s+)?|"
    r"cho\s+(tôi|mình)\s+xem|có\s+sản\s+phẩm\s+nào|ngân\s*sách|"
    r"dưới\s+\d|không\s+quá\s+\d|từ\s+\d|trong\s+khoảng|"
    r"có\s+gì|bán\s+gì|có\s+những\s+gì)",
    re.IGNORECASE,
)

# Distinctive product-line tokens (language cues, not full invented SKUs)
_LINE_TOKEN_RE = re.compile(
    r"(arabica|robusta|typica|shan\s*tuyết|oolong|macca|mắc\s*ca|"
    r"hạt\s*điều|xoài\s*sấy|mít\s*sấy|hoa\s*cúc)",
    re.IGNORECASE,
)

# Usage constructions that request stocked items for a purpose
_USAGE_RE = re.compile(
    r"(phù\s*hợp|nguyên\s*liệu.{0,24}để|cho\s*quán|để\s*uống|"
    r"làm\s*(sữa|bánh|chè)|uống\s*h[ằă]ng\s*ngày|nên\s*dùng|"
    r"gợi\s*ý|tư\s*vấn)",
    re.IGNORECASE,
)

# Named-line / sellable-info constructions (not pure how-to)
_INFO_LINE_RE = re.compile(
    r"(thông\s*tin\s*về|giá\s*bao\s*nhiêu|đặc\s*điểm)",
    re.IGNORECASE,
)

# Pure educational markers — keep KNOWLEDGE when these dominate without list request
_EDUCATIONAL_RE = re.compile(
    r"(cách\s*(chọn|bảo\s*quản|làm|pha|phân\s*biệt)|nhận\s*biết|"
    r"đặc\s*tính\s*sinh\s*học|quy\s*trình|tiêu\s*chuẩn|vietgap|"
    r"hướng\s*dẫn\s*bảo\s*quản|lợi\s*ích\s*sức\s*khỏe)",
    re.IGNORECASE,
)


def _normalize_category(category: Optional[str]) -> Optional[str]:
    if not category:
        return None
    text = category.strip().lower()
    if text in _GENERIC_CATEGORY_LABELS:
        return None
    aliases = {
        "cafe": "cà phê",
        "coffee": "cà phê",
        "ca phe": "cà phê",
        "càphê": "cà phê",
        "chè": "trà",
        "tra": "trà",
        "hat": "hạt",
        "hạt dinh dưỡng": "hạt",
        "gao": "gạo",
        "dau": "đậu",
        "trai cay": "trái cây",
        "rau cu": "rau củ",
        "qua tang": "quà tặng",
        "quà": "quà tặng",
    }
    return aliases.get(text, category.strip())


def _sanitize_query(query: Optional[str], category: Optional[str]) -> Optional[str]:
    """Drop redundant/noisy free-text query so price/category filters can work."""
    if not query:
        return None
    q = query.strip()
    if not q:
        return None
    q_lower = q.lower()
    if re.fullmatch(r"[\d\s.,k\-–—~đồngvnd/kggói]+", q_lower.replace(" ", "")):
        return None
    if "đồng" in q_lower and re.search(r"\d", q_lower):
        return None
    if "/kg" in q_lower or re.search(r"\bkg\b", q_lower):
        return None
    if category and category.lower() in q_lower and len(q_lower) <= len(category) + 12:
        return None
    if _GENERIC_QUERY_RE.match(q_lower) and len(q_lower) < 40:
        return None
    return q


def _has_discovery_signal(message: str, data: dict) -> bool:
    if _DISCOVERY_RE.search(message):
        return True
    if data.get("category") or data.get("origin") or data.get("min_price") is not None or data.get("max_price") is not None:
        # Constraint present with list-y particles
        msg = message.lower()
        if any(tok in msg for tok in ("có ", "tìm", "liệt kê", "cho tôi", "cho mình", "những")):
            return True
    return False


def _has_kind_or_product_token(message: str, data: dict) -> bool:
    """True when a kind noun or product-name token is present (required before leaving KNOWLEDGE)."""
    if data.get("category"):
        return True
    names = data.get("product_names") or []
    if names:
        return True
    q = data.get("query")
    if q and _sanitize_query(str(q), data.get("category")):
        return True
    if infer_kind_from_message(message):
        return True
    if _LINE_TOKEN_RE.search(message or ""):
        return True
    return False


def _infer_line_query(message: str) -> Optional[str]:
    m = _LINE_TOKEN_RE.search(message or "")
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(0).strip().lower())


def _infer_usage_marker(message: str) -> Optional[str]:
    msg_lower = message.lower()
    usage_markers = (
        "pha phin",
        "espresso",
        "ăn vặt",
        "làm bánh",
        "làm sữa",
        "làm chè",
        "nấu chè",
        "nước ép",
        "sữa hạt",
        "uống hằng ngày",
        "uống hàng ngày",
        "cho quán",
        "để uống",
        "phù hợp",
    )
    for marker in usage_markers:
        if marker in msg_lower:
            return marker
    m = re.search(r"nguyên\s*liệu.{0,24}để\s*([^\.?,;]{2,40})", msg_lower)
    if m:
        return "nguyên liệu để " + m.group(1).strip()[:40]
    if _USAGE_RE.search(msg_lower):
        return "usage"
    return None


def normalize_extraction(message: str, result: IntentExtractionResult) -> IntentExtractionResult:
    """Correct LLM/heuristic extraction using deterministic message parsing."""
    data = result.model_dump()
    data["category"] = _normalize_category(data.get("category"))
    data["query"] = _sanitize_query(data.get("query"), data.get("category"))

    msg_min, msg_max = parse_price_bounds(message)
    if msg_min is not None:
        data["min_price"] = msg_min
    if msg_max is not None:
        data["max_price"] = msg_max

    for key in ("min_price", "max_price"):
        val = data.get(key)
        if val is not None and 0 < float(val) < 1000:
            data[key] = float(val) * 1000

    if (
        data.get("min_price") is not None
        and data.get("max_price") is not None
        and data["min_price"] > data["max_price"]
    ):
        data["min_price"], data["max_price"] = data["max_price"], data["min_price"]

    # Price unit from message (authoritative over model when per-kg language present)
    unit = detect_price_unit(message)
    if unit == "PER_KG":
        data["price_unit"] = PriceUnitEnum.PER_KG.value
    elif not data.get("price_unit") or data.get("price_unit") == PriceUnitEnum.UNKNOWN.value:
        data["price_unit"] = PriceUnitEnum.PACKAGE.value

    # Infer kind/category from general retail nouns when model omitted them
    if not data.get("category"):
        kind = infer_kind_from_message(message)
        if kind:
            data["category"] = kind

    # Never keep generic "nông sản" as a hard category (produce-from-region talk)
    if data.get("category") and str(data["category"]).strip().lower() in _GENERIC_CATEGORY_LABELS:
        data["category"] = None

    # Infer origin from general region patterns if model omitted it
    if not data.get("origin"):
        origin = infer_origin_from_message(message)
        if origin:
            data["origin"] = origin

    # Infer usage soft preference
    if not data.get("usage") and not data.get("preferences"):
        usage = _infer_usage_marker(message)
        if usage:
            data["usage"] = usage

    # Fill distinctive line query when model omitted it
    if not data.get("query"):
        line_q = _infer_line_query(message)
        if line_q:
            data["query"] = line_q

    msg_lower = message.lower()
    intent = data.get("intent")
    is_knowledge = intent in (IntentEnum.KNOWLEDGE.value, IntentEnum.KNOWLEDGE)
    has_token = _has_kind_or_product_token(message, data)
    has_discovery = _has_discovery_signal(message, data)
    # True how-to stays knowledge; usage/info/list language still leaves even if "cách" appears
    pure_edu = (
        bool(_EDUCATIONAL_RE.search(msg_lower))
        and not has_discovery
        and not _USAGE_RE.search(msg_lower)
        and not _INFO_LINE_RE.search(msg_lower)
        and not data.get("usage")
        and not data.get("preferences")
    )

    # Leave KNOWLEDGE when kind/product token present, or origin-only discovery list
    can_leave = has_token or (bool(data.get("origin")) and has_discovery)
    if is_knowledge and can_leave and not pure_edu:
        if data.get("usage") or data.get("preferences") or _USAGE_RE.search(msg_lower):
            data["intent"] = IntentEnum.PRODUCT_RECOMMENDATION.value
        elif _INFO_LINE_RE.search(msg_lower):
            # Named-line info → detail when a specific name/query token exists, else search by kind
            names = data.get("product_names") or []
            q = data.get("query")
            if names or (q and not _GENERIC_QUERY_RE.match(str(q).lower())):
                data["intent"] = IntentEnum.PRODUCT_DETAIL.value
            else:
                data["intent"] = IntentEnum.PRODUCT_SEARCH.value
        elif has_discovery:
            if data.get("usage") or data.get("preferences"):
                data["intent"] = IntentEnum.PRODUCT_RECOMMENDATION.value
            else:
                data["intent"] = IntentEnum.PRODUCT_SEARCH.value

    # Usage with soft language → recommendation if still search without hard list-only
    if data.get("intent") in (IntentEnum.PRODUCT_SEARCH.value, IntentEnum.PRODUCT_SEARCH):
        if data.get("usage") and not data.get("product_names"):
            if any(w in msg_lower for w in ("phù hợp", "nên dùng", "gợi ý", "tư vấn", "cần", "cho quán", "để uống")):
                data["intent"] = IntentEnum.PRODUCT_RECOMMENDATION.value

    # Parse user-stated compare names when model/fallback left the list empty
    if data.get("intent") in (IntentEnum.PRODUCT_COMPARE.value, IntentEnum.PRODUCT_COMPARE):
        if not data.get("product_names"):
            data["product_names"] = split_compare_names(message)

    if data.get("intent") in (IntentEnum.PRODUCT_REVIEW.value, IntentEnum.PRODUCT_REVIEW):
        theme = extract_review_theme(message)
        raw_query = (data.get("query") or "").strip()
        if not raw_query or raw_query.lower() == message.strip().lower():
            data["query"] = theme
        leftover = (data.get("query") or "").strip().lower()
        if leftover in {"đánh giá", "danh gia", "review", "reviews", "nhận xét", "nhan xet", "phản hồi", "phan hoi"}:
            data["query"] = None

    # Re-sanitize query after category may have been filled
    data["query"] = _sanitize_query(data.get("query"), data.get("category"))

    return IntentExtractionResult.model_validate(data)


class IntentRouter:
    """Classifies user queries into structured intent objects with validation."""

    def __init__(self, llm=None):
        self.llm = llm or get_chat_model()
        self.fallback = FallbackStructuredLLM()

    async def extract(self, message: str) -> IntentExtractionResult:
        """Extract structured intent and search constraints from a message."""
        clean_msg = message.strip()
        if not clean_msg:
            return IntentExtractionResult(intent=IntentEnum.GENERAL)

        result: Optional[IntentExtractionResult] = None

        if self.llm is not None:
            try:
                structured_llm = self.llm.with_structured_output(IntentExtractionResult)
                messages = [
                    SystemMessage(content=INTENT_EXTRACTION_SYSTEM_PROMPT),
                    HumanMessage(content=clean_msg),
                ]
                raw = await structured_llm.ainvoke(messages)
                if isinstance(raw, IntentExtractionResult):
                    result = raw
                elif isinstance(raw, dict):
                    result = IntentExtractionResult.model_validate(raw)
            except Exception as exc:
                logger.warning(
                    "LLM structured intent extraction failed (%s), falling back to heuristic parser.",
                    exc,
                )

        if result is None:
            raw_dict = self.fallback.extract_intent(clean_msg)
            result = IntentExtractionResult.model_validate(raw_dict)

        normalized = normalize_extraction(clean_msg, result)
        logger.info(
            "intent_extract intent=%s category=%s min=%s max=%s unit=%s query=%s usage=%s",
            normalized.intent.value,
            normalized.category,
            normalized.min_price,
            normalized.max_price,
            normalized.price_unit.value if normalized.price_unit else None,
            normalized.query,
            normalized.usage,
        )
        return normalized
