## Purpose

Return verified, approved product reviews from MySQL.

## ADDED Requirements

### Requirement: Review lookup returns only approved reviews
The system SHALL return only reviews whose status is `APPROVED`, with a bounded result limit.

#### Scenario: Approved review returned
- **WHEN** a product has approved reviews
- **THEN** the response includes those reviews with rating, title, content, and creation time

#### Scenario: Pending or hidden review excluded
- **WHEN** a review is not approved
- **THEN** the response SHALL NOT include that review
