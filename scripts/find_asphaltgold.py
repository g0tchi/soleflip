"""
Find asphaltgold supplier in database
"""

import asyncio

from sqlalchemy import text

from shared.database.connection import db_manager


async def main():
    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # Search for asphaltgold variations
        result = await session.execute(
            text(
                """
                SELECT id, name, slug, city
                FROM core.suppliers
                WHERE LOWER(name) LIKE '%asphalt%'
                   OR LOWER(slug) LIKE '%asphalt%'
                   OR LOWER(city) LIKE '%darmstadt%'
                ORDER BY name
            """
            )
        )
        suppliers = result.fetchall()

        if suppliers:
            print(f"Found {len(suppliers)} matching supplier(s):")
            for sup in suppliers:
                print(f"  - Name: {sup[1]}")
                print(f"    Slug: {sup[2]}")
                print(f"    City: {sup[3]}")
                print(f"    ID: {sup[0]}\n")
        else:
            print("No suppliers found matching 'asphalt' or 'darmstadt'")
            print("\nShowing all suppliers:")
            result = await session.execute(
                text("SELECT name, slug FROM core.suppliers ORDER BY name")
            )
            all_suppliers = result.fetchall()
            for sup in all_suppliers:
                print(f"  - {sup[0]} (slug: {sup[1]})")


if __name__ == "__main__":
    asyncio.run(main())
