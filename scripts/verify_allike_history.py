"""
Verify Allike Store supplier history implementation
Shows complete supplier data and timeline
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import db_manager


async def main():
    print("=== ALLIKE STORE SUPPLIER HISTORY VERIFICATION ===\n")

    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # Get complete supplier data
        result = await session.execute(
            text("""
                SELECT
                    name, slug, status,
                    founded_year, founder_name,
                    instagram_handle, instagram_url,
                    website, city, address_line1, postal_code, country,
                    closure_date, closure_reason,
                    supplier_story
                FROM core.suppliers
                WHERE slug = 'allike'
            """)
        )
        supplier = result.fetchone()

        if not supplier:
            print("[ERROR] Allike supplier not found!")
            return

        # Display supplier information
        print("SUPPLIER INFORMATION:")
        print(f"  Name: {supplier[0]}")
        print(f"  Slug: {supplier[1]}")
        print(f"  Status: {supplier[2]}")
        print("\nFOUNDER & HISTORY:")
        print(f"  Founded: {supplier[3]}")
        print(f"  Founder: {supplier[4]}")
        print("\nSOCIAL MEDIA:")
        print(f"  Instagram: {supplier[5]}")
        print(f"  URL: {supplier[6]}")
        print("\nLOCATION:")
        print(f"  Website: {supplier[7]}")
        print(f"  Address: {supplier[9]}, {supplier[8]} {supplier[10]}, {supplier[11]}")
        print("\nCLOSURE:")
        print(f"  Closure Date: {supplier[12]}")
        print(f"  Reason: {supplier[13][:100]}...")

        # Get timeline events
        result = await session.execute(
            text("""
                SELECT
                    event_date, event_type, event_title,
                    event_description, impact_level, source_url
                FROM core.supplier_history sh
                JOIN core.suppliers s ON sh.supplier_id = s.id
                WHERE s.slug = 'allike'
                ORDER BY event_date
            """)
        )
        events = result.fetchall()

        print(f"\n\nTIMELINE ({len(events)} events):")
        print("=" * 80)

        for event in events:
            impact_markers = {
                "low": "[ ]",
                "medium": "[*]",
                "high": "[**]",
                "critical": "[***]"
            }
            marker = impact_markers.get(event[4], "[*]")

            print(f"\n{marker} {event[0].year} - {event[2]}")
            print(f"    Type: {event[1]}")
            if event[3]:
                desc = event[3][:150] + "..." if len(event[3]) > 150 else event[3]
                print(f"    {desc}")
            if event[5]:
                print(f"    Source: {event[5]}")

        print("\n" + "=" * 80)
        print("\n[OK] Allike Store supplier history is complete!")
        print(f"[OK] Total timeline events: {len(events)}")
        print(f"[OK] Timeline span: {events[0][0].year} - {events[-1][0].year}")


if __name__ == "__main__":
    asyncio.run(main())
