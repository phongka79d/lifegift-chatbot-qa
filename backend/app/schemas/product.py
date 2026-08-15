"""Pydantic models for product catalog and search."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ProductCard(BaseModel):
    """Structured product card returned directly to the frontend."""

    id: int
    name: str
    price: float
    sale_price: Optional[float] = None
    effective_price: float
    origin: Optional[str] = None
    available_quantity: int = 0
    is_available: bool = True
    image_url: Optional[str] = None
    reason: Optional[str] = None


class ProductDetailResponse(BaseModel):
    """Detailed view of a single product with certificates and ingredients."""

    id: int
    name: str
    slug: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    brand_id: Optional[int] = None
    brand_name: Optional[str] = None
    price: float
    sale_price: Optional[float] = None
    effective_price: float
    origin: Optional[str] = None
    image_url: Optional[str] = None
    available_quantity: int = 0
    is_available: bool = True
    ingredients: Optional[str] = None
    taste_profile: Optional[str] = None
    key_benefits: Optional[str] = None
    suitable_for: Optional[str] = None
    usage_instructions: Optional[str] = None
    storage_instructions: Optional[str] = None
    shelf_life: Optional[str] = None
    producer_name: Optional[str] = None
    production_area: Optional[str] = None
    product_story: Optional[str] = None
    extra_attributes: Optional[Dict[str, Any]] = None
    certificates: List[Dict[str, Any]] = Field(default_factory=list)


class ProductSearchParams(BaseModel):
    """Bounded filter parameters extracted from user messages."""

    query: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    origin: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    in_stock: bool = True
    limit: int = Field(default=5, ge=1, le=10)


class ProductComparisonResponse(BaseModel):
    """Structured comparison result across multiple products."""

    products: List[ProductCard]
    comparison_points: Dict[str, Any] = Field(default_factory=dict)
    summary: str
