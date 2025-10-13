"""
Import Awin sample feed and test matching
"""
import asyncio
from domains.integration.services.awin_feed_service import AwinFeedImportService
from shared.database.connection import db_manager


async def main():
    print("=" * 80)
    print("AWIN SAMPLE FEED IMPORT")
    print("=" * 80)

    await db_manager.initialize()

    async with db_manager.get_session() as session:
        service = AwinFeedImportService(session)

        # Parse existing sample feed
        sample_feed_path = "C:/nth_dev/soleflip/context/integrations/awin_feed_sample.csv.gz"

        print(f"\n[*] Parsing sample feed: {sample_feed_path}")
        products = await service.parse_feed(sample_feed_path)

        print(f"\n[*] Importing {len(products)} products...")
        imported_count = await service.import_products(products)

        print(f"\n[*] Matching products by EAN...")
        matched_count = await service.match_products_by_ean()

        print(f"\n[*] Getting import statistics...")
        stats = await service.get_import_stats()

        print("\n" + "=" * 80)
        print("IMPORT SUMMARY")
        print("=" * 80)
        print(f"Imported: {imported_count} products")
        print(f"Matched by EAN: {matched_count} products")
        print(f"\nDatabase Statistics:")
        print(f"  Total Products: {stats['total_products']}")
        print(f"  Unique Brands: {stats['total_brands']}")
        print(f"  Merchants: {stats['total_merchants']}")
        print(f"  In Stock: {stats['in_stock_count']}")
        print(f"  Matched to StockX: {stats['matched_count']}")
        print(f"  Average Price: EUR {stats['avg_price_eur']:.2f}")
        print(f"  Price Range: EUR {stats['min_price_eur']:.2f} - {stats['max_price_eur']:.2f}")

        # Show sample products
        print("\n" + "=" * 80)
        print("SAMPLE PRODUCTS (First 10)")
        print("=" * 80)

        result = await session.execute(
            """
            SELECT product_name, brand_name, size, retail_price_cents / 100.0 as price,
                   in_stock, matched_product_id IS NOT NULL as matched
            FROM integration.awin_products
            ORDER BY retail_price_cents DESC
            LIMIT 10
            """
        )

        for i, row in enumerate(result, 1):
            match_status = "[MATCHED]" if row[5] else "[UNMATCHED]"
            stock_status = "[IN STOCK]" if row[4] else "[OUT OF STOCK]"
            print(f"{i}. {row[0][:50]:50s} | {row[1]:15s} | Size {row[2]:5s} | EUR {row[3]:6.2f} | {stock_status} {match_status}")

        # Find profit opportunities (if any matched)
        if matched_count > 0:
            print("\n" + "=" * 80)
            print("PROFIT OPPORTUNITIES")
            print("=" * 80)

            opportunities = await service.find_profit_opportunities(
                min_profit_cents=1000,  # Min 10 EUR profit
                in_stock_only=True,
                limit=10
            )

            if opportunities:
                for i, opp in enumerate(opportunities, 1):
                    print(f"\n{i}. {opp['product_name']}")
                    print(f"   Brand: {opp['brand_name']} | Size: {opp['size']} | Color: {opp['colour']}")
                    print(f"   Retail: EUR {opp['retail_price_eur']:.2f}")
                    print(f"   StockX: EUR {opp['stockx_price_eur']:.2f}")
                    print(f"   Profit: EUR {opp['profit_eur']:.2f}")
                    print(f"   Stock: {opp['stock_quantity']} available")
                    print(f"   Link: {opp['affiliate_link'][:80]}...")
            else:
                print("[INFO] No profit opportunities found with current thresholds")

        print("\n" + "=" * 80)
        print("[OK] IMPORT COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
