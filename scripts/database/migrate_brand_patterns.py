import asyncio
import os
import sys

from slugify import slugify

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy.future import select

from shared.database.connection import DatabaseManager  # Import class instead of global instance
from shared.database.models import Base, Brand, BrandPattern  # Import Base for schema creation

# This dictionary is copied from the old validators.py
BRAND_PATTERNS = {
    # Nike and Jordan brands
    r"^Nike\s": "Nike",
    r"^Air\s": "Nike",
    r"^Wmns\s": "Nike",
    r"Jordan\s": "Nike Jordan",
    r"Travis Scott x": "Nike Jordan",
    r"Air Max": "Nike",
    r"Air Force": "Nike",
    r"Dunk": "Nike",
    r"Blazer": "Nike",
    r"Cortez": "Nike",
    r"P-6000": "Nike",
    r"React": "Nike",
    r"Zoom": "Nike",
    r"Vapormax": "Nike",
    r"Presto": "Nike",
    # Adidas
    r"^adidas": "Adidas",
    r"^Yeezy": "Adidas",
    r"Campus": "Adidas",
    r"Gazelle": "Adidas",
    r"Forum": "Adidas",
    r"Question": "Adidas",
    r"UltraBoost": "Adidas",
    r"Bad Bunny x": "Adidas",
    r"Gucci x": "Adidas",
    r"Samba": "Adidas",
    r"Stan Smith": "Adidas",
    r"Superstar": "Adidas",
    r"NMD": "Adidas",
    r"Originals": "Adidas",
    # New Balance
    r"^\d{3,4}[RV]?\s": "New Balance",
    r"^Wmns \d{3}": "New Balance",
    r"^New Balance": "New Balance",
    # ASICS
    r"Gel\s": "ASICS",
    r"GmbH x": "ASICS",
    r"HAL STUDIOS x": "ASICS",
    r"Kiko Kostadinov x": "ASICS",
    r"^ASICS": "ASICS",
    # Converse
    r"Chuck Taylor": "Converse",
    r"All Star": "Converse",
    r"^Converse": "Converse",
    r"Chuck 70": "Converse",
    r"One Star": "Converse",
    # Puma
    r"^Puma": "Puma",
    r"Suede": "Puma",
    r"Palermo": "Puma",
    r"Speedcat": "Puma",
    r"RS-X": "Puma",
    # Vans
    r"^Vans": "Vans",
    r"Old Skool": "Vans",
    r"Authentic": "Vans",
    r"Era": "Vans",
    r"Slip-On": "Vans",
    r"Sk8-Hi": "Vans",
    # Stone Island
    r"Stone Island": "Stone Island",
    # Off-White
    r"Off-White": "Off-White",
    r"OFF-WHITE": "Off-White",
    # Fear of God
    r"Fear of God": "Fear of God",
    r"FOG": "Fear of God",
    r"Essentials": "Fear of God Essentials",  # More specific
    # UGG
    r"UGG": "UGG",
    r"Classic Ultra Mini": "UGG",
    r"Classic Short": "UGG",
    r"Tasman": "UGG",
    r"Scuffette": "UGG",
    # Timberland
    r"Timberland": "Timberland",
    r"6-Inch Premium": "Timberland",
    # Crocs
    r"Crocs": "Crocs",
    r"Classic Clog": "Crocs",
    # Dr. Martens
    r"Dr\. Martens": "Dr. Martens",
    r"1460": "Dr. Martens",
    r"1461": "Dr. Martens",
    # Salomon
    r"Salomon": "Salomon",
    r"^Salomon": "Salomon",
    r"XT-6": "Salomon",
    r"XT-4": "Salomon",
    r"XT-Wings": "Salomon",
    r"Speedcross": "Salomon",
    r"S/LAB": "Salomon",
    r"ACS Pro": "Salomon",
    r"ACS\+": "Salomon",
    # Hoka
    r"Hoka": "Hoka",
    r"Clifton": "Hoka",
    r"Bondi": "Hoka",
    # On Running
    r"^On\s": "On Running",
    r"Cloud": "On Running",
    # Golden Goose
    r"Golden Goose": "Golden Goose",
    r"Super-Star": "Golden Goose",
    # Fashion/Streetwear Brands
    r"Telfar": "Telfar",
    r"Palace": "Palace",
    r"Supreme": "Supreme",
    r"Stussy|Stüssy": "Stussy",
    r"Kith": "Kith",
    # Luxury/High Fashion
    r"Louis Vuitton": "Louis Vuitton",
    r"Balenciaga": "Balenciaga",
    r"Gucci": "Gucci",
    r"Bottega Veneta": "Bottega Veneta",
    r"Margiela": "Maison Margiela",
    r"Maison Margiela": "Maison Margiela",
    r"Rick Owens": "Rick Owens",
    r"Comme des Garcons": "Comme des Garcons",
    r"CDG": "Comme des Garcons",
    # Accessories/Bags
    r"Eastpak": "Eastpak",
    r"JanSport": "JanSport",
    r"Taschen": "Taschen",
    # Toy/Collectibles
    r"Mattel": "Mattel",
    r"Hot Wheels": "Mattel",
    r"Cybertruck": "Mattel",
    r"MEGA Construx": "Mattel",
    # KAWS Collaborations
    r"KAWS": "KAWS",
    # Artist/Designer Collaborations
    r"Takashi Murakami": "Murakami",
    r"Field Boot": "Timberland",
    r"Earthkeepers": "Timberland",
    # The North Face
    r"The North Face": "The North Face",
    r"TNF": "The North Face",
    r"North Face": "The North Face",
    r"Nuptse": "The North Face",
    r"Denali": "The North Face",
    r"Base Camp": "The North Face",
    # Y-3 (Yohji Yamamoto x Adidas)
    r"Y-3": "Y-3",
    r"Yohji Yamamoto": "Y-3",
    r"Kusari": "Y-3",
    r"Kaiwa": "Y-3",
    r"Runner 4D": "Y-3",
    # Other brands
    r"Salehe Bembury x": "Crocs",
    r"Tom Sachs x": "Nike",
    r"Classic Cowboy Boot": "Dr. Martens",
    r"Chuck": "Converse",
    r"Reebok": "Reebok",
    r"Club C": "Reebok",
}


async def get_or_create_brand(session, brand_name):
    """Gets a brand by name, creating it if it doesn't exist."""
    slug = slugify(brand_name)

    # Check if brand exists
    stmt = select(Brand).where(Brand.name == brand_name)
    result = await session.execute(stmt)
    brand = result.scalar_one_or_none()

    if brand:
        return brand
    else:
        # Create new brand
        print(f"Creating new brand: {brand_name}")
        new_brand = Brand(name=brand_name, slug=slug)
        session.add(new_brand)
        await session.flush()  # Flush to get the ID for the pattern
        return new_brand


async def main():
    db_path = "./soleflip_demo.db"
    print(f"Ensuring clean state by deleting existing database file at {db_path}...")
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Old database file deleted.")

    # Create a dedicated db_manager for this script that ALWAYS uses SQLite
    db_manager_local = DatabaseManager()
    db_manager_local.database_url = f"sqlite+aiosqlite:///{db_path}"

    print("Initializing new SQLite database and creating schema...")
    await db_manager_local.initialize()  # This will create the engine
    async with db_manager_local.engine.begin() as conn:
        # Using the Base from models to create all tables
        await conn.run_sync(Base.metadata.create_all)
    print("Schema created successfully.")

    print("Populating brand patterns...")
    async with db_manager_local.get_session() as session:
        patterns_added = 0
        for pattern_str, brand_name in BRAND_PATTERNS.items():
            # Check if pattern already exists
            pattern_exists_stmt = select(BrandPattern).where(BrandPattern.pattern == pattern_str)
            result = await session.execute(pattern_exists_stmt)
            if result.scalar_one_or_none():
                continue

            brand = await get_or_create_brand(session, brand_name)

            new_pattern = BrandPattern(
                brand_id=brand.id,
                pattern_type="regex",
                pattern=pattern_str,
                priority=100,  # Default priority
            )
            session.add(new_pattern)
            patterns_added += 1
            print(f"Adding pattern '{pattern_str}' for brand '{brand.name}'")

        if patterns_added > 0:
            print(f"\nAdded {patterns_added} new patterns. Committing changes.")
            await session.commit()
        else:
            print("\nNo new patterns to add. Database is up to date.")

    await db_manager_local.close()
    print("Migration finished.")


if __name__ == "__main__":
    asyncio.run(main())
