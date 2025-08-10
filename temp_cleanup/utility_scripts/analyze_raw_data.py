#!/usr/bin/env python3
"""
Analyze raw import data to see original CSV structure
"""
import sys
import os
import asyncio
import json

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database.connection import db_manager
from sqlalchemy import text

async def analyze_raw_data():
    """Analyze the raw imported data structure"""
    
    # Initialize database connection
    await db_manager.initialize()
    
    print("=== ANALYZING RAW IMPORT DATA ===\n")
    
    async with db_manager.get_session() as db:
        # Get latest batch ID
        batch_query = text(
            "SELECT id, source_type, total_records FROM integration.import_batches "
            "ORDER BY created_at DESC LIMIT 1"
        )
        result = await db.execute(batch_query)
        batch = result.fetchone()
        
        if not batch:
            print("No import batches found!")
            return
            
        batch_id = str(batch[0])
        print(f"Using batch: {batch_id} ({batch[1]}, {batch[2]} records)\n")
    
        # Get sample raw records
        records = await db.execute(text(
            "SELECT source_data FROM integration.import_records "
            "WHERE batch_id = :batch_id LIMIT 3"
        ), {"batch_id": batch_id})
        record_results = records.fetchall()
        
        print("Sample Raw Import Records:") 
        for i, record in enumerate(record_results):
            data = record[0]  # JSONB data
            print(f"\n  Raw Record {i+1}:")
            print(f"    Available fields: {list(data.keys())}")
            print(f"    Item: {data.get('Item', 'N/A')}")
            if 'SKU' in data:
                print(f"    SKU: {data.get('SKU', 'N/A')}")
            if 'Style' in data:
                print(f"    Style: {data.get('Style', 'N/A')}")
            print(f"    Order Number: {data.get('Order Number', 'N/A')}")
            
        print(f"\nAnalysis complete.")

if __name__ == "__main__":
    asyncio.run(analyze_raw_data())