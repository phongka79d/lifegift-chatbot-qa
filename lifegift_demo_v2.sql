-- ============================================================
-- LIFEGIFT DATABASE - STANDARDIZED VERSION
-- Target: MySQL 8.0.16+
-- Charset: utf8mb4
-- ============================================================

DROP DATABASE IF EXISTS lifegift;
CREATE DATABASE lifegift
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE lifegift;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- 1. AUTHENTICATION & USERS
-- ============================================================

CREATE TABLE roles (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone VARCHAR(20) UNIQUE,
    email VARCHAR(150) UNIQUE,
    avatar VARCHAR(500),
    status ENUM('ACTIVE','INACTIVE','LOCKED','PENDING') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE user_roles (
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

CREATE TABLE addresses (
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

-- ============================================================
-- 2. PRODUCT CATALOG
-- ============================================================

CREATE TABLE categories (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    parent_id BIGINT UNSIGNED NULL,
    name VARCHAR(150) NOT NULL,
    slug VARCHAR(180) NOT NULL UNIQUE,
    description TEXT,
    image_url VARCHAR(500),
    status ENUM('ACTIVE','INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_categories_parent
        FOREIGN KEY (parent_id) REFERENCES categories(id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE brands (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    slug VARCHAR(180) NOT NULL UNIQUE,
    description TEXT,
    logo_url VARCHAR(500),
    status ENUM('ACTIVE','INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE products (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    category_id BIGINT UNSIGNED NOT NULL,
    brand_id BIGINT UNSIGNED NULL,
    sku VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(280) NOT NULL UNIQUE,
    description TEXT,
    short_description VARCHAR(500),

    price DECIMAL(15,2) NOT NULL DEFAULT 0,
    sale_price DECIMAL(15,2) NULL,

    unit VARCHAR(50) NOT NULL DEFAULT 'Sản phẩm',
    weight DECIMAL(10,2) NULL,
    origin VARCHAR(150),

    pricing_type ENUM('FIXED_PRICE','CONTACT_FOR_PRICE') NOT NULL DEFAULT 'FIXED_PRICE',
    stock_status ENUM('IN_STOCK','LOW_STOCK','OUT_OF_STOCK','PRE_ORDER') NOT NULL DEFAULT 'IN_STOCK',
    status ENUM('ACTIVE','INACTIVE','DRAFT') NOT NULL DEFAULT 'ACTIVE',
    is_featured BOOLEAN NOT NULL DEFAULT FALSE,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT chk_products_price CHECK (price >= 0),
    CONSTRAINT chk_products_sale_price CHECK (sale_price IS NULL OR sale_price >= 0),
    CONSTRAINT chk_products_weight CHECK (weight IS NULL OR weight >= 0),

    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id) REFERENCES categories(id),

    CONSTRAINT fk_products_brand
        FOREIGN KEY (brand_id) REFERENCES brands(id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE product_images (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT UNSIGNED NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_product_images_sort_order CHECK (sort_order >= 0),

    CONSTRAINT fk_product_images_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 3. CART
-- ============================================================

CREATE TABLE carts (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_carts_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE cart_items (
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

-- ============================================================
-- 4. WAREHOUSE / INVENTORY
-- ============================================================

CREATE TABLE warehouses (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    address VARCHAR(255),
    status ENUM('ACTIVE','INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE inventories (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    warehouse_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,

    quantity INT NOT NULL DEFAULT 0,
    reserved_quantity INT NOT NULL DEFAULT 0,
    available_quantity INT
        GENERATED ALWAYS AS (quantity - reserved_quantity) STORED,
    min_stock INT NOT NULL DEFAULT 0,

    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_inventory_warehouse_product (warehouse_id, product_id),

    CONSTRAINT chk_inventories_quantity CHECK (quantity >= 0),
    CONSTRAINT chk_inventories_reserved CHECK (reserved_quantity >= 0),
    CONSTRAINT chk_inventories_reserved_lte_quantity CHECK (reserved_quantity <= quantity),
    CONSTRAINT chk_inventories_min_stock CHECK (min_stock >= 0),

    CONSTRAINT fk_inventories_warehouse
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),

    CONSTRAINT fk_inventories_product
        FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB;

CREATE TABLE inventory_transactions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    inventory_id BIGINT UNSIGNED NOT NULL,

    transaction_type ENUM(
        'IMPORT',
        'SALE',
        'RETURN',
        'ADJUSTMENT',
        'TRANSFER_IN',
        'TRANSFER_OUT'
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

-- ============================================================
-- 5. SUPPLIER / PURCHASING
-- ============================================================

CREATE TABLE suppliers (
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

CREATE TABLE purchase_orders (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    purchase_code VARCHAR(80) NOT NULL UNIQUE,
    supplier_id BIGINT UNSIGNED NOT NULL,
    warehouse_id BIGINT UNSIGNED NOT NULL,

    total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,

    status ENUM(
        'DRAFT',
        'ORDERED',
        'PARTIAL_RECEIVED',
        'RECEIVED',
        'CANCELLED'
    ) NOT NULL DEFAULT 'DRAFT',

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

CREATE TABLE purchase_order_items (
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

CREATE TABLE goods_receipts (
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

-- Chi tiết hàng thực nhận của từng phiếu nhập.
-- purchase_order_item_id giúp truy ngược chính xác dòng đặt mua.
CREATE TABLE goods_receipt_items (
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

-- ============================================================
-- 6. ORDERS / PAYMENTS
-- ============================================================

CREATE TABLE orders (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_code VARCHAR(80) NOT NULL UNIQUE,
    user_id BIGINT UNSIGNED NOT NULL,

    receiver_name VARCHAR(150) NOT NULL,
    receiver_phone VARCHAR(20) NOT NULL,
    shipping_province VARCHAR(100) NOT NULL,
    shipping_district VARCHAR(100),
    shipping_ward VARCHAR(100),
    shipping_address VARCHAR(255) NOT NULL,

    subtotal DECIMAL(15,2) NOT NULL DEFAULT 0,
    shipping_fee DECIMAL(15,2) NOT NULL DEFAULT 0,
    discount_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,

    payment_method ENUM('COD','BANK_TRANSFER','VNPAY','MOMO') NOT NULL DEFAULT 'COD',

    -- Trạng thái tổng hợp của đơn. Bảng payments là nguồn dữ liệu giao dịch.
    payment_status ENUM('UNPAID','PENDING','PAID','FAILED','REFUNDED')
        NOT NULL DEFAULT 'UNPAID',

    order_status ENUM(
        'PENDING',
        'CONFIRMED',
        'PROCESSING',
        'SHIPPING',
        'DELIVERED',
        'COMPLETED',
        'CANCELLED',
        'RETURN_REQUESTED',
        'RETURNED'
    ) NOT NULL DEFAULT 'PENDING',

    note VARCHAR(500),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Dùng cho composite FK ở reviews để bảo đảm review thuộc đúng chủ đơn.
    UNIQUE KEY uk_orders_id_user (id, user_id),

    CONSTRAINT chk_orders_subtotal CHECK (subtotal >= 0),
    CONSTRAINT chk_orders_shipping_fee CHECK (shipping_fee >= 0),
    CONSTRAINT chk_orders_discount CHECK (discount_amount >= 0),
    CONSTRAINT chk_orders_total CHECK (total_amount >= 0),

    CONSTRAINT fk_orders_user
        FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE order_items (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,

    -- Snapshot tại thời điểm mua.
    product_name VARCHAR(255) NOT NULL,
    sku VARCHAR(80) NOT NULL,
    unit_price DECIMAL(15,2) NOT NULL,
    quantity INT NOT NULL,
    subtotal DECIMAL(15,2) NOT NULL,

    UNIQUE KEY uk_order_product (order_id, product_id),

    CONSTRAINT chk_order_items_unit_price CHECK (unit_price >= 0),
    CONSTRAINT chk_order_items_quantity CHECK (quantity > 0),
    CONSTRAINT chk_order_items_subtotal CHECK (subtotal >= 0),

    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id) REFERENCES orders(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB;

CREATE TABLE order_status_history (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL,

    status ENUM(
        'PENDING',
        'CONFIRMED',
        'PROCESSING',
        'SHIPPING',
        'DELIVERED',
        'COMPLETED',
        'CANCELLED',
        'RETURN_REQUESTED',
        'RETURNED'
    ) NOT NULL,

    note VARCHAR(500),
    changed_by BIGINT UNSIGNED NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_order_status_history_order
        FOREIGN KEY (order_id) REFERENCES orders(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_order_status_history_user
        FOREIGN KEY (changed_by) REFERENCES users(id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE payments (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL,
    payment_method ENUM('COD','BANK_TRANSFER','VNPAY','MOMO') NOT NULL,
    transaction_code VARCHAR(150),
    amount DECIMAL(15,2) NOT NULL,

    status ENUM('PENDING','SUCCESS','FAILED','REFUNDED')
        NOT NULL DEFAULT 'PENDING',

    paid_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_payments_amount CHECK (amount >= 0),

    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id) REFERENCES orders(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 7. COUPON / PROMOTION
-- ============================================================

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
        discount_type <> 'PERCENTAGE'
        OR discount_value <= 100
    )
) ENGINE=InnoDB;

CREATE TABLE coupon_usages (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    coupon_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    order_id BIGINT UNSIGNED NOT NULL,
    discount_amount DECIMAL(15,2) NOT NULL,
    used_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Scope hiện tại: mỗi đơn chỉ áp dụng một coupon.
    UNIQUE KEY uk_coupon_usage_order (order_id),

    CONSTRAINT chk_coupon_usages_discount CHECK (discount_amount >= 0),

    CONSTRAINT fk_coupon_usages_coupon
        FOREIGN KEY (coupon_id) REFERENCES coupons(id),

    CONSTRAINT fk_coupon_usages_user
        FOREIGN KEY (user_id) REFERENCES users(id),

    CONSTRAINT fk_coupon_usages_order
        FOREIGN KEY (order_id) REFERENCES orders(id)
) ENGINE=InnoDB;

-- ============================================================
-- 8. REVIEW
-- ============================================================

CREATE TABLE reviews (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    user_id BIGINT UNSIGNED NOT NULL,
    order_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,

    rating TINYINT NOT NULL,
    title VARCHAR(200),
    content TEXT,

    status ENUM('PENDING','APPROVED','HIDDEN') NOT NULL DEFAULT 'PENDING',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Một sản phẩm trong một đơn chỉ review một lần.
    UNIQUE KEY uk_review_order_product (order_id, product_id),

    CONSTRAINT chk_reviews_rating CHECK (rating BETWEEN 1 AND 5),

    -- Bảo đảm user chính là chủ của order.
    CONSTRAINT fk_reviews_order_user
        FOREIGN KEY (order_id, user_id)
        REFERENCES orders(id, user_id),

    -- Bảo đảm product thực sự nằm trong order.
    CONSTRAINT fk_reviews_order_product
        FOREIGN KEY (order_id, product_id)
        REFERENCES order_items(order_id, product_id),

    CONSTRAINT fk_reviews_product
        FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB;

-- ============================================================
-- 9. BLOG / CONTENT
-- ============================================================

CREATE TABLE blog_categories (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    slug VARCHAR(180) NOT NULL UNIQUE,
    description VARCHAR(500),
    status ENUM('ACTIVE','INACTIVE') NOT NULL DEFAULT 'ACTIVE'
) ENGINE=InnoDB;

CREATE TABLE blog_posts (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    category_id BIGINT UNSIGNED NOT NULL,
    author_id BIGINT UNSIGNED NOT NULL,

    title VARCHAR(255) NOT NULL,
    slug VARCHAR(300) NOT NULL UNIQUE,
    thumbnail VARCHAR(500),
    summary VARCHAR(1000),
    content LONGTEXT,

    status ENUM('DRAFT','PUBLISHED','HIDDEN') NOT NULL DEFAULT 'DRAFT',
    published_at DATETIME,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_blog_posts_category
        FOREIGN KEY (category_id) REFERENCES blog_categories(id),

    CONSTRAINT fk_blog_posts_author
        FOREIGN KEY (author_id) REFERENCES users(id)
) ENGINE=InnoDB;

-- ============================================================
-- 10. AFFILIATE / CTV
-- ============================================================

CREATE TABLE affiliates (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL UNIQUE,
    affiliate_code VARCHAR(80) NOT NULL UNIQUE,

    commission_rate DECIMAL(5,2) NOT NULL DEFAULT 5.00,

    status ENUM('PENDING','ACTIVE','INACTIVE','REJECTED')
        NOT NULL DEFAULT 'PENDING',

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

CREATE TABLE affiliate_links (
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

CREATE TABLE commissions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    affiliate_id BIGINT UNSIGNED NOT NULL,
    order_id BIGINT UNSIGNED NOT NULL,

    order_amount DECIMAL(15,2) NOT NULL,
    commission_rate DECIMAL(5,2) NOT NULL,
    commission_amount DECIMAL(15,2) NOT NULL,

    status ENUM('PENDING','APPROVED','PAID','CANCELLED')
        NOT NULL DEFAULT 'PENDING',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    paid_at DATETIME,

    -- Scope hiện tại: mỗi order chỉ ghi nhận một affiliate.
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
-- INDEXES
-- ============================================================

CREATE INDEX idx_addresses_user ON addresses(user_id);

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_brand ON products(brand_id);
CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_products_featured ON products(is_featured);

CREATE INDEX idx_cart_items_product ON cart_items(product_id);

CREATE INDEX idx_inventory_product ON inventories(product_id);
CREATE INDEX idx_inventory_transactions_inventory_created
    ON inventory_transactions(inventory_id, created_at);

CREATE INDEX idx_purchase_orders_supplier ON purchase_orders(supplier_id);
CREATE INDEX idx_purchase_orders_status ON purchase_orders(status);
CREATE INDEX idx_goods_receipts_po ON goods_receipts(purchase_order_id);

CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(order_status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_order_items_product ON order_items(product_id);

CREATE INDEX idx_payments_order_status ON payments(order_id, status);

CREATE INDEX idx_coupon_usages_coupon_user ON coupon_usages(coupon_id, user_id);

CREATE INDEX idx_reviews_product_status ON reviews(product_id, status);

CREATE INDEX idx_blog_posts_category ON blog_posts(category_id);
CREATE INDEX idx_blog_posts_status_published ON blog_posts(status, published_at);

CREATE INDEX idx_affiliate_links_affiliate ON affiliate_links(affiliate_id);
CREATE INDEX idx_commissions_affiliate_status ON commissions(affiliate_id, status);

-- ============================================================
-- DEMO DATA
-- ============================================================

-- ROLES
INSERT INTO roles (id, name, description) VALUES
(1, 'ADMIN', 'Quản trị viên hệ thống'),
(2, 'STAFF', 'Nhân viên quản lý bán hàng và kho'),
(3, 'CUSTOMER', 'Khách hàng'),
(4, 'AFFILIATE', 'Cộng tác viên / đối tác');

-- USERS
-- Demo password hash: BCrypt demo only.
INSERT INTO users
(id, username, password, full_name, phone, email, avatar, status)
VALUES
(1, 'admin', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'Nguyễn Quản Trị', '0901000001', 'admin@lifegift.vn', NULL, 'ACTIVE'),
(2, 'staff01', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'Trần Thị Nhân Viên', '0901000002', 'staff@lifegift.vn', NULL, 'ACTIVE'),
(3, 'nguyenvana', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'Nguyễn Văn An', '0901000003', 'an@gmail.com', NULL, 'ACTIVE'),
(4, 'tranthib', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'Trần Thị Bình', '0901000004', 'binh@gmail.com', NULL, 'ACTIVE'),
(5, 'leminhc', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'Lê Minh Cường', '0901000005', 'cuong@gmail.com', NULL, 'ACTIVE');

INSERT INTO user_roles (user_id, role_id) VALUES
(1,1),
(2,2),
(3,3),
(4,3),
(5,3),
(5,4);

-- ADDRESSES
INSERT INTO addresses
(id, user_id, receiver_name, receiver_phone, province, district, ward, address_detail, is_default)
VALUES
(1,3,'Nguyễn Văn An','0901000003','Hà Nội','Hoàng Mai','Định Công','12 phố Định Công',TRUE),
(2,3,'Nguyễn Văn An','0901000003','Hà Nội','Hai Bà Trưng','Bạch Mai','25 phố Bạch Mai',FALSE),
(3,4,'Trần Thị Bình','0901000004','Hà Nội','Cầu Giấy','Dịch Vọng','18 Trần Thái Tông',TRUE),
(4,5,'Lê Minh Cường','0901000005','Hà Nội','Thanh Xuân','Khương Đình','45 Nguyễn Trãi',TRUE);

-- CATEGORIES
INSERT INTO categories
(id, parent_id, name, slug, description, image_url, status)
VALUES
(1,NULL,'Nông sản','nong-san','Các sản phẩm nông sản Việt Nam',NULL,'ACTIVE'),
(2,NULL,'Đặc sản vùng miền','dac-san-vung-mien','Đặc sản nổi tiếng từ nhiều vùng miền',NULL,'ACTIVE'),
(3,NULL,'Quà tặng','qua-tang','Các bộ quà tặng phù hợp cá nhân và doanh nghiệp',NULL,'ACTIVE'),
(4,1,'Cà phê','ca-phe','Cà phê Việt Nam',NULL,'ACTIVE'),
(5,1,'Trà','tra','Các loại trà Việt Nam',NULL,'ACTIVE'),
(6,1,'Hạt dinh dưỡng','hat-dinh-duong','Các loại hạt và sản phẩm dinh dưỡng',NULL,'ACTIVE'),
(7,2,'Đặc sản Tây Bắc','dac-san-tay-bac','Đặc sản khu vực Tây Bắc',NULL,'ACTIVE'),
(8,3,'Quà doanh nghiệp','qua-doanh-nghiep','Quà tặng dành cho doanh nghiệp',NULL,'ACTIVE');

-- BRANDS
INSERT INTO brands
(id, name, slug, description, logo_url, status)
VALUES
(1,'LifeGift','lifegift','Thương hiệu quà tặng và nông sản Việt Nam',NULL,'ACTIVE'),
(2,'Buôn Ma Thuột Coffee','buon-ma-thuot-coffee','Cà phê đặc sản Buôn Ma Thuột',NULL,'ACTIVE'),
(3,'Tây Bắc Farm','tay-bac-farm','Nông sản và đặc sản vùng Tây Bắc',NULL,'ACTIVE'),
(4,'Green Việt','green-viet','Sản phẩm nông nghiệp và dinh dưỡng',NULL,'ACTIVE');

-- PRODUCTS
INSERT INTO products
(id, category_id, brand_id, sku, name, slug, description, short_description,
 price, sale_price, unit, weight, origin, pricing_type, stock_status, status, is_featured)
VALUES
(1,4,2,'CF-001','Cà phê Robusta nguyên hạt 500g','ca-phe-robusta-nguyen-hat-500g',
 'Cà phê Robusta rang mộc, hương thơm mạnh, vị đậm đà, phù hợp pha phin và máy.',
 'Cà phê Robusta rang mộc 500g.',
 185000,165000,'Gói',500,'Buôn Ma Thuột','FIXED_PRICE','IN_STOCK','ACTIVE',TRUE),

(2,4,2,'CF-002','Cà phê Arabica Cầu Đất 500g','ca-phe-arabica-cau-dat-500g',
 'Cà phê Arabica trồng tại vùng Cầu Đất, hương thơm dịu và hậu vị cân bằng.',
 'Arabica Cầu Đất 500g.',
 260000,239000,'Gói',500,'Cầu Đất - Đà Lạt','FIXED_PRICE','IN_STOCK','ACTIVE',TRUE),

(3,5,1,'TR-001','Trà Shan Tuyết cổ thụ 200g','tra-shan-tuyet-co-thu-200g',
 'Trà Shan Tuyết được thu hái từ những cây trà cổ thụ vùng núi phía Bắc.',
 'Trà Shan Tuyết cổ thụ 200g.',
 320000,299000,'Hộp',200,'Hà Giang','FIXED_PRICE','IN_STOCK','ACTIVE',TRUE),

(4,5,3,'TR-002','Trà Ô Long Tây Bắc 200g','tra-o-long-tay-bac-200g',
 'Trà Ô Long thơm nhẹ, hậu vị thanh, đóng hộp sang trọng.',
 'Trà Ô Long 200g.',
 280000,NULL,'Hộp',200,'Sơn La','FIXED_PRICE','IN_STOCK','ACTIVE',FALSE),

(5,6,4,'HN-001','Hạt điều rang muối 500g','hat-dieu-rang-muoi-500g',
 'Hạt điều rang muối giòn thơm, phù hợp dùng hằng ngày và làm quà.',
 'Hạt điều rang muối 500g.',
 210000,189000,'Hộp',500,'Bình Phước','FIXED_PRICE','IN_STOCK','ACTIVE',TRUE),

(6,6,4,'HN-002','Hạt mắc ca 500g','hat-mac-ca-500g',
 'Mắc ca giàu dinh dưỡng, đóng gói tiện lợi.',
 'Hạt mắc ca 500g.',
 290000,269000,'Hộp',500,'Lâm Đồng','FIXED_PRICE','IN_STOCK','ACTIVE',FALSE),

(7,7,3,'DS-001','Mật ong hoa rừng Tây Bắc 500ml','mat-ong-hoa-rung-tay-bac-500ml',
 'Mật ong hoa rừng nguyên chất, vị thơm tự nhiên.',
 'Mật ong hoa rừng 500ml.',
 350000,319000,'Chai',500,'Sơn La','FIXED_PRICE','IN_STOCK','ACTIVE',TRUE),

(8,7,3,'DS-002','Măng khô Tây Bắc 500g','mang-kho-tay-bac-500g',
 'Măng khô chọn lọc từ vùng núi Tây Bắc.',
 'Măng khô 500g.',
 240000,NULL,'Túi',500,'Điện Biên','FIXED_PRICE','LOW_STOCK','ACTIVE',FALSE),

(9,8,1,'QT-001','Hộp quà Tết Nông Sản Việt','hop-qua-tet-nong-san-viet',
 'Bộ quà tặng gồm cà phê, trà, hạt điều và mật ong, phù hợp làm quà doanh nghiệp.',
 'Hộp quà nông sản Việt cao cấp.',
 890000,799000,'Hộp',2500,'Việt Nam','FIXED_PRICE','IN_STOCK','ACTIVE',TRUE),

(10,8,1,'QT-002','Quà doanh nghiệp Premium','qua-doanh-nghiep-premium',
 'Bộ quà doanh nghiệp thiết kế theo yêu cầu. Liên hệ để nhận báo giá.',
 'Bộ quà doanh nghiệp tùy chỉnh.',
 0,NULL,'Bộ',5000,'Việt Nam','CONTACT_FOR_PRICE','IN_STOCK','ACTIVE',TRUE);

-- PRODUCT IMAGES
INSERT INTO product_images (product_id,image_url,is_primary,sort_order) VALUES
(1,'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085',TRUE,1),
(1,'https://images.unsplash.com/photo-1512568400610-62da28bc8a13',FALSE,2),
(2,'https://images.unsplash.com/photo-1447933601403-0c6688de566e',TRUE,1),
(3,'https://images.unsplash.com/photo-1594631252845-29fc4cc8cde9',TRUE,1),
(4,'https://images.unsplash.com/photo-1544787219-7f47ccb76574',TRUE,1),
(5,'https://images.unsplash.com/photo-1508061253366-f7da158b6d46',TRUE,1),
(6,'https://images.unsplash.com/photo-1599599810769-bcde5a160d32',TRUE,1),
(7,'https://images.unsplash.com/photo-1471943311424-646960669fbc',TRUE,1),
(8,'https://images.unsplash.com/photo-1600189020115-e6a9f5e7b1c1',TRUE,1),
(9,'https://images.unsplash.com/photo-1549465220-1a8b9238cd48',TRUE,1),
(10,'https://images.unsplash.com/photo-1607344645866-009c320b63e0',TRUE,1);

-- CARTS
INSERT INTO carts (id,user_id) VALUES
(1,3),(2,4),(3,5);

INSERT INTO cart_items (cart_id,product_id,quantity) VALUES
(1,1,2),
(1,5,1),
(2,3,1),
(2,7,2),
(3,9,1);

-- WAREHOUSES
INSERT INTO warehouses (id,code,name,address,status) VALUES
(1,'WH-HN','Kho Hà Nội','Khu công nghiệp Thanh Trì, Hà Nội','ACTIVE'),
(2,'WH-HCM','Kho Hồ Chí Minh','Quận 12, TP. Hồ Chí Minh','ACTIVE');

-- INVENTORY
-- available_quantity là generated column nên không INSERT trực tiếp.
INSERT INTO inventories
(id,warehouse_id,product_id,quantity,reserved_quantity,min_stock)
VALUES
(1,1,1,120,5,20),
(2,1,2,80,0,15),
(3,1,3,60,2,10),
(4,1,4,45,0,10),
(5,1,5,150,3,20),
(6,1,6,90,0,15),
(7,1,7,70,0,10),
(8,1,8,12,2,15),
(9,1,9,35,1,5),
(10,1,10,20,0,5),
(11,2,1,60,0,15),
(12,2,5,80,0,15),
(13,2,9,20,0,5);

-- SUPPLIERS
INSERT INTO suppliers
(id,code,name,phone,email,address,tax_code,status)
VALUES
(1,'SUP-CF','HTX Cà phê Buôn Ma Thuột','0902000001','coffee@supplier.vn','Buôn Ma Thuột, Đắk Lắk','600000001','ACTIVE'),
(2,'SUP-TB','Tây Bắc Nông Sản','0902000002','taybac@supplier.vn','Sơn La','550000002','ACTIVE'),
(3,'SUP-HN','Nông sản Green Việt','0902000003','green@supplier.vn','Hà Nội','010000003','ACTIVE');

-- PURCHASE ORDERS
INSERT INTO purchase_orders
(id,purchase_code,supplier_id,warehouse_id,total_amount,status,ordered_at,expected_at)
VALUES
(1,'PO-202608-0001',1,1,18000000,'RECEIVED','2026-08-01 09:00:00','2026-08-03 09:00:00'),
(2,'PO-202608-0002',2,1,12500000,'PARTIAL_RECEIVED','2026-08-05 10:00:00','2026-08-15 09:00:00');

INSERT INTO purchase_order_items
(id,purchase_order_id,product_id,quantity,unit_cost,subtotal)
VALUES
(1,1,1,100,120000,12000000),
(2,1,2,30,180000,5400000),
(3,1,5,10,60000,600000),
(4,2,3,30,220000,6600000),
(5,2,7,20,295000,5900000);

-- GOODS RECEIPTS
INSERT INTO goods_receipts
(id,receipt_code,purchase_order_id,warehouse_id,received_by,total_amount,note,received_at)
VALUES
(1,'GR-202608-0001',1,1,2,18000000,'Đã nhận đủ hàng PO-202608-0001','2026-08-03 15:30:00'),
(2,'GR-202608-0002',2,1,2,6600000,'Nhập đợt 1 trà Shan Tuyết','2026-08-10 14:00:00');

INSERT INTO goods_receipt_items
(id,goods_receipt_id,purchase_order_item_id,received_quantity,unit_cost,subtotal)
VALUES
(1,1,1,100,120000,12000000),
(2,1,2,30,180000,5400000),
(3,1,3,10,60000,600000),
(4,2,4,30,220000,6600000);

-- INVENTORY TRANSACTIONS - IMPORT
INSERT INTO inventory_transactions
(inventory_id,transaction_type,quantity,reference_type,reference_id,note,created_by,created_at)
VALUES
(1,'IMPORT',100,'GOODS_RECEIPT',1,'Nhập 100 gói Robusta',2,'2026-08-03 15:30:00'),
(2,'IMPORT',30,'GOODS_RECEIPT',1,'Nhập 30 gói Arabica',2,'2026-08-03 15:30:00'),
(5,'IMPORT',10,'GOODS_RECEIPT',1,'Nhập 10 hộp hạt điều',2,'2026-08-03 15:30:00'),
(3,'IMPORT',30,'GOODS_RECEIPT',2,'Nhập 30 hộp Shan Tuyết',2,'2026-08-10 14:00:00');

-- ORDERS
INSERT INTO orders
(id,order_code,user_id,receiver_name,receiver_phone,shipping_province,shipping_district,shipping_ward,shipping_address,
subtotal,shipping_fee,discount_amount,total_amount,payment_method,payment_status,order_status,note,created_at)
VALUES
(1,'ORD-20260812-0001',3,'Nguyễn Văn An','0901000003','Hà Nội','Hoàng Mai','Định Công','12 phố Định Công',
519000,30000,0,549000,'COD','UNPAID','PROCESSING','Giao giờ hành chính','2026-08-12 08:30:00'),

(2,'ORD-20260812-0002',4,'Trần Thị Bình','0901000004','Hà Nội','Cầu Giấy','Dịch Vọng','18 Trần Thái Tông',
618000,30000,50000,598000,'BANK_TRANSFER','PAID','SHIPPING','Đã thanh toán chuyển khoản','2026-08-11 14:20:00'),

(3,'ORD-20260810-0003',5,'Lê Minh Cường','0901000005','Hà Nội','Thanh Xuân','Khương Đình','45 Nguyễn Trãi',
799000,0,0,799000,'VNPAY','PAID','COMPLETED','Khách doanh nghiệp','2026-08-10 10:15:00'),

(4,'ORD-20260809-0004',3,'Nguyễn Văn An','0901000003','Hà Nội','Hai Bà Trưng','Bạch Mai','25 phố Bạch Mai',
485000,30000,0,515000,'COD','UNPAID','DELIVERED','Giao thành công','2026-08-09 09:00:00');

-- ORDER ITEMS
INSERT INTO order_items
(id,order_id,product_id,product_name,sku,unit_price,quantity,subtotal)
VALUES
(1,1,1,'Cà phê Robusta nguyên hạt 500g','CF-001',165000,2,330000),
(2,1,5,'Hạt điều rang muối 500g','HN-001',189000,1,189000),

(3,2,3,'Trà Shan Tuyết cổ thụ 200g','TR-001',299000,1,299000),
(4,2,7,'Mật ong hoa rừng Tây Bắc 500ml','DS-001',319000,1,319000),

(5,3,9,'Hộp quà Tết Nông Sản Việt','QT-001',799000,1,799000),

(6,4,2,'Cà phê Arabica Cầu Đất 500g','CF-002',239000,1,239000),
(7,4,3,'Trà Shan Tuyết cổ thụ 200g','TR-001',246000,1,246000);

-- INVENTORY TRANSACTIONS - SALE
-- Đã bổ sung đầy đủ theo toàn bộ order_items demo.
INSERT INTO inventory_transactions
(inventory_id,transaction_type,quantity,reference_type,reference_id,note,created_by,created_at)
VALUES
(1,'SALE',2,'ORDER',1,'Xuất bán đơn ORD-20260812-0001',2,'2026-08-12 09:00:00'),
(5,'SALE',1,'ORDER',1,'Xuất bán đơn ORD-20260812-0001',2,'2026-08-12 09:00:00'),

(3,'SALE',1,'ORDER',2,'Xuất bán đơn ORD-20260812-0002',2,'2026-08-12 08:00:00'),
(7,'SALE',1,'ORDER',2,'Xuất bán đơn ORD-20260812-0002',2,'2026-08-12 08:00:00'),

(9,'SALE',1,'ORDER',3,'Xuất bán đơn ORD-20260810-0003',2,'2026-08-10 15:00:00'),

(2,'SALE',1,'ORDER',4,'Xuất bán đơn ORD-20260809-0004',2,'2026-08-09 13:00:00'),
(3,'SALE',1,'ORDER',4,'Xuất bán đơn ORD-20260809-0004',2,'2026-08-09 13:00:00');

-- ORDER STATUS HISTORY
INSERT INTO order_status_history
(order_id,status,note,changed_by,created_at)
VALUES
(1,'PENDING','Khách tạo đơn',3,'2026-08-12 08:30:00'),
(1,'CONFIRMED','Nhân viên xác nhận đơn',2,'2026-08-12 08:40:00'),
(1,'PROCESSING','Đang chuẩn bị hàng',2,'2026-08-12 09:00:00'),

(2,'PENDING','Khách tạo đơn',4,'2026-08-11 14:20:00'),
(2,'CONFIRMED','Đã xác nhận thanh toán',2,'2026-08-11 14:30:00'),
(2,'PROCESSING','Đang đóng gói',2,'2026-08-11 15:00:00'),
(2,'SHIPPING','Đã bàn giao đơn vị vận chuyển',2,'2026-08-12 08:00:00'),

(3,'PENDING','Khách tạo đơn',5,'2026-08-10 10:15:00'),
(3,'CONFIRMED','Thanh toán thành công',2,'2026-08-10 10:20:00'),
(3,'PROCESSING','Đang chuẩn bị',2,'2026-08-10 11:00:00'),
(3,'SHIPPING','Đã giao vận chuyển',2,'2026-08-10 15:00:00'),
(3,'DELIVERED','Đã giao hàng',2,'2026-08-11 16:00:00'),
(3,'COMPLETED','Đơn hoàn tất',2,'2026-08-11 20:00:00'),

(4,'PENDING','Khách tạo đơn',3,'2026-08-09 09:00:00'),
(4,'CONFIRMED','Đã xác nhận',2,'2026-08-09 09:10:00'),
(4,'SHIPPING','Đã giao vận chuyển',2,'2026-08-09 13:00:00'),
(4,'DELIVERED','Đã giao hàng',2,'2026-08-10 17:00:00');

-- PAYMENTS
INSERT INTO payments
(id,order_id,payment_method,transaction_code,amount,status,paid_at)
VALUES
(1,1,'COD',NULL,549000,'PENDING',NULL),
(2,2,'BANK_TRANSFER','BANK-20260811-0002',598000,'SUCCESS','2026-08-11 14:25:00'),
(3,3,'VNPAY','VNPAY-20260810-0003',799000,'SUCCESS','2026-08-10 10:18:00'),
(4,4,'COD',NULL,515000,'PENDING',NULL);

-- COUPONS
INSERT INTO coupons
(id,code,name,discount_type,discount_value,min_order_value,max_discount,
 usage_limit,usage_limit_per_user,used_count,start_at,end_at,status)
VALUES
(1,'LIFEGIFT10','Giảm 10% đơn hàng','PERCENTAGE',10,300000,100000,1000,1,0,
 '2026-08-01 00:00:00','2026-08-31 23:59:59','ACTIVE'),

(2,'WELCOME50','Khách hàng mới giảm 50K','FIXED_AMOUNT',50000,300000,50000,500,1,1,
 '2026-08-01 00:00:00','2026-09-30 23:59:59','ACTIVE'),

(3,'TET100','Ưu đãi 100K dịp Tết','FIXED_AMOUNT',100000,700000,100000,100,1,0,
 '2026-08-01 00:00:00','2027-02-28 23:59:59','ACTIVE');

INSERT INTO coupon_usages
(id,coupon_id,user_id,order_id,discount_amount,used_at)
VALUES
(1,2,4,2,50000,'2026-08-11 14:20:00');

-- REVIEWS
-- Chỉ demo review cho đơn đã DELIVERED/COMPLETED.
INSERT INTO reviews
(id,user_id,order_id,product_id,rating,title,content,status)
VALUES
(1,5,3,9,5,'Hộp quà rất đẹp','Đóng gói đẹp, phù hợp làm quà doanh nghiệp.','APPROVED'),
(2,3,4,2,5,'Arabica chất lượng','Vị cân bằng, phù hợp uống buổi sáng.','APPROVED'),
(3,3,4,3,4,'Trà ngon','Trà thơm, đóng gói khá đẹp.','APPROVED');

-- BLOG CATEGORIES
INSERT INTO blog_categories
(id,name,slug,description,status)
VALUES
(1,'Kiến thức nông sản','kien-thuc-nong-san','Thông tin về nông sản Việt Nam','ACTIVE'),
(2,'Câu chuyện vùng miền','cau-chuyen-vung-mien','Câu chuyện về vùng trồng và người nông dân','ACTIVE'),
(3,'Quà tặng doanh nghiệp','qua-tang-doanh-nghiep','Ý tưởng và kinh nghiệm chọn quà doanh nghiệp','ACTIVE');

-- BLOG POSTS
INSERT INTO blog_posts
(id,category_id,author_id,title,slug,thumbnail,summary,content,status,published_at)
VALUES
(1,1,1,'Cách chọn cà phê nguyên chất','cach-chon-ca-phe-nguyen-chat',NULL,
 'Một số tiêu chí giúp người tiêu dùng lựa chọn cà phê chất lượng.',
 'Cà phê nguyên chất cần có nguồn gốc rõ ràng, quy trình rang phù hợp và hương vị tự nhiên.',
 'PUBLISHED','2026-08-05 08:00:00'),

(2,2,1,'Hành trình của hạt cà phê Buôn Ma Thuột','hanh-trinh-cua-hat-ca-phe-buon-ma-thuot',NULL,
 'Tìm hiểu vùng đất tạo nên những hạt cà phê nổi tiếng của Việt Nam.',
 'Buôn Ma Thuột là một trong những vùng cà phê nổi tiếng nhất Việt Nam.',
 'PUBLISHED','2026-08-07 08:00:00'),

(3,3,2,'Gợi ý quà tặng doanh nghiệp bằng nông sản Việt',
 'goi-y-qua-tang-doanh-nghiep-bang-nong-san-viet',NULL,
 'Nông sản Việt có thể trở thành những bộ quà tặng ý nghĩa cho đối tác.',
 'Một bộ quà tặng được thiết kế tốt vừa thể hiện văn hóa Việt Nam vừa tạo dấu ấn với đối tác.',
 'PUBLISHED','2026-08-10 08:00:00');

-- AFFILIATES
INSERT INTO affiliates
(id,user_id,affiliate_code,commission_rate,status,approved_by,approved_at)
VALUES
(1,5,'CTV-CUONG-001',7.50,'ACTIVE',1,'2026-08-01 09:00:00');

-- AFFILIATE LINKS
INSERT INTO affiliate_links
(id,affiliate_id,product_id,code,click_count,status)
VALUES
(1,1,1,'CTV-CUONG-CF001',128,'ACTIVE'),
(2,1,9,'CTV-CUONG-QT001',75,'ACTIVE');

-- COMMISSIONS
INSERT INTO commissions
(id,affiliate_id,order_id,order_amount,commission_rate,commission_amount,status,created_at,paid_at)
VALUES
(1,1,3,799000,7.50,59925,'APPROVED','2026-08-11 20:00:00',NULL);

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- DEMO CHECK QUERIES
-- ============================================================

-- Sản phẩm + danh mục + thương hiệu
-- SELECT
--     p.id,
--     p.name,
--     p.sku,
--     c.name AS category,
--     b.name AS brand,
--     p.price,
--     p.sale_price
-- FROM products p
-- JOIN categories c ON c.id = p.category_id
-- LEFT JOIN brands b ON b.id = p.brand_id;

-- Đơn hàng + khách hàng
-- SELECT
--     o.order_code,
--     u.full_name,
--     o.total_amount,
--     o.payment_status,
--     o.order_status
-- FROM orders o
-- JOIN users u ON u.id = o.user_id
-- ORDER BY o.created_at DESC;

-- Tồn kho
-- SELECT
--     w.name AS warehouse,
--     p.name AS product,
--     i.quantity,
--     i.reserved_quantity,
--     i.available_quantity,
--     i.min_stock
-- FROM inventories i
-- JOIN warehouses w ON w.id = i.warehouse_id
-- JOIN products p ON p.id = i.product_id;

-- Chi tiết phiếu nhập
-- SELECT
--     gr.receipt_code,
--     po.purchase_code,
--     p.name AS product,
--     gri.received_quantity,
--     gri.unit_cost,
--     gri.subtotal
-- FROM goods_receipt_items gri
-- JOIN goods_receipts gr ON gr.id = gri.goods_receipt_id
-- JOIN purchase_order_items poi ON poi.id = gri.purchase_order_item_id
-- JOIN purchase_orders po ON po.id = poi.purchase_order_id
-- JOIN products p ON p.id = poi.product_id;

-- Doanh thu đơn hoàn tất
-- SELECT COALESCE(SUM(total_amount), 0) AS revenue
-- FROM orders
-- WHERE order_status = 'COMPLETED';

-- Kiểm tra coupon usage
-- SELECT
--     cu.id,
--     c.code,
--     u.full_name,
--     o.order_code,
--     cu.discount_amount
-- FROM coupon_usages cu
-- JOIN coupons c ON c.id = cu.coupon_id
-- JOIN users u ON u.id = cu.user_id
-- JOIN orders o ON o.id = cu.order_id;

-- Review hợp lệ theo order + product
-- SELECT
--     r.id,
--     u.full_name,
--     o.order_code,
--     p.name AS product,
--     r.rating,
--     r.title
-- FROM reviews r
-- JOIN users u ON u.id = r.user_id
-- JOIN orders o ON o.id = r.order_id
-- JOIN products p ON p.id = r.product_id
-- WHERE r.status = 'APPROVED';

-- ============================================================
-- END
-- ============================================================
