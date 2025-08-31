import asyncio

import asyncpg


async def check_database_integrity():
    conn = await asyncpg.connect(
        "postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip"
    )

    print("=== DATABASE INTEGRITY CHECK NACH BRAND EXTENSIONS ===\n")

    # Check all schemas and tables
    tables_query = """
        SELECT table_schema, table_name, 
               (SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_schema = t.table_schema AND table_name = t.table_name) as column_count
        FROM information_schema.tables t
        WHERE table_schema IN ('core', 'sales', 'integration', 'analytics')
        ORDER BY table_schema, table_name
    """

    tables = await conn.fetch(tables_query)

    current_schema = None
    total_records = 0

    for table in tables:
        schema = table["table_schema"]
        name = table["table_name"]
        col_count = table["column_count"]

        if schema != current_schema:
            print(f"\n{schema.upper()} SCHEMA:")
            current_schema = schema

        try:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {schema}.{name}")
            total_records += count
            print(f"  {schema}.{name}: {count} records ({col_count} columns)")

        except Exception as e:
            print(f"  {schema}.{name}: ERROR - {str(e)[:60]}")

    print(f"\nTOTAL DATABASE RECORDS: {total_records}")

    # Check brand data specifically
    print("\n=== BRAND DATA ANALYSIS ===")

    # Original brands vs enriched brands
    original_brands = await conn.fetchval(
        "SELECT COUNT(*) FROM core.brands WHERE founder_name IS NULL"
    )
    enriched_brands = await conn.fetchval(
        "SELECT COUNT(*) FROM core.brands WHERE founder_name IS NOT NULL"
    )

    print(f"Original brands (unchanged): {original_brands}")
    print(f"Enriched brands (with deep dive data): {enriched_brands}")

    # Show some examples
    print("\nBEISPIELE ORIGINALER BRANDS (unverändert):")
    original_examples = await conn.fetch(
        "SELECT name, category, segment FROM core.brands WHERE founder_name IS NULL LIMIT 5"
    )
    for brand in original_examples:
        print(f'  {brand["name"]} - {brand["category"]} - {brand["segment"]}')

    print("\nBEISPIELE ERWEITERTER BRANDS:")
    enriched_examples = await conn.fetch(
        "SELECT name, founder_name, headquarters_city FROM core.brands WHERE founder_name IS NOT NULL LIMIT 5"
    )
    for brand in enriched_examples:
        print(
            f'  {brand["name"]} - Gegründet von: {brand["founder_name"]} in {brand["headquarters_city"]}'
        )

    # Check if any existing relationships are broken
    print("\n=== DATENINTEGRITÄT CHECK ===")

    # Check for any potential foreign key issues
    try:
        orphaned_check_queries = [
            (
                "brand_history -> brands",
                "SELECT COUNT(*) FROM core.brand_history WHERE brand_id NOT IN (SELECT id FROM core.brands)",
            ),
            (
                "brand_attributes -> brands",
                "SELECT COUNT(*) FROM core.brand_attributes WHERE brand_id NOT IN (SELECT id FROM core.brands)",
            ),
            (
                "brand_financials -> brands",
                "SELECT COUNT(*) FROM core.brand_financials WHERE brand_id NOT IN (SELECT id FROM core.brands)",
            ),
        ]

        for check_name, query in orphaned_check_queries:
            orphaned = await conn.fetchval(query)
            status = "OK" if orphaned == 0 else f"WARNING: {orphaned} orphaned"
            print(f"  {check_name}: {status}")

    except Exception as e:
        print(f"  Integrity check error: {e}")

    # Summary of new capabilities
    print("\n=== NEUE BRAND INTELLIGENCE FUNKTIONEN ===")
    new_tables_info = [
        ("core.brand_history", "Marken-Timeline mit historischen Events"),
        ("core.brand_collaborations", "Kollaborationen und Partnerschaften"),
        ("core.brand_attributes", "Persönlichkeit und Eigenschaften"),
        ("core.brand_relationships", "Parent-Company und Ownership-Struktur"),
        ("core.brand_financials", "Finanz-Performance über mehrere Jahre"),
        ("analytics.brand_encyclopedia", "Komplette Brand-Profile (View)"),
        ("analytics.brand_timeline", "Chronologische History (View)"),
        ("analytics.brand_collaboration_network", "Partnership-Analyse (View)"),
        ("analytics.brand_cultural_impact", "Cultural Impact Scoring (View)"),
    ]

    for table_name, description in new_tables_info:
        try:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            print(f"  OK {table_name}: {count} Datensaetze - {description}")
        except:
            print(f"  MISSING {table_name}: Nicht verfuegbar - {description}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(check_database_integrity())
