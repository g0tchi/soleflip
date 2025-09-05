#!/usr/bin/env python3
"""
Create performance indexes for dashboard queries
"""

import asyncio
import sys
from sqlalchemy import text

from shared.database.connection import get_db_session

async def create_performance_indexes():
    """Create indexes to optimize dashboard query performance"""
    
    # Initialize database connection
    from shared.database.connection import DatabaseManager
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    indexes = [
        # Sales transactions indexes
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_sale_price_date 
        ON sales.transactions(sale_price, transaction_date DESC) 
        WHERE sale_price IS NOT NULL
        """,
        
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_inventory_id 
        ON sales.transactions(inventory_id) 
        WHERE sale_price IS NOT NULL
        """,
        
        # Inventory indexes
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_status 
        ON products.inventory(status)
        """,
        
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_product_id 
        ON products.inventory(product_id)
        """,
        
        # Products indexes
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_brand_id 
        ON products.products(brand_id)
        """,
        
        # Composite index for JOIN optimization
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_joins 
        ON sales.transactions(inventory_id, sale_price, transaction_date DESC) 
        WHERE sale_price IS NOT NULL
        """
    ]
    
    session = await anext(get_db_session())
    try:
        print("Creating performance indexes...")
        
        for i, index_sql in enumerate(indexes, 1):
            try:
                print(f"Creating index {i}/{len(indexes)}...")
                await session.execute(text(index_sql))
                await session.commit()
                print(f"✓ Index {i} created successfully")
            except Exception as e:
                print(f"⚠ Index {i} failed (might already exist): {e}")
                await session.rollback()
        
        print("All indexes processed successfully!")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(create_performance_indexes())