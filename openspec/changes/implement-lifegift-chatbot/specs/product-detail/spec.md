## Purpose

Return accurate product details, stock, primary image, and active certificates from MySQL.

## ADDED Requirements

### Requirement: Product detail returns a bounded product record
The system SHALL return product identity, category, brand, descriptive details, primary image, and active certificates without exposing supplier internals or unrelated transaction history.

#### Scenario: Product detail success
- **WHEN** the user asks for details about a known product
- **THEN** the response contains that product's public details and only active certificates

#### Scenario: Unknown product
- **WHEN** a requested product cannot be resolved
- **THEN** the system returns a controlled unknown-product response rather than inventing a product

### Requirement: Stock is sourced from inventories
Current stock SHALL be computed from `inventories.available_quantity`, not from vector text or a cached display field.

#### Scenario: Available stock
- **WHEN** inventory rows total more than zero available quantity for a product
- **THEN** the product is reported as available with the summed quantity

#### Scenario: Zero stock
- **WHEN** inventory rows total zero available quantity for a product
- **THEN** the product is reported as unavailable
