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
| `DATABASE_URL` | `string` | SQLAlchemy connection string (MySQL or SQLite) | `mysql+pymysql://root:password@127.0.0.1:3306/lifegift_db?charset=utf8mb4` |
| `MYSQL_HOST` | `string` | MySQL host | `127.0.0.1` |
| `MYSQL_PORT` | `int` | MySQL port | `3306` |
| `MYSQL_USER` | `string` | Database user | `root` |
| `MYSQL_PASSWORD` | `string` | Database password | `""` |
| `MYSQL_DATABASE` | `string` | Database name | `lifegift_db` |
| `QDRANT_HOST` | `string` | Qdrant vector database host | `localhost` |
| `QDRANT_PORT` | `int` | Qdrant port | `6333` |
| `QDRANT_API_KEY` | `string` | Qdrant Cloud API key (optional for local) | `""` |
| `QDRANT_COLLECTION` | `string` | Collection name for semantic retrieval | `lifegift_knowledge` |
| `LLM_PROVIDER` | `string` | LLM provider (`openai`, `azure`, `local`, `mock`) | `openai` |
| `LLM_MODEL` | `string` | Model name | `gpt-4o-mini` |
| `LLM_API_KEY` | `string` | LLM API key | `""` |
| `LLM_BASE_URL` | `string` | Custom OpenAI-compatible base URL | `None` |
| `EMBEDDING_PROVIDER` | `string` | Embedding provider | `openai` |
| `EMBEDDING_MODEL` | `string` | Embedding model name | `text-embedding-3-small` |
| `EMBEDDING_API_KEY` | `string` | Embedding API key | `""` |

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
```

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
      "image_url": "https://images.unsplash.com/photo-1587734195503-904fca47e0e9?w=600"
    }
  ],
  "metadata": {
    "products_count": 1,
    "has_retrieval": false
  }
}
```

### `GET /api/products/{product_id}`
Returns complete product details with active quality certificates and live inventory count.

### `GET /api/chat/sessions/{session_id}`
Returns chat history for a session, checking ownership if the session was created by an authenticated user.
