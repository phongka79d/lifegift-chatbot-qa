"""Product tool adapters for chatbot handlers."""

from typing import Optional, List, Dict, Any
from backend.app.repositories.product_repository import ProductRepository
from backend.app.schemas.product import ProductCard, ProductDetailResponse, ProductSearchParams


def search_products_tool(
    repo: ProductRepository,
    query: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    origin: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: bool = True,
    limit: int = 5,
) -> List[ProductCard]:
    """Search products through authoritative MySQL repository with parameterized constraints."""
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


def get_product_detail_tool(
    repo: ProductRepository, product_id: int
) -> Optional[ProductDetailResponse]:
    """Retrieve full product details, active certificates and stock."""
    return repo.get_by_id(product_id)


def get_product_stock_tool(
    repo: ProductRepository, product_id: int
) -> Dict[str, Any]:
    """Retrieve authoritative inventory stock level."""
    return repo.get_stock(product_id)


def resolve_product_tool(
    repo: ProductRepository, name: str
) -> Optional[ProductCard]:
    """Resolve an approximate product name to a known product."""
    return repo.resolve_by_name(name)
