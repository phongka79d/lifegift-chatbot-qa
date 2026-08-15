-- Migration 002: Add product_certificates table
CREATE TABLE IF NOT EXISTS product_certificates (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    issuer VARCHAR(255),
    certificate_code VARCHAR(150),
    issued_at DATE,
    expires_at DATE,
    description TEXT,
    file_url VARCHAR(500),
    status ENUM('ACTIVE', 'EXPIRED', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_certificates_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Idempotent index creation (MySQL 8.0 lacks CREATE INDEX IF NOT EXISTS)
SET @has_cert_product_idx = (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'product_certificates' AND INDEX_NAME = 'idx_product_certificates_product'
);
SET @ddl_cert_product_idx = IF(
    @has_cert_product_idx = 0,
    'CREATE INDEX idx_product_certificates_product ON product_certificates(product_id)',
    'SELECT ''idx_product_certificates_product already exists'''
);
PREPARE stmt_cert_product_idx FROM @ddl_cert_product_idx;
EXECUTE stmt_cert_product_idx;
DEALLOCATE PREPARE stmt_cert_product_idx;

SET @has_cert_status_idx = (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'product_certificates' AND INDEX_NAME = 'idx_product_certificates_status'
);
SET @ddl_cert_status_idx = IF(
    @has_cert_status_idx = 0,
    'CREATE INDEX idx_product_certificates_status ON product_certificates(status)',
    'SELECT ''idx_product_certificates_status already exists'''
);
PREPARE stmt_cert_status_idx FROM @ddl_cert_status_idx;
EXECUTE stmt_cert_status_idx;
DEALLOCATE PREPARE stmt_cert_status_idx;
