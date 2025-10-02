"""
Script to insert StockX sale 55476797-55376556 with Notion data into PostgreSQL
"""
import asyncio
from decimal import Decimal
from datetime import datetime
from shared.database.connection import DatabaseManager
from shared.database.models import (
    Supplier, InventoryItem, StockXOrder, Brand, Category, Product
)
from sqlalchemy import select

async def insert_sale():
    # Sale data from Notion
    sale_data = {
        'stockx_order_number': '55476797-55376556',
        'sku': 'HQ4276',
        'brand_name': 'Adidas',
        'size_value': '8.5',
        'size_type': 'US',
        'supplier_name': '43einhalb',
        'gross_buy': Decimal('28.00'),
        'net_buy': Decimal('23.53'),
        'sale_date': datetime.strptime('2023-09-17', '%Y-%m-%d').date(),
        'gross_sale': Decimal('24.07'),
        'net_sale': Decimal('24.07'),
        'profit': Decimal('0.54'),
        'roi': Decimal('0.02')  # 2%
    }

    db_manager = DatabaseManager()
    await db_manager.initialize()

    async with db_manager.get_session() as session:
        print('=' * 80)
        print(f'Processing Sale: {sale_data["stockx_order_number"]}')
        print(f'Product: {sale_data["sku"]} - {sale_data["brand_name"]}')
        print(f'Size: {sale_data["size_value"]} {sale_data["size_type"]}')
        print('=' * 80)

        # 1. Get or create supplier
        print('\n[1/5] Handling Supplier...')
        result = await session.execute(
            select(Supplier).where(Supplier.name == sale_data['supplier_name'])
        )
        supplier = result.scalar_one_or_none()

        if not supplier:
            print(f'  Creating supplier: {sale_data["supplier_name"]}')
            supplier = Supplier(
                name=sale_data['supplier_name'],
                slug=sale_data['supplier_name'].lower().replace(' ', '-'),
                status='active',
                supplier_type='retail'  # Required field
            )
            session.add(supplier)
            await session.flush()

        print(f'  Supplier: {supplier.name} (ID: {supplier.id})')

        # 2. Get or create brand
        print('\n[2/5] Handling Brand...')
        result = await session.execute(
            select(Brand).where(Brand.name == sale_data['brand_name'])
        )
        brand = result.scalar_one_or_none()

        if not brand:
            print(f'  Creating brand: {sale_data["brand_name"]}')
            brand = Brand(
                name=sale_data['brand_name'],
                slug=sale_data['brand_name'].lower()
            )
            session.add(brand)
            await session.flush()

        print(f'  Brand: {brand.name} (ID: {brand.id})')

        # 3. Get or create category
        print('\n[3/5] Handling Category...')
        result = await session.execute(
            select(Category).where(Category.name == 'Sneakers')
        )
        category = result.scalar_one_or_none()

        if not category:
            print('  Creating category: Sneakers')
            category = Category(name='Sneakers', slug='sneakers')
            session.add(category)
            await session.flush()

        print(f'  Category: {category.name} (ID: {category.id})')

        # 4. Get or create product
        print('\n[4/5] Handling Product...')
        result = await session.execute(
            select(Product).where(Product.sku == sale_data['sku'])
        )
        product = result.scalar_one_or_none()

        if not product:
            print(f'  Creating product: {sale_data["sku"]}')
            product = Product(
                sku=sale_data['sku'],
                name=f'{sale_data["brand_name"]} {sale_data["sku"]}',
                brand_id=brand.id,
                category_id=category.id
            )
            session.add(product)
            await session.flush()

        print(f'  Product: {product.name} (ID: {product.id})')

        # 5. Create inventory item with size (no separate Size table based on schema)
        print('\n[5/5] Creating Inventory Item...')

        # Check if inventory item already exists for this sale
        result = await session.execute(
            select(InventoryItem).where(
                InventoryItem.product_id == product.id,
                InventoryItem.external_ids.op('->>')('stockx_order_number') == sale_data['stockx_order_number']
            )
        )
        inventory_item = result.scalar_one_or_none()

        if not inventory_item:
            print('  Creating inventory item...')
            inventory_item = InventoryItem(
                product_id=product.id,
                quantity=1,
                purchase_price=sale_data['net_buy'],
                supplier_id=supplier.id,
                status='sold',
                external_ids={'stockx_order_number': sale_data['stockx_order_number']}
            )
        else:
            print('  Inventory item already exists')
        session.add(inventory_item)
        await session.flush()

        print(f'  Inventory ID: {inventory_item.id}')

        # Check if order already exists
        print('\\n  Checking StockX order...')
        result = await session.execute(
            select(StockXOrder).where(
                StockXOrder.stockx_order_number == sale_data['stockx_order_number']
            )
        )
        existing_order = result.scalar_one_or_none()

        if existing_order:
            print(f'  Order already exists: {existing_order.id}')
        else:
            print('  Creating StockX order...')
            stockx_order = StockXOrder(
                listing_id=inventory_item.id,
                stockx_order_number=sale_data['stockx_order_number'],
                sale_price=sale_data['gross_sale'],
                net_proceeds=sale_data['net_sale'],
                gross_profit=sale_data['profit'],
                net_profit=sale_data['profit'],
                roi=sale_data['roi'],
                order_status='completed',
                sold_at=sale_data['sale_date']
            )
            session.add(stockx_order)
            await session.flush()
            print(f'  Order created: {stockx_order.id}')

        await session.commit()

        print('\n' + '=' * 80)
        print('SUCCESS: All data saved to PostgreSQL!')
        print('=' * 80)
        print(f'Supplier: {supplier.name}')
        print(f'Product: {product.name}')
        print(f'Size: {sale_data["size_value"]} {sale_data["size_type"]}')
        print(f'Purchase Price: {sale_data["net_buy"]} EUR')
        print(f'Sale Price: {sale_data["net_sale"]} EUR')
        print(f'Profit: {sale_data["profit"]} EUR ({sale_data["roi"]*100}% ROI)')

    await db_manager.close()

if __name__ == '__main__':
    asyncio.run(insert_sale())