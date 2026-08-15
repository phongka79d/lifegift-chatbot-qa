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
        session.add(User(id=u["id"], email=u["email"], full_name=u["full_name"], phone=u["phone"]))

    for w in WAREHOUSES:
        session.add(Warehouse(id=w["id"], name=w["name"], status=w["status"]))

    session.commit()

    for p in PRODUCTS:
        prod = Product(
            id=p["id"],
            category_id=p["category_id"],
            brand_id=p["brand_id"],
            name=p["name"],
            slug=p["slug"],
            description=p["description"],
            price=p["price"],
            sale_price=p["sale_price"],
            origin=p["origin"],
            status=p["status"],
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
                available_quantity=p["stock"],
                reserved_quantity=0,
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

    for rev in REVIEWS:
        session.add(
            Review(
                id=rev["id"],
                product_id=rev["product_id"],
                user_id=rev["user_id"],
                rating=rev["rating"],
                title=rev["title"],
                content=rev["content"],
                status=rev["status"],
            )
        )

    for blog in BLOG_POSTS:
        session.add(
            BlogPost(
                id=blog["id"],
                category_id=blog["category_id"],
                title=blog["title"],
                slug=blog["slug"],
                summary=blog["summary"],
                content=blog["content"],
                status=blog["status"],
                published_at=datetime.utcnow() if blog["status"] == "PUBLISHED" else None,
            )
        )

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
            session.add(
                OrderItem(
                    order_id=ord_data["id"],
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    price=item["price"],
                )
            )
        for hist in ord_data["history"]:
            session.add(
                OrderStatusHistory(
                    order_id=ord_data["id"],
                    status=hist["status"],
                    notes=hist["notes"],
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
