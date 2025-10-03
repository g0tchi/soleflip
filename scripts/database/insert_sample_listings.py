#!/usr/bin/env python3
"""
Insert Sample StockX Listings Data
Using the 39 listings data we successfully retrieved earlier
"""

import asyncio
import json
import uuid
from datetime import datetime
import asyncpg
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
# Fix asyncpg URL format
if DATABASE_URL and "postgresql+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg", "postgresql")

# Sample listings data from the successful API call
SAMPLE_LISTINGS = [
    {
        "listingId": "f05e13da-2317-4889-93e8-7caef0ae1d25",
        "amount": "110",
        "productName": "Nike Go FlyEase Triple Black (Women's)",
        "size": "12W",
        "status": "ACTIVE",
        "currencyCode": "EUR",
        "createdAt": "2025-09-28T09:53:20.174Z",
        "updatedAt": "2025-09-28T09:53:20.174Z",
        "expires": "2025-10-28T10:53:18.000Z"
    },
    {
        "listingId": "84693195-caab-402f-854a-20900653e43a",
        "amount": "99",
        "productName": "Nike Go FlyEase Pale Ivory (Women's)",
        "size": "12W",
        "status": "ACTIVE",
        "currencyCode": "EUR",
        "createdAt": "2025-09-28T09:50:29.182Z",
        "updatedAt": "2025-09-28T09:50:29.182Z",
        "expires": "2025-10-28T10:50:27.000Z"
    },
    {
        "listingId": "fd58a956-3c7f-413b-96de-d313a5f7b276",
        "amount": "99",
        "productName": "Nike Air Presto Triple Black Shiny Toe",
        "size": "14",
        "status": "ACTIVE",
        "currencyCode": "EUR",
        "createdAt": "2025-09-28T09:27:42.077Z",
        "updatedAt": "2025-09-28T09:27:42.077Z",
        "expires": "2025-10-28T10:27:39.000Z"
    },
    {
        "listingId": "31963a5a-d422-4810-8591-8926b9f65aa1",
        "amount": "113",
        "productName": "ASICS UB10-S Gel-Kayano 20 Kiko Kostadinov Plum Beet Juice",
        "size": "11",
        "status": "ACTIVE",
        "currencyCode": "EUR",
        "createdAt": "2025-09-21T16:08:36.379Z",
        "updatedAt": "2025-09-27T08:39:28.986Z",
        "expires": "2025-10-21T16:08:34.000Z"
    },
    {
        "listingId": "db3c8fbe-05d5-4229-b332-387b1566667b",
        "amount": "114",
        "productName": "Jordan 12 Retro Low Golf Cherry",
        "size": "10.5",
        "status": "ACTIVE",
        "currencyCode": "EUR",
        "createdAt": "2025-09-19T04:02:59.395Z",
        "updatedAt": "2025-09-27T08:27:40.434Z",
        "expires": "2025-10-19T04:02:56.000Z"
    },
    {
        "listingId": "ca9c4133-534f-458a-be9a-c84a9529f5c4",
        "amount": "124",
        "productName": "Merrell Agility Peak 5 Trek Black",
        "size": "9.5",
        "status": "ACTIVE",
        "currencyCode": "EUR",
        "createdAt": "2025-09-17T05:52:36.021Z",
        "updatedAt": "2025-09-27T08:23:40.945Z",
        "expires": "2025-10-17T05:52:34.000Z"
    },
    {
        "listingId": "d6510297-0c0d-44dd-be3d-3fc2ea02297f",
        "amount": "385",
        "productName": "Balenciaga Mallorca Sandal Black Crocodile Embossed",
        "size": "43",
        "status": "ACTIVE",
        "currencyCode": "EUR",
        "createdAt": "2025-08-24T14:59:36.509Z",
        "updatedAt": "2025-09-27T09:14:36.925Z",
        "expires": "2025-11-12T04:25:10.000Z"
    },
    {
        "listingId": "551c0c1c-9d24-43ac-9044-c524a921e65c",
        "amount": "238",
        "productName": "OFF-WHITE New Low Vulcanized Black White",
        "size": "40",
        "status": "ACTIVE",
        "currencyCode": "EUR",
        "createdAt": "2025-08-24T16:11:40.299Z",
        "updatedAt": "2025-09-27T08:45:21.158Z",
        "expires": "2025-11-12T04:25:10.000Z"
    },
    {
        "listingId": "4c82b763-e66f-415d-ab92-7ab338431b4d",
        "amount": "220",
        "productName": "Nike Devin Booker Repel Jacket Multicolor",
        "size": "XL",
        "status": "ACTIVE",
        "currencyCode": "EUR",
        "createdAt": "2025-08-26T11:31:46.862Z",
        "updatedAt": "2025-09-16T10:53:51.012Z",
        "expires": "2025-11-12T04:25:10.000Z"
    },
    {
        "listingId": "7bc6a5c6-1caf-4b71-b640-d1a5e0c2cbbe",
        "amount": "184",
        "productName": "Gucci x adidas Lycra Sweatpants Blue",
        "size": "S",
        "status": "ACTIVE",
        "currencyCode": "EUR",
        "createdAt": "2025-09-02T17:45:05.934Z",
        "updatedAt": "2025-09-27T06:09:04.657Z",
        "expires": "2025-11-12T04:25:10.000Z"
    }
]

async def insert_sample_listings():
    """Insert sample StockX listings to database for testing"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Clear existing listings
        await conn.execute("DELETE FROM products.listings WHERE stockx_listing_id IS NOT NULL")
        print("[CLEAR] Cleared existing StockX listings from database")

        # Insert sample listings
        inserted_count = 0
        for listing in SAMPLE_LISTINGS:
            try:
                # Parse dates
                created_at = datetime.fromisoformat(listing["createdAt"].replace("Z", "+00:00"))
                updated_at = datetime.fromisoformat(listing["updatedAt"].replace("Z", "+00:00"))
                expires_at = datetime.fromisoformat(listing["expires"].replace("Z", "+00:00"))

                # Insert listing
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
                    None,  # inventory_item_id (we'll link later)
                    listing["listingId"],  # stockx_listing_id
                    listing["status"],  # status
                    float(listing["amount"]),  # amount
                    listing["currencyCode"],  # currency_code
                    "STANDARD",  # inventory_type
                    expires_at,  # expires_at
                    created_at,  # stockx_created_at
                    updated_at,  # last_stockx_updated_at
                    json.dumps(listing),  # raw_data
                    datetime.now(),  # created_at
                    datetime.now()  # updated_at
                )

                inserted_count += 1
                print(f"[OK] Inserted: {listing['productName']} - EUR {listing['amount']}")

            except Exception as e:
                print(f"[ERROR] Error inserting listing {listing['listingId']}: {e}")
                continue

        print(f"\n[SUCCESS] Successfully inserted {inserted_count}/{len(SAMPLE_LISTINGS)} sample StockX listings!")

        # Verify the data
        count_result = await conn.fetchrow("SELECT COUNT(*) as count FROM products.listings")
        print(f"[VERIFY] Total listings in database: {count_result['count']}")

    except Exception as e:
        print(f"Database error: {e}")
    finally:
        await conn.close()

async def main():
    """Main function"""
    print("[START] Inserting sample StockX listings...")
    await insert_sample_listings()
    print("[COMPLETE] Sample data insertion complete!")

if __name__ == "__main__":
    asyncio.run(main())