"""
Show all supplier histories - comprehensive overview
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import db_manager


async def main():
    print("=" * 100)
    print("SUPPLIER HISTORY DATABASE - COMPLETE OVERVIEW")
    print("=" * 100)

    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # Get all suppliers with history
        result = await session.execute(
            text("""
                SELECT
                    s.name,
                    s.slug,
                    s.founded_year,
                    s.founder_name,
                    s.city,
                    s.country,
                    s.instagram_handle,
                    s.website,
                    s.status,
                    s.closure_date,
                    COUNT(sh.id) as event_count
                FROM core.suppliers s
                LEFT JOIN core.supplier_history sh ON s.id = sh.supplier_id
                WHERE s.founded_year IS NOT NULL OR sh.id IS NOT NULL
                GROUP BY s.id, s.name, s.slug, s.founded_year, s.founder_name, s.city,
                         s.country, s.instagram_handle, s.website, s.status, s.closure_date
                ORDER BY s.founded_year, s.name
            """)
        )
        suppliers = result.fetchall()

        print(f"\nTotal Suppliers with History: {len(suppliers)}\n")

        for sup in suppliers:
            status_icon = "[X]" if sup[8] == "closed" else "[OK]"
            print(f"\n{status_icon} {sup[0]} ({sup[1]})")
            print(f"    Founded: {sup[2]} by {sup[3]}")
            print(f"    Location: {sup[4]}, {sup[5]}")
            print(f"    Instagram: {sup[6]}")
            print(f"    Website: {sup[7]}")
            print(f"    Status: {sup[8].upper()}", end="")
            if sup[9]:
                print(f" (closed {sup[9]})", end="")
            print(f"\n    Timeline Events: {sup[10]}")

            # Get timeline for this supplier
            result = await session.execute(
                text("""
                    SELECT event_date, event_type, event_title, impact_level
                    FROM core.supplier_history sh
                    JOIN core.suppliers s ON sh.supplier_id = s.id
                    WHERE s.slug = :slug
                    ORDER BY event_date
                """),
                {"slug": sup[1]}
            )
            events = result.fetchall()

            if events:
                print("\n    Timeline:")
                for event in events:
                    impact_markers = {
                        "low": "[ ]",
                        "medium": "[*]",
                        "high": "[**]",
                        "critical": "[***]"
                    }
                    marker = impact_markers.get(event[3], "[*]")
                    print(f"      {marker} {event[0].year} - [{event[1]:12s}] {event[2]}")

        # Statistics
        print(f"\n{'=' * 100}")
        print("STATISTICS")
        print('=' * 100)

        result = await session.execute(
            text("""
                SELECT
                    COUNT(DISTINCT s.id) as total_suppliers,
                    COUNT(sh.id) as total_events,
                    MIN(s.founded_year) as oldest_year,
                    MAX(s.founded_year) as newest_year,
                    SUM(CASE WHEN s.status = 'active' THEN 1 ELSE 0 END) as active_count,
                    SUM(CASE WHEN s.status = 'closed' THEN 1 ELSE 0 END) as closed_count
                FROM core.suppliers s
                LEFT JOIN core.supplier_history sh ON s.id = sh.supplier_id
                WHERE s.founded_year IS NOT NULL OR sh.id IS NOT NULL
            """)
        )
        stats = result.fetchone()

        print(f"\nSuppliers with History: {stats[0]}")
        print(f"Total Timeline Events: {stats[1]}")
        print(f"Founded Years Range: {stats[2]} - {stats[3]}")
        print(f"Active Suppliers: {stats[4]}")
        print(f"Closed Suppliers: {stats[5]}")

        # Event type breakdown
        result = await session.execute(
            text("""
                SELECT event_type, COUNT(*) as count
                FROM core.supplier_history
                GROUP BY event_type
                ORDER BY count DESC
            """)
        )
        event_types = result.fetchall()

        print("\nEvent Type Breakdown:")
        for et in event_types:
            print(f"  {et[0]:15s}: {et[1]:3d}")

        print(f"\n{'=' * 100}")
        print("[OK] SUPPLIER HISTORY OVERVIEW COMPLETE")
        print('=' * 100)


if __name__ == "__main__":
    asyncio.run(main())
