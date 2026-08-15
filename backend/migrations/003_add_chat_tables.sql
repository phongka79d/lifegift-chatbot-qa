-- Migration 003: Add chat_sessions and chat_messages tables
CREATE TABLE IF NOT EXISTS chat_sessions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NULL,
    title VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_chat_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT UNSIGNED NOT NULL,
    role ENUM('USER', 'ASSISTANT') NOT NULL,
    content TEXT NOT NULL,
    metadata JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chat_messages_session FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Idempotent index creation (MySQL 8.0 lacks CREATE INDEX IF NOT EXISTS)
SET @has_session_idx = (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'chat_sessions' AND INDEX_NAME = 'idx_chat_sessions_user_updated'
);
SET @ddl_session_idx = IF(
    @has_session_idx = 0,
    'CREATE INDEX idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at)',
    'SELECT ''idx_chat_sessions_user_updated already exists'''
);
PREPARE stmt_session_idx FROM @ddl_session_idx;
EXECUTE stmt_session_idx;
DEALLOCATE PREPARE stmt_session_idx;

SET @has_message_idx = (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'chat_messages' AND INDEX_NAME = 'idx_chat_messages_session_created'
);
SET @ddl_message_idx = IF(
    @has_message_idx = 0,
    'CREATE INDEX idx_chat_messages_session_created ON chat_messages(session_id, created_at)',
    'SELECT ''idx_chat_messages_session_created already exists'''
);
PREPARE stmt_message_idx FROM @ddl_message_idx;
EXECUTE stmt_message_idx;
DEALLOCATE PREPARE stmt_message_idx;
