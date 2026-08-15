## Purpose

Index and retrieve grounded product and agricultural knowledge from Qdrant.

## ADDED Requirements

### Requirement: Published product and blog content is indexed
The system SHALL index published blog posts and descriptive product content into a single knowledge collection with source metadata.

#### Scenario: Published blog indexed
- **WHEN** a blog post has status `PUBLISHED`
- **THEN** its content is chunked, embedded, and searchable

#### Scenario: Unpublished blog excluded
- **WHEN** a blog post is not published
- **THEN** its content SHALL NOT be indexed

### Requirement: Knowledge retrieval returns relevant grounded chunks
The system SHALL embed the user's question, retrieve a limited number of top chunks, and generate an answer only from retrieved context.

#### Scenario: Answer grounded in retrieved content
- **WHEN** the user asks how to choose pure coffee
- **THEN** the system returns an answer supported by retrieved product or blog content

#### Scenario: Uncertain answer
- **WHEN** retrieved context does not answer the question
- **THEN** the system indicates uncertainty instead of fabricating agricultural claims

### Requirement: Certificate descriptions are retrievable but authority stays in MySQL
Certificate explanatory text MAY be indexed for retrieval, but certificate existence and status SHALL remain sourced from MySQL.

#### Scenario: Certificate retrieved for detail
- **WHEN** indexed certificate description is relevant to a question
- **THEN** the system may return the description but must not assert certificate validity from vector data alone
