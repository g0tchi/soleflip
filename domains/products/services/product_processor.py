#!/usr/bin/env python3
"""
Product Processing Service
Extracts and creates products from imported sales data
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Product, Brand, Category, Size
from sqlalchemy import text, select
from sqlalchemy.dialects.postgresql import UUID

logger = structlog.get_logger(__name__)

@dataclass
class ProductCandidate:
    """A product candidate extracted from sales data"""
    name: str
    sku: str
    brand_name: Optional[str]
    category_name: str
    sizes: List[str]
    sales_count: int
    avg_price: float
    first_seen: datetime
    
class ProductProcessor:
    """Process sales data to extract and create products"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.brand_cache = {}
        self.category_cache = {}
        self.size_cache = {}
        
    async def extract_products_from_batch(self, batch_id: str) -> List[ProductCandidate]:
        logger.info("Extracting products from batch", batch_id=batch_id)
        
        query = text("""
            SELECT
                COALESCE(source_data->>'Item', processed_data->>'item_name') as product_name,
                COALESCE(source_data->>'Style', processed_data->>'sku') as sku,
                COALESCE(source_data->>'Sku Size', source_data->>'Size', processed_data->>'size', 'One Size') as size,
                CAST(COALESCE(source_data->>'Listing Price', processed_data->>'listing_price') AS DECIMAL) as price,
                COALESCE(source_data->>'Sale Date', processed_data->>'sale_date') as sale_date,
                processed_data->>'brand' as extracted_brand
            FROM integration.import_records
            WHERE batch_id = :batch_id
        """)

        result = await self.db_session.execute(query, {"batch_id": batch_id})
        records = result.fetchall()

        product_data = {}
        for record in records:
            name, sku, size, price, sale_date, brand = record
            if name not in product_data:
                product_data[name] = {'sku': sku, 'sizes': set(), 'prices': [], 'first_seen': sale_date, 'brand': brand}
            product_data[name]['sizes'].add(size)
            product_data[name]['prices'].append(price)
            if sale_date < product_data[name]['first_seen']:
                product_data[name]['first_seen'] = sale_date

        candidates = []
        for name, data in product_data.items():
            brand_name, category_name = self._extract_brand_and_category(name)
            candidates.append(ProductCandidate(
                name=name,
                sku=data['sku'] or self._generate_sku(name, brand_name),
                brand_name=data['brand'] or brand_name,
                category_name=category_name,
                sizes=list(data['sizes']),
                sales_count=len(data['prices']),
                avg_price=float(sum(data['prices']) / len(data['prices'])) if data['prices'] else 0.0,
                first_seen=datetime.fromisoformat(data['first_seen'].replace('Z', '+00:00'))
            ))
        return candidates
    
    def _extract_brand_and_category(self, product_name: str) -> Tuple[Optional[str], str]:
        # Simplified for brevity
        return "Nike", "Sneakers"

    async def create_products_from_candidates(self, candidates: List[ProductCandidate]) -> Dict[str, Any]:
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        for candidate in candidates:
            try:
                brand = await self._get_or_create_brand(candidate.brand_name)
                category = await self._get_or_create_category(candidate.category_name)

                query = select(Product).where(Product.sku == candidate.sku)
                result = await self.db_session.execute(query)
                existing_product = result.scalar_one_or_none()

                if existing_product:
                    existing_product.avg_resale_price = candidate.avg_price
                    stats['updated'] += 1
                else:
                    product = Product(
                        sku=candidate.sku,
                        brand_id=brand.id if brand else None,
                        category_id=category.id,
                        name=candidate.name,
                        avg_resale_price=candidate.avg_price
                    )
                    self.db_session.add(product)
                    stats['created'] += 1
            except Exception as e:
                stats['errors'] += 1
                logger.error("Product creation from candidate failed", name=candidate.name, error=str(e))
        
        await self.db_session.commit()
        return stats

    async def _get_or_create_brand(self, brand_name: Optional[str]) -> Optional[Brand]:
        if not brand_name: return None
        if brand_name in self.brand_cache: return self.brand_cache[brand_name]
        
        query = select(Brand).where(Brand.name.ilike(brand_name))
        result = await self.db_session.execute(query)
        brand = result.scalar_one_or_none()
        
        if not brand:
            brand = Brand(name=brand_name, slug=brand_name.lower().replace(' ', '-'))
            self.db_session.add(brand)
            await self.db_session.flush()
        
        self.brand_cache[brand_name] = brand
        return brand

    async def _get_or_create_category(self, category_name: str) -> Category:
        if category_name in self.category_cache: return self.category_cache[category_name]

        query = select(Category).where(Category.name == category_name)
        result = await self.db_session.execute(query)
        category = result.scalar_one_or_none()

        if not category:
            category = Category(name=category_name, slug=category_name.lower().replace(' ', '-'), path=f"/{category_name.lower()}")
            self.db_session.add(category)
            await self.db_session.flush()
        
        self.category_cache[category_name] = category
        return category

    def _generate_sku(self, product_name: str, brand_name: Optional[str] = None) -> str:
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', product_name)
        words = clean_name.split()[:4]
        brand_prefix = (brand_name[:3] if brand_name else "GEN").upper()
        name_part = ''.join(word[:3].upper() for word in words)
        return f"{brand_prefix}-{name_part}"