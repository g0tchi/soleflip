"""
Prepare Notion Sales Data for Bulk Sync
Collects sales from search results and prepares them for sync

This script will be populated by Claude Code with sales data from Notion search results.
"""

from typing import Dict, List

# Raw search results from Notion (highlights contain the data)
SEARCH_RESULTS = [
    # Claude will populate this with search result highlights
]


def parse_highlight_to_properties(highlight: str, url: str) -> Dict:
    """
    Parse Notion search result highlight into properties dict

    The highlight contains field data in format:
    Field Name: Value
    """
    properties = {"url": url}

    lines = highlight.strip().split("\n")

    for line in lines:
        if ":" not in line:
            continue

        # Split on first colon only
        parts = line.split(":", 1)
        if len(parts) != 2:
            continue

        field = parts[0].strip()
        value = parts[1].strip()

        # Skip empty values
        if not value or value in ["", "-"]:
            continue

        # Parse different field types
        if field in [
            "VAT?",
            "Payout Received?",
            "Sold?",
            "Listed on Alias?",
            "Listed on StockX?",
            "Listed Local?",
        ]:
            properties[field] = value.lower() in ["true", "yes", "1"]

        elif field in [
            "Gross Buy",
            "Gross Sale",
            "Net Sale",
            "Net Buy",
            "Profit",
            "Price (Excl. Label)",
        ]:
            # Remove currency symbols and convert
            clean_value = value.replace("€", "").replace(",", ".").strip()
            try:
                properties[field] = float(clean_value)
            except (ValueError, AttributeError):
                properties[field] = 0.0

        elif field in ["ROI", "Sale VAT"]:
            # Remove % and convert
            clean_value = value.replace("%", "").replace(",", ".").strip()
            try:
                properties[field] = float(clean_value)
            except (ValueError, AttributeError):
                properties[field] = 0.0

        elif field in ["Size", "Shelf Life", "Quantity"]:
            try:
                # Try as number first
                properties[field] = value
            except (ValueError, AttributeError):
                properties[field] = value

        elif field in ["Buy Date", "Sale Date", "Delivery Date"]:
            # Store as date string
            properties[f"date:{field}:start"] = value
            properties[f"date:{field}:is_datetime"] = 0

        else:
            # String fields
            properties[field] = value

    return properties


def extract_sales_from_search_results(search_results: List[Dict]) -> List[Dict]:
    """
    Extract sales data from Notion search results

    Returns list of dicts with 'properties' and 'url' keys
    """
    sales = []

    for result in search_results:
        url = result.get("url", "")
        highlight = result.get("highlight", "")
        title = result.get("title", "")

        if not highlight:
            continue

        # Parse highlight into properties
        properties = parse_highlight_to_properties(highlight, url)

        # Add SKU from title if not in properties
        if "SKU" not in properties and title:
            properties["SKU"] = title

        # Skip if missing critical fields
        if not properties.get("Sale ID") or not properties.get("Sale Platform"):
            continue

        # Only StockX sales
        if properties.get("Sale Platform") != "StockX":
            continue

        sales.append({"url": url, "properties": properties})

    return sales


if __name__ == "__main__":
    # Test parsing
    if SEARCH_RESULTS:
        sales = extract_sales_from_search_results(SEARCH_RESULTS)
        print(f"Extracted {len(sales)} StockX sales from search results")

        if sales:
            print("\nFirst sale preview:")
            first = sales[0]
            print(f"  SKU: {first['properties'].get('SKU')}")
            print(f"  Sale ID: {first['properties'].get('Sale ID')}")
            print(f"  Gross Buy: {first['properties'].get('Gross Buy')}")
            print(f"  Gross Sale: {first['properties'].get('Gross Sale')}")
    else:
        print("No search results loaded. Run from Claude Code with populated data.")
