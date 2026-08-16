-- Migration 005: Add product catalog columns from LifeGift Excel export
-- Columns: sku, short_description, unit, weight, pricing_type, stock_status, is_featured

SET @has_sku = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'products' AND COLUMN_NAME = 'sku'
);
SET @ddl_sku = IF(
    @has_sku = 0,
    'ALTER TABLE products ADD COLUMN sku VARCHAR(100) NULL AFTER brand_id',
    'SELECT ''sku already exists'''
);
PREPARE s FROM @ddl_sku; EXECUTE s; DEALLOCATE PREPARE s;

SET @has_sku_uq = (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'products' AND INDEX_NAME = 'uq_products_sku'
);
SET @ddl_sku_uq = IF(
    @has_sku_uq = 0,
    'CREATE UNIQUE INDEX uq_products_sku ON products(sku)',
    'SELECT ''uq_products_sku already exists'''
);
PREPARE s FROM @ddl_sku_uq; EXECUTE s; DEALLOCATE PREPARE s;

SET @has_short = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'products' AND COLUMN_NAME = 'short_description'
);
SET @ddl_short = IF(
    @has_short = 0,
    'ALTER TABLE products ADD COLUMN short_description VARCHAR(500) NULL AFTER description',
    'SELECT ''short_description already exists'''
);
PREPARE s FROM @ddl_short; EXECUTE s; DEALLOCATE PREPARE s;

SET @has_unit = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'products' AND COLUMN_NAME = 'unit'
);
SET @ddl_unit = IF(
    @has_unit = 0,
    'ALTER TABLE products ADD COLUMN unit VARCHAR(50) NULL AFTER sale_price',
    'SELECT ''unit already exists'''
);
PREPARE s FROM @ddl_unit; EXECUTE s; DEALLOCATE PREPARE s;

SET @has_weight = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'products' AND COLUMN_NAME = 'weight'
);
SET @ddl_weight = IF(
    @has_weight = 0,
    'ALTER TABLE products ADD COLUMN weight DECIMAL(12,2) NULL AFTER unit',
    'SELECT ''weight already exists'''
);
PREPARE s FROM @ddl_weight; EXECUTE s; DEALLOCATE PREPARE s;

SET @has_pricing = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'products' AND COLUMN_NAME = 'pricing_type'
);
SET @ddl_pricing = IF(
    @has_pricing = 0,
    'ALTER TABLE products ADD COLUMN pricing_type VARCHAR(50) NULL DEFAULT ''FIXED_PRICE'' AFTER origin',
    'SELECT ''pricing_type already exists'''
);
PREPARE s FROM @ddl_pricing; EXECUTE s; DEALLOCATE PREPARE s;

SET @has_stock_status = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'products' AND COLUMN_NAME = 'stock_status'
);
SET @ddl_stock_status = IF(
    @has_stock_status = 0,
    'ALTER TABLE products ADD COLUMN stock_status VARCHAR(50) NULL DEFAULT ''IN_STOCK'' AFTER pricing_type',
    'SELECT ''stock_status already exists'''
);
PREPARE s FROM @ddl_stock_status; EXECUTE s; DEALLOCATE PREPARE s;

SET @has_featured = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'products' AND COLUMN_NAME = 'is_featured'
);
SET @ddl_featured = IF(
    @has_featured = 0,
    'ALTER TABLE products ADD COLUMN is_featured TINYINT(1) NOT NULL DEFAULT 0 AFTER stock_status',
    'SELECT ''is_featured already exists'''
);
PREPARE s FROM @ddl_featured; EXECUTE s; DEALLOCATE PREPARE s;
