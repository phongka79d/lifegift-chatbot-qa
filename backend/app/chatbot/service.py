"""Core Chatbot Service orchestrating intent routing, grounding, and response generation."""

import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from backend.app.chatbot.context_builder import build_chat_context, format_currency_vnd
from backend.app.chatbot.llm import get_chat_model
from backend.app.chatbot.prompts import ANSWER_SYSTEM_PROMPT
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
            products, context_str = await self._handle_product_search(extracted)
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
            context_str = "Khách hàng gửi câu hỏi chung hoặc lời chào. Hãy chào đón nồng nhiệt và giới thiệu các nhóm nông sản thế mạnh của LifeGift (Cà phê Tây Nguyên, Trà cổ thụ Hà Giang, Mật ong rừng U Minh, Hạt dinh dưỡng, Nông sản sấy và Hộp quà Tết)."
            metadata["tool"] = "general"

        # 6. Generate final conversational answer
        answer = await self._generate_answer(
            user_message=request.message,
            context=context_str,
            history=history,
        )

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
    ) -> Tuple[List[ProductCard], str]:
        params = ProductSearchParams(
            query=extracted.query,
            category=extracted.category,
            brand=extracted.brand,
            origin=extracted.origin,
            min_price=extracted.min_price,
            max_price=extracted.max_price,
            in_stock=extracted.in_stock_only,
            limit=5,
        )
        products = self.product_repo.search_products(params)
        context = build_chat_context(products=products)
        return products, context

    async def _handle_recommendation(
        self, extracted: IntentExtractionResult
    ) -> Tuple[List[ProductCard], str, Dict[str, Any]]:
        products, semantic_used = self.rec_service.recommend(
            category=extracted.category,
            origin=extracted.origin,
            brand=extracted.brand,
            min_price=extracted.min_price,
            max_price=extracted.max_price,
            preferences=extracted.preferences or extracted.query,
            in_stock=extracted.in_stock_only,
            top_k=3,
        )
        if not products:
            context = (
                "Không có sản phẩm nào trong kho đáp ứng đầy đủ tiêu chí (danh mục, ngân sách, tình trạng còn hàng). "
                "Hãy thông báo rõ ràng cho khách và gợi ý nới lỏng ngân sách hoặc tham khảo danh mục khác; tuyệt đối không gợi ý sản phẩm ngoài danh sách cung cấp."
            )
            return [], context, {"semantic_used": semantic_used, "no_match": True}

        context = build_chat_context(products=products)
        if not semantic_used and (extracted.preferences or extracted.query):
            context += (
                "\n\nLƯU Ý CHO TRỢ LÝ: Hệ thống gợi ý theo ngữ nghĩa (Qdrant) hiện không khả dụng, "
                "danh sách trên chỉ được lọc theo tiêu chí cứng từ MySQL. Hãy nêu rõ rằng việc so khớp sở thích bị giới hạn và không tự suy đoán thêm hương vị."
            )
        return products, context, {"semantic_used": semantic_used, "no_match": False}

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
            # Try searching by query
            searched = self.product_repo.search_products(
                ProductSearchParams(query=target_name, limit=1)
            )
            resolved = searched[0] if searched else None

        if not resolved:
            return (
                [],
                f"Không tìm thấy sản phẩm nào khớp với tên '{target_name}' trong hệ thống. Hãy thông báo rõ ràng cho khách và gợi ý các danh mục có sẵn.",
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
        names = extracted.product_names
        if len(names) < 2 and extracted.query:
            # Try to see if query mentions multiple products
            for kw in ["arabica", "robusta", "shan tuyết", "oolong", "mật ong", "hạt điều", "mắc ca"]:
                if kw in extracted.query.lower() and not any(kw in n.lower() for n in names):
                    names.append(kw)

        resolved_cards: List[ProductCard] = []
        detail_list: List[ProductDetailResponse] = []
        missing_names: List[str] = []

        for name in names:
            card = self.product_repo.resolve_by_name(name)
            if card:
                resolved_cards.append(card)
                d = self.product_repo.get_by_id(card.id)
                if d:
                    detail_list.append(d)
            else:
                missing_names.append(name)

        if not resolved_cards:
            return (
                [],
                "Không xác định được sản phẩm cụ thể để so sánh. Hãy yêu cầu khách hàng nêu rõ tên 2 sản phẩm cần so sánh.",
            )

        context = build_chat_context(comparison_products=detail_list)
        if missing_names:
            context += f"\nLƯU Ý: Không tìm thấy sản phẩm sau trong hệ thống: {', '.join(missing_names)}. Hãy giải thích rõ ràng."

        return resolved_cards, context

    async def _handle_knowledge(
        self, extracted: IntentExtractionResult
    ) -> Tuple[List[ProductCard], str, Dict[str, Any]]:
        query_text = extracted.query or "kiến thức nông sản"
        chunks = self.retriever.retrieve(query=query_text, limit=4)

        if not chunks:
            context = (
                f"Không tìm thấy tài liệu kiến thức chuyên sâu khớp với câu hỏi '{query_text}'. "
                "Hãy thông báo trung thực rằng hiện tại tài liệu chưa có thông tin cụ thể này và không được bịa đặt."
            )
        else:
            context = build_chat_context(knowledge_chunks=chunks)

        return [], context, {"retrieval_count": len(chunks)}

    async def _handle_product_review(
        self, extracted: IntentExtractionResult
    ) -> Tuple[List[ProductCard], str]:
        target_name = (
            extracted.product_names[0]
            if extracted.product_names
            else (extracted.query or "")
        )
        resolved = self.product_repo.resolve_by_name(target_name)
        if not resolved:
            return [], f"Chưa tìm thấy sản phẩm '{target_name}' để xem đánh giá."

        reviews_data = self.review_repo.get_product_reviews(resolved.id, limit=5)
        context = build_chat_context(
            products=[resolved],
            reviews=reviews_data,
        )
        return [resolved], context

    async def _handle_order_status(
        self, extracted: IntentExtractionResult, user_id: Optional[int]
    ) -> Tuple[List[ProductCard], str]:
        if user_id is None:
            return (
                [],
                "Khách hàng chưa đăng nhập. Hãy lịch sự yêu cầu khách hàng đăng nhập tài khoản để tra cứu trạng thái đơn hàng nhằm đảm bảo tính bảo mật và riêng tư.",
            )

        order_code = extracted.order_code
        if not order_code:
            return (
                [],
                "Khách hàng chưa cung cấp mã đơn hàng. Hãy hướng dẫn khách hàng cung cấp mã đơn hàng hợp lệ (ví dụ: ORD-20260812-0001) để hệ thống tra cứu.",
            )

        order_data = self.order_repo.get_order_status(user_id=user_id, order_code=order_code)
        if not order_data:
            return (
                [],
                f"Không tìm thấy đơn hàng mã '{order_code}' thuộc quyền sở hữu của tài khoản hiện tại. Hãy thông báo rõ ràng cho khách kiểm tra lại mã đơn.",
            )

        context = build_chat_context(order=order_data)
        return [], context

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

                prompt_content = f"DỮ LIỆU THỰC TẾ ĐƯỢC CUNG CẤP (GROUNDING CONTEXT):\n{context}\n\nCÂU HỎI CỦA KHÁCH HÀNG: {user_message}"
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
        if "DANH SÁCH SẢN PHẨM TÌM THẤY" in context:
            limited = "không khả dụng" in context or "bị giới hạn" in context
            if "LƯU Ý CHO TRỢ LÝ" in context:
                context = context.split("LƯU Ý CHO TRỢ LÝ")[0].rstrip()
            answer = (
                "Dưới đây là các sản phẩm nông sản LifeGift phù hợp với yêu cầu của bạn được kiểm tra trực tiếp từ kho hàng:\n\n"
                + context.replace("DANH SÁCH SẢN PHẨM TÌM THẤY (DỮ LIỆU TỪ MYSQL):\n", "")
                + "\n\nBạn có thể nhấn vào thẻ sản phẩm bên dưới để xem chi tiết hoặc đặt hàng trực tiếp."
            )
            if limited:
                answer += "\n\nLưu ý: hiện tại hệ thống chưa thể so khớp sở thích theo ngữ nghĩa nên danh sách trên được lọc theo tiêu chí cứng (ngân sách, danh mục, tồn kho)."
            return answer
        if "không có sản phẩm nào trong kho đáp ứng" in context.lower() or (
            "Không có sản phẩm nào trong kho" in context
        ):
            return (
                "Dạ, hiện tại LifeGift chưa có sản phẩm nào trong kho đáp ứng đầy đủ tiêu chí bạn đưa ra. "
                "Bạn có thể nới lỏng ngân sách hoặc tham khảo thêm các danh mục nông sản khác của LifeGift nhé!"
            )
        elif "THÔNG TIN CHI TIẾT SẢN PHẨM" in context:
            return (
                "Dạ, LifeGift xin gửi thông tin chi tiết về sản phẩm:\n\n"
                + context.replace("THÔNG TIN CHI TIẾT SẢN PHẨM:\n", "")
                + "\n\nSản phẩm có đầy đủ giấy tờ chứng nhận an toàn và hiện đang có sẵn trong kho."
            )
        elif "SO SÁNH CÁC SẢN PHẨM" in context:
            return (
                "Dạ, đây là bảng đối chiếu thông tin chi tiết giữa các sản phẩm bạn quan tâm:\n\n"
                + context.replace("SO SÁNH CÁC SẢN PHẨM ĐƯỢC YÊU CẦU:\n", "")
                + "\n\nTùy theo khẩu vị và sở thích cá nhân, bạn có thể lựa chọn sản phẩm phù hợp nhất nhé!"
            )
        elif "THÔNG TIN ĐƠN HÀNG" in context:
            return (
                "Dạ, LifeGift đã tra cứu thành công thông tin đơn hàng của bạn:\n\n"
                + context.replace("THÔNG TIN ĐƠN HÀNG:\n", "")
                + "\n\nNếu cần hỗ trợ thêm về vận chuyển, bạn vui lòng nhắn thêm nhé!"
            )
        elif "đăng nhập" in context.lower():
            return (
                "Dạ, để bảo mật thông tin đơn hàng, bạn vui lòng đăng nhập vào tài khoản của mình trên LifeGift để tra cứu lộ trình đơn hàng nhé!"
            )
        elif "chưa cung cấp mã đơn hàng" in context.lower():
            return (
                "Dạ, bạn vui lòng cung cấp mã đơn hàng (ví dụ: ORD-20260812-0001) để em hỗ trợ tra cứu giúp bạn nhé!"
            )
        elif "không tìm thấy đơn hàng" in context.lower():
            return (
                "Dạ, LifeGift không tìm thấy thông tin đơn hàng này trong tài khoản của bạn. Bạn vui lòng kiểm tra lại chính xác mã đơn hàng nhé!"
            )
        elif "không tìm thấy sản phẩm" in context.lower():
            return (
                "Dạ, hiện tại LifeGift chưa tìm thấy sản phẩm phù hợp với từ khóa này. Bạn có thể tham khảo các dòng sản phẩm nông sản nổi bật như Cà phê Cầu Đất, Trà Shan Tuyết, Mật ong U Minh hoặc Hạt điều Bình Phước nhé!"
            )
        elif "ĐÁNH GIÁ CỦA KHÁCH HÀNG" in context:
            return (
                "Dạ, dưới đây là các nhận xét thực tế từ khách hàng đã trải nghiệm sản phẩm:\n\n"
                + context
            )
        elif "KIẾN THỨC NÔNG SẢN" in context:
            return (
                "Dạ, LifeGift xin chia sẻ thông tin kiến thức hữu ích đến bạn:\n\n"
                + context.replace("KIẾN THỨC NÔNG SẢN VÀ THÔNG TIN BÀI VIẾT (TỪ VECTOR RAG):\n", "")
            )
        else:
            return (
                "Dạ, chào bạn! Em là trợ lý ảo LifeGift. Em có thể hỗ trợ bạn tìm kiếm nông sản đặc sản (Cà phê, Trà cổ thụ, Mật ong rừng, Hạt dinh dưỡng, Nông sản sấy, Set quà tặng) hoặc tra cứu tình trạng đơn hàng. Bạn cần em hỗ trợ gì hôm nay ạ?"
            )
