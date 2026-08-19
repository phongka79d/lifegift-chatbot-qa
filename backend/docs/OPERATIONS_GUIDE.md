# LifeGift Chatbot Operations & Architecture Guide

## 1. Overview
The LifeGift Chatbot is a grounded, privacy-preserving e-commerce assistant designed for Vietnamese agricultural products (Specialty Coffee, Ancient Wild Tea, Forest Honey, Premium Nuts, Dried Fruits, and Gift Sets).

---

## 2. Core Architecture & Data Boundaries

```
                 +----------------------------------------------------+
                 |                   User / Client                    |
                 +----------------------------------------------------+
                                           |
                                [POST /api/chat]
                                           v
                             +---------------------------+
                             |   FastAPI Chat Endpoint   |
                             +---------------------------+
                                           |
                             +---------------------------+
                             |  Structured Intent Router |
                             +---------------------------+
                                           |
             +-----------------------------+-----------------------------+
             |                             |                             |
             v                             v                             v
+------------------------+    +------------------------+    +------------------------+
|  Authoritative MySQL   |    |    Qdrant Retriever    |    |  Provider-Neutral LLM  |
|------------------------|    |------------------------|    |------------------------|
| - Current Price        |    | - Semantic chunks      |    | - Intent Extraction    |
| - Available Stock      |    | - Published blogs      |    | - Grounded Explanation |
| - Active Certificates  |    | - Product narratives   |    | - Never generates SQL  |
| - Approved Reviews     |    | - No prices embedded   |    | - Safe context only    |
| - User-Scoped Orders   |    | - Degrades gracefully  |    +------------------------+
| - Session History      |    +------------------------+
+------------------------+
```

### Data Boundary Invariants:
1. **Single Source of Truth**: MySQL is the sole authority for product identity, effective prices (`sale_price ?? price`), real-time stock (`SUM(inventories.available_quantity)`), active certificates (`status = 'ACTIVE'`), approved reviews (`status = 'APPROVED'`), and customer order status.
2. **Semantic Knowledge Only**: Qdrant stores immutable product descriptions, certificates, and published blog posts. Vector chunks never contain mutable price or stock numbers.
3. **No Direct SQL Generation**: LLMs never generate raw SQL. All database access goes through parameterized Python repository methods.
4. **Order Privacy**: Order queries strictly enforce `WHERE orders.user_id = :user_id` using the server-authenticated user context. Cross-user data is inaccessible.

---

## 3. Environment Variables

All settings are configured via environment variables or a `.env` file in `backend/`:

| Variable | Type | Description | Default / Example |
|---|---|---|---|
| `APP_ENV` | `string` | Runtime environment (`development`, `testing`, `production`) | `development` |
| `DATABASE_URL` | `string` | Optional full SQLAlchemy connection string; overrides MYSQL_* settings when set (MySQL or SQLite) | `mysql+pymysql://root:password@127.0.0.1:3306/lifegift?charset=utf8mb4` |
| `MYSQL_HOST` | `string` | MySQL host | `localhost` |
| `MYSQL_PORT` | `int` | MySQL port | `3306` |
| `MYSQL_USER` | `string` | Database user | `root` |
| `MYSQL_PASSWORD` | `string` | Database password | `password` |
| `MYSQL_DATABASE` | `string` | Database name | `lifegift` |
| `QDRANT_URL` | `string` | Qdrant server URL (HTTP/HTTPS) or path for local mode | `http://localhost:6333` |
| `QDRANT_API_KEY` | `string` | Qdrant Cloud API key (optional for local) | `""` |
| `QDRANT_COLLECTION` | `string` | Collection name for semantic retrieval | `lifegift_knowledge` |
| `LLM_BASE_URL` | `string` | OpenAI-compatible LLM endpoint base URL | `https://api.openai.com/v1` |
| `LLM_API_KEY` | `string` | LLM API key (empty disables remote LLM; deterministic fallback is used) | `""` |
| `LLM_MODEL` | `string` | Model name | `gpt-4o-mini` |
| `LLM_TEMPERATURE` | `float` | LLM sampling temperature (keep 0 for extraction/generation determinism) | `0.0` |
| `EMBEDDING_BASE_URL` | `string` | OpenAI-compatible embedding endpoint base URL | `https://api.openai.com/v1` |
| `EMBEDDING_API_KEY` | `string` | Embedding API key (empty disables remote embeddings; deterministic mock embeddings are used) | `""` |
| `EMBEDDING_MODEL` | `string` | Embedding model name | `text-embedding-3-small` |
| `EMBEDDING_DIMENSION` | `int` | Embedding vector dimension used for the Qdrant collection | `1536` |

---

## 4. Operational Commands

### 4.1 Database Migrations
Run MySQL migration scripts located in `backend/migrations/`:
```bash
mysql -u root -p lifegift_db < backend/migrations/000_baseline_schema.sql
mysql -u root -p lifegift_db < backend/migrations/001_add_product_details.sql
mysql -u root -p lifegift_db < backend/migrations/002_add_product_certificates.sql
mysql -u root -p lifegift_db < backend/migrations/003_add_chat_tables.sql
mysql -u root -p lifegift_db < backend/migrations/004_add_effective_price.sql
mysql -u root -p lifegift_db < backend/migrations/005_add_product_catalog_columns.sql
mysql -u root -p lifegift_db < backend/migrations/006_fix_catalog_consistency.sql
# Align existing DB to lifegift_demo_v2.sql without wiping data:
mysql -u root -p lifegift_db < backend/migrations/007_sync_lifegift_demo_v2.sql
# If 007 stopped mid-way previously, resume with:
# mysql -u root -p lifegift_db < backend/migrations/007b_sync_lifegift_demo_v2_resume.sql
```

Notes for `007_sync_lifegift_demo_v2`:
- Does **not** run `DROP DATABASE` from `lifegift_demo_v2.sql`.
- Keeps chatbot tables (`chat_*`, `product_details`, `product_certificates`) and `products.effective_price`.
- Creates synthetic `MIG-REV-*` orders so existing reviews can satisfy v2 `order_id` FKs.
- Does **not** overwrite catalog rows with the demo INSERT block from the SQL file.

### 4.2 Seed Demo Data
Populate the database with 16 realistic Vietnamese agricultural products, active certificates, approved reviews, published articles, and sample customer orders:
```bash
python -m backend.scripts.seed_demo_data
```

### 4.3 Re-index Qdrant Knowledge Layer
Sync published blog articles, product narratives, and certificate descriptions into Qdrant:
```bash
python -m backend.scripts.reindex_qdrant
```

### 4.4 Run Test Suite
Run the comprehensive 30-test suite and benchmark evaluation runner:
```bash
python -m pytest backend/tests -v
```

### 4.5 Start FastAPI Server
Start the local FastAPI development server:
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 5. API Endpoints Reference

### `POST /api/chat`
Handles customer chat turns with intent extraction, grounding context injection, and structured product card generation.
- **Headers**:
  - `Authorization: Bearer <token>` (Optional)
  - `X-User-Id: <id>` (Optional mock auth)
- **Request Body**:
```json
{
  "session_id": null,
  "message": "Có cà phê nào dưới 250 nghìn không?"
}
```
- **Response Body**:
```json
{
  "session_id": 1,
  "intent": "PRODUCT_SEARCH",
  "answer": "Dưới đây là các sản phẩm nông sản LifeGift phù hợp...",
  "products": [
    {
      "id": 1,
      "name": "Cà phê Arabica Cầu Đất 500g",
      "price": 260000.0,
      "sale_price": 239000.0,
      "effective_price": 239000.0,
      "origin": "Cầu Đất - Đà Lạt",
      "available_quantity": 85,
      "is_available": true,
      "image_url": "https://images.unsplash.com/photo-1587734195503-904fca47e0e9?w=600",
      "reason": null
    }
  ],
  "metadata": {
    "intent": "PRODUCT_SEARCH",
    "tool": "search_products"
  }
}
```

### `GET /api/products/{product_id}`
Returns complete product details with active quality certificates and live inventory count.

### `GET /api/chat/sessions/{session_id}`
Returns chat history for a session, checking ownership if the session was created by an authenticated user.

---

## 6. Demo Validation Results (Plan Section 59)

Recorded with the deterministic fallback stack (no `LLM_API_KEY` / `EMBEDDING_API_KEY`) against a seeded
migration database; Qdrant ran locally with mock deterministic embeddings.

| Demo | Query | Result |
|---|---|---|
| 1. Product search | "Có cà phê nào dưới 200 nghìn?" | PASS — Robusta Buôn Ma Thuột returned, effective price 180.000đ |
| 2. Hybrid recommendation | "Tôi thích cà phê thơm nhẹ, ít đắng, dưới 300 nghìn." | PASS — MySQL hard constraints enforced, semantic ranking engaged, `semantic_used: true` |
| 3. Comparison | "So sánh Arabica và Robusta." | PASS — both resolved with current price, origin, and stock |
| 4. Knowledge RAG | "Cách chọn cà phê nguyên chất?" | PASS — 4 grounded chunks retrieved; unpublished draft excluded from index |
| 5. Stock | "Arabica còn hàng không?" | PASS — stock reported from `SUM(inventories.available_quantity)` = 85 |
| 6. Order status | "Đơn ORD-20260812-0001 của tôi đang ở đâu?" | PASS — authenticated owner sees SHIPPING/PAID history; anonymous gets login prompt with zero order data |

Note: semantic ranking *order* in Demo 2 depends on embedding quality; with real provider embeddings the
expected top result is Arabica Cầu Đất. Ranking quality is validated against `tests/eval_cases.json`, not
asserted by the mock-embedding demo.

## 7. Known Limitations

- Authentication is a mock contract (`X-User-Id` header or `Bearer user_<id>` / numeric token). Wire it to
  the real LifeGift auth provider before production.
- The deterministic intent fallback handles common Vietnamese phrasing; connect `LLM_API_KEY` for the full
  structured-extraction path (validated by the same Pydantic schema).
- `products.effective_price` is a MySQL generated column; when using SQLite for tests the equivalent is
  computed as `COALESCE(sale_price, price)` in repository SQL.
- Migrations 002–004 are idempotent for MySQL 8.0 (information_schema-guarded DDL). Re-run safety on
  MariaDB is also confirmed but MySQL remains the supported target.
- No separate observability stack: structured application logs cover request id, intent, tool, duration,
  retrieval count, and error type.
