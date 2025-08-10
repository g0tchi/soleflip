#!/usr/bin/env python3
"""
Test the product extraction from import data
"""
import sys
import os
import asyncio

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domains.products.services.product_processor import ProductProcessor
from shared.database.connection import db_manager
from sqlalchemy import text

async def test_product_extraction():
    """Test extracting products from existing import data"""
    
    # Initialize database
    await db_manager.initialize()
    
    print("=== TESTING PRODUCT EXTRACTION ===\n")
    
    # Get latest batch ID
    async with db_manager.get_session() as db:
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
    
    # Create processor and extract products
    processor = ProductProcessor()
    
    print("Extracting product candidates...")
    candidates = await processor.extract_products_from_batch(batch_id)
    
    print(f"Found {len(candidates)} unique products:\n")
    
    # Show top 10 products
    for i, candidate in enumerate(candidates[:10]):
        print(f"{i+1:2}. {candidate.name}")
        print(f"    Brand: {candidate.brand_name or 'Unknown'}")
        print(f"    Category: {candidate.category_name}")
        print(f"    Sizes: {', '.join(candidate.sizes[:5])}{'...' if len(candidate.sizes) > 5 else ''}")
        print(f"    Sales: {candidate.sales_count}, Avg Price: €{candidate.avg_price:.2f}")
        print()
    
    if len(candidates) > 10:
        print(f"... and {len(candidates) - 10} more products\n")
    
    # Create products in database
    print("Creating products in database...")
    stats = await processor.create_products_from_candidates(candidates)
    
    print("=== RESULTS ===")
    print(f"Brands created: {stats['brands_created']}")
    print(f"Categories created: {stats['categories_created']}")
    print(f"Products created: {stats['products_created']}")
    print(f"Products updated: {stats['products_updated']}")
    
    if stats['errors']:
        print(f"Errors: {len(stats['errors'])}")
        for error in stats['errors'][:3]:
            print(f"  - {error}")
        if len(stats['errors']) > 3:
            print(f"  ... and {len(stats['errors']) - 3} more errors")

if __name__ == "__main__":
    asyncio.run(test_product_extraction())