#!/usr/bin/env python3
"""
Script: Generate Size Master Data with EU Standardization
Purpose: Populate products.sizes table with standardized size data for all regions
Dependencies: Fresh database with consolidated_v1 migration
Estimated Runtime: 10-30 seconds

This script generates comprehensive size data covering:
- US Men's sizes (3.5 - 18, half sizes) → EU standardized
- US Women's sizes (5 - 15, half sizes) → EU standardized
- US Youth sizes (1 - 7, half sizes) → EU standardized
- UK sizes (3 - 16, half sizes) → EU standardized
- EU sizes (35 - 52, half sizes) → direct mapping
- CM sizes (22 - 35, half cm increments) → EU standardized

standardized_value uses EU sizes as the standard for cross-region matching.
Example: US 9 = UK 8 = EU 42.5 (all have standardized_value = 42.5)
"""

import asyncio
import asyncpg
import os
from datetime import datetime
from typing import List, Tuple
from decimal import Decimal

# Database connection from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip"
)


def us_mens_to_eu(us_size: float) -> float:
    """Convert US men's size to EU size."""
    # US men's sizing: US + 33 = EU
    # US 9 -> EU 42
    return us_size + 33


def us_womens_to_eu(us_size: float) -> float:
    """Convert US women's size to EU size."""
    # US women's sizing: US + 30.5 = EU
    # US W 7 -> EU 37.5
    return us_size + 30.5


def us_youth_to_eu(us_size: float) -> float:
    """Convert US youth size to EU size."""
    # US youth sizing: US + 32.5 = EU
    # US Y 5 -> EU 37.5
    return us_size + 32.5


def uk_to_eu(uk_size: float) -> float:
    """Convert UK size to EU size."""
    # UK sizing: UK + 33.5 = EU
    # UK 8 -> EU 42.5 (same as US 9)
    return uk_size + 33.5


def cm_to_eu(cm_size: float) -> float:
    """Convert CM to EU size (approximate)."""
    # This is an approximation: CM * 1.5 = EU (roughly)
    # 25cm -> EU 37.5
    # 28cm -> EU 42
    return (cm_size * 1.5)


def generate_us_mens_sizes() -> List[Tuple[str, str, Decimal]]:
    """Generate US men's sizes from 3.5 to 18 (half sizes) with EU standardization."""
    sizes = []
    size = 3.5
    while size <= 18.0:
        value = f"{size:.1f}" if size % 1 != 0 else f"{int(size)}"
        eu_standard = us_mens_to_eu(size)
        sizes.append((value, "US", Decimal(str(eu_standard))))
        size += 0.5
    return sizes


def generate_us_womens_sizes() -> List[Tuple[str, str, Decimal]]:
    """Generate US women's sizes from 5 to 15 (half sizes) with EU standardization."""
    sizes = []
    size = 5.0
    while size <= 15.0:
        value = f"{size:.1f}W" if size % 1 != 0 else f"{int(size)}W"
        eu_standard = us_womens_to_eu(size)
        sizes.append((value, "US", Decimal(str(eu_standard))))
        size += 0.5
    return sizes


def generate_us_youth_sizes() -> List[Tuple[str, str, Decimal]]:
    """Generate US youth sizes from 1 to 7 (half sizes) with EU standardization."""
    sizes = []
    size = 1.0
    while size <= 7.0:
        value = f"{size:.1f}Y" if size % 1 != 0 else f"{int(size)}Y"
        eu_standard = us_youth_to_eu(size)
        sizes.append((value, "US", Decimal(str(eu_standard))))
        size += 0.5
    return sizes


def generate_uk_sizes() -> List[Tuple[str, str, Decimal]]:
    """Generate UK sizes from 3 to 16 (half sizes) with EU standardization."""
    sizes = []
    size = 3.0
    while size <= 16.0:
        value = f"{size:.1f}" if size % 1 != 0 else f"{int(size)}"
        eu_standard = uk_to_eu(size)
        sizes.append((value, "UK", Decimal(str(eu_standard))))
        size += 0.5
    return sizes


def generate_eu_sizes() -> List[Tuple[str, str, Decimal]]:
    """Generate EU sizes from 35 to 52 (half sizes) - direct mapping."""
    sizes = []
    size = 35.0
    while size <= 52.0:
        value = f"{size:.1f}" if size % 1 != 0 else f"{int(size)}"
        # EU sizes standardize to themselves
        sizes.append((value, "EU", Decimal(str(size))))
        size += 0.5
    return sizes


def generate_cm_sizes() -> List[Tuple[str, str, Decimal]]:
    """Generate CM sizes from 22 to 35 (half cm increments) with EU standardization."""
    sizes = []
    size = 22.0
    while size <= 35.0:
        value = f"{size:.1f}"
        eu_standard = cm_to_eu(size)
        sizes.append((value, "CM", Decimal(str(eu_standard))))
        size += 0.5
    return sizes


async def check_existing_sizes(conn: asyncpg.Connection) -> int:
    """Check if sizes already exist in database."""
    count = await conn.fetchval("SELECT COUNT(*) FROM products.sizes")
    return count


async def insert_sizes(conn: asyncpg.Connection, sizes: List[Tuple[str, str, Decimal]]) -> int:
    """Insert sizes into database using batch insert."""
    query = """
        INSERT INTO products.sizes (id, value, region, standardized_value)
        VALUES (gen_random_uuid(), $1, $2, $3)
    """

    await conn.executemany(query, sizes)
    return len(sizes)


async def validate_sizes(conn: asyncpg.Connection):
    """Validate inserted size data."""
    print("\n=== VALIDATION RESULTS ===\n")

    # Count by region
    region_counts = await conn.fetch("""
        SELECT
            region,
            COUNT(*) as total,
            COUNT(standardized_value) as with_standard,
            MIN(standardized_value) as min_eu,
            MAX(standardized_value) as max_eu
        FROM products.sizes
        GROUP BY region
        ORDER BY region
    """)

    print("Sizes by Region:")
    total_sizes = 0
    for row in region_counts:
        print(f"  {row['region']:3s}: {row['total']:4d} sizes "
              f"(EU range: {float(row['min_eu']):.1f} - {float(row['max_eu']):.1f})")
        total_sizes += row['total']

    print(f"\nTotal sizes: {total_sizes}")

    # Check standardization coverage
    missing_standard = await conn.fetchval("""
        SELECT COUNT(*) FROM products.sizes WHERE standardized_value IS NULL
    """)

    if missing_standard > 0:
        print(f"\nWARNING: {missing_standard} sizes missing standardized_value!")
    else:
        print("\nAll sizes have standardized_value (EU-based)")

    # Check for duplicates
    duplicates = await conn.fetch("""
        SELECT value, region, COUNT(*) as count
        FROM products.sizes
        GROUP BY value, region
        HAVING COUNT(*) > 1
    """)

    if duplicates:
        print(f"\nWARNING: Found {len(duplicates)} duplicate size entries:")
        for dup in duplicates[:5]:  # Show first 5
            print(f"  - {dup['value']} ({dup['region']}): {dup['count']} entries")
    else:
        print("\nNo duplicate sizes found")

    # Sample cross-region matching
    print("\nSample Cross-Region Matching (same standardized_value):")

    # Example: US 9 should match UK 8 and EU 42.5
    us_9_standard = await conn.fetchval("""
        SELECT standardized_value FROM products.sizes
        WHERE region = 'US' AND value = '9'
    """)

    if us_9_standard:
        matches = await conn.fetch("""
            SELECT value, region
            FROM products.sizes
            WHERE standardized_value = $1
            ORDER BY region, value
            LIMIT 10
        """, us_9_standard)

        print(f"  US 9 (EU {float(us_9_standard):.1f}) matches:")
        for m in matches:
            print(f"    - {m['region']} {m['value']}")


async def main():
    """Main execution function."""
    print("=" * 80)
    print("SIZE MASTER DATA GENERATION - EU STANDARDIZATION")
    print("=" * 80)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Connect to database
    print("\nConnecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Check if sizes already exist
        existing_count = await check_existing_sizes(conn)
        if existing_count > 0:
            print(f"\nWARNING: {existing_count} sizes already exist in database!")
            response = input("Do you want to delete existing sizes and regenerate? (yes/no): ")
            if response.lower() == "yes":
                print("Deleting existing sizes...")
                await conn.execute("TRUNCATE products.sizes CASCADE")
                print("Existing sizes deleted.")
            else:
                print("Aborted. No changes made.")
                return

        # Generate all size data
        print("\nGenerating size data with EU standardization...")
        all_sizes = []

        print("  - US Men's sizes (3.5 - 18)...")
        all_sizes.extend(generate_us_mens_sizes())

        print("  - US Women's sizes (5 - 15)...")
        all_sizes.extend(generate_us_womens_sizes())

        print("  - US Youth sizes (1 - 7)...")
        all_sizes.extend(generate_us_youth_sizes())

        print("  - UK sizes (3 - 16)...")
        all_sizes.extend(generate_uk_sizes())

        print("  - EU sizes (35 - 52)...")
        all_sizes.extend(generate_eu_sizes())

        print("  - CM sizes (22 - 35)...")
        all_sizes.extend(generate_cm_sizes())

        print(f"\nGenerated {len(all_sizes)} size entries")

        # Insert sizes
        print("\nInserting sizes into database...")
        async with conn.transaction():
            inserted = await insert_sizes(conn, all_sizes)
            print(f"Inserted {inserted} size records")

        # Validate
        await validate_sizes(conn)

        print("\n" + "=" * 80)
        print("SIZE GENERATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nAll sizes now have EU-based standardized_value for cross-region matching.")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await conn.close()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
