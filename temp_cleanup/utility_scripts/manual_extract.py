#!/usr/bin/env python3
"""
Manually test product extraction on latest batch
"""
import sys
import os
import asyncio

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domains.products.services.product_processor import ProductProcessor
from shared.database.connection import db_manager
from sqlalchemy import text

async def manual_extract():
    """Manually run product extraction on latest batch"""
    
    await db_manager.initialize()
    
    async with db_manager.get_session() as db:
        # Get latest batch ID
        result = await db.execute(text(
            "SELECT id FROM integration.import_batches ORDER BY created_at DESC LIMIT 1"
        ))
        batch = result.fetchone()
        
        if not batch:
            print("No batches found!")
            return
            
        batch_id = str(batch[0])
        print(f"Testing product extraction on batch: {batch_id}")
        
        processor = ProductProcessor()
        
        try:
            # Extract product candidates
            candidates = await processor.extract_products_from_batch(batch_id)
            print(f"Found {len(candidates)} product candidates:")
            
            for candidate in candidates:
                print(f"  - {candidate.name}")
                print(f"    SKU: {candidate.sku}")
                print(f"    Brand: {candidate.brand_name}")
                print(f"    Category: {candidate.category_name}")
                print()
            
            if candidates:
                # Create products
                print("Creating products...")
                stats = await processor.create_products_from_candidates(candidates)
                print("Results:", stats)
            else:
                print("No candidates to create products from")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(manual_extract())