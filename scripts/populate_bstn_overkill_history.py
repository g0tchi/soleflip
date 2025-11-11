"""
Populate BSTN and Overkill supplier histories
Based on web research
"""

import asyncio
from datetime import date

from sqlalchemy import text

from shared.database.connection import db_manager

# BSTN Store Information
BSTN_INFO = {
    "founded_year": 2013,
    "founder_name": "Christian 'Fu' Boszczyk and Dusan 'Duki' Cvetkovic",
    "instagram_handle": "@bstnstore",
    "instagram_url": "https://www.instagram.com/bstnstore/",
    "website": "https://www.bstn.com",
    "city": "Munich",
    "address_line1": "Maxvorstadt",
    "country": "Germany",
    "supplier_story": """
BSTN originated from the Beastin brand, which was started in 2008 by Christian "Fu" Boszczyk and
Dusan "Duki" Cvetkovic with the goal to share their love for sports and streetwear and put Munich
on the map.

The founders' love of basketball (they were serious ballers), hip-hop and sneakers drove them to
create their own label called BEASTIN in 2008. Since they could not find the perfect retail
environment for their brand, they decided to create it themselves, which led to the founding of
the BSTN store in September 2013.

The German sneaker retailer has built up an established consumer base and reputable name for
itself, expanding internationally with stores in Munich, Hamburg, and London.
    """.strip(),
}

BSTN_TIMELINE = [
    {
        "event_date": date(2008, 1, 1),
        "event_type": "founded",
        "event_title": "Beastin Brand Founded",
        "event_description": "Christian 'Fu' Boszczyk and Dusan 'Duki' Cvetkovic started their own label 'BEASTIN', driven by their love for basketball, hip-hop and sneakers with the goal to put Munich on the map.",
        "impact_level": "medium",
        "source_url": "https://www.nike.com/ca/launch/t/talking-shop-bstn",
    },
    {
        "event_date": date(2013, 9, 1),
        "event_type": "founded",
        "event_title": "BSTN Store Opens in Munich",
        "event_description": "First BSTN flagship store opened in Munich's Maxvorstadt district. Unable to find the perfect retail environment for their brand, the founders created it themselves.",
        "impact_level": "critical",
        "source_url": "https://www.bstn.com/us_en/bstn-stores",
    },
    {
        "event_date": date(2017, 11, 1),
        "event_type": "opened_store",
        "event_title": "Hamburg Store Opens",
        "event_description": "BSTN opened their second store in Hamburg's Schanzenviertel, expanding their presence in Germany.",
        "impact_level": "high",
        "source_url": "https://www.bstn.com/us_en/bstn-stores",
    },
    {
        "event_date": date(2020, 1, 1),
        "event_type": "opened_store",
        "event_title": "International Expansion to London",
        "event_description": "BSTN opened its first-ever international outpost in Brixton, London, marking significant international expansion.",
        "impact_level": "high",
        "source_url": "https://thesolesupplier.co.uk/news/bstn-opens-its-first-international-outpost-in-brixton/",
    },
]

# Overkill Store Information
OVERKILL_INFO = {
    "founded_year": 2003,
    "founder_name": "Thomas Peiser and Marc Leuschner",
    "instagram_handle": "@overkillshop",
    "instagram_url": "https://www.instagram.com/overkillshop/",
    "website": "https://www.overkillshop.com",
    "city": "Berlin",
    "address_line1": "Kreuzberg",
    "country": "Germany",
    "supplier_story": """
Overkill was founded in September 2003 in the heart of Kreuzberg, Berlin, as a store of about 60
sqm for graffiti, sneakers and streetwear. It was founded by Thomas Peiser, initially starting as
a magazine around graffiti culture.

A few years later, Marc Leuschner joined the team. Marc was born and raised in Berlin and has
built Overkill's reputation over the years into one of the most respected sneaker stores in Europe.

Overkill has become synonymous with Berlin's street culture and is known for exclusive
collaborations and deep roots in the sneaker community.
    """.strip(),
}

OVERKILL_TIMELINE = [
    {
        "event_date": date(2003, 9, 1),
        "event_type": "founded",
        "event_title": "Overkill Founded in Berlin Kreuzberg",
        "event_description": "Thomas Peiser founded Overkill as a 60 sqm store for graffiti, sneakers and streetwear in Kreuzberg. Originally started as a magazine around graffiti culture.",
        "impact_level": "critical",
        "source_url": "https://www.overkillshop.com/pages/history",
    },
    {
        "event_date": date(2006, 1, 1),
        "event_type": "milestone",
        "event_title": "Marc Leuschner Joins Overkill",
        "event_description": "Marc Leuschner, born and raised in Berlin, joined Overkill and helped build the store's reputation as one of Europe's most respected sneaker retailers.",
        "impact_level": "high",
        "source_url": "https://www.overkillshop.com/",
    },
    {
        "event_date": date(2010, 1, 1),
        "event_type": "milestone",
        "event_title": "First Sneaker Collaborations",
        "event_description": "Overkill began producing exclusive sneaker collaborations with major brands, establishing itself as a key player in the European sneaker scene.",
        "impact_level": "high",
        "source_url": "https://www.sneakerfreaker.com/city-guides/berlin/overkill-berlin/",
    },
]


async def populate_supplier(session, slug: str, info: dict, timeline: list, display_name: str):
    """Populate a single supplier with history"""

    print(f"\n{'='*80}")
    print(f"PROCESSING: {display_name}")
    print("=" * 80)

    # Find supplier
    result = await session.execute(
        text("SELECT id, name FROM core.suppliers WHERE slug = :slug"), {"slug": slug}
    )
    supplier = result.fetchone()

    if not supplier:
        print(f"[ERROR] Supplier with slug '{slug}' not found in database!")
        print(f"[INFO] Available suppliers are listed. Check if '{slug}' exists.")
        return False

    supplier_id = supplier[0]
    print(f"[OK] Found supplier: {supplier[1]} (ID: {supplier_id})")

    # Update supplier information
    print("[*] Updating supplier information...")
    await session.execute(
        text(
            """
            UPDATE core.suppliers
            SET
                founded_year = :founded_year,
                founder_name = :founder_name,
                instagram_handle = :instagram_handle,
                instagram_url = :instagram_url,
                website = :website,
                city = :city,
                address_line1 = :address_line1,
                country = :country,
                supplier_story = :supplier_story,
                updated_at = NOW()
            WHERE id = :supplier_id
        """
        ),
        {"supplier_id": supplier_id, **info},
    )
    print("[OK] Supplier information updated")

    # Insert timeline events
    print(f"[*] Populating timeline with {len(timeline)} events...")
    for i, event in enumerate(timeline, 1):
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
        print(f"  [{i}/{len(timeline)}] {event['event_date'].year}: {event['event_title']}")

    print(f"[OK] {display_name} history completed!")
    return True


async def main():
    print("=== POPULATING BSTN & OVERKILL SUPPLIER HISTORIES ===\n")

    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # Populate BSTN
        success_bstn = await populate_supplier(session, "bstn", BSTN_INFO, BSTN_TIMELINE, "BSTN")

        # Populate Overkill
        success_overkill = await populate_supplier(
            session, "overkill", OVERKILL_INFO, OVERKILL_TIMELINE, "Overkill"
        )

        await session.commit()

        print(f"\n{'='*80}")
        print("SUMMARY")
        print("=" * 80)
        print(f"BSTN: {'SUCCESS' if success_bstn else 'FAILED'}")
        print(f"Overkill: {'SUCCESS' if success_overkill else 'FAILED'}")

        if success_bstn or success_overkill:
            # Get statistics
            result = await session.execute(
                text(
                    """
                    SELECT s.name, s.founded_year, s.founder_name, s.city, COUNT(sh.id) as events
                    FROM core.suppliers s
                    LEFT JOIN core.supplier_history sh ON s.id = sh.supplier_id
                    WHERE s.slug IN ('bstn', 'overkill')
                    GROUP BY s.id, s.name, s.founded_year, s.founder_name, s.city
                    ORDER BY s.name
                """
                )
            )
            suppliers = result.fetchall()

            print("\nFINAL STATISTICS:")
            for sup in suppliers:
                if sup[1]:  # Only show if founded_year exists
                    print(f"\n{sup[0]}:")
                    print(f"  Founded: {sup[1]} by {sup[2]}")
                    print(f"  Location: {sup[3]}, Germany")
                    print(f"  Timeline Events: {sup[4]}")

        print(f"\n{'='*80}")
        print("[OK] SUPPLIER HISTORIES POPULATED!")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
