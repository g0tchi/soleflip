# n8n Data Tables Setup Guide - Product Feed Filtering

## Prerequisites

- n8n instance running (see `docker-compose.yml`)
- Access to n8n UI: http://localhost:5678
- Webgains API credentials
- SoleFlip API running on http://localhost:8000

---

## Step 1: Create Data Tables

### 1.1 Navigate to Data Tables

1. Open n8n UI: http://localhost:5678
2. Click on **"Data tables"** tab in left sidebar
3. Click **"Create Data table"** button

### 1.2 Create `brand_whitelist` Table

**Table Name:** `brand_whitelist`

**Columns:**
| Column Name | Type     | Description                          |
|-------------|----------|--------------------------------------|
| brand_name  | String   | Canonical brand name (e.g., "Nike") |
| variations  | String   | JSON array of variations             |
| active      | Number   | 1 = active, 0 = inactive             |
| priority    | Number   | Higher number = more important       |

**Initial Data:**

```csv
brand_name,variations,active,priority
Nike,"[""NIKE"", ""nike"", ""Nike Inc"", ""Nike Sportswear""]",1,100
Adidas,"[""ADIDAS"", ""adidas"", ""Adidas Originals""]",1,95
Jordan,"[""Air Jordan"", ""JORDAN"", ""Jordan Brand""]",1,90
New Balance,"[""NB"", ""NewBalance"", ""NEW BALANCE""]",1,85
Asics,"[""ASICS"", ""asics""]",1,80
Puma,"[""PUMA"", ""puma""]",1,75
Reebok,"[""REEBOK"", ""reebok""]",1,70
Converse,"[""CONVERSE"", ""converse""]",1,65
Vans,"[""VANS"", ""vans""]",1,60
Under Armour,"[""Under Armour"", ""UNDER ARMOUR"", ""UnderArmour""]",1,55
```

### 1.3 Create `category_filters` Table

**Table Name:** `category_filters`

**Columns:**
| Column Name      | Type   | Description                    |
|------------------|--------|--------------------------------|
| category_keyword | String | Keyword to match               |
| include          | Number | 1 = include, 0 = exclude       |
| category_type    | String | "footwear", "apparel", etc.    |
| match_type       | String | "exact", "contains", "starts_with" |

**Initial Data:**

```csv
category_keyword,include,category_type,match_type
sneaker,1,footwear,contains
trainer,1,footwear,contains
shoe,1,footwear,contains
boot,1,footwear,contains
running,1,footwear,contains
basketball,1,footwear,contains
sandal,0,footwear,contains
flip flop,0,footwear,contains
slipper,0,footwear,contains
high heel,0,footwear,contains
```

### 1.4 Create `product_fingerprints` Table

**Table Name:** `product_fingerprints`

**Columns:**
| Column Name         | Type     | Description                      |
|---------------------|----------|----------------------------------|
| ean_code            | String   | EAN/GTIN/UPC code                |
| brand               | String   | Normalized brand name            |
| model               | String   | Product model/name               |
| color               | String   | Colorway                         |
| size                | String   | Size (if available)              |
| source              | String   | "webgains", "awin", "manual"     |
| merchant_id         | String   | Original merchant identifier     |
| soleflip_product_id | String   | UUID from catalog.product table |
| fingerprint_key     | String   | Composite key for deduplication  |
| first_imported      | Datetime | When first seen                  |
| last_seen           | Datetime | Last time seen in feed           |
| status              | String   | "active", "archived", "error"    |

**Note:** This table starts empty. It will be populated by the workflow.

### 1.5 Create `import_log` Table

**Table Name:** `import_log`

**Columns:**
| Column Name       | Type     | Description                |
|-------------------|----------|----------------------------|
| import_id         | String   | Unique run identifier      |
| source            | String   | "webgains", "awin"         |
| run_date          | Datetime | When import started        |
| total_products    | Number   | Products in feed           |
| brand_filtered    | Number   | Filtered by brand          |
| category_filtered | Number   | Filtered by category       |
| duplicates_found  | Number   | Already in fingerprints    |
| new_products      | Number   | Newly imported             |
| errors            | Number   | Failed imports             |
| duration_seconds  | Number   | Total processing time      |
| status            | String   | "success", "partial", "failed" |

**Note:** This table starts empty. Populated on each workflow run.

---

## Step 2: Configure Environment Variables

### 2.1 Add to `.env` file

```bash
# Webgains API
WEBGAINS_FEED_URL=https://api.webgains.com/v2/products/feed
WEBGAINS_API_KEY=your_webgains_api_key_here

# SoleFlip API (if authentication is required)
SOLEFLIP_API_KEY=your_internal_api_key_here
SOLEFLIP_API_URL=http://localhost:8000
```

### 2.2 Restart n8n to load environment variables

```bash
docker-compose restart n8n
```

---

## Step 3: Create Credentials in n8n

### 3.1 Webgains API Key

1. Go to **Settings** → **Credentials** in n8n
2. Click **"Add credential"**
3. Select **"Header Auth"**
4. Configure:
   - **Name:** `Webgains API Key`
   - **Name:** `Authorization`
   - **Value:** `Bearer {{ $env.WEBGAINS_API_KEY }}`

### 3.2 SoleFlip API Key (if needed)

1. Click **"Add credential"**
2. Select **"Header Auth"**
3. Configure:
   - **Name:** `SoleFlip API Key`
   - **Name:** `Authorization`
   - **Value:** `Bearer {{ $env.SOLEFLIP_API_KEY }}`

---

## Step 4: Import Workflow

### 4.1 Import from JSON

1. In n8n UI, click **"Workflows"** tab
2. Click **"Import from file"** button
3. Select `context/integrations/n8n-workflow-webgains-import.json`
4. Click **"Import"**

### 4.2 Configure Workflow Settings

1. Open the imported workflow
2. Click on **"Fetch Webgains Feed"** node
3. Verify **URL** is set to `{{ $env.WEBGAINS_FEED_URL }}`
4. Select credential: **"Webgains API Key"**
5. Click on **"Create Product in SoleFlip"** node
6. Verify **URL** is `http://localhost:8000/products`
7. Select credential: **"SoleFlip API Key"** (if configured)

### 4.3 Test Workflow

**Manual Test:**
1. Click **"Execute workflow"** button (top-right)
2. Select **"Execute manually"** (ignore schedule)
3. Monitor execution in real-time
4. Check for errors in each node

**Tip:** Use **"Run once"** for initial testing before enabling schedule.

---

## Step 5: Enable Schedule

### 5.1 Activate Workflow

1. In workflow editor, toggle **"Active"** switch (top-right)
2. Workflow will now run daily at 2:00 AM UTC

### 5.2 Adjust Schedule (Optional)

To change the schedule:
1. Click on **"Daily 2:00 AM"** trigger node
2. Modify **Cron Expression**: `0 2 * * *`
   - `0 2 * * *` = Every day at 2:00 AM
   - `0 */6 * * *` = Every 6 hours
   - `0 0 * * 0` = Every Sunday at midnight

---

## Step 6: Monitor Imports

### 6.1 Check Import Logs

1. Go to **Data tables** → `import_log`
2. View recent imports
3. Check `status` column:
   - ✅ `success`: All good
   - ⚠️ `partial`: Some errors occurred
   - ❌ `failed`: Import failed

### 6.2 Review Statistics

**Key Metrics:**
- **total_products**: Original feed size
- **brand_filtered**: How many rejected by brand
- **category_filtered**: How many rejected by category
- **duplicates_found**: Already in catalog
- **new_products**: Successfully imported
- **errors**: Failed imports

**Expected Results (healthy import):**
```
total_products: 50,000
brand_filtered: 48,000 (96% filtered)
category_filtered: 1,800 (90% of remaining)
duplicates_found: 150 (70% of remaining)
new_products: 50 (2-3 new products found)
errors: 0
```

### 6.3 Check Product Fingerprints

1. Go to **Data tables** → `product_fingerprints`
2. Review newly added products
3. Verify `last_seen` timestamps are recent
4. Check `soleflip_product_id` is populated

---

## Step 7: Verify in SoleFlip Database

### 7.1 Query PostgreSQL

```bash
# Check recent products
PGPASSWORD='SoleFlip2025SecureDB!' psql -h localhost -U soleflip_user -d soleflip_db -c "
SELECT id, brand, name, ean, source, created_at
FROM catalog.product
WHERE source = 'webgains'
ORDER BY created_at DESC
LIMIT 10;
"
```

### 7.2 Verify via API

```bash
# Get recent products
curl http://localhost:8000/products?source=webgains&limit=10
```

---

## Step 8: Troubleshooting

### Issue: No products imported

**Check:**
1. Is `brand_whitelist` populated?
   - Go to Data Tables → `brand_whitelist`
   - Ensure `active = 1` for brands
2. Are `category_filters` too restrictive?
   - Review keywords, adjust if needed
3. Check workflow execution logs
   - n8n UI → Executions tab
   - Look for node errors

### Issue: Too many products imported

**Check:**
1. Are brand filters working?
   - Review `Filter by Brand` node output
   - Check brand matching logic
2. Are category filters sufficient?
   - Add more exclusion keywords (sandal, slipper, etc.)
3. Review `import_log` statistics

### Issue: Duplicates appearing in catalog

**Check:**
1. EAN codes missing in feed?
   - Review `product_fingerprints` table
   - Check `fingerprint_key` values
2. Deduplication logic working?
   - Test `Check for Duplicates` node
   - Verify `Route: New vs Duplicate` switch

### Issue: Import taking too long

**Optimize:**
1. Reduce batch size
   - `Split In Batches` node: Change from 1000 to 500
2. Add more category exclusions
   - Filter earlier to reduce processing
3. Check API response times
   - SoleFlip API might be slow

---

## Step 9: Maintenance

### Weekly Tasks

**Review and Update Filters:**
```bash
# Add new brand to whitelist
# In n8n Data Tables UI:
1. Open `brand_whitelist`
2. Click "Add row"
3. Enter: brand_name="Salomon", variations='["SALOMON", "salomon"]', active=1, priority=50
```

**Clean Up Old Fingerprints:**
```sql
-- Archive products not seen in 90 days
UPDATE product_fingerprints
SET status = 'archived'
WHERE last_seen < (NOW() - INTERVAL '90 days')
  AND status = 'active';
```

### Monthly Tasks

**Analyze Import Efficiency:**
1. Go to `import_log` table
2. Export last 30 days to CSV
3. Calculate averages:
   - Average filter rate
   - Average duplicate rate
   - Average errors

**Optimize Filters:**
- If >98% filtered: Filters too strict, relax
- If <90% filtered: Filters too loose, tighten
- Target: 95% filtered, 5% imported

---

## Step 10: Scaling Considerations

### When to Move from Data Tables to PostgreSQL

**Migrate if:**
- `product_fingerprints` >100,000 rows (~20 MB)
- Data Tables nearing 50 MB capacity
- Complex queries needed (joins, aggregations)

**Migration Path:**
1. Create PostgreSQL staging schema:
   ```sql
   CREATE SCHEMA staging;
   CREATE TABLE staging.product_fingerprints (...);
   CREATE TABLE staging.import_log (...);
   ```
2. Export Data Tables to CSV
3. Import CSV to PostgreSQL
4. Update workflow to query PostgreSQL instead

---

## Appendix A: Quick Reference Commands

### Check n8n Status
```bash
docker-compose ps n8n
docker-compose logs -f n8n
```

### Access n8n CLI (inside container)
```bash
docker-compose exec n8n /bin/sh
n8n list:workflow
n8n execute --id=<workflow_id>
```

### Restart n8n
```bash
docker-compose restart n8n
```

### Backup Data Tables
```bash
# Data Tables are stored in n8n's database
# Backup the entire n8n volume
docker run --rm -v soleflip_n8n_data:/data -v $(pwd):/backup ubuntu tar czf /backup/n8n-backup-$(date +%Y%m%d).tar.gz /data
```

---

## Appendix B: Sample Feed Inspection

### Inspect Awin Feed Sample

```bash
# View first 10 rows of Awin feed
head -10 context/integrations/awin_feed_sample.csv

# Count total products
wc -l context/integrations/awin_feed_sample.csv

# Extract unique brands
cat context/integrations/awin_feed_sample.csv | cut -d',' -f3 | sort | uniq -c | sort -rn | head -20
```

### Test Feed Parsing

```python
# Quick Python script to test CSV parsing
import csv

with open('context/integrations/awin_feed_sample.csv', 'r') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= 5:
            break
        print(f"Product {i+1}:")
        print(f"  Brand: {row.get('brand')}")
        print(f"  Name: {row.get('product_name')}")
        print(f"  Category: {row.get('category')}")
        print(f"  EAN: {row.get('ean')}")
        print()
```

---

## Appendix C: SoleFlip API Integration

### Required API Endpoint

**File:** `domains/products/api/router.py`

**Add this endpoint if it doesn't exist:**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from shared.database.session import get_session
from domains.products.services.product_service import ProductService
from domains.products.schemas import ProductCreate, ProductResponse

router = APIRouter(prefix="/products", tags=["products"])

@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    product_data: ProductCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new product in the catalog.

    Used by n8n workflows for affiliate feed imports.
    """
    service = ProductService(session)

    # Check for duplicate by EAN
    if product_data.ean:
        existing = await service.get_by_ean(product_data.ean)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Product with EAN {product_data.ean} already exists"
            )

    product = await service.create(product_data)
    return product
```

**Schema (if needed):**

```python
# domains/products/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class ProductCreate(BaseModel):
    brand: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    ean: Optional[str] = Field(None, max_length=20)
    category: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    currency: str = Field(default="EUR", max_length=3)
    size: Optional[str] = Field(None, max_length=20)
    color: Optional[str] = Field(None, max_length=50)
    image_url: Optional[str] = None
    source: str = Field(default="manual")
    merchant_id: Optional[str] = None

class ProductResponse(BaseModel):
    id: UUID
    brand: str
    name: str
    ean: Optional[str]
    category: str
    price: float
    currency: str
    created_at: datetime

    class Config:
        from_attributes = True
```

### Test API Endpoint

```bash
# Test product creation
curl -X POST http://localhost:8000/products \
  -H "Content-Type: application/json" \
  -d '{
    "brand": "Nike",
    "name": "Air Max 90 Essential",
    "ean": "0194953025890",
    "category": "Sneakers",
    "price": 129.99,
    "currency": "EUR",
    "size": "US 10",
    "color": "White/Black",
    "image_url": "https://example.com/image.jpg",
    "source": "webgains",
    "merchant_id": "webgains_merchant_42"
  }'
```

---

## Support & Resources

- **n8n Documentation**: https://docs.n8n.io
- **n8n Data Tables**: https://docs.n8n.io/data/data-tables
- **SoleFlip Docs**: `CLAUDE.md`, `context/project_overview.md`
- **Issues**: Create GitHub issue or contact team

**Last Updated:** 2025-12-02
**Version:** 1.0.0
