# LifeGift Baseline SQL Schema & Authentication Contract

## 1. Verified Baseline Tables & Enums

### Users & Authentication
- **`users`**:
  - `id`: BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY
  - `email`: VARCHAR(255) NOT NULL UNIQUE
  - `full_name`: VARCHAR(255)
  - `phone`: VARCHAR(50)
  - `created_at`: DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
- **Authentication Contract**:
  - Bearer token / Mock user auth passing authenticated `user_id` (BIGINT UNSIGNED) or `None` for anonymous users.
  - SQL queries on user-scoped resources (e.g. `orders`) must strictly match `WHERE orders.user_id = :authenticated_user_id`.

### Catalog Domain
- **`categories`**:
  - `id`, `name`, `slug` (UNIQUE), `status` ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE'
- **`brands`**:
  - `id`, `name`, `status` ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE'
- **`products`**:
  - `id`, `category_id` (FK -> categories.id), `brand_id` (FK -> brands.id), `name`, `slug` (UNIQUE), `description`, `price` (DECIMAL(15,2)), `sale_price` (DECIMAL(15,2) NULL), `origin`, `status` ENUM('ACTIVE', 'INACTIVE', 'OUT_OF_STOCK') DEFAULT 'ACTIVE', timestamps
- **`product_images`**:
  - `id`, `product_id` (FK -> products.id), `image_url`, `is_primary` (BOOLEAN), `sort_order` (INT)

### Inventory Domain
- **`warehouses`**:
  - `id`, `name`, `status` ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE'
- **`inventories`**:
  - `id`, `product_id` (FK -> products.id), `warehouse_id` (FK -> warehouses.id), `available_quantity` (INT DEFAULT 0), `reserved_quantity` (INT DEFAULT 0)
  - Source of truth for product availability: `SUM(inventories.available_quantity) > 0`.

### Reviews Domain
- **`reviews`**:
  - `id`, `product_id` (FK -> products.id), `user_id` (FK -> users.id), `rating` (INT 1-5), `title`, `content`, `status` ENUM('PENDING', 'APPROVED', 'REJECTED') DEFAULT 'PENDING'
  - Chatbot rule: only `status = 'APPROVED'` reviews are exposed to users.

### Content / Blog Domain
- **`blog_categories`**: `id`, `name`, `slug`
- **`blog_posts`**:
  - `id`, `category_id`, `title`, `slug`, `summary`, `content`, `status` ENUM('DRAFT', 'PUBLISHED', 'ARCHIVED') DEFAULT 'DRAFT', `published_at`, timestamps
  - RAG rule: only `status = 'PUBLISHED'` articles are indexed and retrievable.

### Orders Domain
- **`orders`**:
  - `id`, `order_code` (VARCHAR(100) UNIQUE), `user_id` (FK -> users.id), `total_amount` (DECIMAL(15,2)), `order_status` ENUM('PENDING', 'PROCESSING', 'SHIPPING', 'DELIVERED', 'CANCELLED'), `payment_status` ENUM('UNPAID', 'PAID', 'REFUNDED')
- **`order_items`**:
  - `id`, `order_id` (FK -> orders.id), `product_id` (FK -> products.id), `quantity`, `price`
- **`order_status_history`**:
  - `id`, `order_id` (FK -> orders.id), `status` ENUM('PENDING', 'PROCESSING', 'SHIPPING', 'DELIVERED', 'CANCELLED'), `notes`, `created_at`
