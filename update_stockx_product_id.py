"""
Update StockX Product ID from placeholder to real ID retrieved from API
"""
import asyncio
from shared.database.connection import DatabaseManager
from sqlalchemy import text

async def update_stockx_product_id():
    db_manager = DatabaseManager()
    await db_manager.initialize()

    async with db_manager.get_session() as session:
        print('=' * 80)
        print('Updating StockX Product ID with real value from API')
        print('=' * 80)

        # Update the placeholder with real StockX Product ID
        result = await session.execute(
            text('''
                UPDATE platforms.stockx_listings
                SET stockx_product_id = :real_id
                WHERE stockx_listing_id = :listing_id
                RETURNING id, stockx_product_id, stockx_listing_id
            '''),
            {
                'real_id': 'fa671f11-b94d-4596-a4fe-d91e0bd995a0',
                'listing_id': '55476797-55376556'
            }
        )

        updated = result.fetchone()
        await session.commit()

        if updated:
            print('\nSUCCESS: StockX Product ID updated')
            print(f'Listing ID: {updated[0]}')
            print(f'StockX Order Number: {updated[2]}')
            print(f'New StockX Product ID: {updated[1]}')
        else:
            print('ERROR: No listing found with that order number')

        print('=' * 80)

    await db_manager.close()

if __name__ == '__main__':
    asyncio.run(update_stockx_product_id())