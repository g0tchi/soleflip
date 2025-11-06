"""
Quick check of Awin import results
"""

import asyncio
from sqlalchemy import text
from shared.database.connection import db_manager


async def main():
    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # Get stats
        result = await session.execute(
            text(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT brand_name) as brands,
                    COUNT(CASE WHEN in_stock = true THEN 1 END) as in_stock,
                    AVG(retail_price_cents) / 100.0 as avg_price,
                    MIN(retail_price_cents) / 100.0 as min_price,
                    MAX(retail_price_cents) / 100.0 as max_price
                FROM integration.awin_products
            """
            )
        )
        stats = result.fetchone()

        print("=" * 80)
        print("AWIN IMPORT RESULTS")
        print("=" * 80)
        print(f"Total Products: {stats[0]}")
        print(f"Unique Brands: {stats[1]}")
        print(f"In Stock: {stats[2]}")
        print(f"Avg Price: EUR {stats[3]:.2f}")
        print(f"Price Range: EUR {stats[4]:.2f} - EUR {stats[5]:.2f}")

        # Sample products
        print("\n" + "=" * 80)
        print("SAMPLE PRODUCTS (Top 10 by price)")
        print("=" * 80)

        result = await session.execute(
            text(
                """
                SELECT product_name, brand_name, size, retail_price_cents / 100.0 as price,
                       in_stock, colour
                FROM integration.awin_products
                ORDER BY retail_price_cents DESC
                LIMIT 10
            """
            )
        )

        for i, row in enumerate(result, 1):
            stock = "[IN STOCK]" if row[4] else "[OUT]"
            print(
                f"{i}. EUR {row[3]:6.2f} {stock} | {row[0][:50]:50s} | {row[1]:15s} | Size {row[2]}"
            )

        print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
