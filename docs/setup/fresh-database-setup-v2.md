# Fresh Database Setup Guide v2.0
**Multi-Source Price Architecture - Clean Start Guide**

## Overview

This guide shows how to set up a **fresh database** using the new unified `price_sources` architecture.

**Use this guide when:**
- Starting a new environment from scratch
- Performing a "hard reset" after refactoring
- Setting up development/staging/production databases

**Duration:** ~30-45 minutes (depending on data volume)

---

## Prerequisites

✅ PostgreSQL 14+ installed and running
✅ Python 3.11+ with all dependencies installed
✅ Awin API credentials configured
✅ StockX API credentials configured
✅ Environment variables set in `.env`

---

## Step 1: Database Creation & Schema Setup

### 1.1 Create Fresh Database

```bash
# Drop existing database (⚠️ DESTRUCTIVE - only for fresh start!)
psql -U postgres -c "DROP DATABASE IF EXISTS soleflip;"

# Create new database
psql -U postgres -c "CREATE DATABASE soleflip;"
```

### 1.2 Run Migrations

```bash
# From project root
alembic upgrade head
```

This creates:
- ✅ All schemas (`core`, `products`, `integration`, `transactions`, etc.)
- ✅ All base tables (`products.products`, `core.suppliers`, etc.)
- ✅ **New:** `integration.price_sources` table
- ✅ **New:** `integration.price_history` table
- ✅ **New:** Views (`profit_opportunities_v2`, `latest_prices`)
- ✅ **New:** Price tracking triggers

### 1.3 Verify Schema

```bash
# Check tables exist
psql -U postgres -d soleflip -c "\dt integration.*"
```

Expected output:
```
 integration | awin_products
 integration | price_sources          ← NEW
 integration | price_history          ← NEW
 integration | awin_enrichment_jobs
```

---

## Step 2: Import Suppliers (Foundation)

**Why first?** Price sources can link to suppliers via `supplier_id` FK.

### 2.1 Create Supplier Records

```sql
-- Example: Create size?Official DE supplier
INSERT INTO core.suppliers (id, name, type, country, contact_email, is_active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'size?Official DE',
    'retail',
    'DE',
    'info@size.de',
    true,
    NOW(),
    NOW()
)
ON CONFLICT (name) DO NOTHING;
```

### 2.2 Verify Suppliers

```sql
SELECT id, name, type, country FROM core.suppliers;
```

---

## Step 3: Import Awin Products → Unified Architecture

### 3.1 Download Awin Feed

```bash
# Run Awin import script
python scripts/import_awin_sample_feed.py
```

Or via API:
```python
from domains.integration.services.awin_feed_service import AwinFeedImportService
from shared.database.connection import get_db_session

async with get_db_session() as session:
    service = AwinFeedImportService(session)

    # Download feed
    feed_path = await service.download_feed(
        merchant_ids=[10597],  # size?Official DE
        output_path="context/integrations/awin_feed_latest.csv.gz"
    )

    # Parse products
    products = await service.parse_feed(feed_path)
    print(f"Parsed {len(products)} products")
```

### 3.2 Import Products to Core Table

**New Strategy:** Products go to `products.products` first, prices go to `price_sources` second.

```python
"""
New Awin Import Flow for v2 Architecture
Separates product master data from pricing data
"""
from sqlalchemy import text
import json

async def import_awin_v2(session, awin_products):
    """Import Awin products using price_sources architecture"""

    for product in awin_products:
        # Step 1: Upsert product master data (if EAN exists)
        if product.get('ean'):
            product_id = await upsert_product_master(session, product)

            # Step 2: Insert retail price in price_sources
            await insert_price_source(session, product_id, product)
        else:
            print(f"Skipping product without EAN: {product['product_name']}")

async def upsert_product_master(session, product):
    """Create/update product in products.products"""
    result = await session.execute(
        text("""
            INSERT INTO products.products (
                name, ean, sku, description,
                brand_id, category, color, size,
                image_url, created_at, updated_at
            )
            VALUES (
                :name, :ean, :sku, :description,
                (SELECT id FROM core.brands WHERE LOWER(name) = LOWER(:brand_name) LIMIT 1),
                :category, :color, :size,
                :image_url, NOW(), NOW()
            )
            ON CONFLICT (ean)
            DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                image_url = EXCLUDED.image_url,
                updated_at = NOW()
            RETURNING id
        """),
        {
            "name": product['product_name'],
            "ean": product['ean'],
            "sku": product.get('mpn') or product['ean'],  # Use MPN or EAN as SKU
            "description": product.get('description'),
            "brand_name": product.get('brand_name') or 'Unknown',
            "category": product.get('merchant_category'),
            "color": product.get('colour'),
            "size": product.get('size'),
            "image_url": product.get('image_url')
        }
    )

    row = result.fetchone()
    return row[0] if row else None

async def insert_price_source(session, product_id, product):
    """Insert Awin retail price in price_sources"""

    # Get supplier_id if merchant exists in suppliers
    supplier_result = await session.execute(
        text("SELECT id FROM core.suppliers WHERE name = :merchant_name"),
        {"merchant_name": product['merchant_name']}
    )
    supplier_row = supplier_result.fetchone()
    supplier_id = supplier_row[0] if supplier_row else None

    metadata = {
        "merchant_id": product.get('merchant_id'),
        "merchant_name": product.get('merchant_name'),
        "awin_product_id": product.get('awin_product_id'),
        "data_feed_id": product.get('data_feed_id'),
        "delivery_time": product.get('delivery_time'),
        "alternate_images": product.get('alternate_images')
    }

    await session.execute(
        text("""
            INSERT INTO integration.price_sources (
                product_id, source_type, source_product_id, source_name,
                price_type, price_cents, currency,
                in_stock, stock_quantity,
                affiliate_link, source_url,
                supplier_id, metadata,
                last_updated, created_at, updated_at
            )
            VALUES (
                :product_id, 'awin', :source_product_id, :source_name,
                'retail', :price_cents, :currency,
                :in_stock, :stock_quantity,
                :affiliate_link, :source_url,
                :supplier_id, :metadata::jsonb,
                :last_updated, NOW(), NOW()
            )
            ON CONFLICT (product_id, source_type, source_product_id)
            DO UPDATE SET
                price_cents = EXCLUDED.price_cents,
                in_stock = EXCLUDED.in_stock,
                stock_quantity = EXCLUDED.stock_quantity,
                last_updated = EXCLUDED.last_updated,
                updated_at = NOW()
        """),
        {
            "product_id": str(product_id),
            "source_product_id": product['awin_product_id'],
            "source_name": product['merchant_name'],
            "price_cents": product.get('retail_price_cents') or 0,
            "currency": product.get('currency', 'EUR'),
            "in_stock": product.get('in_stock', False),
            "stock_quantity": product.get('stock_quantity', 0),
            "affiliate_link": product.get('affiliate_link'),
            "source_url": product.get('merchant_link'),
            "supplier_id": str(supplier_id) if supplier_id else None,
            "metadata": json.dumps(metadata),
            "last_updated": product.get('last_updated')
        }
    )
```

### 3.3 Run Import Script

Create `scripts/import_awin_v2.py`:

```python
import asyncio
from shared.database.connection import get_db_session
from domains.integration.services.awin_feed_service import AwinFeedImportService

# ... (include import_awin_v2 function from above)

async def main():
    async with get_db_session() as session:
        # 1. Download & parse feed
        awin_service = AwinFeedImportService(session)
        feed_path = await awin_service.download_feed([10597])
        products = await awin_service.parse_feed(feed_path)

        # 2. Import using v2 architecture
        await import_awin_v2(session, products)
        await session.commit()

        print(f"✅ Imported {len(products)} products to price_sources architecture")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python scripts/import_awin_v2.py
```

---

## Step 4: Enrich with StockX Resale Prices

### 4.1 Start StockX Enrichment Job

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/integration/awin/enrichment/start \
  -H "Content-Type: application/json" \
  -d '{"rate_limit": 60}'
```

Or via Python:
```python
from domains.integration.services.awin_stockx_enrichment_service import AwinStockXEnrichmentService

async with get_db_session() as session:
    enrichment_service = AwinStockXEnrichmentService(
        session,
        rate_limit_requests_per_minute=60
    )

    # This searches StockX by EAN and stores resale prices
    results = await enrichment_service.enrich_all_products()

    print(f"Matched: {results['matched']}")
    print(f"Match Rate: {results['match_rate_percentage']}%")
```

### 4.2 Monitor Progress

```bash
# Check job status
curl http://localhost:8000/api/v1/integration/awin/enrichment/status/{job_id}
```

### 4.3 Update to Price Sources Architecture

**Modified enrichment service** should now write to `price_sources`:

```python
# In awin_stockx_enrichment_service.py - updated _update_product_match method:

async def _update_product_match_v2(
    self,
    product_id: UUID,  # products.products.id
    stockx_product_id: str,
    stockx_data: Dict,
    retail_price_cents: int
):
    """Update with StockX resale price in price_sources"""

    # Get market data for lowest ask
    lowest_ask = stockx_data.get('market_data', {}).get('lowest_ask_cents')

    if not lowest_ask:
        logger.warning("No market data for StockX product", stockx_id=stockx_product_id)
        return

    metadata = {
        "url_key": stockx_data.get('urlKey'),
        "style_id": stockx_data.get('styleId'),
        "product_category": stockx_data.get('productCategory'),
        "price_type": "lowest_ask"
    }

    # Insert StockX resale price
    await self.session.execute(
        text("""
            INSERT INTO integration.price_sources (
                product_id, source_type, source_product_id, source_name,
                price_type, price_cents, currency, in_stock,
                source_url, metadata,
                last_updated, created_at, updated_at
            )
            VALUES (
                :product_id, 'stockx', :source_product_id, 'StockX',
                'resale', :price_cents, 'EUR', true,
                :source_url, :metadata::jsonb,
                NOW(), NOW(), NOW()
            )
            ON CONFLICT (product_id, source_type, source_product_id)
            DO UPDATE SET
                price_cents = EXCLUDED.price_cents,
                last_updated = EXCLUDED.last_updated,
                updated_at = EXCLUDED.updated_at
        """),
        {
            "product_id": str(product_id),
            "source_product_id": stockx_product_id,
            "price_cents": lowest_ask,
            "source_url": f"https://stockx.com/{stockx_data.get('urlKey')}",
            "metadata": json.dumps(metadata)
        }
    )

    await self.session.commit()
```

---

## Step 5: Verify Data & Query Profit Opportunities

### 5.1 Check Data Integrity

```sql
-- Count price sources by type
SELECT
    source_type,
    price_type,
    COUNT(*) as count,
    COUNT(DISTINCT product_id) as unique_products
FROM integration.price_sources
GROUP BY source_type, price_type;
```

Expected output:
```
 source_type | price_type | count | unique_products
-------------+------------+-------+-----------------
 awin        | retail     | 1150  | 1150
 stockx      | resale     | 892   | 892
```

### 5.2 Query Profit Opportunities

```sql
-- Use the new view
SELECT
    product_name,
    brand_name,
    retail_price_eur,
    resale_price_eur,
    profit_eur,
    profit_percentage,
    retail_source,
    retail_affiliate_link
FROM integration.profit_opportunities_v2
WHERE profit_eur >= 20
ORDER BY profit_eur DESC
LIMIT 20;
```

### 5.3 API Check

```bash
# Get top profit opportunities
curl "http://localhost:8000/api/v1/integration/awin/profit-opportunities?min_profit_eur=20&limit=50"
```

---

## Step 6: Set Up Scheduled Jobs (Optional)

### 6.1 Daily Price Updates

```python
# In Budibase or n8n automation:

# 1. Daily Awin feed refresh (2 AM)
POST /api/v1/integration/awin/import

# 2. StockX price updates (3 AM)
POST /api/v1/integration/awin/enrichment/start

# 3. Send profit report (4 AM)
GET /api/v1/integration/awin/profit-opportunities?min_profit_eur=30
→ Email top 20 opportunities to team
```

---

## Step 7: Add Additional Price Sources (Future)

### 7.1 eBay Integration Example

```python
async def import_ebay_prices(session, product_ean, price_cents):
    """Example: Add eBay auction prices"""

    # Find product by EAN
    product = await session.execute(
        text("SELECT id FROM products.products WHERE ean = :ean"),
        {"ean": product_ean}
    )
    product_id = product.fetchone()[0]

    # Insert eBay price
    await session.execute(
        text("""
            INSERT INTO integration.price_sources (
                product_id, source_type, source_product_id,
                price_type, price_cents, currency, in_stock,
                created_at, updated_at
            )
            VALUES (
                :product_id, 'ebay', :ebay_item_id,
                'auction', :price_cents, 'EUR', true,
                NOW(), NOW()
            )
        """),
        {
            "product_id": str(product_id),
            "ebay_item_id": "ebay_123456",
            "price_cents": price_cents
        }
    )
```

The `profit_opportunities_v2` view **automatically** includes eBay prices!

---

## Troubleshooting

### Issue: No products imported
**Check:**
```sql
SELECT COUNT(*) FROM products.products WHERE ean IS NOT NULL;
```
**Fix:** Ensure Awin feed has EAN codes, verify import script ran successfully

### Issue: No profit opportunities
**Check:**
```sql
SELECT
    (SELECT COUNT(*) FROM integration.price_sources WHERE price_type = 'retail') as retail_count,
    (SELECT COUNT(*) FROM integration.price_sources WHERE price_type = 'resale') as resale_count;
```
**Fix:** Run StockX enrichment if resale_count = 0

### Issue: StockX enrichment fails
**Check:** API credentials, rate limits, EAN quality
**Fix:** Reduce rate limit to 30 req/min, check StockX API status

---

## Success Metrics

After fresh setup, you should have:

✅ **Products Table:** 1,000+ products with EAN codes
✅ **Price Sources:** 2,000+ price records (retail + resale)
✅ **Profit Opportunities:** 50+ opportunities with >20 EUR profit
✅ **Match Rate:** >70% Awin products matched to StockX
✅ **Data Quality:** No NULL product_ids in price_sources
✅ **Views Working:** `profit_opportunities_v2` returns results

---

## Next Steps

1. **Set up Metabase dashboards** using `profit_opportunities_v2` view
2. **Configure Budibase automation** for daily enrichment
3. **Add more price sources** (eBay, GOAT, Klekt) using same pattern
4. **Monitor price history** via `integration.price_history` table
5. **Build alerts** for high-profit opportunities (>€100 profit)

---

## Clean Up Old Data (Optional)

Once v2 is verified and working:

```sql
-- Archive old awin_products table
ALTER TABLE integration.awin_products RENAME TO awin_products_legacy_backup;

-- Or drop completely (⚠️ only if confident!)
DROP TABLE integration.awin_products_legacy_backup;
```

---

**Questions?** See `/docs/architecture/multi-source-pricing-refactoring.md` for full architecture details.
