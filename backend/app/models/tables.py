"""SQLAlchemy declarative models for LifeGift database."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import relationship

from backend.app.core.database import Base

# ID column helper compatible with both MySQL (BIGINT UNSIGNED) and SQLite (INTEGER PRIMARY KEY)
PK_BIGINT = BigInteger().with_variant(Integer, "sqlite")


class User(Base):
    __tablename__ = "users"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)
    status = Column(Enum("ACTIVE", "INACTIVE", name="category_status"), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    products = relationship("Product", back_populates="category")


class Brand(Base):
    __tablename__ = "brands"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    status = Column(Enum("ACTIVE", "INACTIVE", name="brand_status"), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    products = relationship("Product", back_populates="brand")


class Product(Base):
    __tablename__ = "products"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    category_id = Column(BigInteger, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    brand_id = Column(BigInteger, ForeignKey("brands.id", ondelete="SET NULL"), nullable=True)
    sku = Column(String(100), nullable=True, unique=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)
    price = Column(Numeric(15, 2), nullable=False)
    sale_price = Column(Numeric(15, 2), nullable=True)
    unit = Column(String(50), nullable=True)
    weight = Column(Numeric(12, 2), nullable=True)
    origin = Column(String(255), nullable=True)
    pricing_type = Column(String(50), nullable=True, default="FIXED_PRICE")
    stock_status = Column(String(50), nullable=True, default="IN_STOCK")
    is_featured = Column(Boolean, nullable=False, default=False)
    status = Column(Enum("ACTIVE", "INACTIVE", "OUT_OF_STOCK", name="product_status"), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    details = relationship("ProductDetail", back_populates="product", uselist=False, cascade="all, delete-orphan")
    certificates = relationship("ProductCertificate", back_populates="product", cascade="all, delete-orphan")
    inventories = relationship("Inventory", back_populates="product", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")

    @property
    def effective_price(self) -> float:
        return float(self.sale_price if self.sale_price is not None else self.price)


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String(500), nullable=False)
    is_primary = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    product = relationship("Product", back_populates="images")


class ProductDetail(Base):
    __tablename__ = "product_details"

    product_id = Column(PK_BIGINT, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    ingredients = Column(Text, nullable=True)
    taste_profile = Column(String(1000), nullable=True)
    key_benefits = Column(String(1000), nullable=True)
    suitable_for = Column(String(1000), nullable=True)
    usage_instructions = Column(Text, nullable=True)
    storage_instructions = Column(Text, nullable=True)
    shelf_life = Column(String(100), nullable=True)
    producer_name = Column(String(255), nullable=True)
    production_area = Column(String(255), nullable=True)
    product_story = Column(Text, nullable=True)
    extra_attributes = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="details")


class ProductCertificate(Base):
    __tablename__ = "product_certificates"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    issuer = Column(String(255), nullable=True)
    certificate_code = Column(String(150), nullable=True)
    issued_at = Column(Date, nullable=True)
    expires_at = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=True)
    status = Column(Enum("ACTIVE", "EXPIRED", "REVOKED", name="cert_status"), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="certificates")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    status = Column(Enum("ACTIVE", "INACTIVE", name="warehouse_status"), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    inventories = relationship("Inventory", back_populates="warehouse", cascade="all, delete-orphan")


class Inventory(Base):
    __tablename__ = "inventories"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    warehouse_id = Column(BigInteger, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    available_quantity = Column(Integer, nullable=False, default=0)
    reserved_quantity = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="inventories")
    warehouse = relationship("Warehouse", back_populates="inventories")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    status = Column(Enum("PENDING", "APPROVED", "REJECTED", name="review_status"), nullable=False, default="PENDING")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews")


class BlogCategory(Base):
    __tablename__ = "blog_categories"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    category_id = Column(BigInteger, nullable=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    status = Column(Enum("DRAFT", "PUBLISHED", "ARCHIVED", name="blog_status"), nullable=False, default="DRAFT")
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    order_code = Column(String(100), nullable=False, unique=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    order_status = Column(
        Enum("PENDING", "PROCESSING", "SHIPPING", "DELIVERED", "CANCELLED", name="order_status"),
        nullable=False,
        default="PENDING",
    )
    payment_status = Column(
        Enum("UNPAID", "PAID", "REFUNDED", name="payment_status"),
        nullable=False,
        default="UNPAID",
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    history = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(15, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    status = Column(
        Enum("PENDING", "PROCESSING", "SHIPPING", "DELIVERED", "CANCELLED", name="order_history_status"),
        nullable=False,
    )
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    order = relationship("Order", back_populates="history")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=True, default="New Conversation")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum("USER", "ASSISTANT", name="message_role"), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")
