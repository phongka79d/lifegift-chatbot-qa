## Purpose

Return order status history only to the authenticated owner of that order.

## ADDED Requirements

### Requirement: Order status lookup enforces ownership
The system SHALL look up order status using the authenticated user identity and SHALL NOT accept a user identity supplied in the chat message.

#### Scenario: Owner requests their order
- **WHEN** the authenticated user asks for the status of their own order code
- **THEN** the system returns order status, payment status, creation time, and status history

#### Scenario: Another user's order is denied
- **WHEN** a request would return an order belonging to a different user
- **THEN** the system rejects the lookup and returns no order details

### Requirement: Order lookup is bounded to safe fields
The system SHALL NOT expose supplier costs, password hashes, or staff-only database fields in an order-status response.

#### Scenario: Safe order response
- **WHEN** an order lookup succeeds
- **THEN** the response contains only the agreed order status fields
