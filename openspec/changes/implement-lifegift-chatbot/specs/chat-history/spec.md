## Purpose

Persist conversation sessions and recent message context.

## ADDED Requirements

### Requirement: Chat sessions support anonymous and authenticated users
The system SHALL create or reuse a chat session and SHALL allow anonymous sessions with a null user identity.

#### Scenario: Authenticated session
- **WHEN** an authenticated user sends a message with a session identifier
- **THEN** the system associates the session with that user

#### Scenario: Anonymous session
- **WHEN** an unauthenticated user sends a message
- **THEN** the system stores the session without a user identity

### Requirement: Recent message context is bounded
The system SHALL load only the most recent six to ten messages for response generation and SHALL persist both user and assistant messages.

#### Scenario: History loaded for context
- **WHEN** a session already contains messages
- **THEN** the system loads the recent bounded history before generating the next assistant response

#### Scenario: Messages persisted
- **WHEN** a chat turn completes
- **THEN** both the user message and the assistant response are saved with their roles and timestamps
