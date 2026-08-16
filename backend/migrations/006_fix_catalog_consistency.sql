-- Migration 006: Align leftover seed rows with the imported catalog.
-- Safe / idempotent data fixes (no destructive schema change).

-- 1) Empty leftover categories must not stay ACTIVE.
UPDATE categories
SET status = 'INACTIVE'
WHERE id IN (1, 2, 3)
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.category_id = categories.id AND p.status = 'ACTIVE'
  );

-- 2) Certificates were left on seed product_ids after catalog import remapped those ids.
--    Re-attach by meaning; revoke GI honey because no U Minh SKU exists.
UPDATE product_certificates
SET product_id = 2
WHERE id IN (1, 2)
  AND product_id <> 2;

UPDATE product_certificates
SET product_id = 3
WHERE id = 3
  AND (name LIKE '%Shan Tuyết%' OR description LIKE '%Shan Tuyết%' OR description LIKE '%trà%');

UPDATE product_certificates
SET status = 'REVOKED'
WHERE id = 4
  AND (name LIKE '%U Minh%' OR description LIKE '%U Minh%');

-- 3) Duplicate display names: name must match weight / origin.
UPDATE products
SET name = 'Nấm hương rừng khô 300g'
WHERE id = 31 AND weight = 300 AND name = 'Nấm hương rừng khô 250g';

UPDATE products
SET name = 'Trà Shan Tuyết cổ thụ 200g Hà Giang'
WHERE id = 3 AND origin = 'Hà Giang' AND name = 'Trà Shan Tuyết cổ thụ 200g';

UPDATE products
SET name = 'Trà Shan Tuyết cổ thụ 200g Sơn La'
WHERE id = 57 AND origin = 'Sơn La' AND name = 'Trà Shan Tuyết cổ thụ 200g';
