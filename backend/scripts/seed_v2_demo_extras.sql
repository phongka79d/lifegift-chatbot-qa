-- Seed demo rows for new v2 tables (coupons/vouchers, addresses, carts, payments, suppliers).
-- Safe for existing lifegift_db data: INSERT IGNORE / ON DUPLICATE KEY UPDATE only.
-- Does not touch catalog, reviews, or chat history.

USE lifegift_db;

SET NAMES utf8mb4;

-- ------------------------------------------------------------
-- Vouchers / Coupons
-- ------------------------------------------------------------
INSERT INTO coupons
(id, code, name, discount_type, discount_value, min_order_value, max_discount,
 usage_limit, usage_limit_per_user, used_count, start_at, end_at, status)
VALUES
(1, 'LIFEGIFT10', 'Giảm 10% đơn hàng', 'PERCENTAGE', 10, 300000, 100000,
 1000, 1, 0, '2026-08-01 00:00:00', '2026-12-31 23:59:59', 'ACTIVE'),

(2, 'WELCOME50', 'Khách hàng mới giảm 50K', 'FIXED_AMOUNT', 50000, 300000, 50000,
 500, 1, 1, '2026-08-01 00:00:00', '2026-12-31 23:59:59', 'ACTIVE'),

(3, 'TET100', 'Ưu đãi 100K dịp Tết', 'FIXED_AMOUNT', 100000, 700000, 100000,
 100, 1, 0, '2026-08-01 00:00:00', '2027-02-28 23:59:59', 'ACTIVE'),

(4, 'FREESHIP', 'Miễn phí vận chuyển (voucher 30K)', 'FIXED_AMOUNT', 30000, 200000, 30000,
 2000, 3, 0, '2026-08-01 00:00:00', '2026-12-31 23:59:59', 'ACTIVE')
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  discount_type = VALUES(discount_type),
  discount_value = VALUES(discount_value),
  min_order_value = VALUES(min_order_value),
  max_discount = VALUES(max_discount),
  usage_limit = VALUES(usage_limit),
  usage_limit_per_user = VALUES(usage_limit_per_user),
  used_count = VALUES(used_count),
  start_at = VALUES(start_at),
  end_at = VALUES(end_at),
  status = VALUES(status);

-- One usage on delivered order #2 (user 2)
INSERT INTO coupon_usages
(id, coupon_id, user_id, order_id, discount_amount, used_at)
VALUES
(1, 2, 2, 2, 50000, '2026-08-11 14:20:00')
ON DUPLICATE KEY UPDATE
  discount_amount = VALUES(discount_amount),
  used_at = VALUES(used_at);

-- ------------------------------------------------------------
-- Addresses
-- ------------------------------------------------------------
INSERT INTO addresses
(id, user_id, receiver_name, receiver_phone, province, district, ward, address_detail, is_default)
VALUES
(1, 3, 'Nguyễn Văn An', '0901000003', 'Hà Nội', 'Hoàng Mai', 'Định Công', '12 phố Định Công', TRUE),
(2, 3, 'Nguyễn Văn An', '0901000003', 'Hà Nội', 'Hai Bà Trưng', 'Bạch Mai', '25 phố Bạch Mai', FALSE),
(3, 4, 'Trần Thị Bình', '0901000004', 'Hà Nội', 'Cầu Giấy', 'Dịch Vọng', '18 Trần Thái Tông', TRUE),
(4, 5, 'Lê Minh Cường', '0901000005', 'Hà Nội', 'Thanh Xuân', 'Khương Đình', '45 Nguyễn Trãi', TRUE)
ON DUPLICATE KEY UPDATE
  receiver_name = VALUES(receiver_name),
  address_detail = VALUES(address_detail),
  is_default = VALUES(is_default);

-- ------------------------------------------------------------
-- Carts
-- ------------------------------------------------------------
INSERT INTO carts (id, user_id)
VALUES
(1, 3),
(2, 4),
(3, 5)
ON DUPLICATE KEY UPDATE user_id = VALUES(user_id);

INSERT INTO cart_items (cart_id, product_id, quantity)
VALUES
(1, 1, 2),
(1, 5, 1),
(2, 3, 1),
(2, 7, 2),
(3, 9, 1)
ON DUPLICATE KEY UPDATE quantity = VALUES(quantity);

-- ------------------------------------------------------------
-- Payments for existing real orders
-- ------------------------------------------------------------
INSERT INTO payments
(id, order_id, payment_method, transaction_code, amount, status, paid_at)
VALUES
(1, 1, 'COD', NULL, 559000, 'PENDING', NULL),
(2, 2, 'BANK_TRANSFER', 'BT-20260810-0099', 320000, 'SUCCESS', '2026-08-10 10:18:00')
ON DUPLICATE KEY UPDATE
  status = VALUES(status),
  amount = VALUES(amount),
  paid_at = VALUES(paid_at);

-- ------------------------------------------------------------
-- Suppliers (empty purchasing tables get starter rows)
-- ------------------------------------------------------------
INSERT INTO suppliers
(id, code, name, phone, email, address, tax_code, status)
VALUES
(1, 'SUP-CF', 'HTX Cà phê Buôn Ma Thuột', '0902000001', 'coffee@supplier.vn', 'Buôn Ma Thuột, Đắk Lắk', '600000001', 'ACTIVE'),
(2, 'SUP-TB', 'Tây Bắc Nông Sản', '0902000002', 'taybac@supplier.vn', 'Sơn La', '550000002', 'ACTIVE'),
(3, 'SUP-HN', 'Nông sản Green Việt', '0902000003', 'green@supplier.vn', 'Hà Nội', '010000003', 'ACTIVE')
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  status = VALUES(status);
