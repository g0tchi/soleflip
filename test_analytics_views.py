"""
Test all migrated analytics views
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import DatabaseManager

ALL_MIGRATED_VIEWS = [
    # Low complexity
    'daily_revenue', 'daily_sales', 'data_quality_check', 'executive_dashboard',
    'monthly_revenue', 'platform_performance', 'recent_transactions',
    'sales_by_country', 'sales_by_weekday', 'top_products', 'top_products_revenue',
    # Medium complexity
    'brand_monthly_performance', 'revenue_growth', 'brand_market_position',
    # High complexity
    'brand_deep_dive_overview', 'nike_product_breakdown',
    # Additional
    'brand_collaboration_performance'
]


async def test_views():
    db = DatabaseManager()
    await db.initialize()

    print("=" * 80)
    print("TESTING ALL MIGRATED ANALYTICS VIEWS")
    print("=" * 80)
    print(f"Total views to test: {len(ALL_MIGRATED_VIEWS)}\n")

    async with db.get_session() as session:
        success_count = 0
        error_count = 0
        results = []

        for idx, view_name in enumerate(ALL_MIGRATED_VIEWS, 1):
            try:
                print(f"[{idx}/{len(ALL_MIGRATED_VIEWS)}] Testing {view_name}...")

                # Test view exists and is queryable
                result = await session.execute(text(f"SELECT COUNT(*) FROM analytics.{view_name}"))
                row_count = result.fetchone()[0]

                # Get column count
                result = await session.execute(text(f"""
                    SELECT COUNT(*) FROM information_schema.columns
                    WHERE table_schema = 'analytics' AND table_name = '{view_name}'
                """))
                col_count = result.fetchone()[0]

                success_count += 1
                results.append({
                    'view': view_name,
                    'rows': row_count,
                    'columns': col_count,
                    'status': 'OK'
                })
                print(f"    OK: {row_count} rows, {col_count} columns")

            except Exception as e:
                error_count += 1
                results.append({
                    'view': view_name,
                    'rows': 0,
                    'columns': 0,
                    'status': f'ERROR: {str(e)[:100]}'
                })
                print(f"    ERROR: {str(e)[:100]}")

        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print(f"{'='*80}")
        print(f"  Total views: {len(ALL_MIGRATED_VIEWS)}")
        print(f"  Successful: {success_count}")
        print(f"  Errors: {error_count}")

        if success_count == len(ALL_MIGRATED_VIEWS):
            print(f"\n[OK] ALL {len(ALL_MIGRATED_VIEWS)} views are working!")

        print(f"\n{'='*80}")
        print("VIEW DETAILS")
        print(f"{'='*80}")
        for result in results:
            print(f"{result['view']:30} | {result['rows']:6} rows | {result['columns']:2} cols | {result['status']}")

        # Check for remaining dependencies on transactions.transactions
        print(f"\n{'='*80}")
        print("CHECKING FOR REMAINING DEPENDENCIES")
        print(f"{'='*80}")

        result = await session.execute(text("""
            SELECT
                schemaname,
                viewname
            FROM pg_views
            WHERE definition LIKE '%transactions.transactions%'
              AND schemaname NOT IN ('pg_catalog', 'information_schema')
        """))

        remaining = list(result)
        if remaining:
            print(f"\n[!] {len(remaining)} views still use transactions.transactions:")
            for view in remaining:
                print(f"  - {view.schemaname}.{view.viewname}")
        else:
            print("\n[OK] NO views depend on transactions.transactions anymore!")

        # Check foreign key constraints
        result = await session.execute(text("""
            SELECT
                tc.table_schema,
                tc.table_name,
                tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
            WHERE ccu.table_name = 'transactions' AND ccu.table_schema = 'transactions'
              AND tc.constraint_type = 'FOREIGN KEY'
        """))

        fks = list(result)
        if fks:
            print(f"\n[!] {len(fks)} foreign keys still reference transactions.transactions:")
            for fk in fks:
                print(f"  - {fk.table_schema}.{fk.table_name} ({fk.constraint_name})")
        else:
            print("\n[OK] NO foreign keys reference transactions.transactions!")

    await db.close()


if __name__ == "__main__":
    asyncio.run(test_views())
