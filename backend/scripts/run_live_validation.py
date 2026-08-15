"""Comprehensive live verification runner testing MySQL, Qdrant, Embedding, LLM/Router, Service, and API."""

import asyncio
import json
import logging
import sys
import time
from typing import Dict, Any

from fastapi.testclient import TestClient
from sqlalchemy import text

# Force UTF-8 output
sys.stdout.reconfigure(encoding="utf-8")

from backend.app.core.config import get_settings
from backend.app.core.database import get_engine, get_db_context
from backend.app.core.qdrant import get_qdrant_client
from backend.app.main import create_app
from backend.app.rag.embeddings import get_embedding_client
from backend.app.rag.retriever import QdrantRetriever
from backend.app.chatbot.router import IntentRouter
from backend.app.chatbot.service import ChatbotService
from backend.app.schemas.chat import ChatRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("live_tester")


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f" >>> {title}")
    print("=" * 70)


def test_layer1_mysql():
    print_header("LAYER 1: Live MySQL Database (Docker container on port 3307)")
    with get_db_context() as session:
        # Check active products count
        prod_count = session.execute(text("SELECT COUNT(*) FROM products WHERE status = 'ACTIVE'")).scalar()
        print(f"[OK] Active products in MySQL: {prod_count}")
        assert prod_count >= 15

        # Check effective price generated column
        rows = session.execute(text("""
            SELECT id, name, price, sale_price, COALESCE(sale_price, price) as eff_price 
            FROM products WHERE sale_price IS NOT NULL LIMIT 3
        """)).fetchall()
        for r in rows:
            print(f"     - [{r.id}] {r.name}: Original {float(r.price):,.0f}d -> Sale {float(r.sale_price):,.0f}d (Effective: {float(r.eff_price):,.0f}d)")
            assert float(r.eff_price) == float(r.sale_price)

        # Check total inventory count
        total_stock = session.execute(text("SELECT SUM(available_quantity) FROM inventories")).scalar()
        print(f"[OK] Total inventory stock units across warehouses: {total_stock}")
        assert total_stock > 500

        # Check active certificates
        cert_count = session.execute(text("SELECT COUNT(*) FROM product_certificates WHERE status = 'ACTIVE'")).scalar()
        print(f"[OK] Active quality certificates: {cert_count}")
        assert cert_count >= 5

        # Check approved reviews
        rev_count = session.execute(text("SELECT COUNT(*) FROM reviews WHERE status = 'APPROVED'")).scalar()
        print(f"[OK] Approved customer reviews: {rev_count}")
        assert rev_count >= 4


def test_layer2_qdrant():
    print_header("LAYER 2: Live Qdrant Vector DB (Docker container on port 6333)")
    settings = get_settings()
    client = get_qdrant_client()

    # Collection info
    info = client.get_collection(settings.QDRANT_COLLECTION)
    points_count = info.points_count
    print(f"[OK] Qdrant Collection: '{settings.QDRANT_COLLECTION}'")
    print(f"[OK] Total indexed vector points: {points_count}")
    print(f"[OK] Vectors status: {info.status.value}")
    assert points_count >= 20


def test_layer3_embeddings():
    print_header("LAYER 3: Embedding Model & Vector Similarity")
    client = get_embedding_client()
    text1 = "Cà phê Arabica Cầu Đất thơm nhẹ ít đắng"
    text2 = "Cà phê Cầu Đất Đà Lạt hương hoa quả chua thanh"
    text3 = "Hạt điều rang muối Bình Phước giòn rụm"

    vec1 = client.embed_query(text1)
    vec2 = client.embed_query(text2)
    vec3 = client.embed_query(text3)

    dim = len(vec1)
    print(f"[OK] Embedding Vector Dimension: {dim}")
    assert dim == 1536

    # Calculate cosine similarity
    def dot_product(v1, v2):
        return sum(a * b for a, b in zip(v1, v2))

    sim12 = dot_product(vec1, vec2)
    sim13 = dot_product(vec1, vec3)

    print(f"[OK] Similarity (Coffee 1 vs Coffee 2): {sim12:.4f}")
    print(f"[OK] Similarity (Coffee 1 vs Cashew Nut): {sim13:.4f}")
    assert sim12 > sim13, "Semantic similarity of related coffee queries should exceed unrelated cashew query"


def test_layer4_intent_routing():
    print_header("LAYER 4: Intent Router & Vietnamese Query Parsing")
    router = IntentRouter()
    test_queries = [
        ("Có cà phê nào dưới 200 nghìn không?", "PRODUCT_SEARCH", "cà phê", 200000.0),
        ("Gợi ý trà cổ thụ thơm ngon giúp ngủ ngon", "PRODUCT_RECOMMENDATION", "trà", None),
        ("So sánh Arabica Cầu Đất và Robusta Buôn Ma Thuột", "PRODUCT_COMPARE", None, None),
        ("Lợi ích sức khỏe của trà Shan Tuyết cổ thụ là gì?", "KNOWLEDGE", None, None),
        ("Cà phê Arabica Cầu Đất 500g còn hàng không?", "PRODUCT_DETAIL", None, None),
        ("Khách hàng đánh giá thế nào về Mật ong U Minh?", "PRODUCT_REVIEW", None, None),
        ("Tra cứu đơn hàng ORD-20260812-0001 của tôi", "ORDER_STATUS", None, None),
        ("Xin chào LifeGift!", "GENERAL", None, None),
    ]

    for q, exp_intent, exp_cat, exp_max_price in test_queries:
        res = asyncio.run(router.extract(q))
        print(f"[OK] Query: '{q}' -> Intent: {res.intent.value}")
        assert res.intent.value == exp_intent
        if exp_cat:
            assert res.category == exp_cat
        if exp_max_price:
            assert res.max_price == exp_max_price


def test_layer5_service_and_grounding():
    print_header("LAYER 5: Grounded Chatbot Service (MySQL + Qdrant + LLM Context)")
    with get_db_context() as session:
        service = ChatbotService(session=session)

        # 1. Product search
        res1 = asyncio.run(service.handle_chat(ChatRequest(message="Có cà phê nào dưới 250k không?")))
        print(f"[OK] Search 'cà phê < 250k' -> Found {len(res1.products)} cards:")
        for p in res1.products:
            print(f"     - [{p.id}] {p.name} | {p.effective_price:,.0f}d | Stock: {p.available_quantity}")
            assert p.effective_price <= 250000.0

        # 2. Hybrid Recommendation
        res2 = asyncio.run(service.handle_chat(ChatRequest(message="Tôi thích trà thơm nhẹ thanh nhiệt dưới 200k")))
        print(f"[OK] Recommendation 'trà thơm nhẹ thanh nhiệt < 200k' -> {len(res2.products)} cards:")
        for p in res2.products:
            print(f"     - [{p.id}] {p.name} | {p.effective_price:,.0f}d | Stock: {p.available_quantity}")
            assert p.effective_price <= 200000.0

        # 3. Product Comparison
        res3 = asyncio.run(service.handle_chat(ChatRequest(message="So sánh Arabica Cầu Đất và Robusta Buôn Ma Thuột")))
        print(f"[OK] Compare 'Arabica vs Robusta' -> Compared {len(res3.products)} items")
        assert len(res3.products) >= 2

        # 4. Knowledge RAG
        res4 = asyncio.run(service.handle_chat(ChatRequest(message="Lợi ích sức khỏe của trà Shan Tuyết cổ thụ là gì?")))
        print(f"[OK] Knowledge RAG -> Generated answer length: {len(res4.answer)} chars")
        assert len(res4.answer) > 20

        # 5. Authenticated Order vs Unauthorized Order
        res5_auth = asyncio.run(service.handle_chat(ChatRequest(message="Tra cứu đơn hàng ORD-20260812-0001"), user_id=1))
        print(f"[OK] Authenticated order lookup (User 1) -> Status: Found, answer contains 'SHIPPING'")
        assert "SHIPPING" in res5_auth.answer

        res5_unauth = asyncio.run(service.handle_chat(ChatRequest(message="Tra cứu đơn hàng ORD-20260812-0001"), user_id=2))
        print(f"[OK] Cross-user unauthorized order lookup (User 2) -> Status: Denied safely")
        assert "không tìm thấy" in res5_unauth.answer.lower() or "đăng nhập" in res5_unauth.answer.lower()


def test_layer6_fastapi_rest_api():
    print_header("LAYER 6: FastAPI HTTP REST Endpoints (Live Server Client)")
    app = create_app()
    with TestClient(app) as client:
        # Health
        res = client.get("/api/health")
        print(f"[OK] GET /api/health -> {res.status_code} {res.json()}")
        assert res.status_code == 200

        # Products list
        res = client.get("/api/products?category=cà phê&max_price=250000")
        data = res.json()
        print(f"[OK] GET /api/products -> Returned {len(data)} filtered products")
        assert res.status_code == 200
        assert len(data) > 0

        # Product detail with certificates
        res = client.get("/api/products/1")
        data = res.json()
        print(f"[OK] GET /api/products/1 -> '{data['name']}', Certificates: {len(data['certificates'])}, Stock: {data['available_quantity']}")
        assert res.status_code == 200
        assert data["effective_price"] == 239000.0

        # Product stock
        res = client.get("/api/products/1/stock")
        print(f"[OK] GET /api/products/1/stock -> {res.json()}")
        assert res.status_code == 200
        assert res.json()["available_quantity"] == 85

        # Chat endpoint turn 1
        res = client.post("/api/chat", json={"message": "Xin chào LifeGift"})
        print(f"[OK] POST /api/chat (Turn 1) -> Session ID: {res.json()['session_id']}")
        assert res.status_code == 200
        sess_id = res.json()["session_id"]

        # Chat endpoint turn 2 (same session)
        res2 = client.post("/api/chat", json={"session_id": sess_id, "message": "Có mật ong rừng U Minh không?"})
        print(f"[OK] POST /api/chat (Turn 2) -> Products: {len(res2.json()['products'])}")
        assert res2.status_code == 200
        assert res2.json()["session_id"] == sess_id

        # Session history read
        res_sess = client.get(f"/api/chat/sessions/{sess_id}")
        print(f"[OK] GET /api/chat/sessions/{sess_id} -> Total messages stored: {len(res_sess.json()['messages'])}")
        assert res_sess.status_code == 200
        assert len(res_sess.json()["messages"]) >= 4


def test_layer7_benchmark_eval_dataset():
    print_header("LAYER 7: 47 Vietnamese Benchmark Evaluation Cases against Live Stack")
    with open("backend/tests/eval_cases.json", "r", encoding="utf-8") as f:
        cases = json.load(f)

    with get_db_context() as session:
        service = ChatbotService(session=session)
        passed = 0
        total = len(cases)

        start_time = time.time()
        for c in cases:
            query = c["query"]
            expected_intent = c["expected_intent"]
            uid = c.get("owner_user_id")

            req = ChatRequest(message=query)
            res = asyncio.run(service.handle_chat(req, user_id=uid))

            intent_ok = res.intent == expected_intent
            price_ok = True
            if c.get("expected_max_price"):
                price_ok = all(p.effective_price <= c["expected_max_price"] for p in res.products)

            if intent_ok and price_ok and len(res.answer) > 0:
                passed += 1
            else:
                print(f"[FAIL CASE] #{c['id']} Query: '{query}' -> Expected: {expected_intent}, Got: {res.intent}")

        elapsed = time.time() - start_time
        accuracy = (passed / total) * 100.0
        print(f"[OK] Evaluated {total} Vietnamese cases in {elapsed:.2f}s")
        print(f"[OK] Benchmark Pass Rate: {passed}/{total} ({accuracy:.1f}%)")
        assert accuracy >= 95.0, f"Benchmark pass rate was {accuracy:.1f}%, expected >= 95%"


if __name__ == "__main__":
    print("\n" + "#" * 70)
    print(" LIFEGIFT CHATBOT - LIVE END-TO-END VERIFICATION RUNNER")
    print("#" * 70)

    try:
        test_layer1_mysql()
        test_layer2_qdrant()
        test_layer3_embeddings()
        test_layer4_intent_routing()
        test_layer5_service_and_grounding()
        test_layer6_fastapi_rest_api()
        test_layer7_benchmark_eval_dataset()

        print("\n" + "#" * 70)
        print(" [SUCCESS] ALL 7 LAYERS PASSED LIVE VERIFICATION ON DOCKER MYSQL & QDRANT!")
        print("#" * 70 + "\n")
    except Exception as exc:
        print(f"\n[ERROR] Verification failed: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
