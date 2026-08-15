-- Migration 004: Add effective_price to products and create supporting index
-- Safe additive migration: only applies the generated column if it is missing.
SET @has_effective_price = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'products'
      AND COLUMN_NAME = 'effective_price'
);

SET @ddl_effective_price = IF(
    @has_effective_price = 0,
    'ALTER TABLE products ADD COLUMN effective_price DECIMAL(15,2) GENERATED ALWAYS AS (COALESCE(sale_price, price)) STORED',
    'SELECT ''effective_price already exists'''
);
PREPARE stmt_effective_price FROM @ddl_effective_price;
EXECUTE stmt_effective_price;
DEALLOCATE PREPARE stmt_effective_price;

SET @has_price_idx = (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'products'
      AND INDEX_NAME = 'idx_products_status_category_price'
);

SET @ddl_price_idx = IF(
    @has_price_idx = 0,
    'CREATE INDEX idx_products_status_category_price ON products(status, category_id, effective_price)',
    'SELECT ''idx_products_status_category_price already exists'''
);
PREPARE stmt_price_idx FROM @ddl_price_idx;
EXECUTE stmt_price_idx;
DEALLOCATE PREPARE stmt_price_idx;

