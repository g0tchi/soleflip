#!/usr/bin/env python3
"""
Add avg_resale_price column to products table and migrate existing data
"""
import sys
import os
import asyncio

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database.connection import db_manager
from sqlalchemy import text

async def add_avg_resale_price_column():
    """Add avg_resale_price column and migrate existing retail_price data"""
    
    await db_manager.initialize()
    
    async with db_manager.get_session() as db:
        try:
            print("Adding avg_resale_price column to products table...")
            
            # Add the new column
            await db.execute(text("""
                ALTER TABLE products.products 
                ADD COLUMN IF NOT EXISTS avg_resale_price NUMERIC(10,2)
            """))
            
            print("Migrating existing retail_price data to avg_resale_price...")
            
            # Migrate existing data: retail_price → avg_resale_price
            await db.execute(text("""
                UPDATE products.products 
                SET avg_resale_price = retail_price 
                WHERE retail_price IS NOT NULL AND avg_resale_price IS NULL
            """))
            
            print("Clearing retail_price column (to be filled with real UVP later)...")
            
            # Clear retail_price column for future real UVP data
            await db.execute(text("""
                UPDATE products.products 
                SET retail_price = NULL
            """))
            
            await db.commit()
            
            # Show results
            result = await db.execute(text("""
                SELECT 
                    COUNT(*) as total_products,
                    COUNT(avg_resale_price) as with_resale_price,
                    COUNT(retail_price) as with_retail_price
                FROM products.products
            """))
            
            stats = result.fetchone()
            print(f"\n✅ SUCCESS!")
            print(f"Total products: {stats.total_products}")
            print(f"Products with avg_resale_price: {stats.with_resale_price}")
            print(f"Products with retail_price: {stats.with_retail_price}")
            
            # Show sample products
            result = await db.execute(text("""
                SELECT sku, name, retail_price, avg_resale_price
                FROM products.products 
                WHERE avg_resale_price IS NOT NULL
                ORDER BY avg_resale_price DESC
                LIMIT 3
            """))
            
            products = result.fetchall()
            print(f"\nSample products:")
            for product in products:
                print(f"  - {product.sku}: {product.name[:50]}...")
                print(f"    Retail Price: {product.retail_price} | Avg Resale Price: €{product.avg_resale_price}")
            
        except Exception as e:
            print(f"Error: {e}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(add_avg_resale_price_column())