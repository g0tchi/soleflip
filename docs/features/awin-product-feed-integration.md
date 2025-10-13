# Awin Product Feed Integration

**Version:** 2.2.9
**Date:** October 11, 2025
**Status:** In Development 🚧

## Overview

Integration with Awin Affiliate Network product feeds to automatically import retail product data from partner stores (size?, JD Sports, Footlocker, etc.). This enables automatic discovery of products available at retail prices for comparison with StockX resale prices.

## Feed Analysis

### Sample Feed Statistics
- **Total Products:** 1,150 items (from size?Official DE)
- **Format:** CSV (gzip compressed)
- **Update Frequency:** Daily
- **Language:** German (de)
- **Categories:** Footwear (Men's & Women's)

### Available Data Fields

#### Product Identification
- `product_name` - Product title (e.g., "ASICS GT-2160 Damen, weiss")
- `aw_product_id` - Awin unique product ID
- `merchant_product_id` - Merchant SKU/ID
- `ean` - EAN barcode (critical for matching with StockX)
- `product_GTIN` - Global Trade Item Number
- `mpn` - Manufacturer Part Number
- `product_model` - Model identifier

#### Brand & Category
- `brand_name` - Brand name (e.g., "ASICS")
- `brand_id` - Awin brand ID
- `merchant_category` - Merchant's category
- `merchant_product_category_path` - Full category path
- `category_name` - Main category (e.g., "Women's Footwear")
- `category_id` - Awin category ID

#### Pricing
- `search_price` - Retail price (e.g., 130.00)
- `store_price` - Store price (if different)
- `rrp_price` - Recommended retail price
- `display_price` - Formatted price (e.g., "EUR130.00")
- `product_price_old` - Previous price
- `saving` - Discount amount
- `savings_percent` - Discount percentage
- `currency` - Currency code (EUR)

#### Product Details
- `description` - Full product description
- `product_short_description` - Short description
- `colour` - Color name (e.g., "weiss", "Gold")
- `Fashion:size` - Size (e.g., "36", "44.5")
- `Fashion:material` - Material information
- `Fashion:pattern` - Pattern details
- `condition` - Product condition (new/used)
- `dimensions` - Product dimensions
- `keywords` - Search keywords

#### Availability
- `in_stock` - Stock status (0/1)
- `stock_quantity` - Available quantity
- `stock_status` - Stock status text
- `size_stock_status` - Size-specific stock
- `size_stock_amount` - Size-specific quantity
- `delivery_time` - Expected delivery (e.g., "5 to 7 days")

#### Images & Media
- `merchant_image_url` - Primary image URL
- `aw_image_url` - Awin CDN image (200x200)
- `merchant_thumb_url` - Thumbnail URL
- `aw_thumb_url` - Awin thumbnail (70x70)
- `large_image` - Large image URL
- `alternate_image` - Alternative image 1
- `alternate_image_two` - Alternative image 2
- `alternate_image_three` - Alternative image 3
- `alternate_image_four` - Alternative image 4

#### Links
- `aw_deep_link` - Awin affiliate link (with tracking)
- `merchant_deep_link` - Direct merchant link
- `basket_link` - Add to cart link

#### Merchant Info
- `merchant_name` - Store name (e.g., "size?Official DE")
- `merchant_id` - Awin merchant ID (e.g., 10597)
- `data_feed_id` - Feed identifier

## Database Schema Design

### Option 1: New Table `awin_products`

Create dedicated table for Awin feed data:

```sql
CREATE TABLE integration.awin_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Awin IDs
    awin_product_id VARCHAR(50) UNIQUE NOT NULL,
    merchant_product_id VARCHAR(100),
    merchant_id INTEGER NOT NULL,
    merchant_name VARCHAR(200),
    data_feed_id INTEGER,

    -- Product Info
    product_name VARCHAR(500) NOT NULL,
    brand_name VARCHAR(200),
    brand_id INTEGER,
    ean VARCHAR(20),  -- Key for StockX matching
    product_gtin VARCHAR(20),
    mpn VARCHAR(100),
    product_model VARCHAR(200),

    -- Pricing (in cents)
    retail_price_cents INTEGER,  -- search_price
    store_price_cents INTEGER,
    rrp_price_cents INTEGER,
    currency VARCHAR(3) DEFAULT 'EUR',

    -- Product Details
    description TEXT,
    short_description TEXT,
    colour VARCHAR(100),
    size VARCHAR(20),  -- Fashion:size
    material VARCHAR(200),

    -- Stock
    in_stock BOOLEAN DEFAULT false,
    stock_quantity INTEGER DEFAULT 0,
    delivery_time VARCHAR(100),

    -- Images
    image_url VARCHAR(1000),
    thumbnail_url VARCHAR(1000),
    alternate_images JSONB,  -- Store all alternate images

    -- Links
    affiliate_link VARCHAR(2000),  -- aw_deep_link
    merchant_link VARCHAR(2000),   -- merchant_deep_link

    -- Matching
    matched_product_id UUID REFERENCES core.products(id),  -- Link to our products
    match_confidence DECIMAL(3,2),  -- 0.00 to 1.00
    match_method VARCHAR(50),  -- 'ean', 'name', 'manual'

    -- Metadata
    last_updated TIMESTAMPTZ,
    feed_import_date TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes
    INDEX idx_awin_ean (ean),
    INDEX idx_awin_merchant (merchant_id),
    INDEX idx_awin_brand (brand_name),
    INDEX idx_awin_matched_product (matched_product_id),
    INDEX idx_awin_in_stock (in_stock),
    INDEX idx_awin_last_updated (last_updated)
);
```

### Option 2: Extend Existing `products` Table

Add Awin-specific fields to existing products:

```sql
ALTER TABLE core.products ADD COLUMN awin_product_id VARCHAR(50);
ALTER TABLE core.products ADD COLUMN awin_retail_price_cents INTEGER;
ALTER TABLE core.products ADD COLUMN awin_affiliate_link VARCHAR(2000);
ALTER TABLE core.products ADD COLUMN awin_merchant_id INTEGER;
ALTER TABLE core.products ADD COLUMN awin_last_sync TIMESTAMPTZ;
```

**Recommendation: Option 1** - Dedicated table allows:
- Multiple merchants selling same product
- Historical price tracking
- Size-specific stock levels
- Clean separation of retail vs resale data

## Use Cases

### 1. Profit Opportunity Finder
Compare Awin retail prices with StockX resale prices:

```sql
SELECT
    ap.product_name,
    ap.brand_name,
    ap.size,
    ap.retail_price_cents / 100.0 as retail_price,
    p.lowest_ask / 100.0 as stockx_price,
    (p.lowest_ask - ap.retail_price_cents) / 100.0 as potential_profit,
    ap.in_stock,
    ap.affiliate_link
FROM integration.awin_products ap
JOIN core.products p ON ap.matched_product_id = p.id
WHERE ap.in_stock = true
  AND p.lowest_ask > ap.retail_price_cents
  AND (p.lowest_ask - ap.retail_price_cents) > 2000  -- Min 20 EUR profit
ORDER BY potential_profit DESC
LIMIT 50;
```

### 2. Automatic Product Matching

**By EAN (Most Reliable):**
```python
async def match_by_ean(ean: str):
    result = await session.execute(
        text("""
            SELECT id, name, style_code
            FROM core.products
            WHERE ean = :ean
        """),
        {"ean": ean}
    )
    return result.fetchone()
```

**By Product Name & Brand:**
```python
async def match_by_name(product_name: str, brand_name: str):
    # Use fuzzy matching or ML model
    result = await session.execute(
        text("""
            SELECT id, name, style_code,
                   similarity(name, :product_name) as match_score
            FROM core.products
            WHERE brand_name = :brand_name
              AND similarity(name, :product_name) > 0.7
            ORDER BY match_score DESC
            LIMIT 1
        """),
        {"product_name": product_name, "brand_name": brand_name}
    )
    return result.fetchone()
```

### 3. Size Availability Tracker

Track which sizes are available at retail:

```sql
SELECT
    product_name,
    brand_name,
    JSON_AGG(
        JSON_BUILD_OBJECT(
            'size', size,
            'in_stock', in_stock,
            'quantity', stock_quantity,
            'price', retail_price_cents / 100.0,
            'link', affiliate_link
        ) ORDER BY size
    ) as sizes_available
FROM integration.awin_products
WHERE in_stock = true
  AND matched_product_id IS NOT NULL
GROUP BY product_name, brand_name, matched_product_id;
```

### 4. Price History Tracking

Track retail price changes over time:

```sql
CREATE TABLE integration.awin_price_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    awin_product_id VARCHAR(50) REFERENCES integration.awin_products(awin_product_id),
    price_cents INTEGER NOT NULL,
    in_stock BOOLEAN,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert on price changes
CREATE OR REPLACE FUNCTION track_awin_price_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.retail_price_cents != NEW.retail_price_cents THEN
        INSERT INTO integration.awin_price_history
            (awin_product_id, price_cents, in_stock, recorded_at)
        VALUES
            (NEW.awin_product_id, NEW.retail_price_cents, NEW.in_stock, NOW());
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER awin_price_change_trigger
AFTER UPDATE ON integration.awin_products
FOR EACH ROW
EXECUTE FUNCTION track_awin_price_changes();
```

## Import Service Design

### Service: `AwinFeedImportService`

```python
# domains/integration/services/awin_feed_service.py

class AwinFeedImportService:
    def __init__(self, db_session):
        self.session = db_session
        self.api_key = "5a6669927305f35249c39e6b3e0a724c"
        self.base_url = "https://productdata.awin.com/datafeed/download"

    async def download_feed(self, merchant_ids: list, categories: list = None):
        """Download latest feed from Awin"""
        params = {
            "apikey": self.api_key,
            "language": "de",
            "bid": ",".join(str(m) for m in merchant_ids),  # 63233,66391
            "format": "csv",
            "delimiter": ",",
            "compression": "gzip"
        }
        # Add all columns...

    async def parse_feed(self, csv_file_path: str):
        """Parse CSV and return product records"""
        import csv
        import gzip

        products = []
        with gzip.open(csv_file_path, 'rt', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                products.append(self._transform_row(row))
        return products

    def _transform_row(self, row: dict):
        """Transform CSV row to database model"""
        return {
            "awin_product_id": row["aw_product_id"],
            "merchant_product_id": row["merchant_product_id"],
            "merchant_id": int(row["merchant_id"]),
            "merchant_name": row["merchant_name"],
            "product_name": row["product_name"],
            "brand_name": row.get("brand_name"),
            "brand_id": int(row["brand_id"]) if row.get("brand_id") else None,
            "ean": row.get("ean"),
            "retail_price_cents": int(float(row["search_price"]) * 100),
            "colour": row.get("colour"),
            "size": row.get("Fashion:size"),
            "description": row.get("description"),
            "in_stock": row.get("in_stock") == "1",
            "stock_quantity": int(row.get("stock_quantity", 0)),
            "image_url": row.get("merchant_image_url"),
            "affiliate_link": row.get("aw_deep_link"),
            "last_updated": row.get("last_updated")
        }

    async def import_products(self, products: list):
        """Bulk import products to database"""
        for product in products:
            await self._upsert_product(product)

    async def _upsert_product(self, product_data: dict):
        """Insert or update product"""
        await self.session.execute(
            text("""
                INSERT INTO integration.awin_products (
                    awin_product_id, merchant_product_id, merchant_id,
                    merchant_name, product_name, brand_name, brand_id,
                    ean, retail_price_cents, colour, size, description,
                    in_stock, stock_quantity, image_url, affiliate_link,
                    last_updated, updated_at
                ) VALUES (
                    :awin_product_id, :merchant_product_id, :merchant_id,
                    :merchant_name, :product_name, :brand_name, :brand_id,
                    :ean, :retail_price_cents, :colour, :size, :description,
                    :in_stock, :stock_quantity, :image_url, :affiliate_link,
                    :last_updated, NOW()
                )
                ON CONFLICT (awin_product_id)
                DO UPDATE SET
                    retail_price_cents = EXCLUDED.retail_price_cents,
                    in_stock = EXCLUDED.in_stock,
                    stock_quantity = EXCLUDED.stock_quantity,
                    last_updated = EXCLUDED.last_updated,
                    updated_at = NOW()
            """),
            product_data
        )

    async def match_products_by_ean(self):
        """Match Awin products to StockX products by EAN"""
        result = await self.session.execute(
            text("""
                UPDATE integration.awin_products ap
                SET
                    matched_product_id = p.id,
                    match_confidence = 1.00,
                    match_method = 'ean',
                    updated_at = NOW()
                FROM core.products p
                WHERE ap.ean = p.ean
                  AND ap.ean IS NOT NULL
                  AND ap.matched_product_id IS NULL
            """)
        )
        return result.rowcount
```

## API Endpoints

### GET `/api/v1/awin/opportunities`
Find profit opportunities:

```python
@router.get("/opportunities")
async def get_profit_opportunities(
    min_profit: int = 2000,  # cents
    in_stock_only: bool = True,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    query = """
        SELECT
            ap.product_name,
            ap.brand_name,
            ap.size,
            ap.retail_price_cents,
            ap.colour,
            p.lowest_ask as stockx_price,
            p.style_code,
            (p.lowest_ask - ap.retail_price_cents) as profit_cents,
            ap.in_stock,
            ap.stock_quantity,
            ap.affiliate_link,
            ap.image_url
        FROM integration.awin_products ap
        JOIN core.products p ON ap.matched_product_id = p.id
        WHERE (p.lowest_ask - ap.retail_price_cents) >= :min_profit
    """

    if in_stock_only:
        query += " AND ap.in_stock = true"

    query += " ORDER BY profit_cents DESC LIMIT :limit"

    result = await db.execute(text(query), {
        "min_profit": min_profit,
        "limit": limit
    })
    return result.fetchall()
```

### POST `/api/v1/awin/sync`
Trigger feed sync:

```python
@router.post("/sync")
async def sync_awin_feed(
    merchant_ids: list[int] = [10597],  # size?Official DE
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    service = AwinFeedImportService(db)

    # Run in background
    background_tasks.add_task(
        service.download_and_import,
        merchant_ids=merchant_ids
    )

    return {"status": "sync_started", "merchants": merchant_ids}
```

## Automation & Scheduling

### Daily Feed Sync

```python
# Add to background tasks or cron job
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=2)  # Run at 2 AM daily
async def sync_awin_feeds():
    async with db_manager.get_session() as session:
        service = AwinFeedImportService(session)

        merchants = [10597]  # size?Official DE
        await service.download_feed(merchants)
        products = await service.parse_feed('latest_feed.csv.gz')
        await service.import_products(products)

        # Match products
        matched_count = await service.match_products_by_ean()
        logger.info(f"Matched {matched_count} products by EAN")

        await session.commit()
```

## Performance Considerations

- **Bulk Import:** Use `COPY` or bulk inserts for 1000+ products
- **Indexing:** Strategic indexes on EAN, merchant_id, matched_product_id
- **Caching:** Cache profit opportunities for 1 hour
- **Incremental Updates:** Only update changed products (compare last_updated)

## Future Enhancements

1. **Multi-Merchant Support** - Import from multiple Awin merchants
2. **Price Drop Alerts** - Notify when retail price drops below threshold
3. **Auto-Listing** - Automatically list profitable items on StockX
4. **Size Run Analysis** - Identify full size runs at retail
5. **Historical Charts** - Visualize retail vs resale price trends
6. **Smart Matching** - ML-based product matching beyond EAN
7. **Commission Tracking** - Track Awin affiliate earnings

## Security & Compliance

- API key stored in environment variables
- Affiliate links properly disclosed
- No price scraping - using official Awin feed
- Respect merchant terms of service
- GDPR compliance for EU data

---

**Status:** Design Phase
**Next Steps:** Create database migration and import service
