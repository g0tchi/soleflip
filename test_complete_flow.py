#!/usr/bin/env python3
"""
Test the complete validation flow as it happens in ImportProcessor
"""
import sys
import os
import asyncio

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domains.integration.services.validators import StockXValidator

async def test_complete_flow():
    # Test record exactly as it comes from mapped_df.to_dict('records')
    test_record = {
        'Item': 'Test Shoe', 
        'Sku Size': 10.5, 
        'Order Number': 12345, 
        'Sale Date': '2022-07-08 00:46:09 +00', 
        'Listing Price': 100, 
        'Seller Fee': 3.0, 
        'Total Gross Amount (Total Payout)': 90.0
    }

    print("Testing complete validation flow...")
    print(f"Test record: {test_record}")

    validator = StockXValidator()

    # Test batch validation like in ImportProcessor
    try:
        validation_result = await validator.validate_batch([test_record])
        print(f"\nBatch validation result:")
        print(f"  is_valid: {validation_result.is_valid}")
        print(f"  errors: {validation_result.errors}")
        print(f"  warnings: {validation_result.warnings}")
        print(f"  normalized_data count: {len(validation_result.normalized_data)}")
        
        if validation_result.normalized_data:
            normalized = validation_result.normalized_data[0]
            print(f"  sale_date in normalized: {normalized.get('sale_date')}")
            
    except Exception as e:
        print(f"BATCH VALIDATION FAILED: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_complete_flow())