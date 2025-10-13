# Awin-StockX Money Printer 💰

**Automated Retail Arbitrage System**
Version: 1.0.0
Status: Production Ready
Last Updated: 2025-10-12

## Overview

The Awin-StockX Money Printer is a **scalable, reproducible system** for finding profit opportunities by matching retail products from Awin affiliate network with resale prices on StockX.

### Key Features

✅ **EAN-based Matching** - Accurate product matching via universal product codes
✅ **Rate Limiting** - Respects StockX API limits (configurable, default: 60 req/min)
✅ **Progress Tracking** - Real-time job monitoring and status updates
✅ **Budibase Integration** - Full REST API control for workflow automation
✅ **Batch Processing** - Scalable to thousands of products
✅ **Reproducible** - Run daily/weekly via scheduled jobs

## Architecture

```
┌─────────────────┐
│  Awin Feed API  │
│  (size?Official)│
└────────┬────────┘
         │ EAN: 0197862948967
         ▼
┌─────────────────────────────────┐
│  Awin Products DB               │
│  integration.awin_products      │
│  - 1,150 products               │
│  - 100% with EAN codes          │
│  - Daily import via API         │
└────────┬───────────────────────┘
         │
         ▼ Enrichment Service
┌─────────────────────────────────┐
│  StockX Catalog API             │
│  Search by EAN/GTIN             │
│  - Product Details              │
│  - Variants (sizes)             │
│  - Market Data (prices)         │
└────────┬───────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Enriched Product Data          │
│  integration.awin_products      │
│  + stockx_product_id            │
│  + stockx_lowest_ask_cents      │
│  + profit_cents                 │
│  + profit_percentage            │
└────────┬───────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Profit Opportunities Report    │
│  API: /awin/profit-opportunities│
│  Sorted by profit (DESC)        │
└─────────────────────────────────┘
```

## Database Schema

### Main Tables

**`integration.awin_products`** - Awin product catalog with StockX matching
```sql
-- Core Product Data
awin_product_id         VARCHAR(50)     -- Awin's unique ID
product_name            VARCHAR(500)    -- Product name
brand_name              VARCHAR(200)    -- Brand (Jordan, ASICS, etc.)
ean                     VARCHAR(20)     -- EAN/GTIN code (matching key!)
retail_price_cents      INTEGER         -- Retail price from Awin
in_stock                BOOLEAN         -- Stock availability
stock_quantity          INTEGER         -- Available quantity

-- StockX Matching Data (NEW)
stockx_product_id       UUID            -- StockX product UUID
stockx_url_key          VARCHAR(200)    -- StockX URL slug
stockx_style_id         VARCHAR(100)    -- Manufacturer style ID
stockx_lowest_ask_cents INTEGER         -- Current resale price
profit_cents            INTEGER         -- Calculated profit
profit_percentage       NUMERIC(5,2)    -- ROI percentage
enrichment_status       VARCHAR(20)     -- 'pending', 'matched', 'not_found', 'error'
last_enriched_at        TIMESTAMP       -- Last enrichment run
```

**`integration.awin_enrichment_jobs`** - Job tracking for automation
```sql
id                      UUID            -- Job ID
job_type                VARCHAR(50)     -- 'stockx_match', 'price_update'
status                  VARCHAR(20)     -- 'pending', 'running', 'completed', 'failed'
total_products          INTEGER         -- Total to process
processed_products      INTEGER         -- Progress counter
matched_products        INTEGER         -- Success counter
failed_products         INTEGER         -- Error counter
results_summary         JSON            -- Final stats
started_at              TIMESTAMP       -- Job start time
completed_at            TIMESTAMP       -- Job end time
```

## API Endpoints

### For Budibase Control

#### 1. Start Enrichment Job
```http
POST /api/v1/integration/awin/enrichment/start
```

**Description**: Starts background job to match all Awin products with StockX via EAN

**Parameters**:
- `limit` (optional): Limit for testing (default: process all)
- `rate_limit` (optional): Requests per minute (default: 60)

**Response**:
```json
{
  "success": true,
  "job_id": "a7b8c9d0-e1f2-1234-5678-9abc def01234",
  "message": "Enrichment job started",
  "total_products": 1150,
  "estimated_duration_minutes": 19
}
```

**Budibase Usage**:
- Button click → Start enrichment
- Schedule daily at 2 AM

---

#### 2. Check Job Status
```http
GET /api/v1/integration/awin/enrichment/status/{job_id}
```

**Description**: Get real-time progress of running enrichment job

**Response**:
```json
{
  "success": true,
  "job": {
    "id": "a7b8c9d0-e1f2-1234-5678-9abcdef01234",
    "status": "running",
    "progress": {
      "total": 1150,
      "processed": 450,
      "matched": 380,
      "not_found": 60,
      "errors": 10,
      "percentage": 39.1
    },
    "started_at": "2025-10-12T08:00:00Z",
    "elapsed_minutes": 7.5,
    "estimated_remaining_minutes": 11.5
  }
}
```

**Budibase Usage**:
- Progress bar component
- Auto-refresh every 30 seconds
- Show notifications on completion

---

#### 3. Get Latest Results
```http
GET /api/v1/integration/awin/enrichment/latest
```

**Description**: Get results from most recent completed enrichment job

**Response**:
```json
{
  "success": true,
  "job": {
    "completed_at": "2025-10-12T08:19:00Z",
    "status": "completed",
    "results": {
      "total_processed": 1150,
      "matched": 892,
      "not_found": 245,
      "errors": 13,
      "match_rate_percentage": 77.6,
      "duration_minutes": 19.2
    }
  }
}
```

---

#### 4. Get Profit Opportunities
```http
GET /api/v1/integration/awin/profit-opportunities
```

**Description**: Get ranked list of profitable arbitrage opportunities

**Parameters**:
- `min_profit_eur` (default: 20.0) - Minimum profit in EUR
- `min_profit_percentage` (default: 10.0) - Minimum ROI %
- `limit` (default: 50) - Number of results

**Response**:
```json
{
  "success": true,
  "message": "Found 47 profit opportunities!",
  "summary": {
    "total_opportunities": 47,
    "total_potential_profit_eur": 3420.50,
    "avg_profit_eur": 72.78,
    "avg_roi_percentage": 45.2,
    "best_opportunity_eur": 145.00
  },
  "opportunities": [
    {
      "awin": {
        "product_name": "Jordan 3 Retro OG Rare Air (TD)",
        "brand": "Jordan",
        "size": "22.5",
        "ean": "0197862948967",
        "retail_price_eur": 50.00,
        "stock_quantity": 7,
        "affiliate_link": "https://www.awin1.com/pclick.php?p=..."
      },
      "stockx": {
        "product_id": "647f5f17-1513-4f88-ac5c-e05a7bb4fd08",
        "resale_price_eur": 195.00
      },
      "profit": {
        "amount_eur": 145.00,
        "percentage": 290.0,
        "roi": 290.0
      }
    }
  ]
}
```

---

#### 5. Get Enrichment Stats
```http
GET /api/v1/integration/awin/enrichment/stats
```

**Description**: Current enrichment status overview

**Response**:
```json
{
  "success": true,
  "stats": {
    "total_products": 1150,
    "matched": 892,
    "not_found": 245,
    "errors": 13,
    "pending": 0,
    "match_rate_percentage": 77.6,
    "last_enrichment": "2025-10-12T08:19:00Z"
  }
}
```

---

## Workflow Integration

### Budibase Automation Example

**Daily Enrichment + Report**

```
Trigger: Scheduled (Daily at 2:00 AM)
  ↓
Action 1: HTTP Request
  POST /api/v1/integration/awin/enrichment/start
  → Store job_id
  ↓
Action 2: Loop Until Complete (max 30 min)
  GET /api/v1/integration/awin/enrichment/status/{job_id}
  → Wait 60 seconds
  ↓
Action 3: Get Results
  GET /api/v1/integration/awin/profit-opportunities
  → Send email with top 20 opportunities
  ↓
Action 4: Create Dashboard Data
  Save results to Budibase table
  Update charts/metrics
```

## Running Enrichment

### Via API (Programmatic)

```bash
# 1. Start enrichment job
curl -X POST http://localhost:8000/api/v1/integration/awin/enrichment/start \
  -H "Content-Type: application/json"

# Response: { "job_id": "..." }

# 2. Check status
curl http://localhost:8000/api/v1/integration/awin/enrichment/status/JOB_ID

# 3. Get profit opportunities
curl "http://localhost:8000/api/v1/integration/awin/profit-opportunities?min_profit_eur=30&limit=20"
```

### Via Python Script

```python
import asyncio
from shared.database.connection import get_db_session
from domains.integration.services.awin_stockx_enrichment_service import AwinStockXEnrichmentService

async def main():
    async with get_db_session() as session:
        service = AwinStockXEnrichmentService(
            session,
            rate_limit_requests_per_minute=60,
            batch_size=50
        )

        # Run enrichment
        results = await service.enrich_all_products(limit=None)  # None = all products

        print(f"Matched: {results['matched']}")
        print(f"Match Rate: {results['match_rate_percentage']}%")

asyncio.run(main())
```

## Rate Limiting & Performance

**StockX API Limits**: Conservative default of **60 requests/minute** to avoid rate limiting

**Performance Estimates**:
- 1,000 products @ 60 req/min = ~16.7 minutes
- 5,000 products @ 60 req/min = ~83 minutes (1.4 hours)

**Recommendations**:
- Run during off-peak hours (2-4 AM)
- Start with small batches (limit=100) to test
- Monitor error rates in job results
- Increase rate limit gradually if no errors (test 120 req/min)

## Error Handling

**Automatic Retry**: No (to respect rate limits)
**Error Logging**: All errors logged to `awin_enrichment_jobs.error_log`
**Graceful Degradation**: Products with errors marked as `enrichment_status='error'`
**Re-enrichment**: Re-run jobs to process previously failed products

## Monitoring & Alerts

### Key Metrics to Track in Budibase

1. **Match Rate** - Should be >70% for good data quality
2. **Error Rate** - Should be <5%, investigate if higher
3. **Job Duration** - Track for performance degradation
4. **Profit Opportunities** - Number of profitable products
5. **Total Potential Profit** - Sum of all profit opportunities

### Alert Conditions

```
IF match_rate < 50% THEN
  Alert: "Low match rate detected - check EAN quality"

IF error_rate > 10% THEN
  Alert: "High error rate - possible API issues"

IF job_duration > expected_duration * 1.5 THEN
  Alert: "Enrichment taking longer than usual"
```

## Profit Calculation Formula

```
Gross Profit = StockX Lowest Ask - Awin Retail Price
Net Profit = Gross Profit - Fees

Fees to Consider:
- Awin Commission: 5-15% of retail price
- StockX Seller Fee: ~10% of sale price
- Shipping to StockX: ~€10-15
- Authentication Fee: Included in seller fee
- Payment Processing: ~3%

Example:
Retail: €50
StockX: €195
Gross Profit: €145
Estimated Net Profit: €195 * 0.87 (fees) - €50 - €12 (shipping) = €95.65
ROI: 191%
```

**Note**: API returns GROSS profit. Calculate net profit in Budibase with fee assumptions.

## Migration

Apply database migration to add tracking tables:

```bash
# From project root
alembic upgrade head
```

This creates:
- `integration.awin_enrichment_jobs` table
- New columns on `integration.awin_products` for StockX matching
- Indexes for performance

## Troubleshooting

### Job Stuck in "running" Status

```sql
-- Check job status
SELECT * FROM integration.awin_enrichment_jobs
WHERE status = 'running'
ORDER BY started_at DESC;

-- Manually mark as failed if stuck
UPDATE integration.awin_enrichment_jobs
SET status = 'failed',
    completed_at = NOW(),
    error_log = 'Manually terminated - stuck job'
WHERE id = 'JOB_ID';
```

### Low Match Rate

1. Check EAN quality in Awin feed
2. Verify StockX Catalog API is working
3. Check error logs for specific failures
4. Test with known products

### Rate Limit Errors

1. Reduce `rate_limit_requests_per_minute` to 30
2. Check StockX API status
3. Verify API credentials are valid
4. Monitor for 429 errors in logs

## Future Enhancements

- [ ] Size-specific matching (match Awin size to StockX variant)
- [ ] Automatic price updates (daily refresh of StockX prices)
- [ ] Multi-currency support
- [ ] Historical profit tracking
- [ ] Webhook notifications on job completion
- [ ] Automatic listing to StockX via API
- [ ] Multiple Awin merchants support
- [ ] Profit trend analysis dashboard

## License & Usage

Internal tool for SoleFlipper business operations.
Respects Awin and StockX Terms of Service.

---

**Questions?** See main project documentation or contact development team.
