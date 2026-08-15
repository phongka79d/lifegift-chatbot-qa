-- Migration 004: Add effective_price to products and create supporting index
ALTER TABLE products
ADD COLUMN effective_price DECIMAL(15,2)
GENERATED ALWAYS AS (
    COALESCE(sale_price, price)
) STORED;

CREATE INDEX idx_products_status_category_price
    ON products(status, category_id, effective_price);
