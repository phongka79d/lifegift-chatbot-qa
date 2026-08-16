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
    weight: Optional[float] = None
    price_per_kg: Optional[float] = None
    price_basis: Optional[str] = None  # package | per_kg
    category_name: Optional[str] = None


class ProductDetailResponse(BaseModel):
    """Detailed view of a single product with certificates and ingredients."""

    id: int
    name: str
    slug: str
    sku: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    brand_id: Optional[int] = None
    brand_name: Optional[str] = None
    price: float
    sale_price: Optional[float] = None
    effective_price: float
    unit: Optional[str] = None
    weight: Optional[float] = None
    origin: Optional[str] = None
    pricing_type: Optional[str] = None
    stock_status: Optional[str] = None
    is_featured: bool = False
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
    price_unit: str = "PACKAGE"  # PACKAGE | PER_KG | UNKNOWN
    in_stock: bool = True
    limit: int = Field(default=5, ge=1, le=10)


class ProductSearchResult(BaseModel):
    """Structured search outcome including empty-state metadata."""

    products: List[ProductCard] = Field(default_factory=list)
    applied_filters: Dict[str, Any] = Field(default_factory=dict)
    empty_reason: Optional[str] = None
    available_categories: List[str] = Field(default_factory=list)
    category_resolved: Optional[bool] = None


class ProductComparisonResponse(BaseModel):
    """Structured comparison result across multiple products."""

    products: List[ProductCard]
    comparison_points: Dict[str, Any] = Field(default_factory=dict)
    summary: str
