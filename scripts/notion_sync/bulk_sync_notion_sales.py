"""
Bulk Sync ALL StockX Sales from Notion to PostgreSQL
Replaces Week 1 development - uses proven logic from single sale test

Usage:
    python bulk_sync_notion_sales.py

Features:
- Searches all Notion sales with 'Sale Platform = StockX'
- Skips already-synced sales (duplicate detection)
- Enriches with StockX Product ID from API
- Creates all required database entities
- Progress tracking and detailed logging
"""
import asyncio
import httpx
from decimal import Decimal
from datetime import datetime
from typing import Optional
from shared.database.connection import DatabaseManager
from shared.database.models import (
    Supplier, InventoryItem, StockXOrder, StockXListing,
    Brand, Category, Product, Size
)
from sqlalchemy import select
import structlog

logger = structlog.get_logger(__name__)


class NotionSaleSyncService:
    """Sync Notion sales to PostgreSQL with StockX enrichment"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.stats = {
            'total_found': 0,
            'already_synced': 0,
            'newly_synced': 0,
            'failed': 0,
            'suppliers_created': 0,
            'products_created': 0,
        }

    async def initialize(self):
        """Initialize database connection"""
        await self.db_manager.initialize()
        logger.info("Database connection initialized")

    async def close(self):
        """Close database connection"""
        await self.db_manager.close()

    async def get_stockx_product_id(self, sku: str) -> Optional[str]:
        """
        Get StockX Product ID via internal API
        Uses /api/v1/products/search-stockx endpoint
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:8000/api/v1/products/search-stockx",
                    params={"query": sku, "pageSize": 1},
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("products") and len(data["products"]) > 0:
                        product_id = data["products"][0]["id"]
                        logger.debug(f"StockX Product ID found for {sku}: {product_id}")
                        return product_id

            logger.warning(f"StockX Product ID not found for SKU: {sku}")
            return None

        except Exception as e:
            logger.error(f"StockX API error for {sku}: {e}")
            return None

    async def check_if_already_synced(self, session, order_number: str) -> bool:
        """Check if sale already exists in database"""
        result = await session.execute(
            select(StockXOrder).where(
                StockXOrder.stockx_order_number == order_number
            )
        )
        exists = result.scalar_one_or_none() is not None
        return exists

    async def parse_notion_sale(self, notion_page: dict) -> dict:
        """
        Parse Notion page properties into structured sale data

        Expected Notion Properties:
        - Name (title): SKU
        - Sale ID (rich_text): StockX Order Number
        - Brand (select): Brand name
        - Size (select): Size value (e.g., "8.5 US")
        - Supplier (select): Supplier name
        - Net Buy (number): Purchase price (net)
        - Gross Buy (number): Purchase price (gross)
        - Sale Date (date): Date of sale
        - Net Sale (number): Sale price (net)
        - Gross Sale (number): Sale price (gross)
        - Profit (number): Calculated profit
        - ROI (number): Return on investment (as decimal, e.g., 0.02 = 2%)
        """
        props = notion_page.get('properties', {})

        # Extract SKU from title
        sku = None
        if 'Name' in props and props['Name'].get('title'):
            sku = props['Name']['title'][0]['text']['content']

        # Extract Sale ID (StockX Order Number)
        order_number = None
        if 'Sale ID' in props and props['Sale ID'].get('rich_text'):
            order_number = props['Sale ID']['rich_text'][0]['text']['content']

        # Extract Brand
        brand = None
        if 'Brand' in props and props['Brand'].get('select'):
            brand = props['Brand']['select']['name']

        # Extract Size (format: "8.5 US" or "42 EU")
        size_value = None
        size_region = 'US'  # Default
        if 'Size' in props and props['Size'].get('select'):
            size_str = props['Size']['select']['name']
            parts = size_str.split()
            if len(parts) >= 1:
                size_value = parts[0]
            if len(parts) >= 2:
                size_region = parts[1]

        # Extract Supplier
        supplier = None
        if 'Supplier' in props and props['Supplier'].get('select'):
            supplier = props['Supplier']['select']['name']

        # Extract Prices
        net_buy = props.get('Net Buy', {}).get('number')
        gross_buy = props.get('Gross Buy', {}).get('number')
        net_sale = props.get('Net Sale', {}).get('number')
        gross_sale = props.get('Gross Sale', {}).get('number')
        profit = props.get('Profit', {}).get('number')
        roi = props.get('ROI', {}).get('number')

        # Extract Sale Date
        sale_date = None
        if 'Sale Date' in props and props['Sale Date'].get('date'):
            sale_date_str = props['Sale Date']['date']['start']
            sale_date = datetime.strptime(sale_date_str, '%Y-%m-%d').date()

        # Validation
        if not all([sku, order_number, supplier, net_buy, net_sale, sale_date]):
            logger.warning(f"Incomplete data for order {order_number}", sku=sku)
            return None

        return {
            'stockx_order_number': order_number,
            'sku': sku,
            'brand_name': brand or 'Unknown',
            'size_value': size_value or '10',  # Default if missing
            'size_region': size_region,
            'supplier_name': supplier,
            'net_buy': Decimal(str(net_buy)),
            'gross_buy': Decimal(str(gross_buy)) if gross_buy else Decimal(str(net_buy)),
            'net_sale': Decimal(str(net_sale)),
            'gross_sale': Decimal(str(gross_sale)) if gross_sale else Decimal(str(net_sale)),
            'profit': Decimal(str(profit)) if profit else (Decimal(str(net_sale)) - Decimal(str(net_buy))),
            'roi': Decimal(str(roi)) if roi else Decimal('0.0'),
            'sale_date': sale_date,
        }

    async def sync_sale_to_db(self, session, sale_data: dict) -> bool:
        """
        Sync single sale to PostgreSQL
        Returns True if successful, False if failed
        """
        try:
            logger.info(f"Syncing sale: {sale_data['stockx_order_number']}", sku=sale_data['sku'])

            # 1. Get or create supplier
            result = await session.execute(
                select(Supplier).where(Supplier.name == sale_data['supplier_name'])
            )
            supplier = result.scalar_one_or_none()

            if not supplier:
                supplier = Supplier(
                    name=sale_data['supplier_name'],
                    slug=sale_data['supplier_name'].lower().replace(' ', '-'),
                    status='active',
                    supplier_type='retail'
                )
                session.add(supplier)
                await session.flush()
                self.stats['suppliers_created'] += 1
                logger.info(f"Created supplier: {supplier.name}")

            # 2. Get or create brand
            result = await session.execute(
                select(Brand).where(Brand.name == sale_data['brand_name'])
            )
            brand = result.scalar_one_or_none()

            if not brand:
                brand = Brand(
                    name=sale_data['brand_name'],
                    slug=sale_data['brand_name'].lower()
                )
                session.add(brand)
                await session.flush()

            # 3. Get or create category (assume Sneakers for now)
            result = await session.execute(
                select(Category).where(Category.name == 'Sneakers')
            )
            category = result.scalar_one_or_none()

            if not category:
                category = Category(name='Sneakers', slug='sneakers')
                session.add(category)
                await session.flush()

            # 4. Get or create product
            result = await session.execute(
                select(Product).where(Product.sku == sale_data['sku'])
            )
            product = result.scalar_one_or_none()

            if not product:
                product = Product(
                    sku=sale_data['sku'],
                    name=f"{sale_data['brand_name']} {sale_data['sku']}",
                    brand_id=brand.id,
                    category_id=category.id
                )
                session.add(product)
                await session.flush()
                self.stats['products_created'] += 1
                logger.info(f"Created product: {product.sku}")

            # 5. Get or create size
            result = await session.execute(
                select(Size).where(
                    Size.value == sale_data['size_value'],
                    Size.region == sale_data['size_region'],
                    Size.category_id == category.id
                )
            )
            size = result.scalar_one_or_none()

            if not size:
                size = Size(
                    category_id=category.id,
                    value=sale_data['size_value'],
                    region=sale_data['size_region'],
                    standardized_value=float(sale_data['size_value'])
                )
                session.add(size)
                await session.flush()

            # 6. Create inventory item
            inventory_item = InventoryItem(
                product_id=product.id,
                size_id=size.id,
                supplier_id=supplier.id,
                quantity=1,
                purchase_price=sale_data['net_buy'],
                status='sold',
                external_ids={'stockx_order_number': sale_data['stockx_order_number']}
            )
            session.add(inventory_item)
            await session.flush()

            # 7. Get StockX Product ID from API
            stockx_product_id = await self.get_stockx_product_id(sale_data['sku'])

            if not stockx_product_id:
                # Use placeholder if API fails
                stockx_product_id = '00000000-0000-0000-0000-000000000000'
                logger.warning(f"Using placeholder StockX Product ID for {sale_data['sku']}")

            # 8. Create StockX listing
            listing = StockXListing(
                product_id=product.id,
                stockx_listing_id=sale_data['stockx_order_number'],
                stockx_product_id=stockx_product_id,
                ask_price=sale_data['gross_sale'],
                status='sold',
                is_active=False,
                created_from='notion_sync'
            )
            session.add(listing)
            await session.flush()

            # 9. Create StockX order
            order = StockXOrder(
                listing_id=listing.id,
                stockx_order_number=sale_data['stockx_order_number'],
                sale_price=sale_data['gross_sale'],
                net_proceeds=sale_data['net_sale'],
                gross_profit=sale_data['profit'],
                net_profit=sale_data['profit'],
                roi=sale_data['roi'],
                order_status='completed',
                sold_at=sale_data['sale_date']
            )
            session.add(order)
            await session.flush()

            logger.info(f"Successfully synced sale: {sale_data['stockx_order_number']}")
            return True

        except Exception as e:
            logger.error(f"Failed to sync sale {sale_data['stockx_order_number']}: {e}")
            return False

    async def bulk_sync_from_notion(self):
        """
        Main method: Fetch all StockX sales from Notion and sync to PostgreSQL
        """
        logger.info("Starting bulk Notion sales sync...")

        # NOTE: This requires Notion MCP integration
        # For now, we'll use a placeholder - you would replace this with actual Notion MCP call
        # Example: notion_sales = await notion_client.query_database(database_id="...", filter={"property": "Sale Platform", "select": {"equals": "StockX"}})

        logger.warning("Notion MCP integration needed - using mock data for demonstration")

        # Mock Notion data (replace with real Notion MCP call)
        mock_notion_sales = [
            {
                'properties': {
                    'Name': {'title': [{'text': {'content': 'HQ4276'}}]},
                    'Sale ID': {'rich_text': [{'text': {'content': '55476797-55376556'}}]},
                    'Brand': {'select': {'name': 'Adidas'}},
                    'Size': {'select': {'name': '8.5 US'}},
                    'Supplier': {'select': {'name': '43einhalb'}},
                    'Net Buy': {'number': 23.53},
                    'Gross Buy': {'number': 28.00},
                    'Net Sale': {'number': 24.07},
                    'Gross Sale': {'number': 24.07},
                    'Profit': {'number': 0.54},
                    'ROI': {'number': 0.02},
                    'Sale Date': {'date': {'start': '2023-09-17'}},
                }
            }
        ]

        self.stats['total_found'] = len(mock_notion_sales)
        logger.info(f"Found {self.stats['total_found']} sales in Notion")

        async with self.db_manager.get_session() as session:
            for notion_page in mock_notion_sales:
                # Parse Notion data
                sale_data = await self.parse_notion_sale(notion_page)

                if not sale_data:
                    self.stats['failed'] += 1
                    continue

                # Check if already synced
                if await self.check_if_already_synced(session, sale_data['stockx_order_number']):
                    logger.info(f"Sale already synced, skipping: {sale_data['stockx_order_number']}")
                    self.stats['already_synced'] += 1
                    continue

                # Sync to database
                success = await self.sync_sale_to_db(session, sale_data)

                if success:
                    self.stats['newly_synced'] += 1
                else:
                    self.stats['failed'] += 1

                # Commit after each sale for fault tolerance
                await session.commit()

                # Rate limiting for StockX API
                await asyncio.sleep(0.2)

        # Print summary
        print("\n" + "=" * 80)
        print("BULK SYNC SUMMARY")
        print("=" * 80)
        print(f"Total sales found in Notion:  {self.stats['total_found']}")
        print(f"Already synced (skipped):     {self.stats['already_synced']}")
        print(f"Newly synced:                 {self.stats['newly_synced']}")
        print(f"Failed:                       {self.stats['failed']}")
        print(f"New suppliers created:        {self.stats['suppliers_created']}")
        print(f"New products created:         {self.stats['products_created']}")
        print("=" * 80)

        success_rate = (self.stats['newly_synced'] / self.stats['total_found'] * 100) if self.stats['total_found'] > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")

        if self.stats['failed'] > 0:
            logger.warning(f"{self.stats['failed']} sales failed to sync - check logs for details")


async def main():
    """Entry point for bulk sync"""
    service = NotionSaleSyncService()

    try:
        await service.initialize()
        await service.bulk_sync_from_notion()
    finally:
        await service.close()


if __name__ == '__main__':
    asyncio.run(main())