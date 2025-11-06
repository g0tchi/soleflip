"""Check StockX credentials in system_config table."""
import asyncio
from sqlalchemy import text
from shared.database.connection import db_manager


async def main():
    await db_manager.initialize()

    async with db_manager.get_session() as session:
        result = await session.execute(
            text("""
                SELECT key,
                       value IS NOT NULL as has_value,
                       LENGTH(value) as value_length,
                       LEFT(value, 20) as value_preview
                FROM core.system_config
                WHERE key LIKE 'stockx%'
                ORDER BY key
            """)
        )
        rows = result.fetchall()

        print("\nStockX Credentials in core.system_config:")
        print("-" * 80)
        for row in rows:
            key, has_value, length, preview = row
            print(f"{key:30} | Has Value: {has_value:5} | Length: {length:4} | Preview: {preview}")
        print("-" * 80)
        print(f"\nTotal: {len(rows)} StockX credential entries found")

    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
