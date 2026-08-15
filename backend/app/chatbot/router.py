"""Deterministic Intent Router and Structured Extraction."""

import json
import logging
from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage

from backend.app.chatbot.llm import get_chat_model, FallbackStructuredLLM
from backend.app.chatbot.prompts import INTENT_EXTRACTION_SYSTEM_PROMPT
from backend.app.schemas.chat import IntentExtractionResult, IntentEnum

logger = logging.getLogger(__name__)


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

        if self.llm is not None:
            try:
                # Use LangChain structured output
                structured_llm = self.llm.with_structured_output(IntentExtractionResult)
                messages = [
                    SystemMessage(content=INTENT_EXTRACTION_SYSTEM_PROMPT),
                    HumanMessage(content=clean_msg),
                ]
                result = await structured_llm.ainvoke(messages)
                if isinstance(result, IntentExtractionResult):
                    return result
                elif isinstance(result, dict):
                    return IntentExtractionResult.model_validate(result)
            except Exception as exc:
                logger.warning(
                    "LLM structured intent extraction failed (%s), falling back to heuristic parser.",
                    exc,
                )

        # Heuristic fallback
        raw_dict = self.fallback.extract_intent(clean_msg)
        return IntentExtractionResult.model_validate(raw_dict)
