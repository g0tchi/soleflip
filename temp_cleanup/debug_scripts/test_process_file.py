#!/usr/bin/env python3
"""
Direct test of process_file method
"""
import sys
import os
import asyncio

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domains.integration.services.import_processor import import_processor, SourceType

async def test_process_file():
    """Test process_file directly"""
    
    print("=== TESTING PROCESS_FILE DIRECTLY ===")
    
    try:
        result = await import_processor.process_file(
            file_path="test_debug.csv",
            source_type=SourceType.STOCKX,
            batch_size=1000
        )
        
        print("SUCCESS!")
        print(f"Batch ID: {result.batch_id}")
        print(f"Processed: {result.processed_records}")
        print(f"Status: {result.status}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_process_file())