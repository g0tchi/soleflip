"""
Create asphaltgold supplier and populate its history
"""
import asyncio
import uuid
from datetime import date
from sqlalchemy import text
from shared.database.connection import db_manager

# asphaltgold Store Information
ASPHALTGOLD_SUPPLIER = {
    "id": str(uuid.uuid4()),
    "name": "Asphaltgold",
    "slug": "asphaltgold",
    "display_name": "Asphaltgold Sneaker Store",
    "supplier_type": "retailer",
    "business_size": "large",
    "contact_person": "Daniel Benz",
    "website": "https://www.asphaltgold.com",
    "city": "Darmstadt",
    "address_line1": "Ludwigsplatz",
    "postal_code": "64283",
    "country": "Germany",
    "status": "active",
    "preferred": True,
    "verified": True,
    "founded_year": 2008,
    "founder_name": "Daniel Benz",
    "instagram_handle": "@asphaltgold",
    "instagram_url": "https://www.instagram.com/asphaltgold/",
    "supplier_story": """
Asphaltgold was founded in 2008 by Daniel Benz, who turned his passion into a career and opened
the store on Darmstadt's Friedensplatz to serve the sneaker scene in the Rhine-Main area. Benz
was driven by his fascination with streetwear culture and his passion for sneakers since the
early 90s.

What was originally a small one-man team has now grown into an international company with over
120 employees, with a portfolio of more than 80 brands. Asphaltgold is one of the top 15 sneaker
retailers in Europe with over 1,000,000 followers worldwide on social media.
    """.strip(),
    "notes": "One of top 15 sneaker retailers in Europe. Over 120 employees, 80+ brands, 1M+ social media followers."
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


async def main():
    print("=== CREATING ASPHALTGOLD SUPPLIER ===\n")

    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # Check if already exists
        result = await session.execute(
            text("SELECT id, name FROM core.suppliers WHERE slug = 'asphaltgold'")
        )
        existing = result.fetchone()

        if existing:
            print(f"[!] asphaltgold already exists (ID: {existing[0]})")
            supplier_id = existing[0]
        else:
            # Create supplier
            print("[*] Creating new asphaltgold supplier...")
            supplier_id = ASPHALTGOLD_SUPPLIER["id"]

            await session.execute(
                text("""
                    INSERT INTO core.suppliers (
                        id, name, slug, display_name, supplier_type, business_size,
                        contact_person, website, city, address_line1, postal_code, country,
                        status, preferred, verified, founded_year, founder_name,
                        instagram_handle, instagram_url, supplier_story, notes
                    )
                    VALUES (
                        :id, :name, :slug, :display_name, :supplier_type, :business_size,
                        :contact_person, :website, :city, :address_line1, :postal_code, :country,
                        :status, :preferred, :verified, :founded_year, :founder_name,
                        :instagram_handle, :instagram_url, :supplier_story, :notes
                    )
                """),
                ASPHALTGOLD_SUPPLIER
            )
            print(f"[OK] Supplier created with ID: {supplier_id}")

        # Populate timeline
        print(f"\n[*] Populating timeline with {len(ASPHALTGOLD_TIMELINE)} events...")
        for i, event in enumerate(ASPHALTGOLD_TIMELINE, 1):
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
            print(f"  [{i}/{len(ASPHALTGOLD_TIMELINE)}] {event['event_date'].year}: {event['event_title']}")

        await session.commit()

        print("\n[OK] asphaltgold supplier created and history populated!")

        # Verify
        result = await session.execute(
            text("""
                SELECT s.name, s.founded_year, s.founder_name, s.city, COUNT(sh.id) as events
                FROM core.suppliers s
                LEFT JOIN core.supplier_history sh ON s.id = sh.supplier_id
                WHERE s.slug = 'asphaltgold'
                GROUP BY s.id, s.name, s.founded_year, s.founder_name, s.city
            """)
        )
        sup = result.fetchone()

        print("\n=== VERIFICATION ===")
        print(f"Name: {sup[0]}")
        print(f"Founded: {sup[1]} by {sup[2]}")
        print(f"Location: {sup[3]}")
        print(f"Timeline Events: {sup[4]}")
        print("\n[OK] ASPHALTGOLD SUPPLIER READY!")


if __name__ == "__main__":
    asyncio.run(main())
