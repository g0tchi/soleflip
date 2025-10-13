#!/usr/bin/env python3
"""
Script: Generate Size Master Data
Purpose: Populate sizes table with standardized size data for all regions
Dependencies: Fresh database with consolidated_v1 migration
Estimated Runtime: 10-30 seconds

This script generates comprehensive size data covering:
- US Men's sizes (3.5 - 18, half sizes)
- US Women's sizes (5 - 15, half sizes)
- US Youth sizes (1 - 7, half sizes)
- UK sizes (3 - 16, half sizes)
- EU sizes (35 - 52, whole sizes)
- CM sizes (22 - 35, half cm increments)

Each size includes a standardized_value for cross-region matching.
"""

import asyncio
import asyncpg
import os
from datetime import datetime
from typing import List, Tuple

# Database connection from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip"
)


def generate_us_mens_sizes() -> List[Tuple[str, str, str]]:
    """Generate US men's sizes from 3.5 to 18 (half sizes)."""
    sizes = []
    size = 3.5
    while size <= 18.0:
        value = f"{size:.1f}" if size % 1 != 0 else f"{int(size)}"
        standardized = f"{size:.1f}_US_M"
        sizes.append((value, "US", standardized))
        size += 0.5
    return sizes


def generate_us_womens_sizes() -> List[Tuple[str, str, str]]:
    """Generate US women's sizes from 5 to 15 (half sizes)."""
    sizes = []
    size = 5.0
    while size <= 15.0:
        value = f"{size:.1f}W" if size % 1 != 0 else f"{int(size)}W"
        standardized = f"{size:.1f}_US_W"
        sizes.append((value, "US", standardized))
        size += 0.5
    return sizes


def generate_us_youth_sizes() -> List[Tuple[str, str, str]]:
    """Generate US youth sizes from 1 to 7 (half sizes)."""
    sizes = []
    size = 1.0
    while size <= 7.0:
        value = f"{size:.1f}Y" if size % 1 != 0 else f"{int(size)}Y"
        standardized = f"{size:.1f}_US_Y"
        sizes.append((value, "US", standardized))
        size += 0.5
    return sizes


def generate_uk_sizes() -> List[Tuple[str, str, str]]:
    """Generate UK sizes from 3 to 16 (half sizes)."""
    sizes = []
    size = 3.0
    while size <= 16.0:
        value = f"{size:.1f}" if size % 1 != 0 else f"{int(size)}"
        standardized = f"{size:.1f}_UK"
        sizes.append((value, "UK", standardized))
        size += 0.5
    return sizes


def generate_eu_sizes() -> List[Tuple[str, str, str]]:
    """Generate EU sizes from 35 to 52 (whole and half sizes)."""
    sizes = []
    size = 35.0
    while size <= 52.0:
        value = f"{size:.1f}" if size % 1 != 0 else f"{int(size)}"
        standardized = f"{size:.1f}_EU"
        sizes.append((value, "EU", standardized))
        size += 0.5
    return sizes


def generate_cm_sizes() -> List[Tuple[str, str, str]]:
    """Generate CM sizes from 22 to 35 (half cm increments)."""
    sizes = []
    size = 22.0
    while size <= 35.0:
        value = f"{size:.1f}"
        standardized = f"{size:.1f}_CM"
        sizes.append((value, "CM", standardized))
        size += 0.5
    return sizes


async def check_existing_sizes(conn: asyncpg.Connection) -> int:
    """Check if sizes already exist in database."""
    count = await conn.fetchval("SELECT COUNT(*) FROM sizes")
    return count


async def insert_sizes(conn: asyncpg.Connection, sizes: List[Tuple[str, str, str]]) -> int:
    """Insert sizes into database using batch insert."""
    # Use executemany for batch insert with UUID generation
    query = """
        INSERT INTO sizes (id, value, region, standardized_value)
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
            COUNT(*) - COUNT(standardized_value) as missing_standard
        FROM sizes
        GROUP BY region
        ORDER BY region
    """)

    print("Sizes by Region:")
    total_sizes = 0
    for row in region_counts:
        print(f"  {row['region']:3s}: {row['total']:4d} sizes "
              f"({row['with_standard']} with standardized_value)")
        total_sizes += row['total']

    print(f"\nTotal sizes: {total_sizes}")

    # Check for duplicates
    duplicates = await conn.fetch("""
        SELECT value, region, COUNT(*) as count
        FROM sizes
        GROUP BY value, region
        HAVING COUNT(*) > 1
    """)

    if duplicates:
        print(f"\nWARNING: Found {len(duplicates)} duplicate size entries:")
        for dup in duplicates[:5]:  # Show first 5
            print(f"  - {dup['value']} ({dup['region']}): {dup['count']} entries")
    else:
        print("\nNo duplicate sizes found")

    # Sample sizes
    print("\nSample sizes by region:")
    for region in ["US", "UK", "EU", "CM"]:
        samples = await conn.fetch("""
            SELECT value, standardized_value
            FROM sizes
            WHERE region = $1
            ORDER BY value
            LIMIT 3
        """, region)

        if samples:
            print(f"  {region}:")
            for s in samples:
                print(f"    {s['value']:8s} -> {s['standardized_value']}")


async def main():
    """Main execution function."""
    print("=" * 80)
    print("SIZE MASTER DATA GENERATION")
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
                await conn.execute("TRUNCATE sizes CASCADE")
                print("Existing sizes deleted.")
            else:
                print("Aborted. No changes made.")
                return

        # Generate all size data
        print("\nGenerating size data...")
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
