"""Semantic Document Builders for Products, Blogs, and Certificates."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class KnowledgeDocument(BaseModel):
    """Normalized document representation ready for embedding and Qdrant ingestion."""

    id: str
    text: str
    metadata: Dict[str, Any]


def build_product_document(product: Dict[str, Any]) -> KnowledgeDocument:
    """Build a unified descriptive document for a product without mutable price or stock facts."""
    pid = product["id"]
    name = product.get("name", "")
    origin = product.get("origin", "")
    description = product.get("description", "")
    details = product.get("details") or {}

    sections = [
        f"Tên sản phẩm: {name}",
        f"Xuất xứ: {origin}" if origin else "",
        f"Mô tả sản phẩm: {description}" if description else "",
    ]

    if details.get("ingredients"):
        sections.append(f"Thành phần: {details['ingredients']}")
    if details.get("taste_profile"):
        sections.append(f"Hương vị đặc trưng: {details['taste_profile']}")
    if details.get("key_benefits"):
        sections.append(f"Công dụng và lợi ích: {details['key_benefits']}")
    if details.get("suitable_for"):
        sections.append(f"Đối tượng phù hợp: {details['suitable_for']}")
    if details.get("usage_instructions"):
        sections.append(f"Hướng dẫn sử dụng & pha chế: {details['usage_instructions']}")
    if details.get("storage_instructions"):
        sections.append(f"Bảo quản: {details['storage_instructions']}")
    if details.get("product_story"):
        sections.append(f"Câu chuyện sản phẩm: {details['product_story']}")

    full_text = "\n\n".join(s for s in sections if s.strip())

    return KnowledgeDocument(
        id=f"prod_{pid}",
        text=full_text,
        metadata={
            "source_type": "product",
            "source_id": pid,
            "product_id": pid,
            "category_id": product.get("category_id"),
            "title": name,
        },
    )


def chunk_text(text: str, chunk_size: int = 700, chunk_overlap: int = 80) -> List[str]:
    """Split text into overlapping chunks respecting line or word boundaries."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # Try to break at a paragraph or sentence boundary
            last_break = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if last_break > start + (chunk_size // 2):
                end = last_break + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - chunk_overlap
    return chunks


def build_blog_documents(
    blog_post: Dict[str, Any], chunk_size: int = 700, chunk_overlap: int = 80
) -> List[KnowledgeDocument]:
    """Build chunked semantic documents for published blog posts only."""
    status = blog_post.get("status", "").upper()
    if status != "PUBLISHED":
        # Strictly exclude unpublished / draft / archived blogs
        return []

    bid = blog_post["id"]
    title = blog_post.get("title", "")
    summary = blog_post.get("summary", "")
    content = blog_post.get("content", "")

    full_body = f"Tiêu đề: {title}\nTóm tắt: {summary}\n\nNội dung chi tiết:\n{content}"
    raw_chunks = chunk_text(full_body, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    docs = []
    for idx, chunk in enumerate(raw_chunks):
        docs.append(
            KnowledgeDocument(
                id=f"blog_{bid}_{idx}",
                text=chunk,
                metadata={
                    "source_type": "blog",
                    "source_id": bid,
                    "product_id": None,
                    "category_id": blog_post.get("category_id"),
                    "title": title,
                    "chunk_index": idx,
                },
            )
        )
    return docs


def build_certificate_document(
    cert: Dict[str, Any], product_name: Optional[str] = None
) -> KnowledgeDocument:
    """Build a semantic document explaining a product certificate standard."""
    cid = cert["id"]
    pid = cert.get("product_id")
    name = cert.get("name", "")
    issuer = cert.get("issuer", "")
    code = cert.get("certificate_code", "")
    description = cert.get("description", "")

    lines = [
        f"Chứng nhận tiêu chuẩn: {name}",
        f"Sản phẩm liên quan: {product_name}" if product_name else "",
        f"Đơn vị cấp / Tổ chức chứng nhận: {issuer}" if issuer else "",
        f"Mã số chứng nhận: {code}" if code else "",
        f"Mô tả và tiêu chuẩn kiểm định: {description}" if description else "",
    ]
    full_text = "\n".join(line for line in lines if line.strip())

    return KnowledgeDocument(
        id=f"cert_{cid}",
        text=full_text,
        metadata={
            "source_type": "certificate",
            "source_id": cid,
            "product_id": pid,
            "title": name,
        },
    )
