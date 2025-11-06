"""
Shopify Compatibility Mapper
This script analyzes the existing database schema against Shopify's core entities
and generates a compatibility and mapping report in Markdown format.
"""

from pathlib import Path

# --- Shopify Core Entity Definitions (Simplified) ---
# Based on common Shopify data models.
SHOPIFY_ENTITIES = {
    "Product": {
        "fields": [
            "id",
            "title",
            "body_html",
            "vendor",
            "product_type",
            "handle",
            "tags",
            "status",
        ],
        "variants": "Variant",
        "images": "ProductImage",
        "options": "ProductOption",
    },
    "Variant": {
        "fields": [
            "id",
            "product_id",
            "title",
            "price",
            "sku",
            "inventory_quantity",
            "weight",
            "weight_unit",
            "option1",
            "option2",
            "option3",
        ]
    },
    "Order": {
        "fields": [
            "id",
            "name",
            "email",
            "total_price",
            "financial_status",
            "fulfillment_status",
            "created_at",
            "currency",
            "customer_locale",
        ],
        "line_items": "LineItem",
        "customer": "Customer",
    },
    "LineItem": {
        "fields": [
            "id",
            "order_id",
            "product_id",
            "variant_id",
            "title",
            "quantity",
            "price",
            "sku",
            "vendor",
        ]
    },
    "Customer": {
        "fields": [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "addresses",
            "default_address",
        ]
    },
}

# --- Mapping from Local Schema to Shopify ---
# This is the core of the analysis, based on the schema documented in db_schema_analysis.md
SCHEMA_MAPPING = {
    "Product": {
        "source_table": "products.products",
        "field_mapping": {
            "title": "name",
            "body_html": "description",
            "vendor": "brand.name (JOIN core.brands)",
            "product_type": "category.name (JOIN core.categories)",
            "sku": "sku",
            "status": "'active' (Hardcoded, as no status field exists)",
        },
        "notes": "The 'handle' and 'tags' fields have no direct equivalent and would need to be generated.",
    },
    "Variant": {
        "source_table": "products.inventory",
        "field_mapping": {
            "product_id": "product_id (FK)",
            "price": "purchase_price (Note: This is purchase price, not selling price)",
            "sku": "product.sku + '-' + size.value (Requires generation)",
            "inventory_quantity": "quantity",
            "option1": "size.value (JOIN core.sizes)",
        },
        "notes": "A single product in the local DB with multiple inventory items of different sizes maps well to a Shopify Product with Variants. The selling price is missing, as `purchase_price` is likely not the final price.",
    },
    "Order": {
        "source_table": "sales.transactions",
        "field_mapping": {
            "id": "external_id or id",
            "name": "id (Could be used for order name)",
            "total_price": "sale_price",
            "created_at": "transaction_date",
            "financial_status": "'paid' (Derived from status)",
            "fulfillment_status": "'fulfilled' (Derived from status)",
        },
        "notes": "This mapping is partial. Crucially, it lacks a link to a customer and detailed line items. A single transaction seems to represent a single line item sale.",
    },
    "LineItem": {
        "source_table": "sales.transactions",
        "field_mapping": {
            "order_id": "id (Self-reference, as one transaction is one line item)",
            "product_id": "inventory_item.product_id (JOIN products.inventory)",
            "variant_id": "inventory_id",
            "title": "inventory_item.product.name (JOIN through inventory)",
            "quantity": "1 (Assumed, as transactions seem to be per-item)",
            "price": "sale_price",
            "sku": "inventory_item.product.sku (JOIN through inventory)",
        },
        "notes": "The local model doesn't have a clear Order/LineItem separation. A single `Transaction` record seems to act as a single `LineItem`.",
    },
    "Customer": {
        "source_table": "N/A",
        "field_mapping": {},
        "notes": "This is the most significant gap. There is no `Customer` table in the local schema. The `core.suppliers` table represents business suppliers, not end customers. Customer data might be in `sales.transactions` (e.g., buyer destination), but it's not structured.",
    },
}

# --- Gap Analysis ---
GAP_ANALYSIS = [
    "**No Customer Entity:** The most critical missing piece. A dedicated `customers` table with first name, last name, email, and addresses is needed for a proper Shopify integration.",
    "**Missing Selling Price:** The `products.inventory` table has a `purchase_price`, but Shopify requires a `price` (selling price) for variants. This needs to be added or sourced from elsewhere.",
    "**Order Structure:** The local `sales.transactions` table is flat. Shopify has a clear `Order -> LineItems` hierarchy. An ETL process would need to group transactions if they belong to a single conceptual order, but there's no grouping key.",
    "**Product Images:** Shopify heavily relies on product images. The current schema has no table for storing image URLs or references.",
    "**Product Options:** Beyond size (`core.sizes`), there's no support for other product options like 'Color' or 'Material' which are fundamental to Shopify.",
    "**Inventory Locations:** Shopify supports multi-location inventory. The local schema assumes a single stock quantity per inventory item.",
    "**Missing Fields:** Many standard Shopify fields like `handle` (for SEO-friendly URLs) and `tags` are missing and would need to be generated during migration.",
]


def generate_mapping_report():
    """Generates the full Markdown report."""
    report = ["# Shopify Compatibility Mapping Analysis"]

    report.append("\n## 1. Mapping Suggestions")
    report.append(
        "\nThis section provides suggestions for mapping the local database schema to Shopify's core entities."
    )

    for entity_name, mapping_info in SCHEMA_MAPPING.items():
        report.append(
            f"\n### Shopify Entity: `{entity_name}` -> Local Table: `{mapping_info['source_table']}`"
        )
        if mapping_info["field_mapping"]:
            report.append("\n| Shopify Field | Local Source |")
            report.append("|---------------|--------------|")
            for shopify_field, local_source in mapping_info["field_mapping"].items():
                report.append(f"| `{shopify_field}` | `{local_source}` |")

        if mapping_info["notes"]:
            report.append(f"\n**Notes:** {mapping_info['notes']}")

    report.append("\n## 2. Gap Analysis & Inconsistencies")
    report.append(
        "\nThis section highlights missing structures and inconsistencies that need to be addressed for a successful Shopify integration."
    )

    for gap in GAP_ANALYSIS:
        report.append(f"\n- {gap}")

    return "\n".join(report)


def main():
    """Main function to generate and save the report."""
    print("Generating Shopify mapping report...")
    report_content = generate_mapping_report()

    output_path = Path("docs/shopify_mapping.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(report_content)

    print(f"Report successfully saved to {output_path}")


if __name__ == "__main__":
    main()
