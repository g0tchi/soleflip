"""
Fetch ALL StockX Sales from Notion using Direct API Queries
Uses database query with filters instead of search (more reliable)

Claude Code will populate this with actual Notion API calls via MCP
"""

from typing import Dict, List

# Will be populated by Claude Code
ALL_STOCKX_SALES = []


def format_for_bulk_sync(sales: List[Dict]) -> str:
    """Format sales for execute_bulk_sync.py"""
    output = "NOTION_SALES_RAW = [\n"

    for sale in sales:
        sku = sale.get("SKU", "UNKNOWN")
        url = sale.get("url", "")

        # Build highlight text from properties
        highlight_lines = [
            sku,
            f"Size: {sale.get('Size', '')}",
            f"Type: {sale.get('Type', '')}",
            f"Buy Date: {sale.get('Buy Date', '')}",
            f"Status: {sale.get('Status', '')}",
            f"Delivery Date: {sale.get('Delivery Date', '')}",
            f"Gross Buy: {sale.get('Gross Buy', '')} €",
            f"VAT?: {str(sale.get('VAT?', '')).lower()}",
            f"Net Buy: {sale.get('Net Buy', '')} €",
            f"Supplier: {sale.get('Supplier', '')}",
            f"Order No.: {sale.get('Order No.', '')}",
            f"Invoice Nr.: {sale.get('Invoice Nr.', '')}",
            f"Email: {sale.get('Email', '')}",
            f"Invoice: {sale.get('Invoice', '')}",
            f"Listed on Alias?: {str(sale.get('Listed on Alias?', False)).lower()}",
            f"Listed on StockX?: {str(sale.get('Listed on StockX?', False)).lower()}",
            f"Sale Date: {sale.get('Sale Date', '')}",
            f"Sale Platform: {sale.get('Sale Platform', '')}",
            f"Sale ID: {sale.get('Sale ID', '')}",
            f"Gross Sale: {sale.get('Gross Sale', '')} €",
            f"Net Sale: {sale.get('Net Sale', '')} €",
            f"Sold?: {str(sale.get('Sold?', False)).lower()}",
            f"Payout Received?: {str(sale.get('Payout Received?', False)).lower()}",
            f"ROI: {sale.get('ROI', '')} %",
            f"Profit: {sale.get('Profit', '')} €",
            f"Shelf Life: {sale.get('Shelf Life', '')}",
            f"Brand: {sale.get('Brand', '')}",
        ]

        highlight = "\n".join(highlight_lines)

        # Escape single quotes
        highlight = highlight.replace("'", "\\'")

        output += f"    ('{sku}', '{url}',\n"
        output += f"     '''{highlight}'''),\n"

    output += "]\n"
    output += f"\n# Total: {len(sales)} StockX sales\n"

    return output


def main():
    """Process collected sales"""
    if not ALL_STOCKX_SALES:
        print("=" * 80)
        print("NO SALES DATA AVAILABLE")
        print("=" * 80)
        print()
        print("This script must be populated by Claude Code using Notion MCP.")
        print()
        print("Claude will:")
        print("1. Query Notion database: collection://26ad4ac8-540e-4ea8-913c-a7bb88747280")
        print("2. Filter: Sale Platform = 'StockX' AND Gross Buy IS NOT NULL")
        print("3. Populate ALL_STOCKX_SALES with all matching pages")
        print("4. Format output for execute_bulk_sync.py")
        print()
        return

    print("=" * 80)
    print("NOTION STOCKX SALES - DIRECT API FETCH")
    print("=" * 80)
    print(f"Total sales found: {len(ALL_STOCKX_SALES)}")
    print()

    # Validate sales
    valid_sales = []
    invalid_sales = []

    for sale in ALL_STOCKX_SALES:
        # Check required fields
        has_gross_buy = sale.get("Gross Buy") is not None
        has_supplier = sale.get("Supplier") is not None
        has_sale_id = sale.get("Sale ID") is not None
        is_stockx = sale.get("Sale Platform") == "StockX"

        if has_gross_buy and has_supplier and has_sale_id and is_stockx:
            valid_sales.append(sale)
        else:
            invalid_sales.append(sale.get("SKU", "UNKNOWN"))

    print(f"Valid sales: {len(valid_sales)}")
    print(f"Invalid/incomplete: {len(invalid_sales)}")

    if invalid_sales:
        print("\nInvalid SKUs (first 10):")
        for sku in invalid_sales[:10]:
            print(f"  - {sku}")

    # Generate output
    print()
    print("=" * 80)
    print("OUTPUT FOR execute_bulk_sync.py")
    print("=" * 80)
    print()

    output = format_for_bulk_sync(valid_sales)
    print(output)

    print()
    print("=" * 80)
    print(f"READY TO SYNC: {len(valid_sales)} sales")
    print("=" * 80)


if __name__ == "__main__":
    main()
