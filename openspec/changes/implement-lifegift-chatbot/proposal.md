## Why

LifeGift needs a grounded agricultural-product chatbot so customers can search, compare, recommend, learn about, and check the status of products and orders in natural language without the LLM inventing prices, stock, certificates, or reviews. The implementation plan exists but has not yet been turned into behavior contracts and executable work.

## What Changes

- Add the MySQL schema additions needed for the chatbot: `product_details`, `product_certificates`, `chat_sessions`, `chat_messages`, and `products.effective_price` with supporting indexes.
- Add repository-level MySQL data access for products, reviews, orders, and chat history, with parameterized SQL and order-ownership enforcement.
- Add Qdrant indexing and semantic retrieval over product knowledge, published blog content, and certificate descriptions.
- Add provider-neutral OpenAI-compatible LLM and embedding configuration with validated structured intent extraction.
- Add a deterministic chatbot service that routes intents to explicit tools and returns natural-language answers plus structured product cards.
- Add a FastAPI chat endpoint, persistent chat sessions, evaluation cases, and pytest coverage.

## Capabilities

### New Capabilities

- `chatbot-intent`: Extract a validated intent and structured constraints from Vietnamese natural-language messages using a configurable OpenAI-compatible LLM.
- `product-search`: Search active products by natural-language-derived filters using MySQL as the source of truth.
- `product-detail`: Return accurate product details, stock, primary image, and active certificates.
- `product-recommendation`: Combine MySQL hard constraints with Qdrant semantic preferences to recommend products.
- `product-comparison`: Compare resolved products using factual structured and conversational output.
- `knowledge-retrieval`: Index and retrieve grounded product and agricultural knowledge from Qdrant.
- `product-reviews`: Return verified, approved product reviews.
- `order-status`: Return order status history only to the authenticated owner of that order.
- `chat-history`: Persist conversation sessions and recent message context.

### Modified Capabilities

None.

## Impact

- New FastAPI backend service and configuration files.
- MySQL schema additions and demo seed data.
- New Qdrant collection and manual reindex script.
- New LangChain and OpenAI-compatible LLM/embedding dependencies.
- New `POST /api/chat` API surface with structured product-card responses.
- New repository, RAG, chatbot, service, script, and test modules.
