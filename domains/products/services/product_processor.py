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

from shared.database.connection import db_manager
from shared.database.models import Product, Brand, Category, Size
from sqlalchemy import text, select
from sqlalchemy.dialects.postgresql import UUID

logger = structlog.get_logger(__name__)

@dataclass
class ProductCandidate:
    """A product candidate extracted from sales data"""
    name: str
    sku: str  # Original SKU from StockX
    brand_name: Optional[str]
    category_name: str
    sizes: List[str]
    sales_count: int
    avg_price: float
    first_seen: datetime
    
class ProductProcessor:
    """Process sales data to extract and create products"""
    
    def __init__(self):
        self.brand_cache = {}
        self.category_cache = {}
        self.size_cache = {}
        
    async def extract_products_from_batch(self, batch_id: str) -> List[ProductCandidate]:
        """Extract unique products from a specific import batch"""
        logger.info("Extracting products from batch", batch_id=batch_id)
        
        async with db_manager.get_session() as db:
            # Get all records from batch with product info
            # Handle both StockX and Alias data formats with brand prioritization
            query = text("""
                SELECT 
                    COALESCE(
                        source_data->>'Item', 
                        processed_data->>'item_name', 
                        processed_data->>'product_name',
                        source_data->>'NAME'
                    ) as product_name,
                    COALESCE(
                        source_data->>'Style', 
                        processed_data->>'sku', 
                        source_data->>'SKU',
                        ''
                    ) as sku,
                    COALESCE(
                        source_data->>'Sku Size', 
                        source_data->>'Size', 
                        processed_data->>'size',
                        source_data->>'SIZE',
                        'One Size'
                    ) as size,
                    CAST(COALESCE(
                        source_data->>'Listing Price', 
                        processed_data->>'listing_price',
                        processed_data->>'sale_price',
                        source_data->>'PRODUCT_PRICE_CENTS_SALE_PRICE'
                    ) AS DECIMAL) as price,
                    COALESCE(
                        source_data->>'Sale Date', 
                        processed_data->>'sale_date',
                        source_data->>'CREDIT_DATE'
                    ) as sale_date,
                    COALESCE(
                        processed_data->>'brand',
                        ''
                    ) as extracted_brand,
                    COALESCE(
                        processed_data->>'source_platform',
                        'unknown'
                    ) as source_platform,
                    COALESCE(
                        processed_data->>'name_source',
                        'original'
                    ) as name_source,
                    COUNT(*) as sales_count,
                    AVG(CAST(COALESCE(
                        source_data->>'Listing Price', 
                        processed_data->>'listing_price',
                        processed_data->>'sale_price',
                        source_data->>'PRODUCT_PRICE_CENTS_SALE_PRICE'
                    ) AS DECIMAL)) as avg_price,
                    MIN(COALESCE(
                        source_data->>'Sale Date', 
                        processed_data->>'sale_date',
                        source_data->>'CREDIT_DATE'
                    )) as first_seen
                FROM integration.import_records 
                WHERE batch_id = :batch_id
                  AND (
                    source_data->>'Item' IS NOT NULL OR 
                    processed_data->>'item_name' IS NOT NULL OR 
                    processed_data->>'product_name' IS NOT NULL OR
                    source_data->>'NAME' IS NOT NULL
                  )
                  AND (
                    source_data->>'Listing Price' IS NOT NULL OR 
                    processed_data->>'listing_price' IS NOT NULL OR
                    processed_data->>'sale_price' IS NOT NULL OR
                    source_data->>'PRODUCT_PRICE_CENTS_SALE_PRICE' IS NOT NULL
                  )
                GROUP BY 
                    COALESCE(source_data->>'Item', processed_data->>'item_name', processed_data->>'product_name', source_data->>'NAME'),
                    COALESCE(source_data->>'Style', processed_data->>'sku', source_data->>'SKU', ''),
                    COALESCE(source_data->>'Sku Size', source_data->>'Size', processed_data->>'size', source_data->>'SIZE', 'One Size'),
                    COALESCE(source_data->>'Listing Price', processed_data->>'listing_price', processed_data->>'sale_price', source_data->>'PRODUCT_PRICE_CENTS_SALE_PRICE'),
                    COALESCE(source_data->>'Sale Date', processed_data->>'sale_date', source_data->>'CREDIT_DATE'),
                    COALESCE(processed_data->>'brand', ''),
                    COALESCE(processed_data->>'source_platform', 'unknown'),
                    COALESCE(processed_data->>'name_source', 'original')
                ORDER BY product_name, sales_count DESC
            """)
            
            result = await db.execute(query, {"batch_id": batch_id})
            records = result.fetchall()
            
            # Group by product name and aggregate
            product_data = {}
            
            for record in records:
                product_name = record[0]
                sku = record[1] or ""
                size = record[2] or "One Size"
                price = float(record[3]) if record[3] else 0.0
                sale_date = record[4]
                extracted_brand = record[5] or ""
                source_platform = record[6] or "unknown"
                name_source = record[7] or "original"
                sales_count = record[8]
                
                if product_name not in product_data:
                    # Clean up the SKU - handle None, nan, empty strings
                    clean_sku = sku
                    if not sku or sku.strip() == '' or sku.lower() in ['none', 'nan', 'null']:
                        # Generate SKU from brand and product name
                        # Use extracted brand from Alias if available, otherwise extract from name
                        brand_name = extracted_brand if extracted_brand else self._extract_brand_and_category(product_name)[0]
                        clean_sku = self._generate_sku(product_name, brand_name)
                        logger.debug("Generated SKU for product", 
                                   product=product_name, 
                                   original_sku=sku, 
                                   generated_sku=clean_sku,
                                   brand_source="extracted" if extracted_brand else "inferred")
                    else:
                        logger.debug("Using original SKU", 
                                   product=product_name, 
                                   sku=clean_sku)
                    
                    product_data[product_name] = {
                        'sku': clean_sku,  # Store the cleaned original or generated SKU 
                        'sizes': set(),
                        'prices': [],
                        'sales_count': 0,
                        'first_seen': sale_date,
                        'extracted_brand': extracted_brand,
                        'source_platform': source_platform,
                        'name_source': name_source
                    }
                
                product_data[product_name]['sizes'].add(size)
                product_data[product_name]['prices'].append(price)
                product_data[product_name]['sales_count'] += sales_count
                
                # Keep earliest date
                if sale_date < product_data[product_name]['first_seen']:
                    product_data[product_name]['first_seen'] = sale_date
            
            # Convert to ProductCandidate objects
            candidates = []
            for name, data in product_data.items():
                # Use extracted brand if available (from Alias), otherwise extract from name
                if data.get('extracted_brand'):
                    brand_name = data['extracted_brand']
                    _, category_name = self._extract_brand_and_category(name)
                    logger.debug("Using extracted brand", 
                               product=name, 
                               brand=brand_name, 
                               source=data.get('source_platform', 'unknown'))
                else:
                    brand_name, category_name = self._extract_brand_and_category(name)
                    logger.debug("Using inferred brand", 
                               product=name, 
                               brand=brand_name)
                
                candidate = ProductCandidate(
                    name=name,
                    sku=data['sku'],  # Use original or generated SKU
                    brand_name=brand_name,
                    category_name=category_name,
                    sizes=list(data['sizes']),
                    sales_count=data['sales_count'],
                    avg_price=sum(data['prices']) / len(data['prices']) if data['prices'] else 0.0,
                    first_seen=datetime.fromisoformat(data['first_seen'].replace('Z', '+00:00'))
                )
                candidates.append(candidate)
            
            logger.info("Product extraction complete", 
                       candidates=len(candidates),
                       batch_id=batch_id)
            
            return candidates
    
    def _extract_brand_and_category(self, product_name: str) -> Tuple[Optional[str], str]:
        """Extract brand and category from product name"""
        name_lower = product_name.lower()
        
        # Extended brands from reference data
        brands = {
            'nike': ['nike', 'air jordan', 'jordan'],
            'jordan': ['jordan', 'air jordan'],
            'adidas': ['adidas', 'yeezy'],
            'yeezy': ['yeezy'],
            'new balance': ['new balance'],
            'asics': ['asics'],
            'vans': ['vans'],
            'converse': ['converse'],
            'puma': ['puma'],
            'reebok': ['reebok'],
            'under armour': ['under armour'],
            'balenciaga': ['balenciaga'],
            'gucci': ['gucci'],
            'louis vuitton': ['louis vuitton', 'lv'],
            'dior': ['dior'],
            'prada': ['prada'],
            'off-white': ['off-white', 'off white'],
            'supreme': ['supreme'],
            'stone island': ['stone island'],
            'a bathing ape': ['bape', 'bathing ape'],
            'golden goose': ['golden goose'],
            'common projects': ['common projects'],
            'maison margiela': ['margiela', 'maison margiela'],
            'birkenstock': ['birkenstock'],
            'hugo boss': ['hugo boss', 'boss'],
            'crocs': ['crocs'],
            'balmain': ['balmain'],
            'comme des garcons': ['comme des garcons', 'cdg', 'comme des garcons play'],
            'hoka': ['hoka', 'hoka one one']
        }
        
        brand_name = None
        for brand, keywords in brands.items():
            if any(keyword in name_lower for keyword in keywords):
                brand_name = brand.title()
                break
        
        # Enhanced category detection based on reference data
        if any(word in name_lower for word in ['dunk', 'air max', 'jordan', 'sneaker', 'shoe', 'slides', 'yeezy', 'boost', 'foam', 'runner', 'gazelle', 'samba', 'stan smith', 'superstar', 'continental', 'forum', 'campus', 'clog', 'clifton', 'speedgoat', 'bondi', 'arahi']):
            category = 'Footwear'
        elif any(word in name_lower for word in ['bag', 'backpack', 'wallet', 'tote', 'belt', 'watch']):
            category = 'Accessories'
        elif any(word in name_lower for word in ['shirt', 't-shirt', 'hoodie', 'sweatshirt', 'jacket', 'sweatpants', 'tee', 'polo']):
            category = 'Apparel'
        elif any(word in name_lower for word in ['lego', 'toy', 'figure', 'construx', 'collectible']):
            category = 'Collectibles'
        elif 'book' in name_lower:
            category = 'Books'
        else:
            category = 'Other'
            
        return brand_name, category
    
    async def create_products_from_candidates(self, candidates: List[ProductCandidate]) -> Dict[str, Any]:
        """Create actual Product records from candidates"""
        logger.info("Creating products from candidates", count=len(candidates))
        
        stats = {
            'brands_created': 0,
            'categories_created': 0,
            'products_created': 0,
            'products_updated': 0,
            'errors': []
        }
        
        async with db_manager.get_session() as db:
            for candidate in candidates:
                try:
                    # Get or create brand
                    brand = await self._get_or_create_brand(db, candidate.brand_name)
                    if brand and candidate.brand_name:
                        stats['brands_created'] += 1
                    
                    # Get or create category
                    category = await self._get_or_create_category(db, candidate.category_name)
                    if category:
                        stats['categories_created'] += 1
                    
                    # Use the candidate SKU (already cleaned in extract phase)
                    sku = candidate.sku
                    # Double-check for edge cases
                    if not sku or sku.lower() in ['none', 'nan', 'null']:
                        sku = self._generate_sku(candidate.name, candidate.brand_name)
                        logger.warning("Had to regenerate SKU during product creation", 
                                     product=candidate.name, sku=sku)
                    
                    # Check if product already exists
                    existing_query = select(Product).where(Product.sku == sku)
                    result = await db.execute(existing_query)
                    existing_product = result.scalar_one_or_none()
                    
                    if existing_product:
                        # Update existing product
                        existing_product.name = candidate.name
                        existing_product.avg_resale_price = candidate.avg_price  # Update with new average
                        stats['products_updated'] += 1
                        logger.debug("Updated existing product", sku=sku, name=candidate.name)
                    else:
                        # Create new product
                        product = Product(
                            sku=sku,
                            brand_id=brand.id if brand else None,
                            category_id=category.id,
                            name=candidate.name,
                            retail_price=None,  # To be filled later with real UVP data
                            avg_resale_price=candidate.avg_price,  # StockX average price
                            # Note: We'll handle sizes separately in inventory
                        )
                        db.add(product)
                        stats['products_created'] += 1
                        logger.debug("Created new product", sku=sku, name=candidate.name)
                    
                    
                except Exception as e:
                    error_msg = f"Failed to create product '{candidate.name}': {str(e)}"
                    stats['errors'].append(error_msg)
                    logger.error("Product creation failed", 
                               product=candidate.name, 
                               error=str(e))
            
            # Commit all changes at once
            try:
                await db.commit()
                logger.info("All product changes committed successfully")
            except Exception as e:
                await db.rollback()
                logger.error("Failed to commit product changes", error=str(e))
                # Mark all as errors since rollback happened
                stats['errors'].append(f"Database commit failed: {str(e)}")
                stats['products_created'] = 0
                stats['products_updated'] = 0
        
        logger.info("Product creation complete", **stats)
        return stats
    
    async def _get_or_create_brand(self, db, brand_name: Optional[str]) -> Optional[Brand]:
        """Get existing brand or create new one"""
        if not brand_name:
            return None
            
        if brand_name in self.brand_cache:
            return self.brand_cache[brand_name]
        
        # Check if brand exists (case-insensitive)
        query = select(Brand).where(Brand.name.ilike(brand_name))
        result = await db.execute(query)
        brand = result.scalar_one_or_none()
        
        if not brand:
            # Also check by slug to avoid duplicates
            slug = brand_name.lower().replace(' ', '-').replace('&', 'and')
            slug_query = select(Brand).where(Brand.slug == slug)
            slug_result = await db.execute(slug_query)
            brand = slug_result.scalar_one_or_none()
            
            if not brand:
                # Create new brand only if neither name nor slug exists
                brand = Brand(
                    name=brand_name,
                    slug=slug
                )
                db.add(brand)
                await db.flush()  # Get ID without committing
        
        self.brand_cache[brand_name] = brand
        return brand
    
    async def _get_or_create_category(self, db, category_name: str) -> Category:
        """Get existing category or create new one"""
        if category_name in self.category_cache:
            return self.category_cache[category_name]
        
        # Check if category exists
        query = select(Category).where(Category.name == category_name)
        result = await db.execute(query)
        category = result.scalar_one_or_none()
        
        if not category:
            # Create new category
            slug = category_name.lower().replace(' ', '-')
            category = Category(
                name=category_name,
                slug=slug,
                path=f"/{slug}"
            )
            db.add(category)
            await db.flush()  # Get ID without committing
        
        self.category_cache[category_name] = category
        return category
    
    def _generate_sku(self, product_name: str, brand_name: Optional[str] = None) -> str:
        """Generate unique SKU for product"""
        # Clean name for SKU
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', product_name)
        words = clean_name.split()[:4]  # Max 4 words
        
        if brand_name:
            brand_prefix = brand_name[:3].upper()
        else:
            brand_prefix = "GEN"  # Generic
        
        name_part = ''.join(word[:3].upper() for word in words)
        
        return f"{brand_prefix}-{name_part}"