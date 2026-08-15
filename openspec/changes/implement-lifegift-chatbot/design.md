## Context

See `proposal.md` for the motivation and capability scope. The implementation
plan describes a single FastAPI application that combines an existing LifeGift
relational schema with one Qdrant knowledge collection and a provider-neutral
OpenAI-compatible LLM endpoint.

The current workspace contains the implementation plan and OpenSpec artifacts,
but not the assumed backend source or `lifegift_demo_v2.sql` baseline. The first
implementation tasks therefore need to verify the real table names, columns,
status values, and authentication integration before applying migrations. The
design below treats the tables listed in the plan as the intended integration
boundary, not as an unverified schema dump.

The authoritative-data boundary is central to the implementation:

- MySQL owns product identity, current price, inventory, reviews, certificates,
  orders, and chat history.
- Qdrant owns semantic retrieval over descriptive product, published blog, and
  optional certificate-explanation documents.
- The LLM interprets messages and writes explanations from supplied context; it
  does not generate SQL or receive unrestricted database access.

The requirements for the individual capabilities are defined in
`specs/**/*.md` and are the acceptance contract for this design.

## Goals / Non-Goals

**Goals:**

- Build a small, testable FastAPI modular monolith with explicit repositories,
  retrieval components, intent extraction, routing, and response schemas.
- Make current-data answers deterministic: active products, effective prices,
  inventory totals, approved reviews, active certificates, and owner-scoped
  order status all come from MySQL queries.
- Add hybrid recommendation by applying MySQL hard constraints before semantic
  preference ranking, with a safe degraded result when Qdrant is unavailable.
- Keep the chat API response machine-readable, including a bounded answer,
  intent, session identifier, and structured product cards.
- Support manual, repeatable Qdrant re-indexing and provider-neutral LLM and
  embedding configuration.
- Deliver the recommended first vertical slice—structured product search through
  `POST /api/chat`—before layering on retrieval, recommendation, history, and
  order support.

**Non-Goals:**

- Multi-agent orchestration, autonomous agent loops, LangGraph, arbitrary
  Text-to-SQL, or agent-generated SQL.
- Microservices, event-driven vector synchronization, a separate reranker,
  fine-tuning, or production-scale workflow infrastructure.
- Conversation summarization, long-term preference memory, or a memory vector
  store in the MVP.
- Duplicating transactional data in Qdrant or creating separate vector
  collections for each content type.

## Decisions

### 1. Use a modular monolith with explicit data-flow boundaries

Place the implementation under the plan’s proposed `backend/app` structure:
`api`, `core`, `schemas`, `repositories`, `tools`, `rag`, `chatbot`, and
`services`. Keep the API layer responsible for authentication and transport,
repositories responsible for SQL, tools responsible for bounded use cases, and
the chatbot service responsible for orchestration. This keeps the feature easy
to test without introducing service-to-service deployment or a workflow engine.

An independently deployed service or an unbounded agent loop was considered,
but would add operational and failure complexity before the MVP has stable
interfaces. The module boundaries provide a migration path later if a concrete
scaling requirement appears.

### 2. Make repository queries the only path to structured facts

Implement `ProductRepository`, `ReviewRepository`, `OrderRepository`, and
`ChatRepository` with parameterized SQL. Product search uses active products and
`effective_price`; stock is the sum of `inventories.available_quantity`;
reviews require `APPROVED`; and certificate detail queries return only active
certificates. Order queries include the authenticated user ID in the database
predicate and return only customer-safe fields.

The generated `products.effective_price` column and supporting indexes are
preferred over recalculating sale-price rules in application code. This makes
search semantics consistent and keeps price filtering in MySQL. Dynamic filters
are assembled from a fixed allowlist of repository parameters, never from LLM
text or generated SQL.

Direct SQL in routers, prompts, or LLM parsers was considered and rejected
because it would weaken authorization and make source-of-truth behavior hard to
test.

### 3. Use one metadata-rich Qdrant collection and manual re-indexing

Create `lifegift_knowledge` with payload metadata such as `source_type`,
`source_id`, `product_id`, `category_id`, and `title`. Build one semantic
document per normal product, chunk published blog posts, and optionally index
certificate explanatory text. The indexing script reads from MySQL, embeds
documents through the configured embedding endpoint, and upserts them with
stable source identities so a manual re-index is repeatable.

Qdrant results are used for descriptive relevance, not current price, stock,
certificate validity, reviews, or order state. Product IDs returned by retrieval
are reconciled with fresh MySQL records before they reach the response context.
Separate collections and realtime CDC were considered, but a single collection
and `scripts/reindex_qdrant.py` match the MVP scale and reduce synchronization
failure modes.

### 4. Separate structured extraction from deterministic routing

Use one provider-neutral structured LLM call to produce a Pydantic-validated
intent object with a small enum (`PRODUCT_SEARCH`, `PRODUCT_DETAIL`,
`PRODUCT_RECOMMENDATION`, `PRODUCT_COMPARE`, `KNOWLEDGE`, `PRODUCT_REVIEW`,
`ORDER_STATUS`, `GENERAL`) and bounded fields for filters, product names, and
order code. This stage has no repository or tool access.

Route the validated object with ordinary Python dispatch to the explicit tool or
service for that intent. The final generation call receives a compact context
assembled from repository results and retrieved chunks. It may explain or
format those facts, but it cannot expand the candidate set or invent missing
values. An autonomous tool-calling loop was considered and rejected because the
specifications require predictable authorization, bounded inputs, and clear
fallbacks.

### 5. Apply hard constraints before semantic recommendation ranking

For recommendations, first query MySQL using category, price, availability, and
other explicit constraints. If no valid candidates remain, return a controlled
no-match response. Otherwise, use the soft-preference text for semantic
matching, intersect retrieved product IDs with the MySQL candidate set, rank by
semantic score, and select the default top three (maximum five unless the API
contract is explicitly expanded). The LLM receives only those selected,
current product records and explains the match.

If Qdrant fails, return the valid MySQL candidates with a limited-preference
indicator. This preserves useful product search and recommendation behavior
without allowing semantic similarity to override budget, category, or stock.

### 6. Keep response construction grounded and frontend-friendly

Use a context-builder module to normalize only the fields needed for the current
intent. Product cards are returned as structured response data rather than being
parsed from assistant prose. Product detail and comparison flows resolve names,
fetch current MySQL records and stock, and then optionally add relevant
knowledge chunks. Knowledge-only flows answer from bounded retrieved chunks and
state uncertainty when the context is insufficient.

The system prompt will explicitly prohibit invented products, prices, stock,
certificates, reviews, and unsupported health claims. It will not include raw
database rows, secrets, password hashes, supplier costs, or hidden reasoning.

### 7. Scope chat history and identity at the service boundary

Create or reuse a `chat_sessions` row, allow `user_id = NULL` for anonymous
sessions, and persist both user and assistant messages. Load only the recent
six-to-ten messages for generation. An authenticated request that supplies a
session ID must be checked against the authenticated owner before reading or
writing it; the user message can never override that identity.

The same authenticated identity is passed directly to `get_order_status`, where
ownership is enforced in SQL. Conversation summarization and long-term memory
were intentionally deferred to keep the persistence contract bounded.

### 8. Treat provider configuration and failure behavior as explicit seams

Use settings for `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`,
`EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`, and `EMBEDDING_MODEL`. Keep LangChain
limited to client initialization, structured output, prompt composition, and
retriever integration; business routing remains normal Python.

Handle invalid structured output, LLM downtime, Qdrant downtime, database
errors, unknown products, empty search results, unauthorized orders, and missing
orders with controlled responses. Log request ID, intent, tool, duration,
retrieval count, and error type without logging credentials, full confidential
order data, or hidden reasoning.

## Risks / Trade-offs

- [Unverified baseline schema] → Inspect the real LifeGift SQL schema and auth
  dependencies before writing migrations; add repository integration tests for
  actual column names and status values.
- [OpenAI-compatible providers differ in structured-output or embedding
  behavior] → Validate every extraction result with Pydantic, keep temperature
  zero for extraction, configure endpoints through settings, and return a
  controlled error when validation or provider calls fail.
- [Qdrant documents become stale or unavailable] → Keep mutable facts in MySQL,
  refresh product records after retrieval, expose a manual re-index command, and
  degrade recommendations to MySQL-filtered candidates.
- [LLM prompt receives more data than intended] → Build allowlisted compact
  context objects and test that supplier fields, password hashes, unpublished
  posts, hidden reviews, and unrelated order data never enter responses.
- [Session or order authorization regression] → Enforce ownership in repository
  predicates and cover anonymous sessions, cross-user session access, and
  cross-user order access with tests.
- [Migration failure affects the existing commerce schema] → Apply additive
  migrations after a verified baseline, back up before deployment, make new
  objects independently removable, and avoid destructive rollback of existing
  tables.
- [The broad MVP delays a usable demo] → Implement and validate the structured
  product-search slice first, then add Qdrant recommendation, knowledge, and
  support capabilities in the plan’s stated order.

## Migration Plan

1. Verify and snapshot the existing MySQL schema and authentication contract.
   Apply additive migrations for `product_details`, `product_certificates`,
   `chat_sessions`, `chat_messages`, `products.effective_price`, and the
   required indexes. Seed only the descriptive product and certificate data
   needed for the demo.
2. Implement and test repository queries against the verified schema before
   enabling the chat route. Confirm effective-price, inventory, review, and
   order-ownership behavior independently of the LLM.
3. Create the Qdrant collection and run the manual indexing script. Validate
   published-content filtering, source metadata, and retrieval quality with the
   evaluation cases.
4. Deploy configuration, intent extraction, deterministic routing, and
   `POST /api/chat` incrementally. Start with product search and structured
   product cards, then enable recommendation, comparison, knowledge, reviews,
   chat history, and order status as their tests pass.
5. If rollback is required, disable the chat route and remove the Qdrant
   collection/indexing deployment first. Restore the database from the backup
   only if necessary; otherwise remove only the new chatbot tables/column after
   confirming no dependent data must be retained. Existing commerce tables and
   data must not be reset as part of a chatbot rollback.
