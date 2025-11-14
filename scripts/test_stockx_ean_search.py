"""
Test StockX Catalog API search by EAN
Take a sample EAN from Awin and search StockX
"""

import asyncio

from sqlalchemy import text

from shared.database.connection import get_db_session


async def main():
    # Get sample Awin products with EAN
    async with get_db_session() as session:
        result = await session.execute(
            text(
                """
            SELECT product_name, brand_name, ean, retail_price_cents / 100.0 as price_eur
            FROM integration.awin_products
            WHERE ean IS NOT NULL AND in_stock = true
            ORDER BY retail_price_cents ASC
            LIMIT 5
        """
            )
        )

        print("Sample Awin Products with EAN:")
        print("=" * 80)

        samples = []
        for row in result.fetchall():
            samples.append(
                {
                    "name": row.product_name,
                    "brand": row.brand_name,
                    "ean": row.ean,
                    "price": row.price_eur,
                }
            )
            print(f"{row.product_name[:50]:50s} | EAN: {row.ean} | EUR {row.price_eur:.2f}")

        if samples:
            test_ean = samples[0]["ean"]
            print(f"\n{'='*80}")
            print(f"Testing StockX Catalog API with EAN: {test_ean}")
            print(f"{'='*80}\n")

            # Now test StockX Catalog API
            from domains.integration.services.stockx_service import StockXService

            stockx_service = StockXService(session)

            # Search by EAN/GTIN
            print(f"Searching StockX for GTIN: {test_ean}...")
            search_results = await stockx_service.search_stockx_catalog(
                query=test_ean, page=1, page_size=5
            )

            if search_results and search_results.get("products"):
                print(f"\n[SUCCESS] Found {len(search_results['products'])} matches on StockX!")
                print("\nMatches:")
                for i, product in enumerate(search_results["products"], 1):
                    print(f"\n{i}. {product.get('title', 'N/A')}")
                    print(f"   Brand: {product.get('brand', 'N/A')}")
                    print(f"   StockX ID: {product.get('id', 'N/A')}")
                    print(f"   Retail Price: ${product.get('retailPrice', 'N/A')}")
                    print(f"   Style ID: {product.get('styleId', 'N/A')}")

                print(f"\n{'='*80}")
                print("MONEY PRINTER READY!")
                print("We can match Awin products to StockX via EAN!")
                print(f"{'='*80}")
            else:
                print("\n[NO MATCH] Product not found on StockX")
                print("This could mean:")
                print("  - Product not available on StockX")
                print("  - EAN not indexed in StockX catalog")
                print("  - Try searching by brand + product name instead")


if __name__ == "__main__":
    asyncio.run(main())
