#!/usr/bin/env python3
"""
Test the validator directly to debug date parsing
"""
import sys
import os
import asyncio

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domains.integration.services.validators import StockXValidator

async def test_validator():
    # Test record with the problematic date format
    test_record = {
        'Order Number': '12345',
        'Sale Date': '2022-07-08 00:46:09 +00',
        'Item': 'Test Shoe',
        'Listing Price': '100'
    }

    print("Testing StockX Validator directly...")
    print(f"Test record: {test_record}")

    validator = StockXValidator()

    try:
        # Test the normalization directly
        result = await validator.normalize_record(test_record)
        print(f"SUCCESS: {result}")
        print(f"Sale date: {result.get('sale_date')}")
        print(f"Sale date type: {type(result.get('sale_date'))}")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

    print("\n=== Testing base normalize_date method directly ===")
    try:
        date_result = validator.normalize_date(
            '2022-07-08 00:46:09 +00',
            ['%Y-%m-%d %H:%M:%S %z', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%m/%d/%Y']
        )
        print(f"Date parsing SUCCESS: {date_result}")
    except Exception as e:
        print(f"Date parsing FAILED: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_validator())