#!/usr/bin/env python3
"""
Analyze imported data to understand what we have for product extraction
"""
import sys
import os
import asyncio
import json

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database.connection import db_manager
from shared.database.models import ImportRecord, ImportBatch
from sqlalchemy import text

async def analyze_import_data():
    """Analyze the imported data structure"""
    
    # Initialize database connection
    await db_manager.initialize()
    
    print("=== ANALYZING IMPORT DATA ===\n")
    
    async with db_manager.get_session() as db:
        # Get recent batches
        print("Recent Import Batches:")
        batches = await db.execute(text(
            "SELECT id, source_type, total_records, processed_records, created_at "
            "FROM integration.import_batches ORDER BY created_at DESC LIMIT 5"
        ))
        batch_results = batches.fetchall()
        
        for batch in batch_results:
            print(f"  - {batch[0]}: {batch[1]} ({batch[2]} records) - {batch[4]}")
        
        if not batch_results:
            print("  No import batches found!")
            return
            
        # Get latest batch ID
        latest_batch_id = batch_results[0][0]
        print(f"\nAnalyzing latest batch: {latest_batch_id}\n")
        
        # Get sample records from latest batch
        records = await db.execute(text(
            "SELECT processed_data FROM integration.import_records "
            "WHERE batch_id = :batch_id LIMIT 10"
        ), {"batch_id": latest_batch_id})
        record_results = records.fetchall()
        
        print("Sample Import Records:")
        for i, record in enumerate(record_results[:3]):
            data = record[0]  # JSONB data
            print(f"\n  Record {i+1}:")
            print(f"    Product: {data.get('product_name', 'N/A')}")
            print(f"    Size: {data.get('size', 'N/A')}")
            print(f"    Order: {data.get('order_number', 'N/A')}")
            print(f"    Price: {data.get('listing_price', 'N/A')}")
            print(f"    Sale Date: {data.get('sale_date', 'N/A')}")
            
        # Analyze unique products
        unique_products = await db.execute(text(
            "SELECT DISTINCT processed_data->>'product_name' as product_name, "
            "       COUNT(*) as sales_count "
            "FROM integration.import_records "
            "WHERE batch_id = :batch_id "
            "GROUP BY processed_data->>'product_name' "
            "ORDER BY sales_count DESC "
            "LIMIT 10"
        ), {"batch_id": latest_batch_id})
        product_results = unique_products.fetchall()
        
        print(f"\nTop Products (by sales volume):")
        for product in product_results:
            print(f"  - {product[0]}: {product[1]} sales")
            
        # Analyze size distribution
        sizes = await db.execute(text(
            "SELECT processed_data->>'size' as size, COUNT(*) as count "
            "FROM integration.import_records "
            "WHERE batch_id = :batch_id "
            "GROUP BY processed_data->>'size' "
            "ORDER BY count DESC "
            "LIMIT 10"
        ), {"batch_id": latest_batch_id})
        size_results = sizes.fetchall()
        
        print(f"\nSize Distribution:")
        for size in size_results:
            print(f"  - {size[0]}: {size[1]} items")
            
        print(f"\nAnalysis complete. Found {len(record_results)} records to process.")

if __name__ == "__main__":
    asyncio.run(analyze_import_data())