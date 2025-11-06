"""
List all products that would be created from Notion sales
Useful for manual review before running bulk sync

Generates CSV with:
- SKU
- Brand
- Product Name (estimated)
- StockX Product ID (if found)
- Source: Notion Sale ID

Usage:
    python list_products_from_notion.py

Output:
    products_to_create.csv
"""
import asyncio
import csv
import httpx
from typing import Dict, Optional
import structlog

logger = structlog.get_logger(__name__)


class ProductDiscoveryService:
    """Discover products from Notion without inserting to DB"""

    def __init__(self):
        self.products = []
        self.api_client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        """Close HTTP client"""
        await self.api_client.aclose()

    async def get_stockx_product_info(self, sku: str) -> Optional[Dict]:
        """
        Get full StockX product information via API
        Returns product details including ID, name, brand, etc.
        """
        try:
            response = await self.api_client.get(
                "http://localhost:8000/api/v1/products/search-stockx",
                params={"query": sku, "pageSize": 1}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("products") and len(data["products"]) > 0:
                    product = data["products"][0]
                    attrs = product.get('productAttributes', {})
                    return {
                        'stockx_product_id': product.get('productId'),
                        'official_name': product.get('title'),
                        'brand': product.get('brand'),
                        'model': product.get('styleId'),
                        'colorway': attrs.get('colorway'),
                        'retail_price': attrs.get('retailPrice'),
                        'release_date': attrs.get('releaseDate'),
                        'url_key': product.get('urlKey'),
                    }

            logger.warning(f"StockX product not found: {sku}")
            return None

        except Exception as e:
            logger.error(f"StockX API error for {sku}: {e}")
            return None

    async def parse_notion_sale(self, notion_page: dict) -> Optional[Dict]:
        """Parse Notion page to extract product info"""
        props = notion_page.get('properties', {})

        # Extract SKU
        sku = None
        if 'Name' in props and props['Name'].get('title'):
            sku = props['Name']['title'][0]['text']['content']

        # Extract Sale ID for reference
        sale_id = None
        if 'Sale ID' in props and props['Sale ID'].get('rich_text'):
            sale_id = props['Sale ID']['rich_text'][0]['text']['content']

        # Extract Brand
        brand = None
        if 'Brand' in props and props['Brand'].get('select'):
            brand = props['Brand']['select']['name']

        if not sku:
            return None

        return {
            'sku': sku,
            'notion_brand': brand or 'Unknown',
            'notion_sale_id': sale_id,
        }

    async def discover_products(self):
        """
        Main method: Discover all unique products from Notion sales
        """
        logger.info("Discovering products from Notion sales...")

        # Fetch all StockX sales from Notion via MCP search
        logger.info("Searching Notion for StockX sales...")

        # We'll collect sales pages by searching for common patterns

        # Search for pages with "StockX" content - this will find sale pages
        logger.info("Fetching sales from Notion (this may take a moment)...")

        # For now, we'll use the search results as-is
        # In production, you'd want to search the specific sales database

        # Since we don't have direct MCP access in this script yet,
        # we'll keep the mock data but note that Notion has many sales
        logger.warning("Using sample data - in production, integrate Notion MCP search results")

        mock_notion_sales = [
            {
                'properties': {
                    'Name': {'title': [{'text': {'content': 'HQ4276'}}]},
                    'Sale ID': {'rich_text': [{'text': {'content': '55476797-55376556'}}]},
                    'Brand': {'select': {'name': 'Adidas'}},
                }
            },
        ]

        logger.info(f"Found {len(mock_notion_sales)} sales in Notion (sample data)")

        # Track unique SKUs
        seen_skus = set()

        for notion_page in mock_notion_sales:
            product_info = await self.parse_notion_sale(notion_page)

            if not product_info:
                continue

            sku = product_info['sku']

            # Skip if already processed
            if sku in seen_skus:
                continue

            seen_skus.add(sku)

            # Get StockX product details
            logger.info(f"Checking StockX for: {sku}")
            stockx_info = await self.get_stockx_product_info(sku)

            # Combine Notion + StockX data
            product_record = {
                'sku': sku,
                'notion_brand': product_info['notion_brand'],
                'notion_sale_id': product_info['notion_sale_id'],
                'stockx_found': 'Yes' if stockx_info else 'No',
                'stockx_product_id': stockx_info.get('stockx_product_id') if stockx_info else '',
                'stockx_official_name': stockx_info.get('official_name') if stockx_info else '',
                'stockx_brand': stockx_info.get('brand') if stockx_info else '',
                'stockx_colorway': stockx_info.get('colorway') if stockx_info else '',
                'stockx_retail_price': stockx_info.get('retail_price') if stockx_info else '',
                'stockx_release_date': stockx_info.get('release_date') if stockx_info else '',
                'stockx_url': f"https://stockx.com/{stockx_info.get('url_key')}" if stockx_info and stockx_info.get('url_key') else '',
                'brand_mismatch': 'Yes' if stockx_info and product_info['notion_brand'].lower() != stockx_info.get('brand', '').lower() else 'No',
            }

            self.products.append(product_record)

            # Rate limiting for StockX API
            await asyncio.sleep(0.15)

        logger.info(f"Discovered {len(self.products)} unique products")

    def export_to_csv(self, filename: str = 'products_to_create.csv'):
        """Export products to CSV for manual review"""
        if not self.products:
            logger.warning("No products to export")
            return

        fieldnames = [
            'sku',
            'notion_brand',
            'notion_sale_id',
            'stockx_found',
            'stockx_product_id',
            'stockx_official_name',
            'stockx_brand',
            'stockx_colorway',
            'stockx_retail_price',
            'stockx_release_date',
            'stockx_url',
            'brand_mismatch',
        ]

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for product in self.products:
                writer.writerow(product)

        logger.info(f"Exported {len(self.products)} products to {filename}")

        # Print summary statistics
        print("\n" + "=" * 80)
        print("PRODUCT DISCOVERY SUMMARY")
        print("=" * 80)
        print(f"Total unique products:           {len(self.products)}")

        found_on_stockx = sum(1 for p in self.products if p['stockx_found'] == 'Yes')
        print(f"Found on StockX:                 {found_on_stockx} ({found_on_stockx/len(self.products)*100:.1f}%)")

        not_found = len(self.products) - found_on_stockx
        print(f"NOT found on StockX:             {not_found} ({not_found/len(self.products)*100:.1f}%)")

        brand_mismatches = sum(1 for p in self.products if p['brand_mismatch'] == 'Yes')
        print(f"Brand mismatches:                {brand_mismatches}")

        print(f"\nCSV exported: {filename}")
        print("=" * 80)

        # Show sample of products not found
        if not_found > 0:
            print("\nSample products NOT found on StockX:")
            print("-" * 80)
            not_found_list = [p for p in self.products if p['stockx_found'] == 'No']
            for product in not_found_list[:10]:
                print(f"  • {product['sku']} ({product['notion_brand']}) - Sale: {product['notion_sale_id']}")
            if len(not_found_list) > 10:
                print(f"  ... and {len(not_found_list) - 10} more")
            print("-" * 80)

        # Show sample of brand mismatches
        if brand_mismatches > 0:
            print("\nBrand mismatches (Notion vs StockX):")
            print("-" * 80)
            mismatch_list = [p for p in self.products if p['brand_mismatch'] == 'Yes']
            for product in mismatch_list[:10]:
                print(f"  • {product['sku']}: Notion={product['notion_brand']} vs StockX={product['stockx_brand']}")
            if len(mismatch_list) > 10:
                print(f"  ... and {len(mismatch_list) - 10} more")
            print("-" * 80)


async def main():
    """Entry point"""
    service = ProductDiscoveryService()

    try:
        print("Starting product discovery...")
        print("NOTE: API server must be running on localhost:8000")
        print()

        await service.discover_products()
        service.export_to_csv('products_to_create.csv')

        print("\n[OK] Product list generated successfully!")
        print("\nNext steps:")
        print("1. Open products_to_create.csv in Excel/Google Sheets")
        print("2. Review products with 'stockx_found = No'")
        print("3. Review products with 'brand_mismatch = Yes'")
        print("4. Decide if those products should be created or skipped")
        print("5. Run bulk_sync_notion_sales.py to execute sync")

    finally:
        await service.close()


if __name__ == '__main__':
    asyncio.run(main())