"""
Populate Allike Store (CTBI) supplier with complete history and timeline
Based on research and Instagram closure announcement
"""

import asyncio
from datetime import date

from sqlalchemy import text

from shared.database.connection import db_manager

# Allike Store complete information
ALLIKE_INFO = {
    "founded_year": 2009,
    "founder_name": "Fiete Bluhm",
    "instagram_handle": "@allikestore",
    "instagram_url": "https://www.instagram.com/allikestore/",
    "facebook_url": "https://www.facebook.com/AllikeStore/",
    "website": "https://allikestore.com",
    "city": "Hamburg",
    "address_line1": "Virchowstraße 2 - Hinterhof",
    "postal_code": "22767",
    "country": "Germany",
    "closure_date": date(2025, 10, 10),
    "closure_reason": """
Change is constant – which obviously applies to the sneaker business as well. The industry is a
different one now than it was back when we started, and it can be tough, especially for smaller
businesses. Shout-out to every sneaker store and every customer out there continuing to contribute
to the culture we love so much. We were not able to get through and will close our doors for now.
    """.strip(),
    "supplier_story": """
What started 16 years ago out of a passion for sneakers and streetwear, skateboarding and design,
has developed into one of the main addresses for sneaker culture and streetwear. Our Online shop
went live 2009, in 2014 we opened our store in Hamburg-Altona. During Covid, in 2020, we opened
our fashion concept @a.plusstore and our sandwich spot @willis.hamburg in order to offer an
exceptional shopping and food experience here on our corner in Altona.

Allike has been curating products and content related to street culture since 2009. The founder
Fiete Bluhm comes from Hamburg, where he developed his passion for skating as well as for fashion
and sneakers. Located in a backyard between the famous Reeperbahn of Hamburg and the district of
Altona, the Allike Concept & Sneaker Store showcased about 750 limited sneakers and selected
streetwear, fashion brands, accessories, toys, books, homewear and magazines.
    """.strip(),
}

# Timeline events for supplier_history
TIMELINE_EVENTS = [
    {
        "event_date": date(2009, 1, 1),
        "event_type": "founded",
        "event_title": "Allike Store Founded",
        "event_description": "Fiete Bluhm founded Allike Store as an online sneaker and streetwear shop, driven by passion for skating, fashion and sneakers.",
        "impact_level": "critical",
        "source_url": "https://www.sneakerfreaker.com/news/clicks-bricks-germanys-allike-opens-store/",
    },
    {
        "event_date": date(2014, 1, 1),
        "event_type": "opened_store",
        "event_title": "Physical Store Opens in Hamburg-Altona",
        "event_description": "After 5 years online, Allike opened their first physical store in Hamburg's Altona district. Located in a backyard between Reeperbahn and Altona, showcasing 750+ limited sneakers and curated streetwear.",
        "impact_level": "high",
        "source_url": "https://www.sneakerfreaker.com/news/clicks-bricks-germanys-allike-opens-store/",
    },
    {
        "event_date": date(2020, 1, 1),
        "event_type": "expansion",
        "event_title": "Expansion: a.plus Fashion & Willi's Sandwich Shop",
        "event_description": "During Covid-19, Allike expanded with two new concepts: @a.plusstore (fashion concept) and @willis.hamburg (sandwich spot) to offer an exceptional shopping and food experience.",
        "impact_level": "medium",
        "source_url": "https://www.instagram.com/p/DPo3_FjiEV-/",
    },
    {
        "event_date": date(2020, 1, 1),
        "event_type": "opened_store",
        "event_title": "Second Store Opens Downtown Hamburg",
        "event_description": "Allike opened a second location in downtown Hamburg, expanding their retail presence.",
        "impact_level": "medium",
        "source_url": "https://www.thenextsole.com/en/a/allike",
    },
    {
        "event_date": date(2025, 10, 10),
        "event_type": "closure",
        "event_title": "Store Closure Announced",
        "event_description": "After 16 years, Allike announced permanent closure. Citing difficult market conditions for smaller businesses and industry changes. Instagram post received 1,400+ likes from 136,000 followers expressing support.",
        "impact_level": "critical",
        "source_url": "https://www.instagram.com/p/DPo3_FjiEV-/",
    },
]


async def main():
    print("=== POPULATING ALLIKE STORE HISTORY ===\n")

    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # 1. Get Allike/CTBI supplier
        result = await session.execute(
            text(
                """
                SELECT id, name, slug FROM core.suppliers
                WHERE LOWER(name) LIKE '%ctbi%' OR LOWER(slug) LIKE '%allike%'
            """
            )
        )
        supplier = result.fetchone()

        if not supplier:
            print("[ERROR] CTBI/Allike supplier not found!")
            return

        supplier_id = supplier[0]
        print(f"[OK] Found supplier: {supplier[1]} (ID: {supplier_id})\n")

        # 2. Update supplier with detailed information
        print("[*] Updating supplier with detailed information...")
        await session.execute(
            text(
                """
                UPDATE core.suppliers
                SET
                    founded_year = :founded_year,
                    founder_name = :founder_name,
                    instagram_handle = :instagram_handle,
                    instagram_url = :instagram_url,
                    facebook_url = :facebook_url,
                    website = :website,
                    city = :city,
                    address_line1 = :address_line1,
                    postal_code = :postal_code,
                    country = :country,
                    closure_date = :closure_date,
                    closure_reason = :closure_reason,
                    supplier_story = :supplier_story,
                    updated_at = NOW()
                WHERE id = :supplier_id
            """
            ),
            {"supplier_id": supplier_id, **ALLIKE_INFO},
        )
        print("[OK] Supplier information updated\n")

        # 3. Insert timeline events into supplier_history
        print("[*] Populating supplier_history timeline...")
        for i, event in enumerate(TIMELINE_EVENTS, 1):
            await session.execute(
                text(
                    """
                    INSERT INTO core.supplier_history
                    (supplier_id, event_date, event_type, event_title, event_description, impact_level, source_url)
                    VALUES
                    (:supplier_id, :event_date, :event_type, :event_title, :event_description, :impact_level, :source_url)
                """
                ),
                {"supplier_id": supplier_id, **event},
            )
            print(
                f"  [{i}/{len(TIMELINE_EVENTS)}] {event['event_date'].year}: {event['event_title']}"
            )

        await session.commit()

        print("\n[OK] Timeline events inserted\n")

        # 4. Verify the data
        print("=== VERIFICATION ===\n")

        # Check supplier data
        result = await session.execute(
            text(
                """
                SELECT founded_year, founder_name, instagram_handle, closure_date
                FROM core.suppliers
                WHERE id = :supplier_id
            """
            ),
            {"supplier_id": supplier_id},
        )
        sup_data = result.fetchone()
        print("Supplier Data:")
        print(f"  Founded: {sup_data[0]}")
        print(f"  Founder: {sup_data[1]}")
        print(f"  Instagram: {sup_data[2]}")
        print(f"  Closed: {sup_data[3]}\n")

        # Check history entries
        result = await session.execute(
            text(
                """
                SELECT COUNT(*),
                       MIN(event_date) as first_event,
                       MAX(event_date) as last_event
                FROM core.supplier_history
                WHERE supplier_id = :supplier_id
            """
            ),
            {"supplier_id": supplier_id},
        )
        hist_data = result.fetchone()
        print("History Timeline:")
        print(f"  Total Events: {hist_data[0]}")
        print(f"  First Event: {hist_data[1]}")
        print(f"  Last Event: {hist_data[2]}\n")

        # Show timeline
        result = await session.execute(
            text(
                """
                SELECT event_date, event_type, event_title, impact_level
                FROM core.supplier_history
                WHERE supplier_id = :supplier_id
                ORDER BY event_date
            """
            ),
            {"supplier_id": supplier_id},
        )
        events = result.fetchall()

        print("Complete Timeline:")
        for event in events:
            impact_icon = {"low": "[ ]", "medium": "[*]", "high": "[**]", "critical": "[***]"}
            icon = impact_icon.get(event[3], "[*]")
            print(f"  {icon} {event[0].year:4d} - [{event[1]:15s}] {event[2]}")

        print("\n=== ALLIKE HISTORY POPULATED SUCCESSFULLY ===")


if __name__ == "__main__":
    asyncio.run(main())
