#!/usr/bin/env python3
"""
Test the size fix with real StockX data
"""
import sys
import os
import asyncio
import math

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domains.integration.services.validators import StockXValidator

async def test_size_parsing():
    # Test records with different size scenarios
    test_records = [
        {
            'Item': 'Nike Dunk Low Panda', 
            'Sku Size': 10.5,  # Normal size as number
            'Order Number': 12345, 
            'Sale Date': '2022-07-08 00:46:09 +00', 
            'Listing Price': 100, 
            'Seller Fee': 3.0,
            'Total Gross Amount (Total Payout)': 97.0
        },
        {
            'Item': 'Test Book', 
            'Sku Size': math.nan,  # NaN for non-shoe items
            'Order Number': 12346, 
            'Sale Date': '2022-07-08 00:46:09 +00', 
            'Listing Price': 45, 
            'Seller Fee': math.nan,
            'Total Gross Amount (Total Payout)': 45.0
        },
        {
            'Item': 'Nike Air Max 90', 
            'Sku Size': '9.5',  # Size as string
            'Order Number': 12347, 
            'Sale Date': '2022-07-08 00:46:09 +00', 
            'Listing Price': 120, 
            'Seller Fee': 4.0,
            'Total Gross Amount (Total Payout)': 116.0
        }
    ]

    validator = StockXValidator()
    
    for i, record in enumerate(test_records):
        print(f"\n=== Test Record {i+1}: {record['Item']} ===")
        print(f"Input Sku Size: {record['Sku Size']} (type: {type(record['Sku Size'])})")
        
        try:
            normalized = await validator.normalize_record(record)
            print(f"SUCCESS Normalized size: '{normalized['size']}'")
            print(f"   Other fields: item='{normalized['item_name']}', order='{normalized['order_number']}'")
        except Exception as e:
            print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_size_parsing())