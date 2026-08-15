## Purpose

Search active products by natural-language-derived filters using MySQL as the authoritative source of truth.

## ADDED Requirements

### Requirement: Product search uses MySQL and effective price
The system SHALL search only active products and SHALL apply price filtering to the stored effective price, which prefers sale price over regular price.

#### Scenario: Sale price overrides regular price
- **WHEN** a product has a regular price and a lower sale price and the search asks for products at or below the sale price
- **THEN** the product is returned with its effective price equal to the sale price

#### Scenario: Inactive products are excluded
- **WHEN** a product is not active
- **THEN** the search result SHALL NOT include that product

### Requirement: Product search supports structured filters
The system SHALL filter products by category, brand, origin, minimum price, maximum price, stock availability, and a result limit.

#### Scenario: Category and origin filter
- **WHEN** the user asks for tea from Ha Giang
- **THEN** the system maps the category and origin to MySQL filters and returns only matching active products

#### Scenario: In-stock filter
- **WHEN** stock filtering is requested
- **THEN** the system derives availability from inventory quantity and excludes products whose total available quantity is zero

### Requirement: Product search does not require vector retrieval
Structured product search SHALL work from MySQL alone, so a Qdrant outage SHALL NOT prevent filtered product search results.

#### Scenario: Qdrant unavailable
- **WHEN** the vector database is unavailable during a category or price search
- **THEN** the system still returns MySQL-backed product candidates
