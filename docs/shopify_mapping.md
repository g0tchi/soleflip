# Shopify Compatibility Mapping Analysis

## 1. Mapping Suggestions

This section provides suggestions for mapping the local database schema to Shopify's core entities.

### Shopify Entity: `Product` -> Local Table: `products.products`

| Shopify Field | Local Source |
|---------------|--------------|
| `title` | `name` |
| `body_html` | `description` |
| `vendor` | `brand.name (JOIN core.brands)` |
| `product_type` | `category.name (JOIN core.categories)` |
| `sku` | `sku` |
| `status` | `'active' (Hardcoded, as no status field exists)` |

**Notes:** The 'handle' and 'tags' fields have no direct equivalent and would need to be generated.

### Shopify Entity: `Variant` -> Local Table: `products.inventory`

| Shopify Field | Local Source |
|---------------|--------------|
| `product_id` | `product_id (FK)` |
| `price` | `purchase_price (Note: This is purchase price, not selling price)` |
| `sku` | `product.sku + '-' + size.value (Requires generation)` |
| `inventory_quantity` | `quantity` |
| `option1` | `size.value (JOIN core.sizes)` |

**Notes:** A single product in the local DB with multiple inventory items of different sizes maps well to a Shopify Product with Variants. The selling price is missing, as `purchase_price` is likely not the final price.

### Shopify Entity: `Order` -> Local Table: `sales.transactions`

| Shopify Field | Local Source |
|---------------|--------------|
| `id` | `external_id or id` |
| `name` | `id (Could be used for order name)` |
| `total_price` | `sale_price` |
| `created_at` | `transaction_date` |
| `financial_status` | `'paid' (Derived from status)` |
| `fulfillment_status` | `'fulfilled' (Derived from status)` |

**Notes:** This mapping is partial. Crucially, it lacks a link to a customer and detailed line items. A single transaction seems to represent a single line item sale.

### Shopify Entity: `LineItem` -> Local Table: `sales.transactions`

| Shopify Field | Local Source |
|---------------|--------------|
| `order_id` | `id (Self-reference, as one transaction is one line item)` |
| `product_id` | `inventory_item.product_id (JOIN products.inventory)` |
| `variant_id` | `inventory_id` |
| `title` | `inventory_item.product.name (JOIN through inventory)` |
| `quantity` | `1 (Assumed, as transactions seem to be per-item)` |
| `price` | `sale_price` |
| `sku` | `inventory_item.product.sku (JOIN through inventory)` |

**Notes:** The local model doesn't have a clear Order/LineItem separation. A single `Transaction` record seems to act as a single `LineItem`.

### Shopify Entity: `Customer` -> Local Table: `N/A`

**Notes:** This is the most significant gap. There is no `Customer` table in the local schema. The `core.suppliers` table represents business suppliers, not end customers. Customer data might be in `sales.transactions` (e.g., buyer destination), but it's not structured.

## 2. Gap Analysis & Inconsistencies

This section highlights missing structures and inconsistencies that need to be addressed for a successful Shopify integration.

- **No Customer Entity:** The most critical missing piece. A dedicated `customers` table with first name, last name, email, and addresses is needed for a proper Shopify integration.

- **Missing Selling Price:** The `products.inventory` table has a `purchase_price`, but Shopify requires a `price` (selling price) for variants. This needs to be added or sourced from elsewhere.

- **Order Structure:** The local `sales.transactions` table is flat. Shopify has a clear `Order -> LineItems` hierarchy. An ETL process would need to group transactions if they belong to a single conceptual order, but there's no grouping key.

- **Product Images:** Shopify heavily relies on product images. The current schema has no table for storing image URLs or references.

- **Product Options:** Beyond size (`core.sizes`), there's no support for other product options like 'Color' or 'Material' which are fundamental to Shopify.

- **Inventory Locations:** Shopify supports multi-location inventory. The local schema assumes a single stock quantity per inventory item.

- **Missing Fields:** Many standard Shopify fields like `handle` (for SEO-friendly URLs) and `tags` are missing and would need to be generated during migration.