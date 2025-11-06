"""Update timestamps in core.system_config table."""

import asyncio
from datetime import datetime
from sqlalchemy import text, select
from shared.database.connection import db_manager
from shared.database.models import SystemConfig


async def main():
    """Update updated_at timestamps for all system_config entries."""
    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # Get all StockX credentials
        print("\n" + "=" * 80)
        print("Current StockX Credentials Status")
        print("=" * 80 + "\n")

        result = await session.execute(select(SystemConfig).where(SystemConfig.key.like("stockx%")))
        configs = result.scalars().all()

        if not configs:
            print("[ERROR] No StockX credentials found in database!")
            return

        print(f"Found {len(configs)} StockX credential entries:\n")

        for config in configs:
            print(f"Key: {config.key}")
            print(f"  Created:  {config.created_at}")
            print(f"  Updated:  {config.updated_at}")
            print(f"  Has Value: {'Yes' if config.value_encrypted else 'No'}")
            print()

        # Update timestamps
        print("=" * 80)
        print("Updating timestamps to current time...")
        print("=" * 80 + "\n")

        current_time = datetime.utcnow()

        await session.execute(
            text(
                """
                UPDATE core.system_config
                SET updated_at = :now
                WHERE key LIKE 'stockx%'
            """
            ),
            {"now": current_time},
        )

        await session.commit()

        print(f"[SUCCESS] Updated {len(configs)} records to: {current_time}\n")

        # Verify the update
        print("=" * 80)
        print("Verification - Updated Credentials")
        print("=" * 80 + "\n")

        result = await session.execute(select(SystemConfig).where(SystemConfig.key.like("stockx%")))
        configs = result.scalars().all()

        for config in configs:
            print(f"Key: {config.key}")
            print(f"  Updated:  {config.updated_at}")
            print()

    await db_manager.close()
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
