"""
Check StockX product data availability for Awin matching
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import db_manager


async def main():
    await db_manager.initialize()

    async with db_manager.get_session() as session:
        print("=" * 80)
        print("STOCKX DATA AVAILABILITY CHECK")
        print("=" * 80)

        # Check if core.products table exists
        try:
            result = await session.execute(
                text("""
                    SELECT table_name, table_schema
                    FROM information_schema.tables
                    WHERE table_name = 'products'
                      AND table_schema IN ('core', 'public')
                """)
            )
            tables = result.fetchall()

            if not tables:
                print("\n[WARNING] No 'products' table found in 'core' or 'public' schema")
                print("Cannot perform StockX matching without product data")
                return

            print("\n[OK] Found products table(s):")
            for table in tables:
                print(f"    {table[1]}.{table[0]}")

            schema = tables[0][1]
            print(f"\nUsing schema: {schema}")

            # Check table structure
            print("\n" + "=" * 80)
            print("PRODUCTS TABLE STRUCTURE")
            print("=" * 80)

            result = await session.execute(
                text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = :schema
                      AND table_name = 'products'
                    ORDER BY ordinal_position
                """),
                {"schema": schema}
            )

            columns = result.fetchall()
            print(f"\nTotal columns: {len(columns)}")
            print("\nKey columns for matching:")

            key_columns = ['id', 'ean', 'style_code', 'name', 'brand',
                          'lowest_ask', 'highest_bid', 'last_sale']
            for col in columns:
                if col[0] in key_columns:
                    nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                    print(f"  {col[0]:20s} {col[1]:20s} {nullable}")

            # Check for EAN data
            print("\n" + "=" * 80)
            print("EAN DATA AVAILABILITY")
            print("=" * 80)

            result = await session.execute(
                text(f"""
                    SELECT
                        COUNT(*) as total_products,
                        COUNT(ean) as products_with_ean,
                        COUNT(CASE WHEN ean IS NOT NULL AND ean != '' THEN 1 END) as valid_eans
                    FROM {schema}.products
                """)
            )
            stats = result.fetchone()

            print(f"\nTotal Products: {stats[0]:,}")
            print(f"With EAN field: {stats[1]:,}")
            print(f"Valid EANs: {stats[2]:,}")

            if stats[2] > 0:
                ean_percentage = (stats[2] / stats[0]) * 100
                print(f"EAN Coverage: {ean_percentage:.1f}%")

            # Check for price data
            print("\n" + "=" * 80)
            print("STOCKX PRICE DATA")
            print("=" * 80)

            price_columns = ['lowest_ask', 'highest_bid', 'last_sale']
            for price_col in price_columns:
                try:
                    result = await session.execute(
                        text(f"""
                            SELECT
                                COUNT(CASE WHEN {price_col} IS NOT NULL THEN 1 END) as count,
                                AVG({price_col}) / 100.0 as avg_price,
                                MIN({price_col}) / 100.0 as min_price,
                                MAX({price_col}) / 100.0 as max_price
                            FROM {schema}.products
                        """)
                    )
                    data = result.fetchone()

                    print(f"\n{price_col}:")
                    print(f"  Products with data: {data[0]:,}")
                    if data[0] > 0:
                        print(f"  Average: EUR {data[1]:.2f}")
                        print(f"  Range: EUR {data[2]:.2f} - EUR {data[3]:.2f}")
                except Exception as e:
                    print(f"\n{price_col}: Column not found or error - {e}")

            # Sample products with EAN
            print("\n" + "=" * 80)
            print("SAMPLE PRODUCTS WITH EAN (First 10)")
            print("=" * 80)

            result = await session.execute(
                text(f"""
                    SELECT name, brand, ean, style_code,
                           lowest_ask / 100.0 as price_eur
                    FROM {schema}.products
                    WHERE ean IS NOT NULL AND ean != ''
                    LIMIT 10
                """)
            )

            for i, row in enumerate(result, 1):
                print(f"{i:2d}. {row[0][:40]:40s} | {row[1]:10s} | EAN: {row[2]} | EUR {row[4]:.2f}")

            # Potential matches with Awin
            print("\n" + "=" * 80)
            print("POTENTIAL AWIN <-> STOCKX MATCHES")
            print("=" * 80)

            result = await session.execute(
                text(f"""
                    SELECT
                        COUNT(DISTINCT ap.awin_product_id) as awin_products,
                        COUNT(DISTINCT p.id) as matching_stockx_products,
                        COUNT(DISTINCT ap.ean) as matching_eans
                    FROM integration.awin_products ap
                    INNER JOIN {schema}.products p ON ap.ean = p.ean
                    WHERE ap.ean IS NOT NULL
                      AND ap.ean != ''
                """)
            )
            match_stats = result.fetchone()

            print(f"\nAwin products with valid EAN: {match_stats[0]:,}")
            print(f"Matching StockX products: {match_stats[1]:,}")
            print(f"Unique matching EANs: {match_stats[2]:,}")

            if match_stats[0] > 0:
                print(f"\n[SUCCESS] Found {match_stats[0]} potential matches!")
                print("Ready to calculate profit opportunities")
            else:
                print("\n[WARNING] No EAN matches found between Awin and StockX")
                print("Need to import more StockX data or verify EAN quality")

        except Exception as e:
            print(f"\n[ERROR] Database check failed: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
