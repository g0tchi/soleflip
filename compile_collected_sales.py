"""
Compile and Deduplicate All Collected Sales from Notion Search Results
This script processes all the search results and creates a deduplicated list
ready for execute_bulk_sync.py

Run this to generate the complete NOTION_SALES_RAW array.
"""

# All collected sales from systematic Notion searches
# Format: (title, url, highlight_snippet)
COLLECTED_SALES = []

# Add all sales with complete highlight data from searches
# Note: Only including sales with Sale ID for deduplication

def extract_sale_id(highlight: str) -> str:
    """Extract Sale ID from highlight text"""
    for line in highlight.split('\n'):
        if 'Sale ID:' in line:
            return line.split('Sale ID:')[1].strip()
    return None

def deduplicate_sales():
    """Deduplicate by Sale ID"""
    seen_ids = set()
    unique_sales = []

    for title, url, highlight in COLLECTED_SALES:
        sale_id = extract_sale_id(highlight)
        if sale_id and sale_id not in seen_ids:
            seen_ids.add(sale_id)
            unique_sales.append((title, url, highlight))

    return unique_sales

def format_for_sync(sales):
    """Format sales for execute_bulk_sync.py"""
    output = "NOTION_SALES_RAW = [\n"

    for i, (title, url, highlight) in enumerate(sales):
        # Escape single quotes
        highlight_escaped = highlight.replace("'", "\\'")

        # Use unique key for duplicates
        key = f"{title}-{i}" if i > 0 else title

        output += f"    ('{title}', '{url}',\n"
        output += f"     '''{highlight}'''),\n\n"

    output += "]\n"
    return output

if __name__ == '__main__':
    print("=" * 80)
    print("SALES COMPILATION REPORT")
    print("=" * 80)
    print(f"Total collected: {len(COLLECTED_SALES)}")

    unique = deduplicate_sales()
    print(f"After deduplication: {len(unique)}")

    print("\n" + "=" * 80)
    print("Formatted output ready for execute_bulk_sync.py")
    print("=" * 80)

    output = format_for_sync(unique)

    # Write to file
    with open('COMPILED_SALES_DATA.txt', 'w', encoding='utf-8') as f:
        f.write(output)

    print("\nWritten to: COMPILED_SALES_DATA.txt")
    print(f"Total unique sales: {len(unique)}")
