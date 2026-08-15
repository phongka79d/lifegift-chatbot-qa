## Purpose

Extract a validated intent and structured search constraints from Vietnamese natural-language messages using a configurable OpenAI-compatible LLM.

## ADDED Requirements

### Requirement: Intent extraction returns a validated structured object
The system SHALL classify each user message into one of the supported intents and return a Pydantic-validated object containing optional product-search constraints.

#### Scenario: Product search message with a price limit
- **WHEN** the user sends a message asking for coffee under 250,000 VND
- **THEN** the system returns an intent of `PRODUCT_SEARCH` with `max_price` set to 250000 and no SQL or tool execution

#### Scenario: Recommendation message with soft preferences
- **WHEN** the user sends a message asking for aromatic coffee with low bitterness under 300,000 VND
- **THEN** the system returns an intent of `PRODUCT_RECOMMENDATION` with the category, price, and preference text preserved

#### Scenario: Order status message
- **WHEN** an authenticated user asks for the status of a specific order code
- **THEN** the system returns an intent of `ORDER_STATUS` with the order code extracted and does not trust a `user_id` embedded in the message

### Requirement: Intent extraction must not generate SQL or execute tools
The structured-output LLM call SHALL only produce intent and constraints; it SHALL NOT emit raw SQL or directly invoke repository or tool functions.

#### Scenario: Valid structured output
- **WHEN** the extraction pipeline runs
- **THEN** the output is parsed through a validated schema and any invalid output is rejected as an error

### Requirement: LLM provider configuration is provider-neutral
The system SHALL allow LLM base URL, API key, and model name to be configured through neutral environment variables without hardcoding a specific provider.

#### Scenario: Configurable endpoint
- **WHEN** the application starts with `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` set
- **THEN** the intent extraction client uses those values rather than a provider-specific constant
