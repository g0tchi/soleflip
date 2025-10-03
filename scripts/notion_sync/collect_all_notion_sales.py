"""
Collect ALL StockX Sales from Notion Inventory Database
Uses systematic search queries to find all sales with complete purchase data

This script should be run by Claude Code with Notion MCP access.
"""
from typing import List

# This will be populated by Claude Code via Notion MCP
# Format: List of (SKU, URL, highlight_text) tuples
ALL_SALES_RAW = []

# Track seen Sale IDs to avoid duplicates
SEEN_SALE_IDS = set()


def extract_sale_id(highlight: str) -> str:
    """Extract Sale ID from highlight text"""
    for line in highlight.split('\n'):
        if line.startswith('Sale ID:'):
            return line.split(':', 1)[1].strip()
    return None


def deduplicate_sales(sales_raw: List[tuple]) -> List[tuple]:
    """Remove duplicate sales based on Sale ID"""
    unique_sales = []
    seen_ids = set()

    for sku, url, highlight in sales_raw:
        sale_id = extract_sale_id(highlight)
        if sale_id and sale_id not in seen_ids:
            seen_ids.add(sale_id)
            unique_sales.append((sku, url, highlight))

    return unique_sales


def validate_sale(highlight: str) -> bool:
    """Check if sale has all required fields"""
    required_fields = [
        'Gross Buy:',
        'Supplier:',
        'Sale Platform: StockX',
        'Sale ID:'
    ]

    return all(field in highlight for field in required_fields)


def main():
    """Process and validate all sales"""
    if not ALL_SALES_RAW:
        print("ERROR: ALL_SALES_RAW is empty!")
        print("This script must be run by Claude Code with Notion MCP.")
        return

    print(f"Total sales collected: {len(ALL_SALES_RAW)}")

    # Deduplicate
    unique_sales = deduplicate_sales(ALL_SALES_RAW)
    print(f"Unique sales (after deduplication): {len(unique_sales)}")

    # Validate
    valid_sales = []
    invalid_sales = []

    for sku, url, highlight in unique_sales:
        if validate_sale(highlight):
            valid_sales.append((sku, url, highlight))
        else:
            invalid_sales.append(sku)

    print(f"Valid sales: {len(valid_sales)}")
    print(f"Invalid sales: {len(invalid_sales)}")

    if invalid_sales:
        print("\nInvalid SKUs (missing required fields):")
        for sku in invalid_sales[:10]:  # Show first 10
            print(f"  - {sku}")

    # Export for execute_bulk_sync.py
    print("\n" + "="*80)
    print("COPY THIS TO execute_bulk_sync.py:")
    print("="*80)
    print("\nNOTION_SALES_RAW = [")
    for sku, url, highlight in valid_sales:
        # Escape quotes in highlight
        highlight_escaped = highlight.replace("'", "\\'")
        print(f"    ('{sku}', '{url}',")
        print(f"     '''{highlight}'''),")
    print("]")
    print(f"\n# Total: {len(valid_sales)} valid StockX sales")


if __name__ == '__main__':
    main()