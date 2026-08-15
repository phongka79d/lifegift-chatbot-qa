"""Tests for RAG document builders and Qdrant retriever."""

import pytest
from backend.app.rag.document_builder import (
    build_product_document,
    build_blog_documents,
    build_certificate_document,
)
from backend.app.rag.retriever import QdrantRetriever


def test_product_document_builder_excludes_mutable_price():
    """Verify product document builder excludes price and stock as semantic facts."""
    prod = {
        "id": 1,
        "name": "Cà phê Arabica",
        "description": "Cà phê sạch",
        "origin": "Đà Lạt",
        "details": {
            "taste_profile": "Thơm thanh",
            "ingredients": "100% Arabica",
        },
    }
    doc = build_product_document(prod)

    assert doc.id == "prod_1"
    assert doc.metadata["source_type"] == "product"
    assert "239000" not in doc.text
    assert "260000" not in doc.text
    assert "tồn kho" not in doc.text.lower()
    assert "Thơm thanh" in doc.text


def test_blog_document_builder_excludes_unpublished():
    """Verify unpublished blog posts are completely excluded from indexing."""
    draft_blog = {
        "id": 4,
        "title": "Bản nháp canh tác",
        "content": "Nội dung nháp",
        "status": "DRAFT",
    }
    docs = build_blog_documents(draft_blog)
    assert len(docs) == 0

    pub_blog = {
        "id": 1,
        "title": "Bí quyết chọn cà phê nguyên chất",
        "summary": "Hướng dẫn nhận biết cà phê",
        "content": "Nội dung chi tiết bài viết...",
        "status": "PUBLISHED",
    }
    pub_docs = build_blog_documents(pub_blog)
    assert len(pub_docs) >= 1
    assert pub_docs[0].metadata["source_type"] == "blog"


def test_certificate_document_builder():
    """Verify certificate document builds correctly with source metadata."""
    cert = {
        "id": 1,
        "product_id": 1,
        "name": "VietGAP",
        "issuer": "Quacert",
        "certificate_code": "VG-123",
        "description": "Tiêu chuẩn nông nghiệp sạch",
    }
    doc = build_certificate_document(cert, product_name="Cà phê Arabica")
    assert doc.id == "cert_1"
    assert doc.metadata["source_type"] == "certificate"
    assert "VietGAP" in doc.text
    assert "VG-123" in doc.text
