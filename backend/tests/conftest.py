"""Pytest configuration and test database fixtures."""

import os
import json
import pytest
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Configure test environment
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["LLM_API_KEY"] = ""
os.environ["EMBEDDING_API_KEY"] = ""

import backend.app.core.database as core_db
from backend.app.core.database import Base, get_db
from backend.app.core.config import get_settings
from backend.app.main import create_app
from backend.app.models.tables import (
    User,
    Category,
    Brand,
    Product,
    ProductImage,
    ProductDetail,
    ProductCertificate,
    Warehouse,
    Inventory,
    Review,
    BlogPost,
    BlogCategory,
    Order,
    OrderItem,
    OrderStatusHistory,
    ChatSession,
    ChatMessage,
)
from backend.scripts.seed_demo_data import (
    CATEGORIES,
    BRANDS,
    PRODUCTS,
    CERTIFICATES,
    USERS,
    WAREHOUSES,
    REVIEWS,
    BLOG_POSTS,
    BLOG_CATEGORIES,
    ORDERS,
)

# Test in-memory SQLite Engine with StaticPool
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Patch core database singletons
core_db._engine = test_engine
core_db._SessionFactory = TestingSessionLocal


def seed_test_database(session: Session):
    """Seed in-memory database with test data."""
    for c in CATEGORIES:
        session.add(Category(id=c["id"], name=c["name"], slug=c["slug"], status=c["status"]))

    for b in BRANDS:
        session.add(Brand(id=b["id"], name=b["name"], status=b["status"]))

    for u in USERS:
        session.add(
            User(
                id=u["id"],
                username=u.get("username") or f"user_{u['id']}",
                password=u.get("password") or "$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy",
                email=u["email"],
                full_name=u["full_name"],
                phone=u["phone"],
                status="ACTIVE",
            )
        )

    for w in WAREHOUSES:
        session.add(Warehouse(id=w["id"], name=w["name"], status=w["status"]))

    session.commit()

    for p in PRODUCTS:
        status = p["status"]
        stock_status = "IN_STOCK"
        if status == "OUT_OF_STOCK":
            status = "INACTIVE"
            stock_status = "OUT_OF_STOCK"
        prod = Product(
            id=p["id"],
            category_id=p["category_id"],
            brand_id=p["brand_id"],
            sku=p.get("sku") or f"SKU-{p['id']}",
            name=p["name"],
            slug=p["slug"],
            description=p["description"],
            price=p["price"],
            sale_price=p["sale_price"],
            origin=p["origin"],
            status=status,
            stock_status=stock_status,
            unit=p.get("unit") or "Sản phẩm",
        )
        session.add(prod)

        session.add(
            ProductImage(
                product_id=p["id"],
                image_url=p["image"],
                is_primary=True,
                sort_order=0,
            )
        )

        session.add(
            Inventory(
                product_id=p["id"],
                warehouse_id=1,
                quantity=p["stock"],
                available_quantity=p["stock"],
                reserved_quantity=0,
                min_stock=0,
            )
        )

        d = p["details"]
        session.add(
            ProductDetail(
                product_id=p["id"],
                ingredients=d.get("ingredients"),
                taste_profile=d.get("taste_profile"),
                key_benefits=d.get("key_benefits"),
                suitable_for=d.get("suitable_for"),
                usage_instructions=d.get("usage_instructions"),
                storage_instructions=d.get("storage_instructions"),
                shelf_life=d.get("shelf_life"),
                producer_name=d.get("producer_name"),
                production_area=d.get("production_area"),
                product_story=d.get("product_story"),
                extra_attributes=d.get("extra_attributes"),
            )
        )

    session.commit()

    for cert in CERTIFICATES:
        session.add(
            ProductCertificate(
                id=cert["id"],
                product_id=cert["product_id"],
                name=cert["name"],
                issuer=cert["issuer"],
                certificate_code=cert["certificate_code"],
                issued_at=datetime.strptime(cert["issued_at"], "%Y-%m-%d").date() if cert.get("issued_at") else None,
                expires_at=datetime.strptime(cert["expires_at"], "%Y-%m-%d").date() if cert.get("expires_at") else None,
                description=cert["description"],
                status=cert["status"],
            )
        )

    for bc in BLOG_CATEGORIES:
        session.add(
            BlogCategory(id=bc["id"], name=bc["name"], slug=bc["slug"])
        )

    for blog in BLOG_POSTS:
        blog_status = "HIDDEN" if blog["status"] == "ARCHIVED" else blog["status"]
        session.add(
            BlogPost(
                id=blog["id"],
                category_id=blog["category_id"],
                title=blog["title"],
                slug=blog["slug"],
                summary=blog["summary"],
                content=blog["content"],
                status=blog_status,
                published_at=datetime.utcnow() if blog_status == "PUBLISHED" else None,
            )
        )

    product_by_id = {p["id"]: p for p in PRODUCTS}
    for ord_data in ORDERS:
        session.add(
            Order(
                id=ord_data["id"],
                order_code=ord_data["order_code"],
                user_id=ord_data["user_id"],
                total_amount=ord_data["total_amount"],
                order_status=ord_data["order_status"],
                payment_status=ord_data["payment_status"],
            )
        )
        for item in ord_data["items"]:
            prod = product_by_id[item["product_id"]]
            session.add(
                OrderItem(
                    order_id=ord_data["id"],
                    product_id=item["product_id"],
                    product_name=prod["name"],
                    sku=prod.get("sku") or f"SKU-{prod['id']}",
                    unit_price=item["price"],
                    quantity=item["quantity"],
                    subtotal=item["price"] * item["quantity"],
                )
            )
        for hist in ord_data["history"]:
            session.add(
                OrderStatusHistory(
                    order_id=ord_data["id"],
                    status=hist["status"],
                    note=hist["notes"],
                )
            )

    session.commit()

    # Reviews require order_id under v2 schema — attach to matching order item or synthesize
    next_order_id = max((o["id"] for o in ORDERS), default=0) + 1
    for rev in REVIEWS:
        status = "HIDDEN" if rev["status"] == "REJECTED" else rev["status"]
        matched_order_id = None
        for ord_data in ORDERS:
            if ord_data["user_id"] != rev["user_id"]:
                continue
            if any(i["product_id"] == rev["product_id"] for i in ord_data["items"]):
                matched_order_id = ord_data["id"]
                break
        if matched_order_id is None:
            prod = product_by_id[rev["product_id"]]
            unit_price = float(prod.get("sale_price") or prod["price"])
            session.add(
                Order(
                    id=next_order_id,
                    order_code=f"MIG-REV-{next_order_id:08d}",
                    user_id=rev["user_id"],
                    total_amount=unit_price,
                    order_status="DELIVERED",
                    payment_status="PAID",
                )
            )
            session.add(
                OrderItem(
                    order_id=next_order_id,
                    product_id=rev["product_id"],
                    product_name=prod["name"],
                    sku=prod.get("sku") or f"SKU-{prod['id']}",
                    unit_price=unit_price,
                    quantity=1,
                    subtotal=unit_price,
                )
            )
            matched_order_id = next_order_id
            next_order_id += 1
        session.add(
            Review(
                id=rev["id"],
                product_id=rev["product_id"],
                user_id=rev["user_id"],
                order_id=matched_order_id,
                rating=rev["rating"],
                title=rev["title"],
                content=rev["content"],
                status=status,
            )
        )

    session.commit()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables and seed in memory once for test session."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    seed_test_database(session)
    session.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Yield a database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """FastAPI TestClient with overridden get_db dependency."""
    app = create_app()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
