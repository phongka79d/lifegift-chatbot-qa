"""Re-index MySQL knowledge data (products, published blogs, certificates) into Qdrant."""

import hashlib
import json
import logging
import uuid
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest_models
from sqlalchemy import text

from backend.app.core.config import get_settings
from backend.app.core.database import get_db_context
from backend.app.core.qdrant import get_qdrant_client, init_qdrant_collection
from backend.app.rag.document_builder import (
    KnowledgeDocument,
    build_product_document,
    build_blog_documents,
    build_certificate_document,
)
from backend.app.rag.embeddings import get_embedding_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_stable_point_id(doc_id: str) -> str:
    """Generate a deterministic UUID string from document id."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id))


def reindex_all() -> int:
    """Execute complete reindexing of knowledge documents into Qdrant."""
    settings = get_settings()
    client = get_qdrant_client()
    embedding_client = get_embedding_client()

    logger.info("Initializing Qdrant collection %s...", settings.QDRANT_COLLECTION)
    init_qdrant_collection(
        client=client,
        collection_name=settings.QDRANT_COLLECTION,
        vector_size=settings.EMBEDDING_DIMENSION,
    )

    all_docs: List[KnowledgeDocument] = []

    with get_db_context() as session:
        # 1. Load active products with details
        logger.info("Fetching active products from MySQL...")
        prod_rows = session.execute(
            text("""
                SELECT
                    p.id,
                    p.category_id,
                    p.name,
                    p.description,
                    p.origin,
                    pd.ingredients,
                    pd.taste_profile,
                    pd.key_benefits,
                    pd.suitable_for,
                    pd.usage_instructions,
                    pd.storage_instructions,
                    pd.product_story,
                    pd.extra_attributes
                FROM products p
                LEFT JOIN product_details pd ON p.id = pd.product_id
                WHERE p.status = 'ACTIVE'
            """)
        ).fetchall()

        for pr in prod_rows:
            extra = {}
            if pr.extra_attributes:
                extra = json.loads(pr.extra_attributes) if isinstance(pr.extra_attributes, str) else pr.extra_attributes
            prod_dict = {
                "id": pr.id,
                "category_id": pr.category_id,
                "name": pr.name,
                "description": pr.description,
                "origin": pr.origin,
                "details": {
                    "ingredients": pr.ingredients,
                    "taste_profile": pr.taste_profile,
                    "key_benefits": pr.key_benefits,
                    "suitable_for": pr.suitable_for,
                    "usage_instructions": pr.usage_instructions,
                    "storage_instructions": pr.storage_instructions,
                    "product_story": pr.product_story,
                    "extra_attributes": extra,
                },
            }
            doc = build_product_document(prod_dict)
            all_docs.append(doc)

        logger.info("Built %d product knowledge documents.", len(prod_rows))

        # 2. Load published blog posts
        logger.info("Fetching published blog posts from MySQL...")
        blog_rows = session.execute(
            text("""
                SELECT id, category_id, title, summary, content, status
                FROM blog_posts
                WHERE status = 'PUBLISHED'
            """)
        ).fetchall()

        blog_doc_count = 0
        for br in blog_rows:
            blog_dict = {
                "id": br.id,
                "category_id": br.category_id,
                "title": br.title,
                "summary": br.summary,
                "content": br.content,
                "status": br.status,
            }
            b_docs = build_blog_documents(blog_dict)
            all_docs.extend(b_docs)
            blog_doc_count += len(b_docs)

        logger.info("Built %d blog chunks from %d published articles.", blog_doc_count, len(blog_rows))

        # 3. Load active certificates
        logger.info("Fetching active certificates from MySQL...")
        cert_rows = session.execute(
            text("""
                SELECT c.id, c.product_id, c.name, c.issuer, c.certificate_code, c.description, c.status, p.name AS product_name
                FROM product_certificates c
                LEFT JOIN products p ON c.product_id = p.id
                WHERE c.status = 'ACTIVE'
            """)
        ).fetchall()

        for cr in cert_rows:
            cert_dict = {
                "id": cr.id,
                "product_id": cr.product_id,
                "name": cr.name,
                "issuer": cr.issuer,
                "certificate_code": cr.certificate_code,
                "description": cr.description,
            }
            c_doc = build_certificate_document(cert_dict, product_name=cr.product_name)
            all_docs.append(c_doc)

        logger.info("Built %d certificate knowledge documents.", len(cert_rows))

    if not all_docs:
        logger.warning("No knowledge documents to index.")
        return 0

    # 4. Generate embeddings and upsert into Qdrant
    logger.info("Embedding %d total documents...", len(all_docs))
    texts = [d.text for d in all_docs]
    embeddings = embedding_client.embed_documents(texts)

    points = []
    for doc, vec in zip(all_docs, embeddings):
        payload = dict(doc.metadata)
        payload["text"] = doc.text
        points.append(
            rest_models.PointStruct(
                id=generate_stable_point_id(doc.id),
                vector=vec,
                payload=payload,
            )
        )

    # Batch upsert
    batch_size = 50
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=batch,
        )

    logger.info("Successfully indexed %d knowledge documents into Qdrant.", len(points))
    return len(points)


if __name__ == "__main__":
    reindex_all()
