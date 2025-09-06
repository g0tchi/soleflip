#!/usr/bin/env python3
"""
Test script to check StockX API response structure
"""

import asyncio
import structlog
from shared.database.connection import db_manager
from domains.integration.services.stockx_service import StockXService

logger = structlog.get_logger(__name__)

async def test_stockx_api():
    """Test the StockX API to see what data it returns"""
    
    await db_manager.initialize()
    
    async with db_manager.get_session() as session:
        stockx_service = StockXService(session)
        
        try:
            print("Testing StockX API connection...")
            
            # Test get all listings
            print("Fetching StockX listings...")
            listings = await stockx_service.get_all_listings(limit=5)
            
            print(f"Found {len(listings)} listings")
            
            if listings:
                print("\nSample listing structure:")
                for i, listing in enumerate(listings[:2]):
                    print(f"\n--- Listing {i+1} ---")
                    print(f"Keys available: {list(listing.keys())}")
                    
                    # Check product info
                    product = listing.get("product", {})
                    variant = listing.get("variant", {})
                    
                    print(f"Product keys: {list(product.keys()) if product else 'None'}")
                    print(f"Variant keys: {list(variant.keys()) if variant else 'None'}")
                    
                    # Check the actual values
                    print(f"Product name possibilities:")
                    print(f"  - product.productName: {product.get('productName')}")
                    print(f"  - product.name: {product.get('name')}")
                    print(f"  - variant.product.name: {variant.get('product', {}).get('name')}")
                    
                    print(f"Size possibilities:")
                    print(f"  - variant.size: {variant.get('size')}")
                    print(f"  - variant.variantValue: {variant.get('variantValue')}")
                    print(f"  - variant.sizeValue: {variant.get('sizeValue')}")
                    
                    print(f"Price info:")
                    print(f"  - amount: {listing.get('amount')}")
                    print(f"  - status: {listing.get('status')}")
                    print(f"  - currencyCode: {listing.get('currencyCode')}")
                    
            else:
                print("No listings found - this could mean:")
                print("   - No active listings on StockX")
                print("   - API credentials issue")
                print("   - API endpoint issue")
                
        except Exception as e:
            print(f"StockX API test failed: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_stockx_api())