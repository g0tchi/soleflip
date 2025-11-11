#!/usr/bin/env python3
"""
Sync StockX Listings from API to Database
Fetches live StockX listings and stores them in products.listings table
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List

import aiohttp
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
API_BASE_URL = "http://localhost:8000"


async def fetch_stockx_listings() -> List[Dict]:
    """Fetch current StockX listings from API"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/api/v1/inventory/stockx-listings") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {}).get("listings", [])
                else:
                    print(f"API Error: {response.status}")
                    return []
        except Exception as e:
            print(f"Error fetching StockX listings: {e}")
            return []


async def sync_listings_to_db(listings: List[Dict]) -> None:
    """Sync StockX listings to database"""
    if not listings:
        print("No listings to sync")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Clear existing listings to avoid duplicates
        await conn.execute("DELETE FROM products.listings WHERE stockx_listing_id IS NOT NULL")
        print("Cleared existing StockX listings from database")

        # Insert new listings
        inserted_count = 0
        for listing in listings:
            try:
                # Extract data from StockX API response
                stockx_listing_id = listing.get("listingId")
                amount = listing.get("amount")
                currency_code = listing.get("currencyCode", "EUR")
                status = listing.get("status", "ACTIVE")
                inventory_type = listing.get("inventoryType", "STANDARD")

                # Parse dates
                created_at = None
                updated_at = None
                expires_at = None

                if listing.get("createdAt"):
                    created_at = datetime.fromisoformat(listing["createdAt"].replace("Z", "+00:00"))
                if listing.get("updatedAt"):
                    updated_at = datetime.fromisoformat(listing["updatedAt"].replace("Z", "+00:00"))
                if listing.get("ask", {}).get("askExpiresAt"):
                    expires_at = datetime.fromisoformat(
                        listing["ask"]["askExpiresAt"].replace("Z", "+00:00")
                    )

                # Try to find matching inventory item by product name and size
                inventory_item_id = None
                product_name = listing.get("productName")
                size = listing.get("size")

                if product_name:
                    # Look for matching inventory item
                    query = """
                    SELECT i.id
                    FROM products.inventory i
                    LEFT JOIN products.products p ON i.product_id = p.id
                    LEFT JOIN core.sizes s ON i.size_id = s.id
                    WHERE p.name ILIKE $1
                    AND (s.value = $2 OR $2 IS NULL)
                    LIMIT 1
                    """
                    result = await conn.fetchrow(query, f"%{product_name}%", size)
                    if result:
                        inventory_item_id = result["id"]

                # Insert listing into database
                insert_query = """
                INSERT INTO products.listings (
                    id,
                    inventory_item_id,
                    stockx_listing_id,
                    status,
                    amount,
                    currency_code,
                    inventory_type,
                    expires_at,
                    stockx_created_at,
                    last_stockx_updated_at,
                    raw_data,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """

                await conn.execute(
                    insert_query,
                    uuid.uuid4(),  # id
                    inventory_item_id,  # inventory_item_id
                    stockx_listing_id,  # stockx_listing_id
                    status,  # status
                    float(amount) if amount else None,  # amount
                    currency_code,  # currency_code
                    inventory_type,  # inventory_type
                    expires_at,  # expires_at
                    created_at,  # stockx_created_at
                    updated_at,  # last_stockx_updated_at
                    json.dumps(listing),  # raw_data
                    datetime.now(),  # created_at
                    datetime.now(),  # updated_at
                )

                inserted_count += 1
                print(f"[OK] Inserted listing: {product_name} - EUR {amount}")

            except Exception as e:
                print(f"[ERROR] Error inserting listing {listing.get('listingId', 'unknown')}: {e}")
                continue

        print(
            f"\n[SUCCESS] Successfully synced {inserted_count}/{len(listings)} StockX listings to database!"
        )

    except Exception as e:
        print(f"Database error: {e}")
    finally:
        await conn.close()


async def main():
    """Main sync function"""
    print("[START] Starting StockX Listings Sync...")
    print("[FETCH] Fetching listings from StockX API...")

    listings = await fetch_stockx_listings()

    if listings:
        print(f"[FOUND] Found {len(listings)} active StockX listings")
        print("[SYNC] Syncing to database...")
        await sync_listings_to_db(listings)
    else:
        print("[ERROR] No listings found or API error")

    print("[COMPLETE] Sync complete!")


if __name__ == "__main__":
    asyncio.run(main())
