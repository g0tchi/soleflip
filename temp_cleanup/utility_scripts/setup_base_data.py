#!/usr/bin/env python3
"""
Setup base data for brands and categories
"""
import sys
import os
import asyncio

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database.connection import db_manager
from shared.database.models import Brand, Category
from sqlalchemy import text

async def setup_base_data():
    """Setup basic brands and categories"""
    
    await db_manager.initialize()
    
    print("=== SETTING UP BASE DATA ===\n")
    
    async with db_manager.get_session() as db:
        # Extended brands from reference data
        brands = {
            # Nike Family
            'Nike': 'nike',
            'Jordan': 'jordan',
            'Converse': 'converse',
            
            # Adidas Family
            'Adidas': 'adidas',
            'Yeezy': 'yeezy',
            
            # Luxury Brands
            'Balenciaga': 'balenciaga',
            'Gucci': 'gucci',
            'Louis Vuitton': 'louis-vuitton',
            'Dior': 'dior',
            'Prada': 'prada',
            
            # Streetwear
            'Off-White': 'off-white',
            'Supreme': 'supreme',
            'Stone Island': 'stone-island',
            'A Bathing Ape': 'bape',
            
            # Other Popular Brands
            'New Balance': 'new-balance',
            'Asics': 'asics',
            'Vans': 'vans',
            'Puma': 'puma',
            'Reebok': 'reebok',
            'Under Armour': 'under-armour',
            
            # Luxury Sneaker Brands
            'Golden Goose': 'golden-goose',
            'Common Projects': 'common-projects',
            'Maison Margiela': 'maison-margiela',
            
            # European Brands
            'Birkenstock': 'birkenstock',
            'Hugo Boss': 'hugo-boss'
        }
        
        print("Creating brands...")
        for name, slug in brands.items():
            # Check if exists
            existing = await db.execute(text("SELECT id FROM core.brands WHERE name = :name"), {"name": name})
            if existing.fetchone():
                print(f"  - {name} (exists)")
                continue
                
            brand = Brand(name=name, slug=slug)
            db.add(brand)
            print(f"  - {name} (created)")
        
        await db.commit()
        
        # Enhanced categories from reference data
        categories = {
            'Footwear': 'footwear',
            'Apparel': 'apparel', 
            'Accessories': 'accessories',
            'Collectibles': 'collectibles',
            'Books': 'books',
            'Other': 'other'
        }
        
        print("\nCreating categories...")
        for name, slug in categories.items():
            # Check if exists
            existing = await db.execute(text("SELECT id FROM core.categories WHERE name = :name"), {"name": name})
            if existing.fetchone():
                print(f"  - {name} (exists)")
                continue
                
            category = Category(name=name, slug=slug, path=f"/{slug}")
            db.add(category)
            print(f"  - {name} (created)")
        
        await db.commit()
        
        print("\n=== BASE DATA SETUP COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(setup_base_data())