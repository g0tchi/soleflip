"""
Quick script to find StockX-Awin profit opportunities
Checks if we already have matching data in the database
"""

import asyncio

from sqlalchemy import text

from shared.database.connection import db_manager


async def main():
    await db_manager.initialize()

    async with db_manager.get_session() as session:
        print("=" * 80)
        print("CHECKING DATABASE FOR STOCKX-AWIN MATCHING CAPABILITY")
        print("=" * 80)

        # 1. Check for products table
        print("\n[1/4] Checking for StockX products table...")
        result = await session.execute(
            text(
                """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name = 'products'
            ORDER BY table_schema
        """
            )
        )
        products_tables = result.fetchall()

        if not products_tables:
            print("  [!] No 'products' table found")
            print("  -> Need to import StockX data first")
            return

        print(f"  [OK] Found {len(products_tables)} products table(s):")
        for t in products_tables:
            print(f"      - {t.table_schema}.{t.table_name}")

        # Use first products table
        schema = products_tables[0].table_schema
        print(f"\n  Using: {schema}.products")

        # 2. Check table structure
        print("\n[2/4] Checking products table structure...")
        result = await session.execute(
            text(
                """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = 'products'
            AND column_name IN ('id', 'ean', 'name', 'lowest_ask', 'highest_bid', 'price')
            ORDER BY column_name
        """
            ),
            {"schema": schema},
        )

        columns = {row.column_name: row.data_type for row in result.fetchall()}

        has_ean = "ean" in columns
        has_price = "lowest_ask" in columns or "price" in columns
        price_col = "lowest_ask" if "lowest_ask" in columns else "price"

        print(f"  EAN column: {'✓' if has_ean else '✗'}")
        print(f"  Price column: {'✓ (' + price_col + ')' if has_price else '✗'}")

        if not (has_ean and has_price):
            print("\n  [!] Missing required columns for matching")
            return

        # 3. Check data availability
        print("\n[3/4] Checking data availability...")
        result = await session.execute(
            text(
                f"""
            SELECT
                COUNT(*) as total_products,
                COUNT(ean) as products_with_ean,
                COUNT({price_col}) as products_with_price
            FROM {schema}.products
        """
            )
        )
        stats = result.fetchone()

        print(f"  Total StockX products: {stats.total_products:,}")
        print(f"  With EAN: {stats.products_with_ean:,}")
        print(f"  With price: {stats.products_with_price:,}")

        # 4. Try to find matches
        print("\n[4/4] Searching for Awin <-> StockX matches...")
        result = await session.execute(
            text(
                f"""
            SELECT
                COUNT(DISTINCT ap.awin_product_id) as awin_count,
                COUNT(DISTINCT p.id) as stockx_count,
                COUNT(DISTINCT ap.ean) as matching_eans
            FROM integration.awin_products ap
            INNER JOIN {schema}.products p ON ap.ean = p.ean
            WHERE ap.ean IS NOT NULL AND ap.ean != ''
              AND p.{price_col} IS NOT NULL
        """
            )
        )
        match_stats = result.fetchone()

        print(f"  Awin products matched: {match_stats.awin_count:,}")
        print(f"  StockX products matched: {match_stats.stockx_count:,}")
        print(f"  Unique EAN matches: {match_stats.matching_eans:,}")

        if match_stats.awin_count == 0:
            print("\n  [!] NO MATCHES FOUND")
            print("  This means:")
            print("    - Either StockX products don't have EAN codes")
            print("    - Or Awin/StockX EANs don't overlap")
            print("\n  SOLUTION: Need to enrich StockX data with EANs from catalog API")
            return

        # 5. Show profit opportunities!
        print("\n" + "=" * 80)
        print("PROFIT OPPORTUNITIES (Money Printer!)")
        print("=" * 80)

        result = await session.execute(
            text(
                f"""
            SELECT
                ap.product_name,
                ap.brand_name,
                ap.size,
                ap.ean,
                ap.retail_price_cents / 100.0 as retail_price_eur,
                p.{price_col} / 100.0 as stockx_price_eur,
                (p.{price_col} - ap.retail_price_cents) / 100.0 as profit_eur,
                ROUND(((p.{price_col} - ap.retail_price_cents)::numeric /
                       NULLIF(ap.retail_price_cents, 0)::numeric * 100), 1) as profit_pct,
                ap.stock_quantity,
                ap.affiliate_link
            FROM integration.awin_products ap
            INNER JOIN {schema}.products p ON ap.ean = p.ean
            WHERE ap.ean IS NOT NULL
              AND ap.in_stock = true
              AND p.{price_col} IS NOT NULL
              AND (p.{price_col} - ap.retail_price_cents) >= 2000  -- Min 20 EUR profit
            ORDER BY profit_eur DESC
            LIMIT 20
        """
            )
        )

        opportunities = result.fetchall()

        if not opportunities:
            print("\n  [!] No profitable opportunities found (min 20 EUR profit)")
            print("  Try lowering the profit threshold or check if prices are up-to-date")
        else:
            print(f"\n  Found {len(opportunities)} opportunities with 20+ EUR profit!\n")
            total_profit = 0

            for i, opp in enumerate(opportunities, 1):
                print(f"{i:2d}. {opp.product_name[:50]}")
                print(
                    f"    Brand: {opp.brand_name} | Size: {opp.size} | Stock: {opp.stock_quantity}"
                )
                print(
                    f"    Retail: EUR {opp.retail_price_eur:.2f} -> StockX: EUR {opp.stockx_price_eur:.2f}"
                )
                print(f"    PROFIT: EUR {opp.profit_eur:.2f} ({opp.profit_pct}% ROI)")
                print(f"    Link: {opp.affiliate_link}")
                print()
                total_profit += opp.profit_eur

            print("=" * 80)
            print(f"Total potential profit (top 20): EUR {total_profit:.2f}")
            print("=" * 80)
            print("\nNOTE: Factor in:")
            print("  - Awin commission (5-15%)")
            print("  - StockX seller fees (~10%)")
            print("  - Shipping costs")
            print("  - Authentication fees")


if __name__ == "__main__":
    asyncio.run(main())
