"""
Import purchases from allike invoice AL50333785
"""
import asyncio
import os
from datetime import datetime
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Corrected purchase data from invoice
purchases = [
    {
        'sku': 'HQ8752',
        'name': 'adidas Adifom Superstar',
        'color': 'Schwarz / Weiß',
        'size': '38',
        'gross_price': Decimal('27.99'),
        'net_price': Decimal('23.52')
    },
    {
        'sku': 'JH9768',
        'name': 'adidas WMNS Campus 00s',
        'color': 'Braun / Schwarz',
        'size': '38',
        'gross_price': Decimal('49.99'),
        'net_price': Decimal('42.01')
    },
    {
        'sku': 'JH9768',
        'name': 'adidas WMNS Campus 00s',
        'color': 'Braun / Schwarz',
        'size': '39 1/3',
        'gross_price': Decimal('49.99'),
        'net_price': Decimal('42.01')
    },
    {
        'sku': '1203A388-100',
        'name': 'Asics Gel-Kayano 20',
        'color': 'Weiss / Silber',
        'size': '38',
        'gross_price': Decimal('104.99'),
        'net_price': Decimal('88.23')
    },
    {
        'sku': 'TW2V50800U8',
        'name': 'Timex Camper x Stranger Things 40mm Fabric Strap Watch',
        'color': 'Schwarz',
        'size': 'One Size',
        'gross_price': Decimal('35.19'),
        'net_price': Decimal('29.57')
    }
]

purchase_date = datetime(2025, 7, 15)  # Auftragsdatum
invoice_number = 'AL50333785'


async def create_purchases():
    engine = create_async_engine(os.getenv('DATABASE_URL'), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get supplier ID for allike
        supplier_result = await session.execute(
            text("SELECT id FROM core.suppliers WHERE slug = 'allike'")
        )
        supplier = supplier_result.fetchone()
        if not supplier:
            print("[ERROR] Supplier 'allike' not found!")
            return

        supplier_id = supplier[0]
        print(f"[OK] Found supplier 'allike': {supplier_id}\n")

        # Get brands
        adidas_result = await session.execute(
            text("SELECT id FROM core.brands WHERE LOWER(name) = 'adidas'")
        )
        adidas_brand = adidas_result.fetchone()

        asics_result = await session.execute(
            text("SELECT id FROM core.brands WHERE LOWER(name) = 'asics'")
        )
        asics_brand = asics_result.fetchone()

        timex_result = await session.execute(
            text("SELECT id FROM core.brands WHERE LOWER(name) = 'timex'")
        )
        timex_brand = timex_result.fetchone()

        # Get categories
        sneakers_result = await session.execute(
            text("SELECT id FROM core.categories WHERE LOWER(name) = 'sneakers' OR LOWER(slug) = 'sneakers'")
        )
        sneakers_cat = sneakers_result.fetchone()

        watches_result = await session.execute(
            text("SELECT id FROM core.categories WHERE LOWER(name) LIKE '%watch%' OR LOWER(name) LIKE '%uhr%'")
        )
        watches_cat = watches_result.fetchone()

        # If watches category doesn't exist, use sneakers
        if not watches_cat and sneakers_cat:
            watches_cat = sneakers_cat

        created_items = []

        for i, purchase in enumerate(purchases, 1):
            print(f"\n{'='*60}")
            print(f"Processing item {i}/5: {purchase['name']}")
            print(f"{'='*60}")

            # Determine brand
            if 'adidas' in purchase['name'].lower():
                brand_id = adidas_brand[0] if adidas_brand else None
                brand_name = 'adidas'
            elif 'asics' in purchase['name'].lower():
                brand_id = asics_brand[0] if asics_brand else None
                brand_name = 'Asics'
            elif 'timex' in purchase['name'].lower():
                brand_id = timex_brand[0] if timex_brand else None
                brand_name = 'Timex'
            else:
                brand_id = None
                brand_name = 'Unknown'

            # Determine category
            if 'watch' in purchase['name'].lower() or 'uhr' in purchase['name'].lower():
                category_id = watches_cat[0] if watches_cat else None
                category_name = 'Watches'
            else:
                category_id = sneakers_cat[0] if sneakers_cat else None
                category_name = 'Sneakers'

            if not category_id:
                print(f"  [WARNING] No category found, skipping item")
                continue

            # Check if product exists
            product_result = await session.execute(
                text("SELECT id, name FROM products.products WHERE sku = :sku"),
                {'sku': purchase['sku']}
            )
            product = product_result.fetchone()

            if product:
                product_id = product[0]
                print(f"  [OK] Product exists: {product[1]}")
            else:
                # Create new product
                full_name = f"{brand_name} {purchase['name']}"
                if purchase.get('color'):
                    full_name += f" ({purchase['color']})"

                insert_result = await session.execute(
                    text("""
                        INSERT INTO products.products (id, sku, name, brand_id, category_id, created_at, updated_at)
                        VALUES (gen_random_uuid(), :sku, :name, :brand_id, :category_id, NOW(), NOW())
                        RETURNING id
                    """),
                    {
                        'sku': purchase['sku'],
                        'name': full_name,
                        'brand_id': brand_id,
                        'category_id': category_id
                    }
                )
                await session.commit()
                product_id = insert_result.fetchone()[0]
                print(f"  [OK] Created product: {full_name}")

            # Get or create size
            size_result = await session.execute(
                text("SELECT id FROM core.sizes WHERE value = :size AND category_id = :cat_id"),
                {'size': purchase['size'], 'cat_id': category_id}
            )
            size = size_result.fetchone()

            if size:
                size_id = size[0]
                print(f"  [OK] Size exists: {purchase['size']}")
            else:
                # Create size
                size_insert = await session.execute(
                    text("""
                        INSERT INTO core.sizes (id, value, category_id, region, created_at, updated_at)
                        VALUES (gen_random_uuid(), :value, :cat_id, 'EU', NOW(), NOW())
                        RETURNING id
                    """),
                    {'value': purchase['size'], 'cat_id': category_id}
                )
                await session.commit()
                size_id = size_insert.fetchone()[0]
                print(f"  [OK] Created size: {purchase['size']}")

            # Create inventory item
            vat_amount = purchase['gross_price'] - purchase['net_price']

            inventory_insert = await session.execute(
                text("""
                    INSERT INTO products.inventory (
                        id, product_id, size_id, supplier_id, quantity,
                        purchase_price, gross_purchase_price, vat_amount, vat_rate,
                        purchase_date, supplier, status, notes,
                        created_at, updated_at
                    )
                    VALUES (
                        gen_random_uuid(), :product_id, :size_id, :supplier_id, 1,
                        :net_price, :gross_price, :vat_amount, 19.00,
                        :purchase_date, 'allike', 'in_stock', :notes,
                        NOW(), NOW()
                    )
                    RETURNING id
                """),
                {
                    'product_id': product_id,
                    'size_id': size_id,
                    'supplier_id': supplier_id,
                    'net_price': purchase['net_price'],
                    'gross_price': purchase['gross_price'],
                    'vat_amount': vat_amount,
                    'purchase_date': purchase_date,
                    'notes': f"Rechnung {invoice_number}, SKU: {purchase['sku']}"
                }
            )
            await session.commit()
            inventory_id = inventory_insert.fetchone()[0]

            created_items.append({
                'id': inventory_id,
                'product': purchase['name'],
                'size': purchase['size'],
                'net_price': purchase['net_price'],
                'gross_price': purchase['gross_price']
            })

            print(f"  [OK] Created inventory item ID: {inventory_id}")
            print(f"     Net: {purchase['net_price']} EUR | Gross: {purchase['gross_price']} EUR")

        print(f"\n{'='*60}")
        print("[SUCCESS] All purchases created successfully!")
        print(f"{'='*60}\n")

        print("Summary:")
        print(f"  Invoice: {invoice_number}")
        print(f"  Date: {purchase_date.strftime('%Y-%m-%d')}")
        print(f"  Supplier: allike")
        print(f"  Items: {len(created_items)}")
        print(f"  Total Net: {sum(item['net_price'] for item in created_items):.2f} EUR")
        print(f"  Total Gross: {sum(item['gross_price'] for item in created_items):.2f} EUR")

        print("\nCreated inventory items:")
        for item in created_items:
            print(f"  - {item['product']} (Size {item['size']}) - {item['gross_price']} EUR")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_purchases())
