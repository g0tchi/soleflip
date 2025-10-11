"""
Quick cleanup script to remove duplicate supplier_history entries
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import db_manager


async def main():
    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # Delete duplicates, keeping only the oldest entry for each unique event
        result = await session.execute(
            text("""
                DELETE FROM core.supplier_history
                WHERE id IN (
                    SELECT id
                    FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (PARTITION BY supplier_id, event_date, event_type, event_title ORDER BY created_at) as rn
                        FROM core.supplier_history
                    ) t
                    WHERE rn > 1
                )
            """)
        )

        deleted_count = result.rowcount
        await session.commit()

        print(f"[OK] Removed {deleted_count} duplicate entries")

        # Verify
        result = await session.execute(
            text("SELECT COUNT(*) FROM core.supplier_history")
        )
        total = result.scalar()
        print(f"[OK] Total supplier_history entries: {total}")


if __name__ == "__main__":
    asyncio.run(main())
