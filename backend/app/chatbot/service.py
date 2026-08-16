"""Core Chatbot Service orchestrating intent routing, grounding, and response generation."""

import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from backend.app.chatbot.context_builder import build_chat_context, format_currency_vnd
from backend.app.chatbot.llm import (
    get_chat_model,
    is_review_quality_theme,
    parse_review_min_rating,
)
from backend.app.chatbot.prompts import (
    ANSWER_SYSTEM_PROMPT,
    LABELS,
    load_note,
    render_note,
)
from backend.app.chatbot.router import IntentRouter
from backend.app.rag.retriever import QdrantRetriever
from backend.app.repositories.chat_repository import ChatRepository
from backend.app.repositories.order_repository import OrderRepository
from backend.app.repositories.product_repository import ProductRepository
from backend.app.repositories.review_repository import ReviewRepository
from backend.app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    IntentEnum,
    IntentExtractionResult,
    OrderStatusResponse,
    PriceUnitEnum,
)
from backend.app.schemas.product import ProductCard, ProductDetailResponse, ProductSearchParams
from backend.app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)


class ChatbotService:
    """Orchestrates deterministic intent dispatch, grounded context assembly, and conversation memory."""

    def __init__(
        self,
        session: Session,
        router: Optional[IntentRouter] = None,
        retriever: Optional[QdrantRetriever] = None,
        llm=None,
    ):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.review_repo = ReviewRepository(session)
        self.order_repo = OrderRepository(session)
        self.chat_repo = ChatRepository(session)
        self.retriever = retriever or QdrantRetriever()
        self.rec_service = RecommendationService(self.product_repo, self.retriever)
        self.router = router or IntentRouter()
        self.llm = llm or get_chat_model()

    async def handle_chat(
        self, request: ChatRequest, user_id: Optional[int] = None
    ) -> ChatResponse:
        """Handle a single chat turn with persistence and grounded routing."""
        # 1. Session management & Ownership check
        session_id = self.chat_repo.get_or_create_session(
            session_id=request.session_id,
            user_id=user_id,
        )

        # 2. Persist user message
        self.chat_repo.save_message(
            session_id=session_id,
            role="USER",
            content=request.message,
        )

        # 3. Load recent chat history for context (last 6 messages)
        history = self.chat_repo.get_recent_messages(session_id=session_id, limit=6)

        # 4. Intent Classification and extraction
        extracted = await self.router.extract(request.message)
        intent = extracted.intent

        # 5. Deterministic intent routing
        products: List[ProductCard] = []
        context_str = ""
        metadata: Dict[str, Any] = {"intent": intent.value}

        if intent == IntentEnum.PRODUCT_SEARCH:
            products, context_str, search_meta = await self._handle_product_search(extracted)
            metadata.update(search_meta)
            metadata["tool"] = "search_products"
        elif intent == IntentEnum.PRODUCT_RECOMMENDATION:
            products, context_str, rec_meta = await self._handle_recommendation(extracted)
            metadata.update(rec_meta)
            metadata["tool"] = "recommendation_service"
        elif intent == IntentEnum.PRODUCT_DETAIL:
            products, context_str, meta = await self._handle_product_detail(extracted)
            metadata.update(meta)
            metadata["tool"] = "get_product"
        elif intent == IntentEnum.PRODUCT_COMPARE:
            products, context_str = await self._handle_product_compare(extracted)
            metadata["tool"] = "compare_products"
        elif intent == IntentEnum.KNOWLEDGE:
            products, context_str, meta = await self._handle_knowledge(extracted)
            metadata.update(meta)
            metadata["tool"] = "search_knowledge"
        elif intent == IntentEnum.PRODUCT_REVIEW:
            products, context_str = await self._handle_product_review(extracted)
            metadata["tool"] = "get_product_reviews"
        elif intent == IntentEnum.ORDER_STATUS:
            products, context_str = await self._handle_order_status(extracted, user_id)
            metadata["tool"] = "get_order_status"
        else:
            context_str = load_note("general_greeting")
            metadata["tool"] = "general"

        # 6. Generate final conversational answer (grounded; fall back if LLM ignores product list)
        answer = await self._generate_answer(
            user_message=request.message,
            context=context_str,
            history=history,
        )
        if products and self._answer_ignores_products(answer, products):
            logger.warning(
                "LLM answer ignored %d grounded products; using deterministic formatter.",
                len(products),
            )
            answer = self._format_deterministic_fallback(request.message, context_str)

        # 7. Persist assistant message
        self.chat_repo.save_message(
            session_id=session_id,
            role="ASSISTANT",
            content=answer,
            metadata={
                "intent": intent.value,
                "product_ids": [p.id for p in products],
            },
        )

        return ChatResponse(
            session_id=session_id,
            intent=intent.value,
            answer=answer,
            products=products,
            metadata=metadata,
        )

    async def _handle_product_search(
        self, extracted: IntentExtractionResult
    ) -> Tuple[List[ProductCard], str, Dict[str, Any]]:
        price_unit = (
            extracted.price_unit.value
            if getattr(extracted, "price_unit", None)
            else PriceUnitEnum.PACKAGE.value
        )
        # Progressive relaxation: only drop free-text query / stock-only — never hard filters
        attempts = [
            ProductSearchParams(
                query=extracted.query,
                category=extracted.category,
                brand=extracted.brand,
                origin=extracted.origin,
                min_price=extracted.min_price,
                max_price=extracted.max_price,
                price_unit=price_unit,
                in_stock=extracted.in_stock_only,
                limit=5,
            ),
            ProductSearchParams(
                query=None,
                category=extracted.category,
                brand=extracted.brand,
                origin=extracted.origin,
                min_price=extracted.min_price,
                max_price=extracted.max_price,
                price_unit=price_unit,
                in_stock=extracted.in_stock_only,
                limit=5,
            ),
            ProductSearchParams(
                query=None,
                category=extracted.category,
                brand=extracted.brand,
                origin=extracted.origin,
                min_price=extracted.min_price,
                max_price=extracted.max_price,
                price_unit=price_unit,
                in_stock=False,
                limit=5,
            ),
        ]

        result = None
        for params in attempts:
            result = self.product_repo.search_products_detailed(params)
            if result.products:
                break
            # Unknown category will never recover by relaxing query/stock
            if result.empty_reason == "UNKNOWN_CATEGORY":
                break

        assert result is not None
        products = result.products[:5]
        meta = {
            "applied_filters": result.applied_filters,
            "empty_reason": result.empty_reason,
            "price_unit": price_unit,
            "available_categories": result.available_categories,
        }

        context = build_chat_context(
            products=products or None,
            applied_filters=result.applied_filters,
            empty_reason=result.empty_reason,
            available_categories=result.available_categories or None,
        )
        if products:
            note_name = "per_kg" if price_unit == PriceUnitEnum.PER_KG.value else "package_price"
            context += f"\n\n{LABELS['ASSISTANT_NOTE']} {load_note(note_name)}"
        return products, context, meta

    async def _handle_recommendation(
        self, extracted: IntentExtractionResult
    ) -> Tuple[List[ProductCard], str, Dict[str, Any]]:
        # Prefer usage/preferences text for soft ranking
        soft = extracted.preferences or extracted.usage or extracted.query
        price_unit = (
            extracted.price_unit.value
            if getattr(extracted, "price_unit", None)
            else PriceUnitEnum.PACKAGE.value
        )
        products, semantic_used = self.rec_service.recommend(
            category=extracted.category,
            origin=extracted.origin,
            brand=extracted.brand,
            min_price=extracted.min_price,
            max_price=extracted.max_price,
            price_unit=price_unit,
            preferences=soft,
            in_stock=extracted.in_stock_only,
            top_k=3,
        )
        if not products:
            facets = self.product_repo.list_available_categories()
            context = build_chat_context(
                empty_reason="NO_MATCH_FILTERS",
                available_categories=facets,
                applied_filters={
                    "category": extracted.category,
                    "origin": extracted.origin,
                    "brand": extracted.brand,
                    "min_price": extracted.min_price,
                    "max_price": extracted.max_price,
                    "price_unit": price_unit,
                    "usage": soft,
                },
            )
            return [], context, {
                "semantic_used": semantic_used,
                "no_match": True,
                "price_unit": price_unit,
            }

        context = build_chat_context(products=products)
        if not semantic_used and soft:
            context += f"\n\n{LABELS['ASSISTANT_NOTE']} {load_note('semantic_unavailable')}"
        return products, context, {
            "semantic_used": semantic_used,
            "no_match": False,
            "price_unit": price_unit,
        }

    async def _handle_product_detail(
        self, extracted: IntentExtractionResult
    ) -> Tuple[List[ProductCard], str, Dict[str, Any]]:
        # Try resolving product
        target_name = (
            extracted.product_names[0]
            if extracted.product_names
            else (extracted.query or "")
        )
        resolved = self.product_repo.resolve_by_name(target_name)
        if not resolved:
            # Try searching by query — reject if a digit-code token (e.g. st25) is missing
            searched = self.product_repo.search_products(
                ProductSearchParams(query=target_name, limit=1)
            )
            if searched:
                hit = searched[0]
                extra = [
                    t
                    for t in re.findall(r"[a-z0-9]+", (target_name or "").lower())
                    if t not in (hit.name or "").lower()
                ]
                if any(any(ch.isdigit() for ch in t) for t in extra):
                    resolved = None
                else:
                    resolved = hit

        if not resolved:
            return (
                [],
                render_note("product_not_found", target_name=target_name),
                {"retrieval_count": 0},
            )

        detail = self.product_repo.get_by_id(resolved.id)
        # Also fetch relevant knowledge chunks for this product if available
        k_chunks = self.retriever.retrieve(
            query=target_name,
            product_id=resolved.id,
            limit=2,
        )

        context = build_chat_context(
            product_detail=detail,
            knowledge_chunks=k_chunks,
        )
        return [resolved], context, {"retrieval_count": len(k_chunks)}

    async def _handle_product_compare(
        self, extracted: IntentExtractionResult
    ) -> Tuple[List[ProductCard], str]:
        # Only use names the extractor provided — never invent SKUs from keyword lists
        names = list(extracted.product_names or [])

        resolved_cards: List[ProductCard] = []
        detail_list: List[ProductDetailResponse] = []
        missing_names: List[str] = []
        seen_ids = set()

        for name in names:
            card = self.product_repo.resolve_by_name(name)
            if card and card.id not in seen_ids:
                seen_ids.add(card.id)
                resolved_cards.append(card)
                d = self.product_repo.get_by_id(card.id)
                if d:
                    detail_list.append(d)
            else:
                missing_names.append(name)

        if len(resolved_cards) < 2:
            # Same constrained search as product search (category/query/price_unit/min/max)
            products, search_context, _meta = await self._handle_product_search(extracted)
            notice = load_note("compare_insufficient")
            if missing_names:
                notice += " " + render_note(
                    "compare_missing_names", missing_names=", ".join(missing_names)
                )
            elif names:
                notice += " The stated names did not resolve to two catalog SKUs."
            else:
                notice += " The question did not name two specific products."
            context = notice + "\n\n" + search_context
            return products, context

        context = build_chat_context(comparison_products=detail_list)
        if missing_names:
            context += "\n" + render_note(
                "compare_missing_names", missing_names=", ".join(missing_names)
            )

        return resolved_cards, context

    async def _handle_knowledge(
        self, extracted: IntentExtractionResult
    ) -> Tuple[List[ProductCard], str, Dict[str, Any]]:
        query_text = extracted.query or "kiến thức nông sản"
        chunks = self.retriever.retrieve(query=query_text, limit=4)

        if not chunks:
            context = render_note("knowledge_not_found", query_text=query_text)
        else:
            context = build_chat_context(knowledge_chunks=chunks)

        return [], context, {"retrieval_count": len(chunks)}

    async def _handle_product_review(
        self, extracted: IntentExtractionResult
    ) -> Tuple[List[ProductCard], str]:
        min_rating = parse_review_min_rating(extracted.preferences, extracted.query)
        quality = min_rating is not None or is_review_quality_theme(
            extracted.preferences
        ) or is_review_quality_theme(extracted.query)

        target_name = (
            extracted.product_names[0]
            if extracted.product_names
            else None
        )
        if target_name and (
            parse_review_min_rating(target_name) is not None
            or is_review_quality_theme(target_name)
        ):
            target_name = None
        resolved = self.product_repo.resolve_by_name(target_name) if target_name else None
        # Only treat leftover query as a SKU when it is not a rating/quality phrase
        if not resolved and extracted.query and not quality:
            maybe = self.product_repo.resolve_by_name(extracted.query)
            if maybe:
                resolved = maybe

        if resolved:
            reviews_data = self.review_repo.get_product_reviews(resolved.id, limit=5)
            context = build_chat_context(
                products=[resolved],
                reviews=reviews_data,
            )
            return [resolved], context

        category_id = None
        if extracted.category:
            category_id, cat_ok = self.product_repo.resolve_category_id(extracted.category)
            if not cat_ok:
                category_id = None

        # Never LIKE-search rating floors ("đánh giá trên 5 sao") or quality adjectives.
        review_text = None if quality else extracted.query
        hits = self.review_repo.list_reviewed_products(
            review_text=review_text,
            category_id=category_id,
            min_avg_rating=min_rating if min_rating is not None else (4.0 if quality else None),
            limit=5,
        )
        if not hits:
            theme = review_text or extracted.category or "review"
            return [], render_note(
                "reviews_none_matching",
                theme=theme,
            )

        cards = self.product_repo.get_by_ids([h["product_id"] for h in hits])
        by_id = {c.id: c for c in cards}
        ordered: List[ProductCard] = []
        for hit in hits:
            card = by_id.get(hit["product_id"])
            if not card:
                continue
            title = hit.get("sample_title") or ""
            snippet = (hit.get("sample_content") or "")[:120]
            rating = hit.get("sample_rating")
            star = f"{rating}★ " if rating is not None else ""
            card.reason = f'{star}"{title}" — {snippet}'.strip(" —")
            ordered.append(card)

        first_reviews = self.review_repo.get_product_reviews(ordered[0].id, limit=3)
        context = build_chat_context(products=ordered, reviews=first_reviews)
        theme_clause = f" matching '{extracted.query}'" if extracted.query else ""
        context += (
            f"\n\n{LABELS['ASSISTANT_NOTE']} "
            + render_note("review_discovery", theme_clause=theme_clause)
        )
        return ordered, context

    async def _handle_order_status(
        self, extracted: IntentExtractionResult, user_id: Optional[int]
    ) -> Tuple[List[ProductCard], str]:
        if user_id is None:
            return (
                [],
                load_note("order_login_required"),
            )

        order_code = extracted.order_code
        if not order_code:
            return (
                [],
                load_note("order_code_missing"),
            )

        order_data = self.order_repo.get_order_status(user_id=user_id, order_code=order_code)
        if not order_data:
            return (
                [],
                render_note("order_not_found", order_code=order_code),
            )

        context = build_chat_context(order=order_data)
        return [], context

    def _answer_ignores_products(self, answer: str, products: List[ProductCard]) -> bool:
        """Detect ungrounded answers that claim no data despite non-empty product results."""
        if not answer or not products:
            return False
        lower = answer.lower()
        denial_markers = (
            "chưa có dữ liệu",
            "chưa có thông tin",
            "không có dữ liệu",
            "chưa có sản phẩm",
            "không có sản phẩm",
            "chưa có thông tin chính xác",
            "chưa có dữ liệu cụ thể",
            "vui lòng liên hệ trực tiếp",
        )
        if not any(m in lower for m in denial_markers):
            return False
        # If a product is clearly named (full name or a distinctive multi-char token), treat as grounded
        for p in products:
            name_l = (p.name or "").lower()
            if name_l and name_l in lower:
                return False
            # Use a mid-length token from the product name (skip very short generic words)
            for token in name_l.replace("-", " ").split():
                if len(token) >= 5 and token in lower:
                    return False
        return True

    async def _generate_answer(
        self, user_message: str, context: str, history: List[Any]
    ) -> str:
        """Invoke LLM with grounded system prompt and context or format deterministic template."""
        if self.llm is not None:
            try:
                messages = [SystemMessage(content=ANSWER_SYSTEM_PROMPT)]
                # Add past turn context
                for m in history[:-1]:  # Exclude current message
                    if m.role == "USER":
                        messages.append(HumanMessage(content=m.content))
                    else:
                        messages.append(AIMessage(content=m.content))

                prompt_content = render_note(
                    "human_turn", context=context, user_message=user_message
                )
                messages.append(HumanMessage(content=prompt_content))

                response = await self.llm.ainvoke(messages)
                if response and response.content:
                    return response.content.strip()
            except Exception as exc:
                logger.warning("LLM answer generation failed (%s), using deterministic fallback.", exc)

        # High-quality deterministic fallback response formatting
        return self._format_deterministic_fallback(user_message, context)

    def _format_deterministic_fallback(self, user_message: str, context: str) -> str:
        """Deterministic, grounded answer formatter for offline / test environments."""
        products_header = LABELS["PRODUCTS_FOUND"]
        if products_header in context or "PRODUCTS FOUND" in context:
            limited = "preference matching is limited" in context.lower()
            note_mark = LABELS["ASSISTANT_NOTE"]
            if note_mark in context:
                context = context.split(note_mark)[0].rstrip()
            answer = (
                "Dưới đây là các sản phẩm nông sản LifeGift phù hợp với yêu cầu của bạn được kiểm tra trực tiếp từ kho hàng:\n\n"
                + context.replace(products_header + "\n", "")
                + "\n\nBạn có thể nhấn vào thẻ sản phẩm bên dưới để xem chi tiết hoặc đặt hàng trực tiếp."
            )
            if limited:
                answer += "\n\nLưu ý: hiện tại hệ thống chưa thể so khớp sở thích theo ngữ nghĩa nên danh sách trên được lọc theo tiêu chí cứng (ngân sách, danh mục, tồn kho)."
            return answer
        if LABELS["NO_MATCH"] in context or "NO PRODUCTS MATCH FILTERS" in context:
            answer = (
                "Dạ, hiện tại LifeGift chưa có sản phẩm nào trong kho khớp đúng bộ lọc bạn đưa ra. "
                "Bạn có thể nới lỏng ngân sách, danh mục hoặc tiêu chí khác nhé!"
            )
            cat_prefix = LABELS["AVAILABLE_CATEGORIES"].lower()
            for line in context.splitlines():
                if line.strip().lower().startswith(cat_prefix.lower()):
                    answer += f"\n\n{line.strip()}"
                    break
            return answer
        elif LABELS["PRODUCT_DETAIL"] in context:
            return (
                "Dạ, LifeGift xin gửi thông tin chi tiết về sản phẩm:\n\n"
                + context.replace(LABELS["PRODUCT_DETAIL"] + "\n", "")
                + "\n\nSản phẩm có đầy đủ giấy tờ chứng nhận an toàn và hiện đang có sẵn trong kho."
            )
        elif LABELS["COMPARISON"] in context:
            return (
                "Dạ, đây là bảng đối chiếu thông tin chi tiết giữa các sản phẩm bạn quan tâm:\n\n"
                + context.replace(LABELS["COMPARISON"] + "\n", "")
                + "\n\nTùy theo khẩu vị và sở thích cá nhân, bạn có thể lựa chọn sản phẩm phù hợp nhất nhé!"
            )
        elif LABELS["ORDER"] in context:
            return (
                "Dạ, LifeGift đã tra cứu thành công thông tin đơn hàng của bạn:\n\n"
                + context.replace(LABELS["ORDER"] + "\n", "")
                + "\n\nNếu cần hỗ trợ thêm về vận chuyển, bạn vui lòng nhắn thêm nhé!"
            )
        elif "not logged in" in context.lower() or "sign in" in context.lower():
            return (
                "Dạ, để bảo mật thông tin đơn hàng, bạn vui lòng đăng nhập vào tài khoản của mình trên LifeGift để tra cứu lộ trình đơn hàng nhé!"
            )
        elif "no order code" in context.lower() or "ord-20260812-0001" in context.lower():
            return (
                "Dạ, bạn vui lòng cung cấp mã đơn hàng (ví dụ: ORD-20260812-0001) để em hỗ trợ tra cứu giúp bạn nhé!"
            )
        elif "order" in context.lower() and "not found" in context.lower():
            return (
                "Dạ, LifeGift không tìm thấy thông tin đơn hàng này trong tài khoản của bạn. Bạn vui lòng kiểm tra lại chính xác mã đơn hàng nhé!"
            )
        elif "no product matched" in context.lower() or "reviews cannot be shown" in context.lower():
            return (
                "Dạ, hiện tại LifeGift chưa tìm thấy sản phẩm phù hợp với từ khóa này. Bạn có thể tham khảo các dòng sản phẩm nông sản nổi bật như Cà phê Cầu Đất, Trà Shan Tuyết, Mật ong U Minh hoặc Hạt điều Bình Phước nhé!"
            )
        elif LABELS["REVIEWS_HEADER"] in context:
            return (
                "Dạ, dưới đây là các nhận xét thực tế từ khách hàng đã trải nghiệm sản phẩm:\n\n"
                + context
            )
        elif LABELS["KNOWLEDGE"] in context:
            return (
                "Dạ, LifeGift xin chia sẻ thông tin kiến thức hữu ích đến bạn:\n\n"
                + context.replace(LABELS["KNOWLEDGE"] + "\n", "")
            )
        else:
            return (
                "Dạ, chào bạn! Em là trợ lý ảo LifeGift. Em có thể hỗ trợ bạn tìm kiếm nông sản đặc sản (Cà phê, Trà cổ thụ, Mật ong rừng, Hạt dinh dưỡng, Nông sản sấy, Set quà tặng) hoặc tra cứu tình trạng đơn hàng. Bạn cần em hỗ trợ gì hôm nay ạ?"
            )
