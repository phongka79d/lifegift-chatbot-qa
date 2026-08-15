"""Tests for FastAPI chat endpoints, anonymous/authenticated sessions, and card formats."""

import pytest
from fastapi.testclient import TestClient


def test_anonymous_chat_search(client: TestClient):
    """Verify anonymous user can perform product search and receive structured product cards."""
    payload = {
        "message": "Có cà phê nào dưới 250 nghìn không?"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "session_id" in data
    assert data["intent"] in ["PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION"]
    assert len(data["products"]) > 0

    first_prod = data["products"][0]
    assert "id" in first_prod
    assert "name" in first_prod
    assert "effective_price" in first_prod
    assert first_prod["effective_price"] <= 250000.0
    assert first_prod["is_available"] is True


def test_session_history_turn(client: TestClient):
    """Verify follow-up message reuses session and saves message history."""
    # First turn
    res1 = client.post("/api/chat", json={"message": "Xin chào LifeGift"})
    assert res1.status_code == 200
    session_id = res1.json()["session_id"]

    # Second turn with same session_id
    res2 = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Có trà Shan Tuyết không?"},
    )
    assert res2.status_code == 200
    assert res2.json()["session_id"] == session_id

    # Query session history
    res3 = client.get(f"/api/chat/sessions/{session_id}")
    assert res3.status_code == 200
    sess_data = res3.json()
    assert len(sess_data["messages"]) >= 4  # 2 user messages + 2 assistant replies


def test_authenticated_order_status_chat(client: TestClient):
    """Verify authenticated user can look up their own order in chat."""
    headers = {"X-User-Id": "1"}
    payload = {"message": "Đơn hàng ORD-20260812-0001 của tôi đang ở đâu?"}

    response = client.post("/api/chat", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "ORDER_STATUS"
    assert "ORD-20260812-0001" in data["answer"]
    assert "SHIPPING" in data["answer"] or "giao" in data["answer"].lower()


def test_unauthenticated_order_status_denial(client: TestClient):
    """Verify unauthenticated user receives a prompt to login when asking for order status."""
    payload = {"message": "Đơn hàng ORD-20260812-0001 của tôi đang ở đâu?"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "đăng nhập" in data["answer"].lower()
