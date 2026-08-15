"""Pydantic models for chat requests, intent extraction and responses."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from backend.app.schemas.product import ProductCard


class IntentEnum(str, Enum):
    """Supported intent classification categories."""

    PRODUCT_SEARCH = "PRODUCT_SEARCH"
    PRODUCT_DETAIL = "PRODUCT_DETAIL"
    PRODUCT_RECOMMENDATION = "PRODUCT_RECOMMENDATION"
    PRODUCT_COMPARE = "PRODUCT_COMPARE"
    KNOWLEDGE = "KNOWLEDGE"
    PRODUCT_REVIEW = "PRODUCT_REVIEW"
    ORDER_STATUS = "ORDER_STATUS"
    GENERAL = "GENERAL"


class IntentExtractionResult(BaseModel):
    """Structured extraction output from LLM for routing."""

    intent: IntentEnum = Field(
        default=IntentEnum.GENERAL,
        description="The primary identified intent from the user query."
    )
    query: Optional[str] = Field(
        default=None,
        description="Cleaned keyword search query or subject."
    )
    category: Optional[str] = Field(
        default=None,
        description="Specific agricultural product category (e.g., cà phê, trà, mật ong, hạt, quà tặng)."
    )
    brand: Optional[str] = Field(
        default=None,
        description="Extracted brand name if specified."
    )
    origin: Optional[str] = Field(
        default=None,
        description="Geographic origin if specified (e.g., Cầu Đất, Hà Giang, U Minh, Tây Nguyên)."
    )
    min_price: Optional[float] = Field(
        default=None,
        description="Minimum budget / price constraint in VND."
    )
    max_price: Optional[float] = Field(
        default=None,
        description="Maximum budget / price constraint in VND."
    )
    in_stock_only: bool = Field(
        default=True,
        description="Whether only currently available products should be matched."
    )
    preferences: Optional[str] = Field(
        default=None,
        description="Soft taste or sensory preferences (e.g., ít đắng, thơm nhẹ, quà tặng bố mẹ)."
    )
    product_names: List[str] = Field(
        default_factory=list,
        description="Product names mentioned in comparison or detail queries."
    )
    order_code: Optional[str] = Field(
        default=None,
        description="Order tracking code (e.g., ORD-20260812-0001)."
    )


class ChatRequest(BaseModel):
    """Chat API request payload."""

    session_id: Optional[int] = None
    message: str = Field(..., min_length=1, max_length=1000)


class ChatMessageItem(BaseModel):
    """Single message item in a session history."""

    id: int
    role: str
    content: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class ChatSessionResponse(BaseModel):
    """Chat session representation."""

    id: int
    user_id: Optional[int] = None
    title: Optional[str] = None
    created_at: datetime
    messages: List[ChatMessageItem] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Chat API structured response payload."""

    session_id: int
    intent: str
    answer: str
    products: List[ProductCard] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class OrderStatusResponse(BaseModel):
    """Safe authenticated order status response."""

    order_code: str
    order_status: str
    payment_status: str
    created_at: datetime
    status_history: List[Dict[str, Any]] = Field(default_factory=list)
