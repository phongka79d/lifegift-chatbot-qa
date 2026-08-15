## Purpose

Compare resolved products using factual structured and conversational output.

## ADDED Requirements

### Requirement: Product comparison resolves named products
The system SHALL resolve the requested product names, fetch their records, details, and current stock, and return both a natural-language explanation and structured product objects.

#### Scenario: Two products compared
- **WHEN** the user asks to compare two known products
- **THEN** the response contains factual fields for both products and structured product objects

#### Scenario: One product unresolved
- **WHEN** one requested product name cannot be resolved
- **THEN** the system reports the unresolved name and does not fabricate a product record

### Requirement: Comparison is grounded in current data
Comparison output SHALL use current MySQL price, stock, and product details rather than stale vector text.

#### Scenario: Current stock used
- **WHEN** stock changes after indexing
- **THEN** the comparison reports the current inventory value
