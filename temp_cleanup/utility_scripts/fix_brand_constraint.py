#!/usr/bin/env python3
"""
Fix brand_id constraint in database
"""
import sys
import os
import asyncio

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database.connection import db_manager
from sqlalchemy import text

async def fix_constraint():
    """Fix brand_id constraint"""
    
    await db_manager.initialize()
    
    async with db_manager.get_session() as db:
        try:
            print("Removing NOT NULL constraint from brand_id...")
            await db.execute(text("ALTER TABLE products.products ALTER COLUMN brand_id DROP NOT NULL"))
            await db.commit()
            print("SUCCESS: Constraint removed successfully!")
            
        except Exception as e:
            print(f"Error: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(fix_constraint())