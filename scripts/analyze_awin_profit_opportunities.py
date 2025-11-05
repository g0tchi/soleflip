"""
Analyze Awin Profit Opportunities
Find the best retail products for potential resale
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import db_manager


async def main():
    await db_manager.initialize()

    async with db_manager.get_session() as session:
        print("=" * 100)
        print("AWIN PROFIT OPPORTUNITY ANALYSIS")
        print("=" * 100)

        # 1. Most Affordable Products (Best for Quick Flip)
        print("\n" + "=" * 100)
        print("1. CHEAPEST IN-STOCK PRODUCTS (Quick Flip Potential)")
        print("=" * 100)
        print("These are the most affordable products currently in stock - ideal for low-risk flips\n")

        result = await session.execute(
            text("""
                SELECT
                    product_name,
                    brand_name,
                    colour,
                    size,
                    retail_price_cents / 100.0 as price_eur,
                    stock_quantity,
                    ean,
                    affiliate_link
                FROM integration.awin_products
                WHERE in_stock = true
                  AND retail_price_cents IS NOT NULL
                ORDER BY retail_price_cents ASC
                LIMIT 15
            """)
        )

        for i, row in enumerate(result, 1):
            print(f"{i:2d}. EUR {row[4]:6.2f} | {row[0][:45]:45s} | {row[1]:10s} | Size {row[3]:5s} | Stock: {row[5]:2d}")
            print(f"    Color: {row[2]} | EAN: {row[6]}")
            print(f"    Link: {row[7][:90]}...")
            print()

        # 2. Popular Models with Good Stock
        print("\n" + "=" * 100)
        print("2. POPULAR MODELS WITH HIGH AVAILABILITY")
        print("=" * 100)
        print("Models with multiple sizes in stock - easier to find buyers\n")

        result = await session.execute(
            text("""
                SELECT
                    product_name,
                    brand_name,
                    COUNT(DISTINCT size) as size_count,
                    SUM(stock_quantity) as total_stock,
                    MIN(retail_price_cents) / 100.0 as min_price,
                    MAX(retail_price_cents) / 100.0 as max_price,
                    AVG(retail_price_cents) / 100.0 as avg_price
                FROM integration.awin_products
                WHERE in_stock = true
                GROUP BY product_name, brand_name
                HAVING COUNT(DISTINCT size) >= 3
                ORDER BY size_count DESC, total_stock DESC
                LIMIT 10
            """)
        )

        for i, row in enumerate(result, 1):
            print(f"{i:2d}. {row[0][:50]:50s} | {row[1]:10s}")
            print(f"    Sizes Available: {row[2]} | Total Stock: {row[3]}")
            print(f"    Price Range: EUR {row[4]:.2f} - EUR {row[5]:.2f} (Avg: EUR {row[6]:.2f})")
            print()

        # 3. Brand Breakdown
        print("\n" + "=" * 100)
        print("3. BRAND ANALYSIS")
        print("=" * 100)

        result = await session.execute(
            text("""
                SELECT
                    brand_name,
                    COUNT(*) as total_products,
                    COUNT(CASE WHEN in_stock = true THEN 1 END) as in_stock_count,
                    MIN(retail_price_cents) / 100.0 as min_price,
                    MAX(retail_price_cents) / 100.0 as max_price,
                    AVG(retail_price_cents) / 100.0 as avg_price
                FROM integration.awin_products
                WHERE brand_name IS NOT NULL
                GROUP BY brand_name
                ORDER BY total_products DESC
            """)
        )

        for row in result:
            stock_pct = (row[2] / row[1] * 100) if row[1] > 0 else 0
            print(f"{row[0]:15s} | Products: {row[1]:4d} | In Stock: {row[2]:4d} ({stock_pct:5.1f}%) | EUR {row[3]:.2f} - {row[4]:.2f} (Avg: EUR {row[5]:.2f})")

        # 4. Size Distribution Analysis
        print("\n" + "=" * 100)
        print("4. SIZE DISTRIBUTION (In-Stock Products)")
        print("=" * 100)
        print("Identify which sizes have the most availability\n")

        result = await session.execute(
            text("""
                SELECT
                    size,
                    COUNT(*) as product_count,
                    AVG(retail_price_cents) / 100.0 as avg_price,
                    MIN(retail_price_cents) / 100.0 as min_price,
                    MAX(retail_price_cents) / 100.0 as max_price
                FROM integration.awin_products
                WHERE in_stock = true
                  AND size IS NOT NULL
                  AND size != ''
                GROUP BY size
                ORDER BY
                    CASE
                        WHEN size ~ '^[0-9]+\\.?[0-9]*$' THEN CAST(size AS NUMERIC)
                        ELSE 999
                    END
            """)
        )

        for row in result:
            bar = "#" * int(row[1] / 5)
            print(f"Size {row[0]:5s} | {row[1]:3d} products {bar:30s} | EUR {row[2]:6.2f} avg ({row[3]:.2f} - {row[4]:.2f})")

        # 5. Best Value Products (Low Price + High Stock)
        print("\n" + "=" * 100)
        print("5. BEST VALUE OPPORTUNITIES")
        print("=" * 100)
        print("Low-priced products with good stock - lowest risk, fastest turnover\n")

        result = await session.execute(
            text("""
                SELECT
                    product_name,
                    brand_name,
                    colour,
                    size,
                    retail_price_cents / 100.0 as price_eur,
                    stock_quantity,
                    affiliate_link
                FROM integration.awin_products
                WHERE in_stock = true
                  AND retail_price_cents < 15000  -- Under EUR 150
                  AND stock_quantity > 3
                ORDER BY retail_price_cents ASC, stock_quantity DESC
                LIMIT 10
            """)
        )

        for i, row in enumerate(result, 1):
            print(f"{i:2d}. EUR {row[4]:6.2f} | Stock: {row[5]:2d} | {row[0][:45]:45s}")
            print(f"    {row[1]} | {row[2]} | Size {row[3]}")
            print(f"    {row[6][:90]}...")
            print()

        # 6. Premium Products (High Price Point)
        print("\n" + "=" * 100)
        print("6. PREMIUM PRODUCTS (Higher Margins)")
        print("=" * 100)
        print("Higher-priced items that might have better resale margins\n")

        result = await session.execute(
            text("""
                SELECT
                    product_name,
                    brand_name,
                    colour,
                    size,
                    retail_price_cents / 100.0 as price_eur,
                    stock_quantity,
                    affiliate_link
                FROM integration.awin_products
                WHERE in_stock = true
                  AND retail_price_cents > 20000  -- Over EUR 200
                ORDER BY retail_price_cents DESC
                LIMIT 10
            """)
        )

        for i, row in enumerate(result, 1):
            print(f"{i:2d}. EUR {row[4]:6.2f} | Stock: {row[5]:2d} | {row[0][:45]:45s}")
            print(f"    {row[1]} | {row[2]} | Size {row[3]}")
            print(f"    {row[6][:90]}...")
            print()

        # 7. Summary Recommendations
        print("\n" + "=" * 100)
        print("7. SUMMARY & RECOMMENDATIONS")
        print("=" * 100)

        # Get overall stats
        result = await session.execute(
            text("""
                SELECT
                    COUNT(*) as total_products,
                    COUNT(CASE WHEN in_stock = true THEN 1 END) as in_stock,
                    COUNT(CASE WHEN in_stock = true AND retail_price_cents < 10000 THEN 1 END) as under_100,
                    COUNT(CASE WHEN in_stock = true AND retail_price_cents BETWEEN 10000 AND 20000 THEN 1 END) as mid_range,
                    COUNT(CASE WHEN in_stock = true AND retail_price_cents > 20000 THEN 1 END) as premium,
                    AVG(CASE WHEN in_stock = true THEN retail_price_cents END) / 100.0 as avg_in_stock_price
                FROM integration.awin_products
            """)
        )
        stats = result.fetchone()

        print("\n[MARKET OVERVIEW]:")
        print(f"   Total Products: {stats[0]:,}")
        print(f"   In Stock: {stats[1]:,} ({stats[1]/stats[0]*100:.1f}%)")
        print(f"   Average Price (in-stock): EUR {stats[5]:.2f}")

        print("\n[PRICE SEGMENTS] (In-Stock Only):")
        print(f"   Budget (< EUR 100):     {stats[2]:,} products - BEST for quick flips")
        print(f"   Mid-Range (EUR 100-200): {stats[3]:,} products - Balanced risk/reward")
        print(f"   Premium (> EUR 200):     {stats[4]:,} products - Higher margins potential")

        print("\n[RECOMMENDED STRATEGY]:")
        print("   1. Start with budget products (< EUR 100) for fast turnover")
        print("   2. Focus on models with 3+ sizes available")
        print("   3. ASICS products dominate the feed - check StockX demand")
        print("   4. Jordan products have strong resale history")
        print("   5. Use EAN codes to match with StockX pricing")

        print("\n" + "=" * 100)
        print("[OK] ANALYSIS COMPLETE")
        print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())
