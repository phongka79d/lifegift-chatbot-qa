"""Evaluation runner verifying all 47 evaluation test cases in eval_cases.json."""

import json
import os
from pathlib import Path
import pytest
from sqlalchemy.orm import Session

from backend.app.chatbot.router import IntentRouter
from backend.app.chatbot.service import ChatbotService
from backend.app.schemas.chat import ChatRequest


@pytest.mark.asyncio
async def test_run_eval_cases(db_session: Session):
    """Execute all eval cases from tests/eval_cases.json and assert high benchmark accuracy."""
    cases_file = Path(__file__).parent / "eval_cases.json"
    with open(cases_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    assert len(cases) >= 40

    router = IntentRouter()
    service = ChatbotService(session=db_session, router=router)

    passed_intent = 0
    total_cases = len(cases)

    for case in cases:
        query = case["query"]
        expected_intent = case["expected_intent"]

        extracted = await router.extract(query)
        if extracted.intent.value == expected_intent:
            passed_intent += 1

        # Test full chat turn
        user_id = case.get("owner_user_id")
        req = ChatRequest(message=query)
        res = await service.handle_chat(req, user_id=user_id)

        assert res.answer is not None
        assert len(res.answer) > 0

        # Category / price constraint verification if specified
        if case.get("expected_max_price"):
            for p in res.products:
                assert p.effective_price <= case["expected_max_price"]

    intent_accuracy = passed_intent / total_cases
    # Intent accuracy should exceed 90%
    assert intent_accuracy >= 0.90, f"Intent accuracy was {intent_accuracy:.2%}, expected >= 90%"
