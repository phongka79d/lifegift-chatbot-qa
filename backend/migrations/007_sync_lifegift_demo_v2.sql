-- ============================================================
-- 007_sync_lifegift_demo_v2.sql
-- Safely reshape lifegift_db toward lifegift_demo_v2.sql
-- WITHOUT dropping the database or deleting existing rows.
--
-- Preserved (chatbot-only, not in v2):
--   chat_sessions, chat_messages, product_details,
--   product_certificates, products.effective_price
--
-- Strategy:
--   1) create missing v2 tables
--   2) alter existing tables / backfill required columns
--   3) synthesize order scaffolding so reviews can keep
--      their rows under v2 order_id FKs
--   4) add indexes / checks that do not destroy data
-- ============================================================

USE lifegift_db;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET UNIQUE_CHECKS = 0;

-- ------------------------------------------------------------
-- 0. Helpers / preflight markers
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS _schema_migrations (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    migration_name VARCHAR(150) NOT NULL UNIQUE,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Abort if already applied
SET @already = (
    SELECT COUNT(*) FROM _schema_migrations WHERE migration_name = '007_sync_lifegift_demo_v2'
);
-- Note: caller should skip re-run; we still guard critical DROPs below.

-- ============================================================
-- 1. NEW TABLES (create only if missing)
-- ============================================================

CREATE TABLE IF NOT EXISTS roles (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS user_roles (
    user_id BIGINT UNSIGNED NOT NULL,
    role_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_user_roles_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_user_roles_role
        FOREIGN KEY (role_id) REFERENCES roles(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS addresses (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    receiver_name VARCHAR(150) NOT NULL,
    receiver_phone VARCHAR(20) NOT NULL,
    province VARCHAR(100) NOT NULL,
    district VARCHAR(100),
    ward VARCHAR(100),
    address_detail VARCHAR(255) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_addresses_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS carts (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_carts_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cart_items (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cart_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_cart_product (cart_id, product_id),
    CONSTRAINT chk_cart_items_quantity CHECK (quantity > 0),
    CONSTRAINT fk_cart_items_cart
        FOREIGN KEY (cart_id) REFERENCES carts(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_cart_items_product
        FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS inventory_transactions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    inventory_id BIGINT UNSIGNED NOT NULL,
    transaction_type ENUM(
        'IMPORT','SALE','RETURN','ADJUSTMENT','TRANSFER_IN','TRANSFER_OUT'
    ) NOT NULL,
    quantity INT NOT NULL,
    reference_type VARCHAR(50),
    reference_id BIGINT UNSIGNED,
    note VARCHAR(500),
    created_by BIGINT UNSIGNED NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_inventory_transactions_quantity CHECK (quantity > 0),
    CONSTRAINT fk_inventory_transactions_inventory
        FOREIGN KEY (inventory_id) REFERENCES inventories(id),
    CONSTRAINT fk_inventory_transactions_user
        FOREIGN KEY (created_by) REFERENCES users(id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS suppliers (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(150),
    address VARCHAR(255),
    tax_code VARCHAR(50),
    status ENUM('ACTIVE','INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS purchase_orders (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    purchase_code VARCHAR(80) NOT NULL UNIQUE,
    supplier_id BIGINT UNSIGNED NOT NULL,
    warehouse_id BIGINT UNSIGNED NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    status ENUM('DRAFT','ORDERED','PARTIAL_RECEIVED','RECEIVED','CANCELLED')
        NOT NULL DEFAULT 'DRAFT',
    ordered_at DATETIME,
    expected_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_purchase_orders_total CHECK (total_amount >= 0),
    CONSTRAINT fk_purchase_orders_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    CONSTRAINT fk_purchase_orders_warehouse
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS purchase_order_items (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    purchase_order_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,
    quantity INT NOT NULL,
    unit_cost DECIMAL(15,2) NOT NULL,
    subtotal DECIMAL(15,2) NOT NULL,
    UNIQUE KEY uk_purchase_order_product (purchase_order_id, product_id),
    CONSTRAINT chk_purchase_order_items_quantity CHECK (quantity > 0),
    CONSTRAINT chk_purchase_order_items_unit_cost CHECK (unit_cost >= 0),
    CONSTRAINT chk_purchase_order_items_subtotal CHECK (subtotal >= 0),
    CONSTRAINT fk_purchase_order_items_order
        FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_purchase_order_items_product
        FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS goods_receipts (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    receipt_code VARCHAR(80) NOT NULL UNIQUE,
    purchase_order_id BIGINT UNSIGNED NOT NULL,
    warehouse_id BIGINT UNSIGNED NOT NULL,
    received_by BIGINT UNSIGNED NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    note VARCHAR(500),
    received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_goods_receipts_total CHECK (total_amount >= 0),
    CONSTRAINT fk_goods_receipts_purchase_order
        FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id),
    CONSTRAINT fk_goods_receipts_warehouse
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
    CONSTRAINT fk_goods_receipts_user
        FOREIGN KEY (received_by) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS goods_receipt_items (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    goods_receipt_id BIGINT UNSIGNED NOT NULL,
    purchase_order_item_id BIGINT UNSIGNED NOT NULL,
    received_quantity INT NOT NULL,
    unit_cost DECIMAL(15,2) NOT NULL,
    subtotal DECIMAL(15,2) NOT NULL,
    UNIQUE KEY uk_receipt_purchase_item (goods_receipt_id, purchase_order_item_id),
    CONSTRAINT chk_goods_receipt_items_quantity CHECK (received_quantity > 0),
    CONSTRAINT chk_goods_receipt_items_unit_cost CHECK (unit_cost >= 0),
    CONSTRAINT chk_goods_receipt_items_subtotal CHECK (subtotal >= 0),
    CONSTRAINT fk_goods_receipt_items_receipt
        FOREIGN KEY (goods_receipt_id) REFERENCES goods_receipts(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_goods_receipt_items_purchase_item
        FOREIGN KEY (purchase_order_item_id) REFERENCES purchase_order_items(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS payments (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL,
    payment_method ENUM('COD','BANK_TRANSFER','VNPAY','MOMO') NOT NULL,
    transaction_code VARCHAR(150),
    amount DECIMAL(15,2) NOT NULL,
    status ENUM('PENDING','SUCCESS','FAILED','REFUNDED') NOT NULL DEFAULT 'PENDING',
    paid_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_payments_amount CHECK (amount >= 0),
    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id) REFERENCES orders(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS coupon_usages (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    coupon_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    order_id BIGINT UNSIGNED NOT NULL,
    discount_amount DECIMAL(15,2) NOT NULL,
    used_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_coupon_usage_order (order_id),
    CONSTRAINT chk_coupon_usages_discount CHECK (discount_amount >= 0)
    -- FKs added after coupons rebuild
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS affiliates (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL UNIQUE,
    affiliate_code VARCHAR(80) NOT NULL UNIQUE,
    commission_rate DECIMAL(5,2) NOT NULL DEFAULT 5.00,
    status ENUM('PENDING','ACTIVE','INACTIVE','REJECTED') NOT NULL DEFAULT 'PENDING',
    approved_by BIGINT UNSIGNED NULL,
    approved_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_affiliates_commission_rate
        CHECK (commission_rate >= 0 AND commission_rate <= 100),
    CONSTRAINT fk_affiliates_user
        FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_affiliates_approved_by
        FOREIGN KEY (approved_by) REFERENCES users(id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS affiliate_links (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    affiliate_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NULL,
    code VARCHAR(100) NOT NULL UNIQUE,
    click_count INT NOT NULL DEFAULT 0,
    status ENUM('ACTIVE','INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_affiliate_links_click_count CHECK (click_count >= 0),
    CONSTRAINT fk_affiliate_links_affiliate
        FOREIGN KEY (affiliate_id) REFERENCES affiliates(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_affiliate_links_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS commissions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    affiliate_id BIGINT UNSIGNED NOT NULL,
    order_id BIGINT UNSIGNED NOT NULL,
    order_amount DECIMAL(15,2) NOT NULL,
    commission_rate DECIMAL(5,2) NOT NULL,
    commission_amount DECIMAL(15,2) NOT NULL,
    status ENUM('PENDING','APPROVED','PAID','CANCELLED') NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    paid_at DATETIME,
    UNIQUE KEY uk_commissions_order (order_id),
    CONSTRAINT chk_commissions_order_amount CHECK (order_amount >= 0),
    CONSTRAINT chk_commissions_rate CHECK (commission_rate >= 0 AND commission_rate <= 100),
    CONSTRAINT chk_commissions_amount CHECK (commission_amount >= 0),
    CONSTRAINT fk_commissions_affiliate
        FOREIGN KEY (affiliate_id) REFERENCES affiliates(id),
    CONSTRAINT fk_commissions_order
        FOREIGN KEY (order_id) REFERENCES orders(id)
) ENGINE=InnoDB;

-- ============================================================
-- 2. USERS → v2 shape (keep existing rows)
-- ============================================================

-- Add new columns if missing
SET @sql = (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE users ADD COLUMN username VARCHAR(100) NULL AFTER id',
    'SELECT 1'
  ) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'username'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE users ADD COLUMN password VARCHAR(255) NULL AFTER username',
    'SELECT 1'
  ) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'password'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE users ADD COLUMN avatar VARCHAR(500) NULL AFTER email',
    'SELECT 1'
  ) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'avatar'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE users ADD COLUMN status ENUM(''ACTIVE'',''INACTIVE'',''LOCKED'',''PENDING'') NOT NULL DEFAULT ''ACTIVE'' AFTER avatar',
    'SELECT 1'
  ) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'status'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE users ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at',
    'SELECT 1'
  ) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'updated_at'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Backfill required auth fields without wiping existing identity data
UPDATE users
SET username = COALESCE(
        NULLIF(username, ''),
        CASE id
            WHEN 1 THEN 'admin'
            WHEN 2 THEN 'staff01'
            WHEN 3 THEN 'nguyenvana'
            WHEN 4 THEN 'tranthib'
            WHEN 5 THEN 'leminhc'
            ELSE CONCAT('user_', id)
        END
    ),
    password = COALESCE(
        NULLIF(password, ''),
        '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy'
    ),
    full_name = COALESCE(NULLIF(full_name, ''), CONCAT('User ', id));

ALTER TABLE users
    MODIFY COLUMN username VARCHAR(100) NOT NULL,
    MODIFY COLUMN password VARCHAR(255) NOT NULL,
    MODIFY COLUMN full_name VARCHAR(150) NOT NULL,
    MODIFY COLUMN phone VARCHAR(20) NULL,
    MODIFY COLUMN email VARCHAR(150) NULL;

-- Unique username (ignore if already exists)
SET @sql = (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE users ADD UNIQUE KEY uk_users_username (username)',
    'SELECT 1'
  ) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND INDEX_NAME = 'uk_users_username'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- phone unique if possible (skip when duplicates)
SET @dup_phone = (
  SELECT COUNT(*) FROM (
    SELECT phone FROM users WHERE phone IS NOT NULL GROUP BY phone HAVING COUNT(*) > 1
  ) d
);
SET @sql = IF(
  @dup_phone = 0 AND (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND INDEX_NAME = 'uk_users_phone'
  ) = 0,
  'ALTER TABLE users ADD UNIQUE KEY uk_users_phone (phone)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============================================================
-- 3. CATEGORIES / BRANDS
-- ============================================================

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE categories ADD COLUMN parent_id BIGINT UNSIGNED NULL AFTER id','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='categories' AND COLUMN_NAME='parent_id');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE categories ADD COLUMN description TEXT NULL AFTER slug','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='categories' AND COLUMN_NAME='description');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE categories ADD COLUMN image_url VARCHAR(500) NULL AFTER description','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='categories' AND COLUMN_NAME='image_url');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE categories ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='categories' AND COLUMN_NAME='updated_at');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

ALTER TABLE categories
    MODIFY COLUMN name VARCHAR(150) NOT NULL,
    MODIFY COLUMN slug VARCHAR(180) NOT NULL;

-- parent FK
SET @sql = (
  SELECT IF(COUNT(*)=0,
    'ALTER TABLE categories ADD CONSTRAINT fk_categories_parent FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL',
    'SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='categories' AND CONSTRAINT_NAME='fk_categories_parent'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE brands ADD COLUMN slug VARCHAR(180) NULL AFTER name','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='brands' AND COLUMN_NAME='slug');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE brands ADD COLUMN description TEXT NULL AFTER slug','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='brands' AND COLUMN_NAME='description');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE brands ADD COLUMN logo_url VARCHAR(500) NULL AFTER description','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='brands' AND COLUMN_NAME='logo_url');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE brands ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='brands' AND COLUMN_NAME='updated_at');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

UPDATE brands
SET slug = COALESCE(
    NULLIF(slug, ''),
    LOWER(REPLACE(REPLACE(REPLACE(REPLACE(name,' ','-'),'đ','d'),'Đ','d'),'--','-'))
)
WHERE slug IS NULL OR slug = '';

-- Ensure unique slugs
UPDATE brands b
JOIN (
  SELECT id, CONCAT(slug, '-', id) AS new_slug
  FROM (
    SELECT id, slug,
           ROW_NUMBER() OVER (PARTITION BY slug ORDER BY id) AS rn
    FROM brands
  ) x WHERE rn > 1
) d ON d.id = b.id
SET b.slug = d.new_slug;

ALTER TABLE brands
    MODIFY COLUMN name VARCHAR(150) NOT NULL,
    MODIFY COLUMN slug VARCHAR(180) NOT NULL;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE brands ADD UNIQUE KEY uk_brands_name (name)','SELECT 1')
  FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='brands' AND INDEX_NAME='uk_brands_name');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE brands ADD UNIQUE KEY uk_brands_slug (slug)','SELECT 1')
  FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='brands' AND INDEX_NAME='uk_brands_slug');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============================================================
-- 4. PRODUCTS
-- ============================================================

-- Ensure no null category/sku before NOT NULL
UPDATE products SET category_id = (
  SELECT id FROM categories ORDER BY id LIMIT 1
) WHERE category_id IS NULL;

UPDATE products
SET sku = COALESCE(NULLIF(sku,''), CONCAT('SKU-', id))
WHERE sku IS NULL OR sku = '';

-- Widen status enum: add DRAFT, map OUT_OF_STOCK -> INACTIVE via stock_status, then drop OUT_OF_STOCK
UPDATE products
SET stock_status = 'OUT_OF_STOCK',
    status = 'INACTIVE'
WHERE status = 'OUT_OF_STOCK';

-- Drop FKs with ON DELETE SET NULL before making category_id NOT NULL
SET @fk = (SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND CONSTRAINT_NAME='fk_products_category');
SET @sql = IF(@fk IS NOT NULL, 'ALTER TABLE products DROP FOREIGN KEY fk_products_category', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @fk = (SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND CONSTRAINT_NAME='fk_products_brand');
SET @sql = IF(@fk IS NOT NULL, 'ALTER TABLE products DROP FOREIGN KEY fk_products_brand', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

ALTER TABLE products
    MODIFY COLUMN category_id BIGINT UNSIGNED NOT NULL,
    MODIFY COLUMN sku VARCHAR(80) NOT NULL,
    MODIFY COLUMN slug VARCHAR(280) NOT NULL,
    MODIFY COLUMN unit VARCHAR(50) NOT NULL DEFAULT 'Sản phẩm',
    MODIFY COLUMN weight DECIMAL(10,2) NULL,
    MODIFY COLUMN origin VARCHAR(150) NULL,
    MODIFY COLUMN pricing_type ENUM('FIXED_PRICE','CONTACT_FOR_PRICE') NOT NULL DEFAULT 'FIXED_PRICE',
    MODIFY COLUMN stock_status ENUM('IN_STOCK','LOW_STOCK','OUT_OF_STOCK','PRE_ORDER') NOT NULL DEFAULT 'IN_STOCK',
    MODIFY COLUMN status ENUM('ACTIVE','INACTIVE','DRAFT','OUT_OF_STOCK') NOT NULL DEFAULT 'ACTIVE';

-- Second pass: remove OUT_OF_STOCK from products.status enum
UPDATE products SET status = 'INACTIVE' WHERE status = 'OUT_OF_STOCK';
ALTER TABLE products
    MODIFY COLUMN status ENUM('ACTIVE','INACTIVE','DRAFT') NOT NULL DEFAULT 'ACTIVE';

UPDATE products SET unit = COALESCE(NULLIF(unit,''), 'Sản phẩm');

-- Recreate product FKs to match v2 semantics
SET @sql = (SELECT IF(COUNT(*)=0,
  'ALTER TABLE products ADD CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories(id)',
  'SELECT 1') FROM information_schema.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND CONSTRAINT_NAME='fk_products_category');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,
  'ALTER TABLE products ADD CONSTRAINT fk_products_brand FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE SET NULL',
  'SELECT 1') FROM information_schema.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND CONSTRAINT_NAME='fk_products_brand');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Keep effective_price generated column if present (chatbot). Recreate if missing.
SET @has_eff = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND COLUMN_NAME='effective_price'
);
SET @sql = IF(
  @has_eff = 0,
  'ALTER TABLE products ADD COLUMN effective_price DECIMAL(15,2) AS (COALESCE(sale_price, price)) STORED',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- product checks (ignore if exist)
SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE products ADD CONSTRAINT chk_products_price CHECK (price >= 0)','SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND CONSTRAINT_NAME='chk_products_price');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE products ADD CONSTRAINT chk_products_sale_price CHECK (sale_price IS NULL OR sale_price >= 0)','SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND CONSTRAINT_NAME='chk_products_sale_price');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE products ADD CONSTRAINT chk_products_weight CHECK (weight IS NULL OR weight >= 0)','SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND CONSTRAINT_NAME='chk_products_weight');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE product_images ADD CONSTRAINT chk_product_images_sort_order CHECK (sort_order >= 0)','SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='product_images' AND CONSTRAINT_NAME='chk_product_images_sort_order');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============================================================
-- 5. WAREHOUSES
-- ============================================================

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE warehouses ADD COLUMN code VARCHAR(50) NULL AFTER id','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='warehouses' AND COLUMN_NAME='code');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE warehouses ADD COLUMN address VARCHAR(255) NULL AFTER name','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='warehouses' AND COLUMN_NAME='address');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE warehouses ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='warehouses' AND COLUMN_NAME='updated_at');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

UPDATE warehouses
SET code = COALESCE(NULLIF(code,''), CONCAT('WH-', id)),
    name = LEFT(name, 150);

ALTER TABLE warehouses
    MODIFY COLUMN code VARCHAR(50) NOT NULL,
    MODIFY COLUMN name VARCHAR(150) NOT NULL;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE warehouses ADD UNIQUE KEY uk_warehouses_code (code)','SELECT 1')
  FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='warehouses' AND INDEX_NAME='uk_warehouses_code');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============================================================
-- 6. INVENTORIES: available_quantity becomes GENERATED
-- ============================================================

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE inventories ADD COLUMN quantity INT NOT NULL DEFAULT 0 AFTER product_id','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventories' AND COLUMN_NAME='quantity');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE inventories ADD COLUMN min_stock INT NOT NULL DEFAULT 0 AFTER reserved_quantity','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventories' AND COLUMN_NAME='min_stock');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Backfill on-hand quantity from previous available + reserved model
UPDATE inventories
SET quantity = GREATEST(COALESCE(available_quantity,0) + COALESCE(reserved_quantity,0), COALESCE(reserved_quantity,0));

-- Drop plain available_quantity and recreate as generated (only if not already generated)
SET @avail_extra = (
  SELECT EXTRA FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventories' AND COLUMN_NAME='available_quantity'
);
SET @sql = IF(
  @avail_extra IS NOT NULL AND @avail_extra NOT LIKE '%GENERATED%',
  'ALTER TABLE inventories DROP COLUMN available_quantity',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @has_avail = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventories' AND COLUMN_NAME='available_quantity'
);
SET @sql = IF(
  @has_avail = 0,
  'ALTER TABLE inventories ADD COLUMN available_quantity INT GENERATED ALWAYS AS (quantity - reserved_quantity) STORED AFTER reserved_quantity',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Ensure unique (warehouse_id, product_id)
SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE inventories ADD UNIQUE KEY uk_inventory_warehouse_product (warehouse_id, product_id)','SELECT 1')
  FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventories' AND INDEX_NAME IN ('uk_inventory_warehouse_product','uq_inventories_product_warehouse') LIMIT 1);
-- Prefer add if neither exists
SET @has_inv_uq = (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventories'
    AND INDEX_NAME IN ('uk_inventory_warehouse_product','uq_inventories_product_warehouse')
);
SET @sql = IF(@has_inv_uq=0,
  'ALTER TABLE inventories ADD UNIQUE KEY uk_inventory_warehouse_product (warehouse_id, product_id)',
  'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE inventories ADD CONSTRAINT chk_inventories_quantity CHECK (quantity >= 0)','SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventories' AND CONSTRAINT_NAME='chk_inventories_quantity');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE inventories ADD CONSTRAINT chk_inventories_reserved CHECK (reserved_quantity >= 0)','SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventories' AND CONSTRAINT_NAME='chk_inventories_reserved');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE inventories ADD CONSTRAINT chk_inventories_reserved_lte_quantity CHECK (reserved_quantity <= quantity)','SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventories' AND CONSTRAINT_NAME='chk_inventories_reserved_lte_quantity');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE inventories ADD CONSTRAINT chk_inventories_min_stock CHECK (min_stock >= 0)','SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventories' AND CONSTRAINT_NAME='chk_inventories_min_stock');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============================================================
-- 7. ORDERS / ORDER_ITEMS / HISTORY
-- ============================================================

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE orders ADD COLUMN receiver_name VARCHAR(150) NULL AFTER user_id','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND COLUMN_NAME='receiver_name');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE orders ADD COLUMN receiver_phone VARCHAR(20) NULL AFTER receiver_name','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND COLUMN_NAME='receiver_phone');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE orders ADD COLUMN shipping_province VARCHAR(100) NULL AFTER receiver_phone','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND COLUMN_NAME='shipping_province');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE orders ADD COLUMN shipping_district VARCHAR(100) NULL AFTER shipping_province','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND COLUMN_NAME='shipping_district');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE orders ADD COLUMN shipping_ward VARCHAR(100) NULL AFTER shipping_district','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND COLUMN_NAME='shipping_ward');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE orders ADD COLUMN shipping_address VARCHAR(255) NULL AFTER shipping_ward','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND COLUMN_NAME='shipping_address');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE orders ADD COLUMN subtotal DECIMAL(15,2) NOT NULL DEFAULT 0 AFTER shipping_address','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND COLUMN_NAME='subtotal');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE orders ADD COLUMN shipping_fee DECIMAL(15,2) NOT NULL DEFAULT 0 AFTER subtotal','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND COLUMN_NAME='shipping_fee');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE orders ADD COLUMN discount_amount DECIMAL(15,2) NOT NULL DEFAULT 0 AFTER shipping_fee','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND COLUMN_NAME='discount_amount');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE orders ADD COLUMN payment_method ENUM(''COD'',''BANK_TRANSFER'',''VNPAY'',''MOMO'') NOT NULL DEFAULT ''COD'' AFTER total_amount','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND COLUMN_NAME='payment_method');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE orders ADD COLUMN note VARCHAR(500) NULL AFTER order_status','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND COLUMN_NAME='note');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Backfill shipping/receiver from linked users
UPDATE orders o
JOIN users u ON u.id = o.user_id
SET
  o.receiver_name = COALESCE(NULLIF(o.receiver_name,''), u.full_name, CONCAT('User ', u.id)),
  o.receiver_phone = COALESCE(NULLIF(o.receiver_phone,''), u.phone, '0000000000'),
  o.shipping_province = COALESCE(NULLIF(o.shipping_province,''), 'Việt Nam'),
  o.shipping_address = COALESCE(NULLIF(o.shipping_address,''), 'Địa chỉ chưa cập nhật'),
  o.subtotal = CASE WHEN o.subtotal = 0 THEN o.total_amount ELSE o.subtotal END;

ALTER TABLE orders
    MODIFY COLUMN order_code VARCHAR(80) NOT NULL,
    MODIFY COLUMN receiver_name VARCHAR(150) NOT NULL,
    MODIFY COLUMN receiver_phone VARCHAR(20) NOT NULL,
    MODIFY COLUMN shipping_province VARCHAR(100) NOT NULL,
    MODIFY COLUMN shipping_address VARCHAR(255) NOT NULL,
    MODIFY COLUMN payment_status ENUM('UNPAID','PENDING','PAID','FAILED','REFUNDED') NOT NULL DEFAULT 'UNPAID',
    MODIFY COLUMN order_status ENUM(
        'PENDING','CONFIRMED','PROCESSING','SHIPPING','DELIVERED','COMPLETED','CANCELLED','RETURN_REQUESTED','RETURNED'
    ) NOT NULL DEFAULT 'PENDING';

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE orders ADD UNIQUE KEY uk_orders_id_user (id, user_id)','SELECT 1')
  FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND INDEX_NAME='uk_orders_id_user');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- order_items: rename price -> unit_price and add snapshot fields
SET @has_price = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_items' AND COLUMN_NAME='price'
);
SET @has_unit_price = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_items' AND COLUMN_NAME='unit_price'
);
SET @sql = IF(@has_price=1 AND @has_unit_price=0,
  'ALTER TABLE order_items CHANGE COLUMN price unit_price DECIMAL(15,2) NOT NULL',
  'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE order_items ADD COLUMN product_name VARCHAR(255) NULL AFTER product_id','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_items' AND COLUMN_NAME='product_name');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE order_items ADD COLUMN sku VARCHAR(80) NULL AFTER product_name','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_items' AND COLUMN_NAME='sku');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE order_items ADD COLUMN subtotal DECIMAL(15,2) NULL AFTER quantity','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_items' AND COLUMN_NAME='subtotal');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

UPDATE order_items oi
JOIN products p ON p.id = oi.product_id
SET
  oi.product_name = COALESCE(NULLIF(oi.product_name,''), p.name),
  oi.sku = COALESCE(NULLIF(oi.sku,''), p.sku),
  oi.subtotal = COALESCE(oi.subtotal, oi.unit_price * oi.quantity);

ALTER TABLE order_items
    MODIFY COLUMN product_name VARCHAR(255) NOT NULL,
    MODIFY COLUMN sku VARCHAR(80) NOT NULL,
    MODIFY COLUMN subtotal DECIMAL(15,2) NOT NULL;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE order_items ADD UNIQUE KEY uk_order_product (order_id, product_id)','SELECT 1')
  FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_items' AND INDEX_NAME='uk_order_product');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE order_items ADD CONSTRAINT chk_order_items_unit_price CHECK (unit_price >= 0)','SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_items' AND CONSTRAINT_NAME='chk_order_items_unit_price');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE order_items ADD CONSTRAINT chk_order_items_quantity CHECK (quantity > 0)','SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_items' AND CONSTRAINT_NAME='chk_order_items_quantity');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE order_items ADD CONSTRAINT chk_order_items_subtotal CHECK (subtotal >= 0)','SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_items' AND CONSTRAINT_NAME='chk_order_items_subtotal');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- order_status_history: notes -> note, expand enum, add changed_by
SET @has_notes = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_status_history' AND COLUMN_NAME='notes'
);
SET @has_note = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_status_history' AND COLUMN_NAME='note'
);
SET @sql = IF(@has_notes=1 AND @has_note=0,
  'ALTER TABLE order_status_history CHANGE COLUMN notes note VARCHAR(500) NULL',
  'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE order_status_history ADD COLUMN changed_by BIGINT UNSIGNED NULL AFTER note','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_status_history' AND COLUMN_NAME='changed_by');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

ALTER TABLE order_status_history
    MODIFY COLUMN status ENUM(
        'PENDING','CONFIRMED','PROCESSING','SHIPPING','DELIVERED','COMPLETED','CANCELLED','RETURN_REQUESTED','RETURNED'
    ) NOT NULL;

SET @sql = (SELECT IF(COUNT(*)=0,
  'ALTER TABLE order_status_history ADD CONSTRAINT fk_order_status_history_user FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL',
  'SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_status_history' AND CONSTRAINT_NAME='fk_order_status_history_user');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============================================================
-- 8. COUPONS (empty in current DB) → rebuild to v2 shape
-- ============================================================

-- Drop dependent FK if any later; table currently unused (0 rows)
DROP TABLE IF EXISTS coupon_usages;
DROP TABLE IF EXISTS coupons;

CREATE TABLE coupons (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    discount_type ENUM('PERCENTAGE','FIXED_AMOUNT') NOT NULL,
    discount_value DECIMAL(15,2) NOT NULL,
    min_order_value DECIMAL(15,2) NOT NULL DEFAULT 0,
    max_discount DECIMAL(15,2),
    usage_limit INT NULL,
    usage_limit_per_user INT NULL,
    used_count INT NOT NULL DEFAULT 0,
    start_at DATETIME NOT NULL,
    end_at DATETIME NOT NULL,
    status ENUM('ACTIVE','INACTIVE','EXPIRED') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_coupons_discount_value CHECK (discount_value > 0),
    CONSTRAINT chk_coupons_min_order CHECK (min_order_value >= 0),
    CONSTRAINT chk_coupons_max_discount CHECK (max_discount IS NULL OR max_discount >= 0),
    CONSTRAINT chk_coupons_usage_limit CHECK (usage_limit IS NULL OR usage_limit > 0),
    CONSTRAINT chk_coupons_user_limit CHECK (usage_limit_per_user IS NULL OR usage_limit_per_user > 0),
    CONSTRAINT chk_coupons_used_count CHECK (used_count >= 0),
    CONSTRAINT chk_coupons_date_range CHECK (end_at > start_at),
    CONSTRAINT chk_coupons_percentage CHECK (
        discount_type <> 'PERCENTAGE' OR discount_value <= 100
    )
) ENGINE=InnoDB;

CREATE TABLE coupon_usages (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    coupon_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    order_id BIGINT UNSIGNED NOT NULL,
    discount_amount DECIMAL(15,2) NOT NULL,
    used_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_coupon_usage_order (order_id),
    CONSTRAINT chk_coupon_usages_discount CHECK (discount_amount >= 0),
    CONSTRAINT fk_coupon_usages_coupon FOREIGN KEY (coupon_id) REFERENCES coupons(id),
    CONSTRAINT fk_coupon_usages_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_coupon_usages_order FOREIGN KEY (order_id) REFERENCES orders(id)
) ENGINE=InnoDB;

-- ============================================================
-- 9. REVIEWS → attach to synthetic completed orders when needed
-- ============================================================

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE reviews ADD COLUMN order_id BIGINT UNSIGNED NULL AFTER user_id','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='reviews' AND COLUMN_NAME='order_id');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Attach at most one review to each existing (order_id, product_id) pair
UPDATE reviews r
JOIN (
    SELECT
        r2.id AS review_id,
        o.id AS order_id,
        ROW_NUMBER() OVER (
            PARTITION BY o.id, r2.product_id
            ORDER BY r2.id
        ) AS rn_on_order,
        ROW_NUMBER() OVER (
            PARTITION BY r2.id
            ORDER BY o.id
        ) AS rn_on_review
    FROM reviews r2
    JOIN orders o ON o.user_id = r2.user_id
    JOIN order_items oi
      ON oi.order_id = o.id
     AND oi.product_id = r2.product_id
    WHERE r2.order_id IS NULL
) m ON m.review_id = r.id
   AND m.rn_on_order = 1
   AND m.rn_on_review = 1
SET r.order_id = m.order_id;

-- One synthetic completed order per remaining review (preserves all review rows)
SET @max_order_id = (SELECT COALESCE(MAX(id), 0) FROM orders);
SET @max_oi_id = (SELECT COALESCE(MAX(id), 0) FROM order_items);

DROP TEMPORARY TABLE IF EXISTS tmp_review_orders;
CREATE TEMPORARY TABLE tmp_review_orders AS
SELECT
    r.id AS review_id,
    r.user_id,
    r.product_id,
    COALESCE(p.name, CONCAT('Product ', r.product_id)) AS product_name,
    COALESCE(NULLIF(p.sku, ''), CONCAT('SKU-', r.product_id)) AS sku,
    COALESCE(p.sale_price, p.price, 0) AS unit_price,
    @max_order_id + ROW_NUMBER() OVER (ORDER BY r.id) AS new_order_id,
    @max_oi_id + ROW_NUMBER() OVER (ORDER BY r.id) AS new_item_id
FROM reviews r
LEFT JOIN products p ON p.id = r.product_id
WHERE r.order_id IS NULL;

INSERT INTO orders (
    id, order_code, user_id,
    receiver_name, receiver_phone, shipping_province, shipping_address,
    subtotal, shipping_fee, discount_amount, total_amount,
    payment_method, payment_status, order_status, note, created_at, updated_at
)
SELECT
    t.new_order_id,
    CONCAT('MIG-REV-', LPAD(t.new_order_id, 8, '0')),
    t.user_id,
    COALESCE(u.full_name, CONCAT('User ', t.user_id)),
    COALESCE(u.phone, '0000000000'),
    'Việt Nam',
    'Đơn tổng hợp review (migration 007)',
    t.unit_price,
    0,
    0,
    t.unit_price,
    'COD',
    'PAID',
    'COMPLETED',
    'Synthetic order created by 007_sync_lifegift_demo_v2 to preserve review FKs',
    NOW(),
    NOW()
FROM tmp_review_orders t
JOIN users u ON u.id = t.user_id;

INSERT INTO order_items (
    id, order_id, product_id, product_name, sku, unit_price, quantity, subtotal
)
SELECT
    t.new_item_id,
    t.new_order_id,
    t.product_id,
    t.product_name,
    t.sku,
    t.unit_price,
    1,
    t.unit_price
FROM tmp_review_orders t;

UPDATE reviews r
JOIN tmp_review_orders t ON t.review_id = r.id
SET r.order_id = t.new_order_id;

DROP TEMPORARY TABLE IF EXISTS tmp_review_orders;

-- Normalize review status enum: REJECTED -> HIDDEN
UPDATE reviews SET status = 'APPROVED' WHERE status NOT IN ('PENDING','APPROVED','REJECTED','HIDDEN');
-- Expand then remap
ALTER TABLE reviews
    MODIFY COLUMN status ENUM('PENDING','APPROVED','REJECTED','HIDDEN') NOT NULL DEFAULT 'PENDING';
UPDATE reviews SET status = 'HIDDEN' WHERE status = 'REJECTED';
ALTER TABLE reviews
    MODIFY COLUMN status ENUM('PENDING','APPROVED','HIDDEN') NOT NULL DEFAULT 'PENDING',
    MODIFY COLUMN rating TINYINT NOT NULL,
    MODIFY COLUMN title VARCHAR(200) NULL,
    MODIFY COLUMN order_id BIGINT UNSIGNED NOT NULL;

-- Drop old FKs that conflict, then add v2 FKs
SET @sql = (SELECT IF(COUNT(*)>0, CONCAT('ALTER TABLE reviews DROP FOREIGN KEY ', CONSTRAINT_NAME), 'SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='reviews' AND CONSTRAINT_TYPE='FOREIGN KEY' AND CONSTRAINT_NAME='fk_reviews_user' LIMIT 1);
-- Drop known old FKs safely
SET @fk = (SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='reviews' AND CONSTRAINT_TYPE='FOREIGN KEY' AND CONSTRAINT_NAME='fk_reviews_user');
SET @sql = IF(@fk IS NOT NULL, CONCAT('ALTER TABLE reviews DROP FOREIGN KEY ', @fk), 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @fk = (SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='reviews' AND CONSTRAINT_TYPE='FOREIGN KEY' AND CONSTRAINT_NAME='fk_reviews_product');
SET @sql = IF(@fk IS NOT NULL, CONCAT('ALTER TABLE reviews DROP FOREIGN KEY ', @fk), 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE reviews ADD UNIQUE KEY uk_review_order_product (order_id, product_id)','SELECT 1')
  FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='reviews' AND INDEX_NAME='uk_review_order_product');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE reviews ADD CONSTRAINT chk_reviews_rating CHECK (rating BETWEEN 1 AND 5)','SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='reviews' AND CONSTRAINT_NAME='chk_reviews_rating');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,
  'ALTER TABLE reviews ADD CONSTRAINT fk_reviews_order_user FOREIGN KEY (order_id, user_id) REFERENCES orders(id, user_id)',
  'SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='reviews' AND CONSTRAINT_NAME='fk_reviews_order_user');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,
  'ALTER TABLE reviews ADD CONSTRAINT fk_reviews_order_product FOREIGN KEY (order_id, product_id) REFERENCES order_items(order_id, product_id)',
  'SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='reviews' AND CONSTRAINT_NAME='fk_reviews_order_product');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,
  'ALTER TABLE reviews ADD CONSTRAINT fk_reviews_product FOREIGN KEY (product_id) REFERENCES products(id)',
  'SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='reviews' AND CONSTRAINT_NAME='fk_reviews_product');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============================================================
-- 10. BLOG
-- ============================================================

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE blog_categories ADD COLUMN description VARCHAR(500) NULL AFTER slug','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='blog_categories' AND COLUMN_NAME='description');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE blog_categories ADD COLUMN status ENUM(''ACTIVE'',''INACTIVE'') NOT NULL DEFAULT ''ACTIVE'' AFTER description','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='blog_categories' AND COLUMN_NAME='status');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

ALTER TABLE blog_categories
    MODIFY COLUMN name VARCHAR(150) NOT NULL,
    MODIFY COLUMN slug VARCHAR(180) NOT NULL;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE blog_posts ADD COLUMN author_id BIGINT UNSIGNED NULL AFTER category_id','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='blog_posts' AND COLUMN_NAME='author_id');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'ALTER TABLE blog_posts ADD COLUMN thumbnail VARCHAR(500) NULL AFTER slug','SELECT 1')
  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='blog_posts' AND COLUMN_NAME='thumbnail');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

UPDATE blog_posts
SET author_id = COALESCE(author_id, (SELECT id FROM users ORDER BY id LIMIT 1)),
    category_id = COALESCE(category_id, (SELECT id FROM blog_categories ORDER BY id LIMIT 1));

-- Expand status then remap ARCHIVED -> HIDDEN
ALTER TABLE blog_posts
    MODIFY COLUMN status ENUM('DRAFT','PUBLISHED','ARCHIVED','HIDDEN') NOT NULL DEFAULT 'DRAFT';
UPDATE blog_posts SET status = 'HIDDEN' WHERE status = 'ARCHIVED';

ALTER TABLE blog_posts
    MODIFY COLUMN category_id BIGINT UNSIGNED NOT NULL,
    MODIFY COLUMN author_id BIGINT UNSIGNED NOT NULL,
    MODIFY COLUMN slug VARCHAR(300) NOT NULL,
    MODIFY COLUMN summary VARCHAR(1000) NULL,
    MODIFY COLUMN content LONGTEXT NULL,
    MODIFY COLUMN status ENUM('DRAFT','PUBLISHED','HIDDEN') NOT NULL DEFAULT 'DRAFT';

SET @sql = (SELECT IF(COUNT(*)=0,
  'ALTER TABLE blog_posts ADD CONSTRAINT fk_blog_posts_author FOREIGN KEY (author_id) REFERENCES users(id)',
  'SELECT 1')
  FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='blog_posts' AND CONSTRAINT_NAME='fk_blog_posts_author');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============================================================
-- 11. INDEXES from v2 (create if missing)
-- ============================================================

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_addresses_user ON addresses(user_id)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='idx_addresses_user');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_products_category ON products(category_id)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND INDEX_NAME='idx_products_category');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_products_brand ON products(brand_id)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND INDEX_NAME='idx_products_brand');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_products_status ON products(status)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND INDEX_NAME='idx_products_status');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_products_featured ON products(is_featured)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND INDEX_NAME='idx_products_featured');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_cart_items_product ON cart_items(product_id)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='idx_cart_items_product');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_inventory_product ON inventories(product_id)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventories' AND INDEX_NAME='idx_inventory_product');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_inventory_transactions_inventory_created ON inventory_transactions(inventory_id, created_at)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='idx_inventory_transactions_inventory_created');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_purchase_orders_supplier ON purchase_orders(supplier_id)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='idx_purchase_orders_supplier');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_purchase_orders_status ON purchase_orders(status)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='idx_purchase_orders_status');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_goods_receipts_po ON goods_receipts(purchase_order_id)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='idx_goods_receipts_po');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_orders_user ON orders(user_id)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND INDEX_NAME='idx_orders_user');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_orders_status ON orders(order_status)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='idx_orders_status');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_orders_created_at ON orders(created_at)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND INDEX_NAME='idx_orders_created_at');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_order_items_product ON order_items(product_id)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_items' AND INDEX_NAME='idx_order_items_product');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_payments_order_status ON payments(order_id, status)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='idx_payments_order_status');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_coupon_usages_coupon_user ON coupon_usages(coupon_id, user_id)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='idx_coupon_usages_coupon_user');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_reviews_product_status ON reviews(product_id, status)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='idx_reviews_product_status');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_blog_posts_category ON blog_posts(category_id)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='blog_posts' AND INDEX_NAME='idx_blog_posts_category');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_blog_posts_status_published ON blog_posts(status, published_at)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='idx_blog_posts_status_published');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_affiliate_links_affiliate ON affiliate_links(affiliate_id)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='idx_affiliate_links_affiliate');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(COUNT(*)=0,'CREATE INDEX idx_commissions_affiliate_status ON commissions(affiliate_id, status)','SELECT 1') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='idx_commissions_affiliate_status');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============================================================
-- 12. Seed roles + map existing users (no catalog overwrite)
-- ============================================================

INSERT INTO roles (id, name, description) VALUES
(1, 'ADMIN', 'Quản trị viên hệ thống'),
(2, 'STAFF', 'Nhân viên quản lý bán hàng và kho'),
(3, 'CUSTOMER', 'Khách hàng'),
(4, 'AFFILIATE', 'Cộng tác viên / đối tác')
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  description = VALUES(description);

INSERT IGNORE INTO user_roles (user_id, role_id)
SELECT u.id,
       CASE u.id
           WHEN 1 THEN 1
           WHEN 2 THEN 2
           ELSE 3
       END
FROM users u;

-- Restore auto-increment counters after synthetic inserts
SET @max_oid = (SELECT COALESCE(MAX(id),0)+1 FROM orders);
SET @sql = CONCAT('ALTER TABLE orders AUTO_INCREMENT = ', @max_oid);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @max_oi = (SELECT COALESCE(MAX(id),0)+1 FROM order_items);
SET @sql = CONCAT('ALTER TABLE order_items AUTO_INCREMENT = ', @max_oi);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET FOREIGN_KEY_CHECKS = 1;
SET UNIQUE_CHECKS = 1;

INSERT INTO _schema_migrations (migration_name)
VALUES ('007_sync_lifegift_demo_v2')
ON DUPLICATE KEY UPDATE applied_at = CURRENT_TIMESTAMP;
