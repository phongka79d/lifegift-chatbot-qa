"""Tests for structured intent router and extraction."""

import pytest
from backend.app.chatbot.router import IntentRouter
from backend.app.schemas.chat import IntentEnum


@pytest.mark.asyncio
async def test_extract_product_search_intent():
    """Verify price and category extraction in product search."""
    router = IntentRouter()
    res = await router.extract("Có cà phê nào dưới 250 nghìn không?")
    assert res.intent == IntentEnum.PRODUCT_SEARCH
    assert res.category == "cà phê"
    assert res.max_price == 250000.0


@pytest.mark.asyncio
async def test_extract_recommendation_intent():
    """Verify soft preferences extraction in recommendation."""
    router = IntentRouter()
    res = await router.extract("Tôi thích cà phê thơm nhẹ, ít đắng dưới 300k")
    assert res.intent == IntentEnum.PRODUCT_RECOMMENDATION
    assert res.category == "cà phê"
    assert res.max_price == 300000.0
    assert res.preferences is not None


@pytest.mark.asyncio
async def test_extract_order_status_intent():
    """Verify order code extraction from user query."""
    router = IntentRouter()
    res = await router.extract("Đơn hàng ORD-20260812-0001 của tôi đang ở đâu?")
    assert res.intent == IntentEnum.ORDER_STATUS
    assert res.order_code == "ORD-20260812-0001"


@pytest.mark.asyncio
async def test_extract_compare_intent():
    """Verify comparison intent and product extraction."""
    router = IntentRouter()
    res = await router.extract("So sánh Arabica Cầu Đất và Robusta Buôn Ma Thuột")
    assert res.intent == IntentEnum.PRODUCT_COMPARE
    assert len(res.product_names) >= 2


@pytest.mark.asyncio
async def test_extract_knowledge_intent():
    """Verify knowledge intent detection."""
    router = IntentRouter()
    res = await router.extract("Cách chọn cà phê nguyên chất chuẩn vị không pha tạp?")
    assert res.intent == IntentEnum.KNOWLEDGE
