-- Migration 001: Add product_details table
CREATE TABLE IF NOT EXISTS product_details (
    product_id BIGINT UNSIGNED PRIMARY KEY,
    ingredients TEXT,
    taste_profile VARCHAR(1000),
    key_benefits VARCHAR(1000),
    suitable_for VARCHAR(1000),
    usage_instructions TEXT,
    storage_instructions TEXT,
    shelf_life VARCHAR(100),
    producer_name VARCHAR(255),
    production_area VARCHAR(255),
    product_story TEXT,
    extra_attributes JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_details_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
