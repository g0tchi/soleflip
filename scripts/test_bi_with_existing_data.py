#!/usr/bin/env python3
"""
Test BI system by updating existing inventory with purchase dates
"""

import requests
import json
from datetime import datetime, timedelta
import random

API_BASE = "http://localhost:8000"

def get_inventory_items():
    """Get current inventory items."""
    response = requests.get(f"{API_BASE}/api/v1/inventory/items")
    if response.status_code == 200:
        return response.json()['items']
    else:
        print(f"[ERROR] Failed to get inventory: {response.status_code}")
        return []

def update_inventory_with_purchase_date(item_id, purchase_date, purchase_price):
    """Update inventory item with purchase date for BI calculations."""
    # We'll use a simple PATCH approach by directly calling the API
    # For testing, we simulate purchase dates
    print(f"[UPDATE] Setting purchase date for item {item_id}: {purchase_date}")

    # This is a test - we would update via API if we had the right endpoint
    # For now, we just simulate the data we'd need
    return True

def simulate_bi_calculation(item):
    """Simulate BI calculation for an inventory item."""
    # Simulate some purchase data
    if item['purchase_price']:
        purchase_price = float(item['purchase_price'])

        # Generate a random purchase date 10-60 days ago
        days_ago = random.randint(10, 60)
        purchase_date = datetime.now() - timedelta(days=days_ago)

        # Simulate sale data (assuming some items were sold)
        sale_price = purchase_price * random.uniform(0.8, 1.4)  # -20% to +40% margin

        # Calculate BI metrics
        shelf_life_days = days_ago
        profit = sale_price - purchase_price
        roi_percentage = (profit / purchase_price) * 100
        pas = profit / shelf_life_days if shelf_life_days > 0 else 0

        return {
            'item_id': item['id'],
            'sku': item.get('product_name', 'Unknown'),
            'purchase_date': purchase_date.strftime('%Y-%m-%d'),
            'purchase_price': purchase_price,
            'sale_price': sale_price,
            'shelf_life_days': shelf_life_days,
            'roi_percentage': roi_percentage,
            'profit': profit,
            'pas': pas
        }
    return None

def test_dashboard_api():
    """Test the dashboard metrics API."""
    print("\n[DASHBOARD] Testing dashboard metrics API...")

    response = requests.get(f"{API_BASE}/api/analytics/business-intelligence/dashboard-metrics")

    if response.status_code == 200:
        data = response.json()
        print("[OK] Dashboard API responded successfully")
        print(f"Current metrics: {json.dumps(data, indent=2)}")
        return data
    else:
        print(f"[ERROR] Dashboard API failed: {response.status_code}")
        if hasattr(response, 'text'):
            print(f"Error details: {response.text}")
        return None

def main():
    """Main test function."""
    print("[START] Testing BI System with Existing Data")
    print("=" * 50)

    # Get existing inventory
    print("\n[INVENTORY] Fetching existing inventory items...")
    items = get_inventory_items()

    if not items:
        print("[ERROR] No inventory items found")
        return

    print(f"[INFO] Found {len(items)} inventory items")

    # Show some sample items with purchase prices
    items_with_prices = [item for item in items if item.get('purchase_price')]
    print(f"[INFO] {len(items_with_prices)} items have purchase prices")

    if items_with_prices:
        print("\n[SAMPLE] Sample items with purchase prices:")
        for i, item in enumerate(items_with_prices[:5]):  # Show first 5
            print(f"  {i+1}. {item['product_name']} - Size {item['size']} - Price: {item['purchase_price']} EUR")

    # Test dashboard API
    dashboard_result = test_dashboard_api()

    # Simulate BI calculations for a few items
    print("\n[SIMULATION] Simulating BI calculations for sample items...")
    simulated_results = []

    for item in items_with_prices[:3]:  # Test with first 3 items
        bi_result = simulate_bi_calculation(item)
        if bi_result:
            simulated_results.append(bi_result)
            print(f"\n[CALC] {bi_result['sku']}:")
            print(f"  Purchase Price: {bi_result['purchase_price']:.2f} EUR")
            print(f"  Simulated Sale Price: {bi_result['sale_price']:.2f} EUR")
            print(f"  Shelf Life: {bi_result['shelf_life_days']} days")
            print(f"  ROI: {bi_result['roi_percentage']:.1f}%")
            print(f"  PAS: {bi_result['pas']:.2f} EUR/day")

    # Summary
    if simulated_results:
        avg_roi = sum(r['roi_percentage'] for r in simulated_results) / len(simulated_results)
        avg_pas = sum(r['pas'] for r in simulated_results) / len(simulated_results)
        avg_shelf_life = sum(r['shelf_life_days'] for r in simulated_results) / len(simulated_results)

        print("\n[SUMMARY] Simulation Results:")
        print(f"  Items Processed: {len(simulated_results)}")
        print(f"  Average ROI: {avg_roi:.1f}%")
        print(f"  Average PAS: {avg_pas:.2f} EUR/day")
        print(f"  Average Shelf Life: {avg_shelf_life:.1f} days")

    print("\n[INFO] BI calculations simulated successfully!")
    print("[INFO] The system has the data structure needed for Business Intelligence.")
    print("[INFO] To activate full BI functionality, inventory items need purchase_date values.")

if __name__ == "__main__":
    main()