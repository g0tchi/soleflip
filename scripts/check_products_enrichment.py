"""
Check products.products table structure and enrichment_data field
"""

import asyncio
import json
from sqlalchemy import text
from shared.database.connection import get_db_session


async def main():
    async with get_db_session() as session:
        print("=" * 80)
        print("PRODUCTS TABLE STRUCTURE & ENRICHMENT DATA")
        print("=" * 80)

        # 1. Check table structure
        print("\n[1/3] Checking products.products table structure...")
        result = await session.execute(
            text(
                """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'products' AND table_name = 'products'
            ORDER BY ordinal_position
        """
            )
        )

        columns = result.fetchall()
        print(f"\nFound {len(columns)} columns:")
        for col in columns:
            nullable = "NULL" if col.is_nullable == "YES" else "NOT NULL"
            print(f"  {col.column_name:30s} {col.data_type:20s} {nullable}")

        # 2. Check if enrichment_data exists and has data
        print("\n[2/3] Checking enrichment_data field...")
        result = await session.execute(
            text(
                """
            SELECT
                COUNT(*) as total_products,
                COUNT(enrichment_data) as products_with_enrichment,
                COUNT(ean) as products_with_ean
            FROM products.products
        """
            )
        )
        stats = result.fetchone()

        print(f"\nTotal products: {stats.total_products:,}")
        print(f"Products with enrichment_data: {stats.products_with_enrichment:,}")
        if "products_with_ean" in stats._fields:
            print(f"Products with ean field: {stats.products_with_ean:,}")

        # 3. Sample enrichment_data
        if stats.products_with_enrichment > 0:
            print("\n[3/3] Sample enrichment_data content (first 5 products)...")
            result = await session.execute(
                text(
                    """
                SELECT
                    id,
                    name,
                    sku,
                    enrichment_data
                FROM products.products
                WHERE enrichment_data IS NOT NULL
                LIMIT 5
            """
                )
            )

            for i, row in enumerate(result.fetchall(), 1):
                print(f"\n--- Product {i}: {row.name[:50]} ---")
                print(f"ID: {row.id}")
                print(f"SKU: {row.sku}")
                if row.enrichment_data:
                    # Pretty print JSON
                    enrichment = row.enrichment_data
                    if isinstance(enrichment, str):
                        enrichment = json.loads(enrichment)
                    print(f"Enrichment Data Keys: {list(enrichment.keys())}")

                    # Check for EAN-related fields
                    ean_fields = ["ean", "gtin", "upc", "barcode", "gtins"]
                    found_eans = {}
                    for field in ean_fields:
                        if field in enrichment:
                            found_eans[field] = enrichment[field]

                    if found_eans:
                        print(f"EAN/GTIN Fields Found: {json.dumps(found_eans, indent=2)}")
                    else:
                        print("No EAN/GTIN fields found")
                        print(f"Full data: {json.dumps(enrichment, indent=2)[:500]}...")
        else:
            print("\n[3/3] No products with enrichment_data found")

        # 4. Check for EAN in main table
        print("\n" + "=" * 80)
        print("CHECKING FOR EAN IN MAIN TABLE")
        print("=" * 80)

        try:
            result = await session.execute(
                text(
                    """
                SELECT
                    id,
                    name,
                    sku,
                    ean
                FROM products.products
                WHERE ean IS NOT NULL
                LIMIT 5
            """
                )
            )

            ean_products = result.fetchall()
            if ean_products:
                print(f"\nFound {len(ean_products)} products with EAN in main table:")
                for p in ean_products:
                    print(f"  {p.name[:40]:40s} | EAN: {p.ean}")
            else:
                print("\nNo products with EAN in main table column")
        except Exception as e:
            print(f"\nNo 'ean' column in main table: {e}")

        # 5. Check Awin EAN overlap potential
        print("\n" + "=" * 80)
        print("POTENTIAL MATCHING STRATEGIES")
        print("=" * 80)

        # Get sample Awin EANs
        result = await session.execute(
            text(
                """
            SELECT ean, product_name, brand_name, size
            FROM integration.awin_products
            WHERE ean IS NOT NULL
            LIMIT 5
        """
            )
        )

        awin_samples = result.fetchall()
        print("\nSample Awin EANs:")
        for a in awin_samples:
            print(f"  {a.ean} | {a.brand_name} {a.product_name[:30]} | Size {a.size}")


if __name__ == "__main__":
    asyncio.run(main())
