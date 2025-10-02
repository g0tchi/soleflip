"""
Analyze Notion Database Schema vs PostgreSQL Schema
Identifies missing fields that need to be added to DB
"""

# Notion Sale Entry Fields (from previous test)
notion_fields = {
    # Product Information
    "SKU": "text/title",  # maps to Product.sku
    "Brand": "select",     # maps to Brand.name
    "Product": "text",     # maps to Product.name
    "Size": "text",        # maps to Size.value

    # Supplier/Purchase Information
    "Supplier": "text",              # maps to Supplier.name
    "Gross Buy": "number",           # Price WITH VAT
    "Net Buy": "number",             # Price WITHOUT VAT (what we store as purchase_price)
    "VAT Included": "checkbox",      # Boolean
    "Buy Date": "date",              # maps to InventoryItem.purchase_date
    "Delivery Date": "date",         # ??? NOT IN DB
    "Order No.": "text",             # ??? NOT IN DB (external_ids JSONB?)
    "Invoice Nr.": "text",           # ??? NOT IN DB (external_ids JSONB?)

    # StockX Sale Information
    "Sale Date": "date",             # maps to StockXOrder.sold_at
    "Sale Platform": "select",       # Should be "StockX" - validation
    "Sale ID": "text",               # maps to StockXOrder.stockx_order_number
    "Gross Sale": "number",          # ??? NOT IN DB DIRECTLY
    "Net Sale": "number",            # maps to StockXOrder.sale_price
    "Profit": "number",              # maps to StockXOrder.net_profit
    "ROI": "number",                 # maps to StockXOrder.roi
    "Payout Received": "checkbox",   # ??? NOT IN DB
    "Status": "select",              # maps to StockXOrder.order_status
    "Shelf Life": "number",          # CALCULATED: Sale Date - Buy Date
    "Order No. (StockX)": "text",    # Same as Sale ID
    "PAS": "number",                 # CALCULATED: Profit / Shelf Life (Profit per Day)
}

# PostgreSQL Schema (from models.py)
postgres_schema = {
    "core.suppliers": {
        "id": "UUID",
        "name": "String",
        "slug": "String",
        "supplier_type": "String",
        "status": "String",
        "contact_person": "String",
        "email": "String",
        "phone": "String",
        "website": "String",
        "return_policy_days": "Integer",
        "return_policy_text": "Text",
        "payment_terms": "String",
        # ... many more fields
    },
    "core.sizes": {
        "id": "UUID",
        "category_id": "UUID (FK)",
        "value": "String",
        "region": "String",
        "standardized_value": "Numeric",
    },
    "products.inventory": {
        "id": "UUID",
        "product_id": "UUID (FK)",
        "size_id": "UUID (FK)",
        "supplier_id": "UUID (FK)",
        "quantity": "Integer",
        "purchase_price": "Numeric",  # Net Buy Price
        "purchase_date": "DateTime",   # Buy Date
        "status": "String",
        "supplier": "String",          # Redundant with supplier_id?
        "source_platform": "String",
        "external_ids": "JSONB",       # Could store Order No., Invoice Nr.
        "notes": "Text",
        # MISSING: delivery_date
        # MISSING: vat_amount
        # MISSING: gross_purchase_price
    },
    "platforms.stockx_listings": {
        "id": "UUID",
        "product_id": "UUID (FK)",
        "stockx_listing_id": "String",
        "stockx_product_id": "String",
        "ask_price": "Numeric",
        "status": "String",
        "is_active": "Boolean",
        "created_from": "String",
        # ... more fields
    },
    "platforms.stockx_orders": {
        # Uses transactions.orders table instead!
        # See: transactions.orders
    },
    "transactions.orders": {
        "id": "UUID",
        "inventory_item_id": "UUID (FK)",
        "listing_id": "UUID (FK)",
        "stockx_order_number": "String",  # Sale ID
        "status": "String",                # Sale Status
        "amount": "Numeric",               # Sale Price
        "currency_code": "String",
        "inventory_type": "String",
        "shipping_label_url": "String",
        "stockx_created_at": "DateTime",
        "last_stockx_updated_at": "DateTime",
        "raw_data": "JSONB",
        # MISSING: sold_at (Sale Date)
        # MISSING: net_proceeds (Net Sale)
        # MISSING: gross_sale
        # MISSING: gross_profit
        # MISSING: net_profit (Profit)
        # MISSING: roi (ROI)
        # MISSING: payout_received (Boolean)
        # MISSING: payout_date
    },
}

# Analysis Results
print("=" * 80)
print("NOTION vs POSTGRESQL SCHEMA ANALYSIS")
print("=" * 80)
print()

print("[!] MISSING FIELDS IN POSTGRESQL")
print("-" * 80)

missing_fields = {
    "products.inventory": [
        ("delivery_date", "DateTime", "When item was delivered by supplier"),
        ("gross_purchase_price", "Numeric(10,2)", "Purchase price WITH VAT"),
        ("vat_amount", "Numeric(10,2)", "VAT amount paid"),
        ("vat_rate", "Numeric(5,2)", "VAT rate (e.g., 19.00 for Germany)"),
    ],
    "transactions.orders": [
        ("sold_at", "DateTime", "Sale completion date (from Notion: Sale Date)"),
        ("gross_sale", "Numeric(10,2)", "Sale price before fees/taxes"),
        ("net_proceeds", "Numeric(10,2)", "Net sale proceeds after fees (from Notion: Net Sale)"),
        ("gross_profit", "Numeric(10,2)", "Gross profit before expenses"),
        ("net_profit", "Numeric(10,2)", "Net profit after all costs (from Notion: Profit)"),
        ("roi", "Numeric(5,2)", "Return on investment percentage (from Notion: ROI)"),
        ("payout_received", "Boolean", "Whether payout was received (from Notion: Payout Received)"),
        ("payout_date", "DateTime", "Date payout was received"),
        ("shelf_life_days", "Integer", "Days between purchase and sale (calculated)"),
    ],
}

for table, fields in missing_fields.items():
    print(f"\n{table}:")
    for field_name, field_type, description in fields:
        print(f"  - {field_name} ({field_type})")
        print(f"    > {description}")

print()
print("=" * 80)
print("[OK] FIELDS THAT CAN USE EXISTING JSONB COLUMNS")
print("-" * 80)

jsonb_mappings = {
    "products.inventory.external_ids": [
        "supplier_order_number (from Notion: Order No.)",
        "supplier_invoice_number (from Notion: Invoice Nr.)",
    ],
    "transactions.orders.raw_data": [
        "notion_page_id (for reference)",
        "pas_metric (Profit per day)",
        "original_notion_data (full backup)",
    ],
}

for jsonb_field, values in jsonb_mappings.items():
    print(f"\n{jsonb_field}:")
    for value in values:
        print(f"  - {value}")

print()
print("=" * 80)
print("[*] RECOMMENDED DATABASE MIGRATION")
print("-" * 80)

print("""
CREATE MIGRATION: "add_notion_sale_fields"

-- Add inventory purchase tracking fields
ALTER TABLE products.inventory
ADD COLUMN delivery_date TIMESTAMP WITH TIME ZONE,
ADD COLUMN gross_purchase_price NUMERIC(10,2),
ADD COLUMN vat_amount NUMERIC(10,2),
ADD COLUMN vat_rate NUMERIC(5,2) DEFAULT 19.00,
ADD COLUMN notes TEXT;  -- If not exists

COMMENT ON COLUMN products.inventory.delivery_date IS 'Delivery date from supplier';
COMMENT ON COLUMN products.inventory.gross_purchase_price IS 'Purchase price including VAT';
COMMENT ON COLUMN products.inventory.vat_amount IS 'VAT amount paid on purchase';
COMMENT ON COLUMN products.inventory.vat_rate IS 'VAT rate percentage (e.g., 19.00)';

-- Add order financial tracking fields
ALTER TABLE transactions.orders
ADD COLUMN sold_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN gross_sale NUMERIC(10,2),
ADD COLUMN net_proceeds NUMERIC(10,2),
ADD COLUMN gross_profit NUMERIC(10,2),
ADD COLUMN net_profit NUMERIC(10,2),
ADD COLUMN roi NUMERIC(5,2),
ADD COLUMN payout_received BOOLEAN DEFAULT FALSE,
ADD COLUMN payout_date TIMESTAMP WITH TIME ZONE,
ADD COLUMN shelf_life_days INTEGER;

COMMENT ON COLUMN transactions.orders.sold_at IS 'Sale completion date';
COMMENT ON COLUMN transactions.orders.gross_sale IS 'Gross sale amount before fees';
COMMENT ON COLUMN transactions.orders.net_proceeds IS 'Net proceeds after platform fees';
COMMENT ON COLUMN transactions.orders.gross_profit IS 'Sale price - Purchase price';
COMMENT ON COLUMN transactions.orders.net_profit IS 'Net profit after all costs';
COMMENT ON COLUMN transactions.orders.roi IS 'Return on investment percentage';
COMMENT ON COLUMN transactions.orders.payout_received IS 'Whether payout was received';
COMMENT ON COLUMN transactions.orders.payout_date IS 'Date payout was received';
COMMENT ON COLUMN transactions.orders.shelf_life_days IS 'Days between purchase and sale';

-- Add indexes for common queries
CREATE INDEX idx_orders_sold_at ON transactions.orders(sold_at);
CREATE INDEX idx_orders_payout_received ON transactions.orders(payout_received);
CREATE INDEX idx_inventory_delivery_date ON products.inventory(delivery_date);
""")

print()
print("=" * 80)
print("[+] NEXT STEPS")
print("-" * 80)
print("""
1. Create Alembic migration with above SQL
2. Run migration: alembic upgrade head
3. Update models.py with new fields
4. Update bulk_sync_notion_sales.py to populate new fields
5. Re-run product discovery to generate updated CSV
6. Execute bulk sync with complete data
""")

print()
print("=" * 80)
print("[i] DATA MAPPING SUMMARY")
print("-" * 80)

mapping = {
    "Notion Field": "PostgreSQL Field",
    "-" * 30: "-" * 45,
    "SKU": "Product.sku",
    "Brand": "Brand.name",
    "Product": "Product.name",
    "Size": "Size.value",
    "Supplier": "Supplier.name",
    "Gross Buy": "InventoryItem.gross_purchase_price (NEW)",
    "Net Buy": "InventoryItem.purchase_price",
    "VAT Included": "InventoryItem.vat_rate (NEW)",
    "Buy Date": "InventoryItem.purchase_date",
    "Delivery Date": "InventoryItem.delivery_date (NEW)",
    "Order No.": "InventoryItem.external_ids['supplier_order']",
    "Invoice Nr.": "InventoryItem.external_ids['supplier_invoice']",
    "Sale Date": "Order.sold_at (NEW)",
    "Sale ID": "Order.stockx_order_number",
    "Gross Sale": "Order.gross_sale (NEW)",
    "Net Sale": "Order.net_proceeds (NEW)",
    "Profit": "Order.net_profit (NEW)",
    "ROI": "Order.roi (NEW)",
    "Payout Received": "Order.payout_received (NEW)",
    "Status": "Order.status",
    "Shelf Life": "Order.shelf_life_days (NEW)",
}

for notion, postgres in mapping.items():
    print(f"{notion:30} -> {postgres}")

print()
print("=" * 80)