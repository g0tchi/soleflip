"""Quick check of enrichment status"""
import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv()

async def check():
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    async with engine.connect() as conn:
        result = await conn.execute(text(
            'SELECT COUNT(*) as enriched FROM products.products WHERE last_enriched_at IS NOT NULL'
        ))
        enriched = result.scalar()

        result2 = await conn.execute(text('SELECT COUNT(*) FROM products.products'))
        total = result2.scalar()

        print(f"Enriched products: {enriched} / {total} ({enriched/total*100:.1f}%)")

    await engine.dispose()

asyncio.run(check())
