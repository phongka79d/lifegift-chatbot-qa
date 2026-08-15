"""Product API endpoints."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.repositories.product_repository import ProductRepository
from backend.app.repositories.review_repository import ReviewRepository
from backend.app.schemas.product import (
    ProductCard,
    ProductDetailResponse,
    ProductSearchParams,
)

router = APIRouter()


@router.get(
    "/products",
    response_model=List[ProductCard],
    summary="Search and filter active products",
)
def list_products(
    query: Optional[str] = Query(None, description="Search keyword"),
    category: Optional[str] = Query(None, description="Category name"),
    brand: Optional[str] = Query(None, description="Brand name"),
    origin: Optional[str] = Query(None, description="Origin region"),
    min_price: Optional[float] = Query(None, description="Minimum price in VND"),
    max_price: Optional[float] = Query(None, description="Maximum price in VND"),
    in_stock: bool = Query(True, description="Only in-stock products"),
    limit: int = Query(5, ge=1, le=10, description="Max results to return"),
    db: Session = Depends(get_db),
):
    """List products matching structured filter criteria."""
    repo = ProductRepository(db)
    params = ProductSearchParams(
        query=query,
        category=category,
        brand=brand,
        origin=origin,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        limit=limit,
    )
    return repo.search_products(params)


@router.get(
    "/products/{product_id}",
    response_model=ProductDetailResponse,
    summary="Get full product details including active certificates",
)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Retrieve product detail by ID."""
    repo = ProductRepository(db)
    detail = repo.get_by_id(product_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found.",
        )
    return detail


@router.get(
    "/products/{product_id}/stock",
    response_model=Dict[str, Any],
    summary="Get product available stock",
)
def get_stock(product_id: int, db: Session = Depends(get_db)):
    """Retrieve current stock count from inventories."""
    repo = ProductRepository(db)
    return repo.get_stock(product_id)


@router.get(
    "/products/{product_id}/reviews",
    response_model=Dict[str, Any],
    summary="Get approved reviews for a product",
)
def get_reviews(
    product_id: int,
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Retrieve approved customer reviews."""
    repo = ReviewRepository(db)
    return repo.get_product_reviews(product_id=product_id, limit=limit)
