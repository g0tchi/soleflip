"""
Populate afew and asphaltgold supplier histories
Based on web research
"""
import asyncio
from datetime import date
from sqlalchemy import text
from shared.database.connection import db_manager

# afew Store Information
AFEW_INFO = {
    "founded_year": 2008,
    "founder_name": "Andy and Marco (Brothers)",
    "instagram_handle": "@afew_store",
    "instagram_url": "https://www.instagram.com/afew_store/",
    "website": "https://en.afew-store.com",
    "city": "Düsseldorf",
    "address_line1": "Oststraße 36",
    "postal_code": "40211",
    "country": "Germany",
    "supplier_story": """
AFEW STORE was founded in 2008 in Düsseldorf by two brothers, Andy and Marco, who shared a big
passion for basketball sneakers. They started by selling shoes out of their father's garage with
an initial small range of sneakers and DIY shelves.

Before becoming the well-known AFEW STORE, the store at Oststraße 36 was originally called
"Schuh-You". Smart marketing campaigns and guerilla marketing helped the store grow, and it
became more popular due to its growing assortment and stylish interior.

The store has grown from a local garage operation to an international power-house in the sneaker
world, collaborating with brands such as Nike, Adidas, ASICSTIGER, Diadora and KangaROOS.
    """.strip()
}

AFEW_TIMELINE = [
    {
        "event_date": date(2008, 1, 1),
        "event_type": "founded",
        "event_title": "afew Store Founded in Düsseldorf",
        "event_description": "Two brothers Andy and Marco founded afew, starting by selling basketball sneakers out of their father's garage with DIY shelves. Originally named 'Schuh-You'.",
        "impact_level": "critical",
        "source_url": "https://en.afew-store.com/pages/about-afew"
    },
    {
        "event_date": date(2008, 6, 1),
        "event_type": "opened_store",
        "event_title": "Physical Store Opens at Oststraße 36",
        "event_description": "Opened brick-and-mortar store 'Schuh-You' at Oststraße 36 in Düsseldorf, moving from garage sales to professional retail.",
        "impact_level": "high",
        "source_url": "https://www.shelflife.co.za/magazine/afew-store-brief-history-past-collabs"
    },
    {
        "event_date": date(2010, 1, 1),
        "event_type": "rebranding",
        "event_title": "Rebranding to AFEW STORE",
        "event_description": "Store rebranded from 'Schuh-You' to 'AFEW STORE'. Smart marketing campaigns and guerilla marketing helped establish the new brand identity.",
        "impact_level": "high",
        "source_url": "https://fizzymag.com/fizzypages/afew"
    },
    {
        "event_date": date(2017, 1, 1),
        "event_type": "milestone",
        "event_title": "Complete Store Redesign",
        "event_description": "Major renovation with whole new design and functionalities. This was the biggest advancement for the store, establishing it as an international powerhouse.",
        "impact_level": "high",
        "source_url": "https://en.afew-store.com/pages/store"
    }
]

# asphaltgold Store Information
ASPHALTGOLD_INFO = {
    "founded_year": 2008,
    "founder_name": "Daniel Benz",
    "instagram_handle": "@asphaltgold",
    "instagram_url": "https://www.instagram.com/asphaltgold/",
    "website": "https://www.asphaltgold.com",
    "city": "Darmstadt",
    "address_line1": "Ludwigsplatz",
    "postal_code": "64283",
    "country": "Germany",
    "supplier_story": """
Asphaltgold was founded in 2008 by Daniel Benz, who turned his passion into a career and opened
the store on Darmstadt's Friedensplatz to serve the sneaker scene in the Rhine-Main area. Benz
was driven by his fascination with streetwear culture and his passion for sneakers since the
early 90s.

What was originally a small one-man team has now grown into an international company with over
120 employees, with a portfolio of more than 80 brands. Asphaltgold is one of the top 15 sneaker
retailers in Europe with over 1,000,000 followers worldwide on social media.
    """.strip()
}

ASPHALTGOLD_TIMELINE = [
    {
        "event_date": date(2008, 1, 1),
        "event_type": "founded",
        "event_title": "asphaltgold Founded in Darmstadt",
        "event_description": "Daniel Benz founded asphaltgold on Friedensplatz in Darmstadt to serve the sneaker scene in the Rhine-Main area, turning his passion for streetwear and sneakers into a career.",
        "impact_level": "critical",
        "source_url": "https://www.asphaltgold.com/en/pages/uber-uns"
    },
    {
        "event_date": date(2009, 3, 1),
        "event_type": "milestone",
        "event_title": "Online Shop Launch",
        "event_description": "Just a few months after opening, Asphaltgold.com online shop was launched, expanding reach beyond local customers.",
        "impact_level": "high",
        "source_url": "https://www.asphaltgold.com/en/"
    },
    {
        "event_date": date(2015, 1, 1),
        "event_type": "opened_store",
        "event_title": "Second Store: AGC Store Opens",
        "event_description": "Seven years after opening, asphaltgold expanded with the AGC Store in downtown Darmstadt, operating two locations simultaneously.",
        "impact_level": "medium",
        "source_url": "https://www.asphaltgold.com/en/pages/asphaltgold-store-darmstadt"
    },
    {
        "event_date": date(2020, 3, 1),
        "event_type": "milestone",
        "event_title": "Store Consolidation at Ludwigsplatz",
        "event_description": "AGC Store was converted into a single, larger asphaltgold flagship store at Ludwigsplatz in the city center, consolidating operations.",
        "impact_level": "medium",
        "source_url": "https://www.asphaltgold.com/en/pages/asphaltgold-store-darmstadt"
    },
    {
        "event_date": date(2020, 1, 1),
        "event_type": "milestone",
        "event_title": "Top 15 Sneaker Retailer in Europe",
        "event_description": "Achieved recognition as one of the top 15 sneaker retailers in Europe with over 120 employees and 1M+ social media followers.",
        "impact_level": "high",
        "source_url": "https://www.asphaltgold.com/en/pages/uber-uns"
    },
    {
        "event_date": date(2025, 1, 1),
        "event_type": "opened_store",
        "event_title": "Frankfurt Store Opens",
        "event_description": "Opened second retail location in Frankfurt am Main, expanding presence in the Rhine-Main metropolitan region.",
        "impact_level": "high",
        "source_url": "https://www.asphaltgold.com/en/pages/uber-uns"
    }
]


async def populate_supplier(session, slug: str, info: dict, timeline: list, display_name: str):
    """Populate a single supplier with history"""

    print(f"\n{'='*80}")
    print(f"PROCESSING: {display_name}")
    print('='*80)

    # Find supplier
    result = await session.execute(
        text("SELECT id, name FROM core.suppliers WHERE slug = :slug"),
        {"slug": slug}
    )
    supplier = result.fetchone()

    if not supplier:
        print(f"[ERROR] Supplier with slug '{slug}' not found!")
        return False

    supplier_id = supplier[0]
    print(f"[OK] Found supplier: {supplier[1]} (ID: {supplier_id})")

    # Update supplier information
    print("[*] Updating supplier information...")
    await session.execute(
        text("""
            UPDATE core.suppliers
            SET
                founded_year = :founded_year,
                founder_name = :founder_name,
                instagram_handle = :instagram_handle,
                instagram_url = :instagram_url,
                website = :website,
                city = :city,
                address_line1 = :address_line1,
                postal_code = :postal_code,
                country = :country,
                supplier_story = :supplier_story,
                updated_at = NOW()
            WHERE id = :supplier_id
        """),
        {
            "supplier_id": supplier_id,
            **info
        }
    )
    print("[OK] Supplier information updated")

    # Insert timeline events
    print(f"[*] Populating timeline with {len(timeline)} events...")
    for i, event in enumerate(timeline, 1):
        await session.execute(
            text("""
                INSERT INTO core.supplier_history
                (supplier_id, event_date, event_type, event_title, event_description, impact_level, source_url)
                VALUES
                (:supplier_id, :event_date, :event_type, :event_title, :event_description, :impact_level, :source_url)
            """),
            {
                "supplier_id": supplier_id,
                **event
            }
        )
        print(f"  [{i}/{len(timeline)}] {event['event_date'].year}: {event['event_title']}")

    print(f"[OK] {display_name} history completed!")
    return True


async def main():
    print("=== POPULATING AFEW & ASPHALTGOLD SUPPLIER HISTORIES ===\n")

    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # Populate afew
        success_afew = await populate_supplier(
            session, "afew", AFEW_INFO, AFEW_TIMELINE, "afew Store"
        )

        # Populate asphaltgold
        success_asphaltgold = await populate_supplier(
            session, "asphaltgold", ASPHALTGOLD_INFO, ASPHALTGOLD_TIMELINE, "asphaltgold"
        )

        await session.commit()

        print(f"\n{'='*80}")
        print("SUMMARY")
        print('='*80)
        print(f"afew Store: {'SUCCESS' if success_afew else 'FAILED'}")
        print(f"asphaltgold: {'SUCCESS' if success_asphaltgold else 'FAILED'}")

        if success_afew and success_asphaltgold:
            # Get statistics
            result = await session.execute(
                text("""
                    SELECT s.name, s.founded_year, s.founder_name, COUNT(sh.id) as events
                    FROM core.suppliers s
                    LEFT JOIN core.supplier_history sh ON s.id = sh.supplier_id
                    WHERE s.slug IN ('afew', 'asphaltgold')
                    GROUP BY s.id, s.name, s.founded_year, s.founder_name
                    ORDER BY s.name
                """)
            )
            suppliers = result.fetchall()

            print("\nFINAL STATISTICS:")
            for sup in suppliers:
                print(f"\n{sup[0]}:")
                print(f"  Founded: {sup[1]} by {sup[2]}")
                print(f"  Timeline Events: {sup[3]}")

        print(f"\n{'='*80}")
        print("[OK] SUPPLIER HISTORIES POPULATED SUCCESSFULLY!")
        print('='*80)


if __name__ == "__main__":
    asyncio.run(main())
