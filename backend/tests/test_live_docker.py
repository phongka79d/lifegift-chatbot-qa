"""Live integration tests executing against running Docker MySQL and Qdrant instances."""

import os
import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.core.database import get_engine, get_db_context
from backend.app.core.qdrant import get_qdrant_client
from backend.app.main import create_app
from backend.app.repositories.product_repository import ProductRepository
from backend.app.repositories.order_repository import OrderRepository
from backend.app.rag.retriever import QdrantRetriever
from backend.app.chatbot.service import ChatbotService
from backend.app.schemas.chat import ChatRequest


def test_live_mysql_connection():
    """Verify live connection and tables in Docker MySQL container."""
    with get_db_context() as session:
        result = session.execute(text("SELECT COUNT(*) FROM products WHERE status = 'ACTIVE'")).scalar()
        assert result >= 15, f"Expected at least 15 active products in MySQL, found {result}"


def test_live_mysql_effective_price_and_inventory():
    """Verify live effective_price generated column and inventory stock summing."""
    with get_db_context() as session:
        repo = ProductRepository(session)
        detail = repo.get_by_id(product_id=1)
        assert detail is not None
        assert detail.name == "Cà phê Arabica Cầu Đất 500g"
        assert detail.price == 260000.0
        assert detail.sale_price == 239000.0
        assert detail.effective_price == 239000.0
        assert detail.available_quantity == 85
        assert detail.is_available is True
        assert len(detail.certificates) == 2


def test_live_qdrant_retrieval():
    """Verify live Qdrant container contains the indexed 26 documents and returns hits."""
    retriever = QdrantRetriever()
    results = retriever.retrieve("trà Shan Tuyết cổ thụ", limit=3)
    assert len(results) > 0
    assert any("Shan Tuyết" in r["content"] for r in results)


def test_live_chatbot_knowledge_rag():
    """Verify live ChatbotService queries Qdrant knowledge layer."""
    with get_db_context() as session:
        service = ChatbotService(session=session)
        req = ChatRequest(message="Lợi ích sức khỏe của trà Shan Tuyết cổ thụ là gì?")
        import asyncio
        response = asyncio.run(service.handle_chat(req))

        assert response.intent == "KNOWLEDGE"
        assert response.answer is not None
        assert len(response.answer) > 0


def test_live_chatbot_order_status_authenticated():
    """Verify live ChatbotService queries MySQL order status for authenticated user."""
    with get_db_context() as session:
        service = ChatbotService(session=session)
        req = ChatRequest(message="Tra cứu đơn hàng ORD-20260812-0001")
        import asyncio
        response = asyncio.run(service.handle_chat(req, user_id=1))

        assert response.intent == "ORDER_STATUS"
        assert "ORD-20260812-0001" in response.answer
        assert "SHIPPING" in response.answer


def test_live_fastapi_endpoints():
    """Verify live FastAPI app responds to HTTP requests using live MySQL."""
    app = create_app()
    with TestClient(app) as client:
        # Health check
        res_health = client.get("/api/health")
        assert res_health.status_code == 200

        # Product detail
        res_prod = client.get("/api/products/1")
        assert res_prod.status_code == 200
        data_prod = res_prod.json()
        assert data_prod["id"] == 1
        assert data_prod["effective_price"] == 239000.0

        # Chat endpoint
        res_chat = client.post("/api/chat", json={"message": "Có cà phê nào dưới 250k không?"})
        assert res_chat.status_code == 200
        data_chat = res_chat.json()
        assert len(data_chat["products"]) > 0
