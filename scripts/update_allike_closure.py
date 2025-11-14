"""
Script to document Allike Store closure in supplier history
Instagram post: https://www.instagram.com/p/DPo3_FjiEV-/
Date: October 10, 2025
"""

import asyncio
from datetime import datetime

from sqlalchemy import text

from shared.database.connection import db_manager

CLOSURE_NOTE = """
=== STORE CLOSURE - October 10, 2025 ===

Allike Store announced permanent closure on Instagram (https://www.instagram.com/p/DPo3_FjiEV-/).

Closing Message:
"Dear friends of Allike,

It's with a heavy heart that we have to say Goodbye.

What started 16 years ago out of a passion for sneakers and streetwear, skateboarding and design,
has developed into one of the main addresses for sneaker culture and streetwear. Our Online shop
went live 2009, in 2014 we opened our store in Hamburg-Altona. During Covid, in 2020, we opened
our fashion concept @a.plusstore and our sandwich spot @willis.hamburg in order to offer an
exceptional shopping and food experience here on our corner in Altona.

Change is constant – which obviously applies to the sneaker business as well. The industry is a
different one now than it was back when we started, and it can be tough, especially for smaller
businesses. We were not able to get through and will close our doors for now.

Much love,
Your team of Allike, a.plus and Willi's 🤍"

Key Facts:
- Founded: 2009 (16 years ago)
- Online shop launched: 2009
- Physical store opened: Hamburg-Altona, 2014
- Additional concepts: a.plus (fashion), Willi's (food) - opened 2020 during Covid
- Location: Virchowstrasse 2 - Hinterhof, 22767 Hamburg
- Instagram: @allikestore
- Followers: 136,000

Reason for closure: Industry changes, difficult market conditions for smaller businesses

Status changed to: closed
Last updated: {date}
""".format(
    date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)


async def main():
    print("Searching for Allike Store (CTBI) in suppliers database...")

    # Initialize database manager
    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # Search for CTBI supplier (Allike's database name)
        result = await session.execute(
            text(
                """
                SELECT id, name, slug, status, city, website, notes, internal_notes
                FROM core.suppliers
                WHERE LOWER(name) LIKE '%ctbi%' OR LOWER(slug) LIKE '%ctbi%'
                   OR LOWER(name) LIKE '%allike%' OR LOWER(slug) LIKE '%allike%'
            """
            )
        )
        supplier = result.fetchone()

        if not supplier:
            print("\n[!] CTBI/Allike Store NOT FOUND in suppliers database.")
            print("[i] Searching all suppliers...")

            # Show all suppliers
            result = await session.execute(
                text("SELECT id, name, slug, status FROM core.suppliers ORDER BY name")
            )
            all_suppliers = result.fetchall()
            print(f"\n[i] Found {len(all_suppliers)} suppliers in database:")
            for s in all_suppliers:
                print(f"  - {s[1]} (slug: {s[2]}, status: {s[3]})")

            print("\n[?] CTBI not found. Please check the database name.")
            return

        # Supplier found
        print("\n[OK] Found CTBI/Allike Store:")
        print(f"  ID: {supplier[0]}")
        print(f"  Name: {supplier[1]}")
        print(f"  Slug: {supplier[2]}")
        print(f"  Current Status: {supplier[3]}")
        print(f"  City: {supplier[4]}")
        print(f"  Website: {supplier[5]}")

        # Update supplier with closure information
        print("\n[*] Updating supplier with closure information...")

        # Combine existing notes with closure note
        existing_internal_notes = supplier[7] or ""
        new_internal_notes = CLOSURE_NOTE
        if existing_internal_notes:
            new_internal_notes = existing_internal_notes + "\n\n" + CLOSURE_NOTE

        await session.execute(
            text(
                """
                UPDATE core.suppliers
                SET
                    status = 'closed',
                    internal_notes = :internal_notes,
                    updated_at = NOW()
                WHERE id = :supplier_id
            """
            ),
            {"supplier_id": supplier[0], "internal_notes": new_internal_notes},
        )

        await session.commit()

        print("\n[OK] Successfully updated Allike Store supplier record:")
        print("  - Status changed to: closed")
        print("  - Added closure documentation to internal_notes")
        print("  - Updated timestamp recorded")

        # Verify update
        result = await session.execute(
            text(
                """
                SELECT status, updated_at
                FROM core.suppliers
                WHERE id = :supplier_id
            """
            ),
            {"supplier_id": supplier[0]},
        )
        updated = result.fetchone()
        print(f"\n[VERIFY] Current status: {updated[0]}")
        print(f"[VERIFY] Last updated: {updated[1]}")


if __name__ == "__main__":
    asyncio.run(main())
