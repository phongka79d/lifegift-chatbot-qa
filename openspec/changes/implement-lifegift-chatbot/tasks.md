## 1. Verify the baseline and scaffold the application

- [ ] 1.1 Locate and inspect the existing LifeGift SQL schema and authentication integration; record the actual table names, column types, foreign keys, and status values needed by the chatbot.
- [ ] 1.2 Create the planned `backend/app` package structure for API routes, configuration, schemas, repositories, tools, RAG, chatbot orchestration, and services, plus `scripts/` and `tests/` entry points.
- [ ] 1.3 Add provider-neutral settings and database/Qdrant client wiring for `MYSQL_*`, `QDRANT_*`, `LLM_*`, and `EMBEDDING_*` variables, with a safe `.env.example` and no hardcoded credentials.
- [ ] 1.4 Add the minimal runtime and test dependencies required by the verified project setup, and make the FastAPI application importable by a smoke test.

## 2. Extend MySQL without changing existing commerce behavior

- [ ] 2.1 Add an additive migration for the one-to-one `product_details` table, including its foreign key, timestamps, and JSON `extra_attributes` field.
- [ ] 2.2 Add an additive migration for `product_certificates`, its product index, lifecycle status, and expiry fields; verify the status values against the baseline schema conventions.
- [ ] 2.3 Add additive migrations for `chat_sessions` and `chat_messages`, including anonymous-session support, cascading session deletion, and recent-message indexes.
- [ ] 2.4 Add the generated `products.effective_price` column and the active/category/price index using the verified MySQL syntax and existing product status values.
- [ ] 2.5 Seed representative descriptive product details and certificates for the demo categories without duplicating current price or stock in semantic fields.
- [ ] 2.6 Run the migrations and seed script against a disposable database, then verify existing commerce tables remain usable and effective price/inventory totals match expected fixtures.

## 3. Implement authoritative MySQL repositories

- [ ] 3.1 Add repository database fixtures and a parameterized-query test harness that can run without an LLM or Qdrant.
- [ ] 3.2 Implement `ProductRepository.search_products` with active-product filtering, category/brand/origin filters, effective-price bounds, bounded limits, and optional inventory-based availability filtering.
- [ ] 3.3 Implement product detail and stock queries that return public product/category/brand/details/image data and compute stock from summed `inventories.available_quantity`.
- [ ] 3.4 Implement `ReviewRepository.get_product_reviews` to return only approved reviews with a bounded limit and customer-safe fields.
- [ ] 3.5 Implement `OrderRepository.get_order_status` with authenticated-user ownership in the SQL predicate and only the approved order/status-history fields.
- [ ] 3.6 Implement `ChatRepository` methods to create or reuse anonymous/authenticated sessions, persist both message roles, and load only the configured recent-message window.
- [ ] 3.7 Add repository tests for sale-price precedence, inactive products, zero stock, approved-review filtering, cross-user order denial, and bounded chat history.

## 4. Build the Qdrant knowledge layer

- [ ] 4.1 Implement the configured embedding client and Qdrant collection initialization for one `lifegift_knowledge` collection with source metadata.
- [ ] 4.2 Implement document builders for one normal product document, chunked published blog content, and optional certificate explanatory text without embedding mutable price or stock as facts.
- [ ] 4.3 Implement `scripts/reindex_qdrant.py` to load MySQL content, exclude unpublished blogs, create embeddings, and upsert stable source identities into the collection.
- [ ] 4.4 Implement the bounded knowledge retriever with optional `product_id` and `source_type` filters and a controlled unavailable-Qdrant error.
- [ ] 4.5 Add document-builder and retriever tests proving unpublished content is excluded, metadata is preserved, and certificate text cannot establish certificate validity by itself.

## 5. Add validated intent extraction and deterministic routing

- [ ] 5.1 Define Pydantic models for the supported intent enum, bounded search constraints, product names, order code, and extraction errors.
- [ ] 5.2 Implement the provider-neutral structured LLM factory and extraction prompt using `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` without repository or tool access.
- [ ] 5.3 Validate structured extraction output and add tests for Vietnamese product search, recommendation preferences, order-code extraction, invalid output, and rejection of SQL/tool instructions.
- [ ] 5.4 Implement ordinary Python intent dispatch for all supported intents with explicit handlers and no unbounded autonomous agent loop.

## 6. Implement grounded chatbot services

- [ ] 6.1 Implement the context builder and system prompt rules that pass only normalized current product data, bounded knowledge chunks, approved reviews, and safe order fields to the answer model.
- [ ] 6.2 Implement the product-search handler using MySQL only, returning a natural-language answer plus structured product cards and working when Qdrant is unavailable.
- [ ] 6.3 Implement product-detail, stock, and review handlers that resolve products, refresh current MySQL facts, include only active certificates, and return controlled unknown-product responses.
- [ ] 6.4 Implement hybrid recommendation by applying MySQL hard constraints first, intersecting Qdrant results with valid candidate IDs, selecting bounded results, and falling back to filtered candidates when semantic retrieval fails.
- [ ] 6.5 Implement product comparison by resolving each requested name, fetching current records/details/stock, reporting unresolved names safely, and returning structured comparison data.
- [ ] 6.6 Implement knowledge and mixed-query handling with bounded Qdrant context and an explicit uncertainty response when retrieved content is insufficient.
- [ ] 6.7 Integrate chat history into the service so the user message is saved, recent context is loaded, the assistant response is saved, and authenticated sessions are owner-checked.
- [ ] 6.8 Implement authenticated order-status handling that passes the authenticated user identity directly to the repository and returns no details for unauthorized or missing orders.
- [ ] 6.9 Add service tests for grounding, no-hallucination constraints, recommendation budget/stock preservation, Qdrant fallback, comparison resolution, and order privacy.

## 7. Expose the FastAPI contract

- [ ] 7.1 Define request and response schemas for `POST /api/chat`, including session ID, message, intent, answer, structured product cards, and controlled error fields.
- [ ] 7.2 Implement `POST /api/chat` with authentication context injection, session handling, service dispatch, bounded inputs, and stable HTTP error mapping.
- [ ] 7.3 Implement the planned product-detail and chat-session read endpoints with ownership checks where the session is authenticated.
- [ ] 7.4 Ensure product-card responses contain frontend fields such as image, name, effective price, origin, availability, and reason without requiring frontend parsing of answer text.
- [ ] 7.5 Add API tests covering anonymous chat, authenticated chat, malformed input, empty results, structured product cards, and unauthorized session/order access.

## 8. Add evaluation, observability, and demo validation

- [ ] 8.1 Add structured application logging for request ID, intent, tool, duration, retrieval count, and error type while excluding credentials, password hashes, confidential order data, and hidden reasoning.
- [ ] 8.2 Create `tests/eval_cases.json` with approximately 40–50 Vietnamese search, recommendation, comparison, knowledge, stock, review, and order cases from the implementation plan.
- [ ] 8.3 Add a lightweight evaluation runner or pytest coverage for intent accuracy, hard-filter correctness, current price/stock, grounding, and order privacy.
- [ ] 8.4 Run the manual demo scenarios from the plan and record results for product search, hybrid recommendation, comparison, knowledge RAG, stock, and authenticated order status.
- [ ] 8.5 Verify the definition of done, document the re-index command and required environment variables, and record any remaining schema/provider limitations before implementation handoff.
