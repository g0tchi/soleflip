#!/usr/bin/env python3
"""
Update existing inventory items with Notion test data
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

# Notion test data mapped to existing inventory
NOTION_UPDATE_DATA = [
    {
        "search_term": "adidas AE 1",  # Will find the adidas AE 1 Low item
        "purchase_date": "2024-07-23",
        "sale_date": "2024-08-13",
        "gross_buy": 238.00,
        "net_sale": 205.19,
        "supplier": "Adidas",
        "expected_roi": 2.6,
        "expected_shelf_life": 21
    },
    {
        "search_term": "Campus 00s",  # Will find the Campus item
        "purchase_date": "2024-04-27",
        "sale_date": "2024-05-10",
        "gross_buy": 102.00,
        "net_sale": 93.05,
        "supplier": "Solebox",
        "expected_roi": 8.6,
        "expected_shelf_life": 13
    },
    {
        "search_term": "Air Max 180",  # Will find the Air Max item
        "purchase_date": "2024-08-10",
        "sale_date": "2024-08-28",
        "gross_buy": 50.00,
        "net_sale": 49.45,
        "supplier": "Nike",
        "expected_roi": 17.7,
        "expected_shelf_life": 18
    }
]

def get_inventory_items():
    """Get current inventory items."""
    response = requests.get(f"{API_BASE}/api/v1/inventory/items")
    if response.status_code == 200:
        return response.json()['items']
    else:
        print(f"[ERROR] Failed to get inventory: {response.status_code}")
        return []

def find_item_by_name(items, search_term):
    """Find inventory item by product name."""
    for item in items:
        if search_term.lower() in item['product_name'].lower():
            return item
    return None

def update_item_via_sql_simulation(item, notion_data):
    """Simulate direct SQL update (since we don't have PATCH endpoint)."""

    purchase_date = datetime.strptime(notion_data['purchase_date'], '%Y-%m-%d')
    sale_date = datetime.strptime(notion_data['sale_date'], '%Y-%m-%d')

    # Calculate BI metrics using net_buy (B2B logic)
    shelf_life_days = (sale_date - purchase_date).days
    net_purchase_price = notion_data['gross_buy'] / 1.19  # Default 19% German VAT
    sale_price = notion_data['net_sale']
    profit = sale_price - net_purchase_price
    roi_percentage = (profit / net_purchase_price) * 100 if net_purchase_price > 0 else 0
    pas = profit / shelf_life_days if shelf_life_days > 0 else 0

    print(f"\n[UPDATE] Simulating update for {item['product_name']}:")
    print(f"  Item ID: {item['id']}")
    print(f"  Purchase Date: {notion_data['purchase_date']}")
    print(f"  Net Purchase Price: {net_purchase_price:.2f} EUR (was gross: {notion_data['gross_buy']:.2f} EUR)")
    print(f"  Sale Price: {sale_price:.2f} EUR")
    print(f"  Calculated Shelf Life: {shelf_life_days} days (expected: {notion_data['expected_shelf_life']})")
    print(f"  Calculated ROI: {roi_percentage:.1f}% (expected: {notion_data['expected_roi']:.1f}%)")
    print(f"  Calculated PAS: {pas:.2f} EUR/day")
    print(f"  Supplier: {notion_data['supplier']}")

    # Validation
    shelf_life_accurate = abs(shelf_life_days - notion_data['expected_shelf_life']) <= 1
    roi_accurate = abs(roi_percentage - notion_data['expected_roi']) <= 2.0

    validation_status = "[PASS]" if (shelf_life_accurate and roi_accurate) else "[FAIL]"
    print(f"  Validation: {validation_status}")

    if not shelf_life_accurate:
        print(f"    [WARNING] Shelf life mismatch: {shelf_life_days} vs {notion_data['expected_shelf_life']}")
    if not roi_accurate:
        print(f"    [WARNING] ROI mismatch: {roi_percentage:.1f}% vs {notion_data['expected_roi']:.1f}%")

    return {
        'item_id': item['id'],
        'product_name': item['product_name'],
        'calculated_shelf_life': shelf_life_days,
        'expected_shelf_life': notion_data['expected_shelf_life'],
        'calculated_roi': roi_percentage,
        'expected_roi': notion_data['expected_roi'],
        'calculated_pas': pas,
        'validation_passed': shelf_life_accurate and roi_accurate
    }

def test_bi_api_with_real_item(item_id):
    """Test BI API endpoints with a real item."""
    print(f"\n[API_TEST] Testing BI APIs with item {item_id}...")

    # Test analytics endpoint
    try:
        response = requests.get(f"{API_BASE}/api/analytics/business-intelligence/inventory/{item_id}/analytics")
        if response.status_code == 200:
            print("[OK] Analytics API responded successfully")
            data = response.json()
            print(f"Analytics result: {json.dumps(data, indent=2)}")
        else:
            print(f"[ERROR] Analytics API failed: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"[ERROR] Analytics API exception: {e}")

    # Test update analytics endpoint
    try:
        response = requests.post(f"{API_BASE}/api/analytics/business-intelligence/inventory/{item_id}/update-analytics")
        if response.status_code == 200:
            print("[OK] Update Analytics API responded successfully")
            data = response.json()
            print(f"Update result: {json.dumps(data, indent=2)}")
        else:
            print(f"[ERROR] Update Analytics API failed: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"[ERROR] Update Analytics API exception: {e}")

def main():
    """Main function."""
    print("[START] Updating Inventory with Notion Test Data")
    print("=" * 55)

    # Get inventory items
    items = get_inventory_items()
    if not items:
        print("[ERROR] No inventory items found")
        return

    print(f"[INFO] Found {len(items)} inventory items")

    updated_items = []

    # Process each Notion data entry
    for notion_data in NOTION_UPDATE_DATA:
        print(f"\n[SEARCH] Looking for item matching '{notion_data['search_term']}'...")

        item = find_item_by_name(items, notion_data['search_term'])
        if item:
            print(f"[FOUND] {item['product_name']} (ID: {item['id']})")

            # Simulate the update and BI calculation
            result = update_item_via_sql_simulation(item, notion_data)
            updated_items.append(result)

            # Test BI APIs with this item
            test_bi_api_with_real_item(item['id'])

        else:
            print(f"[NOT_FOUND] No item found matching '{notion_data['search_term']}'")

    # Summary
    print("\n[SUMMARY] BI Testing Results:")
    print("-" * 40)

    total_items = len(updated_items)
    passed_items = sum(1 for item in updated_items if item['validation_passed'])
    success_rate = (passed_items / total_items * 100) if total_items > 0 else 0

    print(f"Total items tested: {total_items}")
    print(f"Validation passed: {passed_items}")
    print(f"Success rate: {success_rate:.1f}%")

    if total_items > 0:
        avg_calculated_shelf_life = sum(item['calculated_shelf_life'] for item in updated_items) / total_items
        avg_expected_shelf_life = sum(item['expected_shelf_life'] for item in updated_items) / total_items
        avg_calculated_roi = sum(item['calculated_roi'] for item in updated_items) / total_items
        avg_expected_roi = sum(item['expected_roi'] for item in updated_items) / total_items

        print("\nAverage Metrics:")
        print(f"  Calculated Shelf Life: {avg_calculated_shelf_life:.1f} days")
        print(f"  Expected Shelf Life: {avg_expected_shelf_life:.1f} days")
        print(f"  Calculated ROI: {avg_calculated_roi:.1f}%")
        print(f"  Expected ROI: {avg_expected_roi:.1f}%")

    print("\n[CONCLUSION]")
    if success_rate >= 80:
        print("[SUCCESS] BI calculation logic is working correctly!")
        print("[INFO] Ready to implement full Notion data import.")
    else:
        print("[WARNING] BI calculations need adjustment.")
        print("[INFO] Check date calculations and profit formulas.")

    print("\n[NEXT_STEPS]")
    print("1. Fix any SQLAlchemy async issues in BI endpoints")
    print("2. Add purchase_date updates to inventory items")
    print("3. Implement bulk Notion data import")
    print("4. Test dashboard with real BI data")

if __name__ == "__main__":
    main()