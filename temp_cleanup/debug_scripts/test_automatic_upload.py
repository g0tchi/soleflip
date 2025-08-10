#!/usr/bin/env python3
"""
Test automatic product creation during upload
"""
import sys
import os
import asyncio

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domains.integration.services.import_processor import import_processor

async def test_automatic_upload():
    """Test the complete upload pipeline with automatic product creation"""
    
    print("=== TESTING AUTOMATIC PRODUCT CREATION ===\n")
    
    # Use the test CSV file
    csv_file = "test_size_upload.csv"
    
    if not os.path.exists(csv_file):
        print(f"Test file {csv_file} not found!")
        return
    
    print(f"Processing file: {csv_file}")
    
    # Process the file - this should now automatically create products
    result = await import_processor.process_file(csv_file)
    
    print("\n=== UPLOAD RESULTS ===")
    print(f"Batch ID: {result.batch_id}")
    print(f"Source Type: {result.source_type}")
    print(f"Total Records: {result.total_records}")
    print(f"Processed Records: {result.processed_records}")
    print(f"Error Records: {result.error_records}")
    print(f"Status: {result.status}")
    print(f"Processing Time: {result.processing_time_ms}ms")
    
    if result.validation_errors:
        print(f"\nValidation Errors: {len(result.validation_errors)}")
        for error in result.validation_errors[:3]:
            print(f"  - {error}")
    
    print("\n✅ Products should now be automatically created!")

if __name__ == "__main__":
    asyncio.run(test_automatic_upload())