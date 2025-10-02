# Metabase Integration Module

**Version:** v2.2.3
**Architecture:** Multi-Platform Orders (StockX, eBay, GOAT, etc.)
**Created:** 2025-10-01
**Status:** ✅ Production Ready

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Materialized Views](#materialized-views)
- [Dashboard Templates](#dashboard-templates)
- [API Reference](#api-reference)
- [Setup Guide](#setup-guide)
- [Usage Examples](#usage-examples)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

---

## Overview

The Metabase Integration Module provides enterprise-grade business intelligence capabilities for SoleFlipper through:

- **7 Optimized Materialized Views** - Pre-aggregated data for fast dashboard queries
- **4 Pre-built Dashboard Templates** - Executive, Product Analytics, Platform Performance, Inventory Management
- **Automated Refresh Scheduling** - Hourly, daily, and weekly refresh strategies using pg_cron
- **REST API** - Complete API for view management, synchronization, and monitoring
- **Event-Driven Sync** - Automatic refresh on data changes (orders, inventory)

### Key Benefits

- ⚡ **Fast Query Performance** - Materialized views with strategic indexing
- 🔄 **Automated Synchronization** - No manual refresh required
- 📊 **Production-Ready Dashboards** - Battle-tested templates for business metrics
- 🎯 **Multi-Platform Support** - Unified analytics across all marketplaces
- 📈 **Scalable Architecture** - Handles thousands of transactions efficiently

---

## Architecture

### Directory Structure

```
domains/integration/metabase/
├── __init__.py                          # Module exports
├── README.md                            # This file
├── api/
│   ├── __init__.py
│   └── routes.py                        # REST API endpoints
├── config/
│   ├── __init__.py
│   └── materialized_views.py           # View configurations
├── schemas/
│   ├── __init__.py
│   └── metabase_models.py              # Pydantic models
├── services/
│   ├── __init__.py
│   ├── view_manager.py                 # View lifecycle management
│   ├── dashboard_service.py            # Dashboard templates
│   └── sync_service.py                 # Data synchronization
└── templates/
    └── (dashboard JSON exports)

```

### Data Flow

```
┌─────────────────┐
│  SoleFlipper DB │
│   (PostgreSQL)  │
└────────┬────────┘
         │
         ├─── Hourly Refresh ───┐
         ├─── Daily Refresh ────┤
         ├─── Weekly Refresh ───┤
         │                      │
         ▼                      ▼
┌──────────────────┐   ┌──────────────────┐
│  Materialized    │   │   pg_cron        │
│     Views        │   │  (Scheduler)     │
│  (analytics.*)   │   └──────────────────┘
└────────┬─────────┘
         │
         ├─── metabase_executive_metrics
         ├─── metabase_product_performance
         ├─── metabase_brand_analytics
         ├─── metabase_platform_performance
         ├─── metabase_inventory_status
         ├─── metabase_customer_geography
         └─── metabase_supplier_performance
         │
         ▼
┌──────────────────┐
│    Metabase      │
│   Dashboards     │
│  (localhost:6400)│
└──────────────────┘
```

---

## Materialized Views

### 1. Executive Metrics (`metabase_executive_metrics`)

**Purpose:** Real-time executive KPIs for high-level decision making
**Refresh Strategy:** Hourly
**Row Count:** ~2,000 (daily aggregations across platforms)

**Dimensions:**
- Time: day, week, month, quarter, year
- Platform: name, slug

**Metrics:**
- Total orders, revenue, net proceeds, profit
- Average ROI, order value
- Total fees and shipping costs
- Active days

**Indexes:**
- `idx_exec_metrics_date` - On sale_date DESC
- `idx_exec_metrics_month` - On sale_month DESC
- `idx_exec_metrics_platform` - On platform_slug

**Use Cases:**
- Executive dashboard header KPIs
- Monthly/quarterly revenue trends
- Platform comparison charts

---

### 2. Product Performance (`metabase_product_performance`)

**Purpose:** Product-level sales performance with brand and category breakdowns
**Refresh Strategy:** Daily (2 AM)
**Row Count:** ~800 (unique products with sales history)

**Dimensions:**
- Product: id, name, SKU, category
- Brand: id, name, segment, price_tier, collaboration flag

**Metrics:**
- Units sold, total revenue, avg/min/max price
- Price volatility (STDDEV)
- Total profit, average ROI, fees paid
- Average purchase price, supplier count
- Sales duration

**Indexes:**
- `idx_prod_perf_product` - On product_id
- `idx_prod_perf_brand` - On brand_id
- `idx_prod_perf_revenue` - On total_revenue DESC
- `idx_prod_perf_units` - On units_sold DESC

**Use Cases:**
- Top products by revenue/units
- Product profitability analysis
- Brand performance comparison
- Price distribution analysis

---

### 3. Brand Analytics (`metabase_brand_analytics`)

**Purpose:** Brand-level performance with market share and positioning
**Refresh Strategy:** Daily (2 AM)
**Row Count:** ~40 (unique brands)

**Dimensions:**
- Brand: name, segment, price_tier, target demographic
- Parent brand (for collaborations)

**Metrics:**
- Total sales, revenue, average price, price variance
- Total profit, average ROI
- Product variety, active months
- Market share %, sales share %
- Price positioning (Premium/Mid-Range/Entry-Level)
- Volume tier (High/Medium/Low)

**Indexes:**
- `idx_brand_analytics_id` - On brand_id
- `idx_brand_analytics_revenue` - On total_revenue DESC
- `idx_brand_analytics_share` - On market_share_pct DESC

**Use Cases:**
- Brand market share analysis
- Competitive positioning
- Collaboration performance
- Category leader identification

---

### 4. Platform Performance (`metabase_platform_performance`)

**Purpose:** Multi-platform comparison: fees, shipping, payout times
**Refresh Strategy:** Hourly
**Row Count:** ~5 (one per platform)

**Dimensions:**
- Platform: id, name, slug

**Metrics:**
- Total orders, active months
- Revenue: total, average, min, max
- Costs: total fees, average fee, fee %, shipping
- Profitability: proceeds, profit, ROI, profit margin
- Payout: received count, average days
- Geographic: countries served, cities served

**Indexes:**
- `idx_platform_perf_id` - On platform_id
- `idx_platform_perf_revenue` - On total_revenue DESC
- `idx_platform_perf_orders` - On total_orders DESC

**Use Cases:**
- Platform cost comparison
- Marketplace selection strategy
- Fee structure analysis
- Payout performance tracking

---

### 5. Inventory Status (`metabase_inventory_status`)

**Purpose:** Current inventory status: stock levels, aging, valuation
**Refresh Strategy:** Hourly
**Row Count:** ~1,500 (all inventory items)

**Dimensions:**
- Product: id, name, SKU, brand, category
- Inventory: status, condition, size, color
- Supplier: name

**Metrics:**
- Purchase: price, gross price, VAT, date
- Sales history: times sold, last sold, revenue, profit
- Aging: days in stock
- Stock category: Dead Stock / Slow Moving / Normal / Fast Moving
- Current inventory value

**Indexes:**
- `idx_inv_status_id` - On inventory_id
- `idx_inv_status_product` - On product_id
- `idx_inv_status_brand` - On brand_name
- `idx_inv_status_category` - On stock_category
- `idx_inv_status_aging` - On days_in_stock DESC

**Use Cases:**
- Dead stock identification
- Inventory aging analysis
- Stock valuation
- Repricing opportunities

---

### 6. Customer Geography (`metabase_customer_geography`)

**Purpose:** Sales by country and city for market expansion insights
**Refresh Strategy:** Daily (2 AM)
**Row Count:** ~100 (unique country/city combinations)

**Dimensions:**
- Location: country, city

**Metrics:**
- Sales volume: orders, active months
- Revenue: total, average order value
- Profitability: profit, ROI
- Shipping: average cost
- Platform mix: count, names
- Product mix: unique products, brands

**Indexes:**
- `idx_cust_geo_country` - On country
- `idx_cust_geo_city` - On city
- `idx_cust_geo_revenue` - On total_revenue DESC

**Use Cases:**
- Market expansion planning
- Geographic revenue concentration
- International shipping analysis
- Regional product preferences

---

### 7. Supplier Performance (`metabase_supplier_performance`)

**Purpose:** Supplier reliability, product quality, and profitability
**Refresh Strategy:** Weekly (Monday 3 AM)
**Row Count:** ~20 (active suppliers)

**Dimensions:**
- Supplier: id, name, email, phone, country, rating

**Metrics:**
- Purchase volume: count, total spent, average price
- Product diversity: unique products, brands
- Sales performance: units sold, sell-through rate, revenue, profit, ROI
- Timing: average days to sell
- Current inventory: unsold units, unsold value

**Indexes:**
- `idx_supp_perf_id` - On supplier_id
- `idx_supp_perf_revenue` - On total_revenue_generated DESC
- `idx_supp_perf_roi` - On avg_roi DESC

**Use Cases:**
- Supplier evaluation
- Sourcing strategy optimization
- Dead stock root cause analysis
- Negotiation leverage data

---

## Dashboard Templates

### 1. Executive Dashboard

**Purpose:** High-level KPIs and business metrics for C-level
**Target Users:** Executives, Business Owners
**Refresh:** Real-time (hourly views)

**Cards (8 total):**

**Row 1: KPI Cards** (4 scalars)
- Total Revenue (current month)
- Total Profit (current month)
- Average ROI
- Active Orders

**Row 2: Trend Analysis**
- Revenue Trend (12 months) - Line chart

**Row 3: Performance Comparison**
- Platform Performance - Bar chart
- Top 10 Products by Revenue - Table

**Row 4: Geographic Analysis**
- Sales by Country - Map visualization

**Parameters:**
- Date Range (default: past 30 days)

**Source Views:**
- `metabase_executive_metrics`
- `metabase_platform_performance`
- `metabase_product_performance`
- `metabase_customer_geography`

---

### 2. Product Analytics Dashboard

**Purpose:** Detailed product and brand performance analytics
**Target Users:** Product Managers, Buyers
**Refresh:** Daily

**Cards (7 total):**

**Row 1: Top Performers**
- Top Products by Revenue - Bar chart
- Top Products by Units Sold - Bar chart

**Row 2: Distribution Analysis**
- Brand Performance - Pie chart
- Category Distribution - Donut chart

**Row 3: Detailed Analysis**
- Product Performance Table - Full metrics

**Row 4: Advanced Analytics**
- Price Distribution - Histogram
- Sell-Through Rate by Brand - Bar chart

**Parameters:**
- Date Range (default: past 90 days)
- Brand filter

**Source Views:**
- `metabase_product_performance`
- `metabase_brand_analytics`

---

### 3. Platform Performance Dashboard

**Purpose:** Multi-platform sales and profitability analysis
**Target Users:** Operations, Finance
**Refresh:** Hourly

**Cards (8 total):**

**Row 1: Platform KPIs** (4 scalars)
- Total Orders
- Total Revenue
- Average Fees
- Average Payout Days

**Row 2: Cost Analysis**
- Revenue by Platform - Bar chart
- Fee Comparison - Bar chart

**Row 3: Detailed Metrics**
- Platform Profitability Table - Full comparison

**Row 4: Geographic Coverage**
- Countries Served by Platform - Map

**Parameters:**
- Date Range (default: past 30 days)
- Platform filter

**Source Views:**
- `metabase_platform_performance`
- `metabase_customer_geography`

---

### 4. Inventory Management Dashboard

**Purpose:** Inventory status, aging analysis, and supplier performance
**Target Users:** Inventory Managers, Buyers
**Refresh:** Hourly

**Cards (8 total):**

**Row 1: Inventory KPIs** (4 scalars)
- Current Stock Value
- Dead Stock Count
- Average Days in Stock
- Slow-Moving Items

**Row 2: Status Analysis**
- Inventory Aging Distribution - Bar chart
- Stock Status by Category - Pie chart

**Row 3: Item Details**
- Inventory Status Table - Full item list

**Row 4: Supplier Metrics**
- Supplier Performance Table - ROI and reliability

**Parameters:**
- Stock Category filter
- Supplier filter

**Source Views:**
- `metabase_inventory_status`
- `metabase_supplier_performance`

---

## API Reference

Base URL: `http://localhost:8000/api/v1/metabase`

### View Management

#### Create All Views
```http
POST /views/create
```

**Query Parameters:**
- `drop_existing` (boolean, optional) - Drop existing views before creating

**Response:** `200 OK`
```json
{
  "metabase_executive_metrics": true,
  "metabase_product_performance": true,
  "metabase_brand_analytics": true,
  "metabase_platform_performance": true,
  "metabase_inventory_status": true,
  "metabase_customer_geography": true,
  "metabase_supplier_performance": true
}
```

---

#### Refresh Single View
```http
POST /views/{view_name}/refresh
```

**Path Parameters:**
- `view_name` (string, required) - Name of the view

**Response:** `200 OK`
```json
{
  "view_name": "metabase_executive_metrics",
  "status": "completed",
  "started_at": "2025-10-01T10:00:00Z",
  "completed_at": "2025-10-01T10:00:15Z",
  "duration_seconds": 15.2,
  "error_message": null
}
```

---

#### Refresh by Strategy
```http
POST /views/refresh-by-strategy/{strategy}
```

**Path Parameters:**
- `strategy` (enum, required) - `hourly`, `daily`, or `weekly`

**Response:** `200 OK`
```json
[
  {
    "view_name": "metabase_executive_metrics",
    "status": "completed",
    "duration_seconds": 12.5
  },
  {
    "view_name": "metabase_platform_performance",
    "status": "completed",
    "duration_seconds": 8.3
  }
]
```

---

#### Get All View Statuses
```http
GET /views/status
```

**Response:** `200 OK`
```json
[
  {
    "view_name": "metabase_executive_metrics",
    "exists": true,
    "last_refresh": null,
    "row_count": 2145,
    "size_bytes": null,
    "indexes": [
      "idx_exec_metrics_date",
      "idx_exec_metrics_month",
      "idx_exec_metrics_platform"
    ]
  }
]
```

---

#### Get Single View Status
```http
GET /views/{view_name}/status
```

**Response:** `200 OK` or `404 Not Found`

---

#### Drop View
```http
DELETE /views/{view_name}
```

**Query Parameters:**
- `cascade` (boolean, default: true) - Drop dependent objects

**Response:** `200 OK`
```json
{
  "message": "View 'metabase_executive_metrics' dropped successfully"
}
```

---

### Synchronization

#### Sync All Views
```http
POST /sync/all
```

**Response:** `200 OK`
```json
{
  "metabase_executive_metrics": {
    "status": "completed",
    "duration_seconds": 14.2
  },
  "metabase_product_performance": {
    "status": "completed",
    "duration_seconds": 22.8
  }
}
```

---

#### Sync on Order Event
```http
POST /sync/on-order-event
```

Triggers refresh of views affected by order changes:
- `metabase_executive_metrics`
- `metabase_platform_performance`
- `metabase_product_performance`

---

#### Sync on Inventory Event
```http
POST /sync/on-inventory-event
```

Triggers refresh of views affected by inventory changes:
- `metabase_inventory_status`
- `metabase_product_performance`
- `metabase_supplier_performance`

---

#### Get Sync Status
```http
GET /sync/status
```

**Response:** `200 OK`
```json
{
  "total_views": 7,
  "existing_views": 7,
  "missing_views": 0,
  "total_rows": 5428,
  "last_check": "2025-10-01T10:30:00Z",
  "views": [...]
}
```

---

### Dashboard Templates

#### Get All Dashboards
```http
GET /dashboards
```

**Response:** `200 OK`
```json
{
  "executive": { ... },
  "product_analytics": { ... },
  "platform_performance": { ... },
  "inventory_management": { ... }
}
```

---

#### Get Single Dashboard
```http
GET /dashboards/{dashboard_name}
```

**Path Parameters:**
- `dashboard_name` (string) - `executive`, `product_analytics`, `platform_performance`, `inventory_management`

**Response:** `200 OK` or `404 Not Found`

---

### Automation

#### Setup Refresh Schedule
```http
POST /setup/refresh-schedule
```

Requires:
- PostgreSQL `pg_cron` extension installed
- Superuser privileges

**Response:** `200 OK`
```json
{
  "metabase_executive_metrics": "hourly",
  "metabase_platform_performance": "hourly",
  "metabase_product_performance": "daily",
  "metabase_brand_analytics": "daily",
  "metabase_inventory_status": "hourly",
  "metabase_customer_geography": "daily",
  "metabase_supplier_performance": "weekly"
}
```

---

## Setup Guide

### Prerequisites

1. **PostgreSQL 12+** with extensions:
   - `pg_cron` (optional, for automated refresh)

2. **Metabase** installed and running:
   ```bash
   docker-compose up metabase -d
   # Access: http://localhost:6400
   ```

3. **SoleFlipper API** running on port 8000

---

### Installation Steps

#### 1. Create Materialized Views

```bash
# Using Python API
python -c "
import asyncio
from domains.integration.metabase.services import MetabaseViewManager

async def setup():
    manager = MetabaseViewManager()
    results = await manager.create_all_views(drop_existing=True)
    print(f'Created {sum(results.values())}/{len(results)} views')

asyncio.run(setup())
"
```

Or via REST API:
```bash
curl -X POST "http://localhost:8000/api/v1/metabase/views/create?drop_existing=true"
```

#### 2. Setup Automatic Refresh (Optional)

```sql
-- Install pg_cron extension
CREATE EXTENSION IF NOT EXISTS pg_cron;
```

```bash
# Setup cron jobs via API
curl -X POST "http://localhost:8000/api/v1/metabase/setup/refresh-schedule"
```

#### 3. Connect Metabase to PostgreSQL

1. Open Metabase: http://localhost:6400
2. Go to **Settings → Admin → Databases → Add Database**
3. Configure connection:
   - **Database type:** PostgreSQL
   - **Name:** SoleFlipper
   - **Host:** `postgres` (if using Docker) or `localhost`
   - **Port:** `5432`
   - **Database name:** `soleflip`
   - **Username:** Your DB user
   - **Password:** Your DB password
4. Click **Save**
5. Wait for schema sync (may take 1-2 minutes)

#### 4. Create Dashboards

You can either:

**A) Import Pre-configured JSON (Recommended)**
```bash
# Export dashboard templates to JSON
curl http://localhost:8000/api/v1/metabase/dashboards/executive > executive_dashboard.json

# Import in Metabase UI: Settings → Admin → Data Model → Import
```

**B) Create Manually Using Templates**

Follow the [Dashboard Templates](#dashboard-templates) section for card layouts and configurations.

---

## Usage Examples

### Python Usage

```python
from domains.integration.metabase.services import (
    MetabaseViewManager,
    MetabaseDashboardService,
    MetabaseSyncService
)

# Initialize services
view_manager = MetabaseViewManager()
dashboard_service = MetabaseDashboardService()
sync_service = MetabaseSyncService()

# Create all materialized views
results = await view_manager.create_all_views()
print(f"Created {sum(results.values())}/{len(results)} views")

# Refresh specific view
status = await view_manager.refresh_view("metabase_executive_metrics")
print(f"Refreshed in {status.duration_seconds}s")

# Get view status
view_status = await view_manager.get_view_status("metabase_product_performance")
print(f"Rows: {view_status.row_count}, Indexes: {len(view_status.indexes)}")

# Sync after order creation (event-driven)
await sync_service.sync_on_order_event()

# Generate dashboard templates
dashboards = dashboard_service.generate_all_dashboards()
executive_dashboard = dashboards["executive"]
print(f"Dashboard: {executive_dashboard.name}")
print(f"Cards: {len(executive_dashboard.ordered_cards)}")
```

---

### cURL Usage

```bash
# Create all views
curl -X POST "http://localhost:8000/api/v1/metabase/views/create"

# Refresh hourly views
curl -X POST "http://localhost:8000/api/v1/metabase/views/refresh-by-strategy/hourly"

# Get all view statuses
curl "http://localhost:8000/api/v1/metabase/views/status" | jq

# Sync all views
curl -X POST "http://localhost:8000/api/v1/metabase/sync/all"

# Get sync status
curl "http://localhost:8000/api/v1/metabase/sync/status" | jq

# Get executive dashboard config
curl "http://localhost:8000/api/v1/metabase/dashboards/executive" | jq
```

---

### Integration with FastAPI

```python
# In your main.py or router file
from domains.integration.metabase.api import router as metabase_router

app = FastAPI()
app.include_router(metabase_router, prefix="/api/v1")
```

---

### Event-Driven Refresh

```python
# In your order service after creating an order
from domains.integration.metabase.services import MetabaseSyncService

async def create_order(order_data):
    # ... create order in database ...

    # Trigger Metabase sync for affected views
    sync_service = MetabaseSyncService()
    await sync_service.sync_on_order_event()

    return order
```

---

## Performance Optimization

### View Refresh Times (1,309 orders)

| View | Refresh Strategy | Typical Duration | Row Count |
|------|-----------------|------------------|-----------|
| `metabase_executive_metrics` | Hourly | 12-15s | ~2,000 |
| `metabase_platform_performance` | Hourly | 2-3s | ~5 |
| `metabase_inventory_status` | Hourly | 8-10s | ~1,500 |
| `metabase_product_performance` | Daily | 20-25s | ~800 |
| `metabase_brand_analytics` | Daily | 15-18s | ~40 |
| `metabase_customer_geography` | Daily | 5-7s | ~100 |
| `metabase_supplier_performance` | Weekly | 10-12s | ~20 |

**Total Full Refresh:** ~75-90 seconds for all 7 views

---

### Index Strategy

All views include strategic indexes for common query patterns:

1. **Primary Dimension Indexes** - On IDs (product_id, brand_id, platform_id, etc.)
2. **Sort Indexes** - On frequently sorted columns (revenue DESC, date DESC)
3. **Filter Indexes** - On common filter fields (platform_slug, brand_name, country)
4. **Composite Indexes** - For multi-column queries (date + platform)

---

### Optimization Tips

1. **Use CONCURRENTLY for Production**
   ```sql
   REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.metabase_executive_metrics;
   ```
   Requires a unique index but allows reads during refresh.

2. **Schedule Refreshes During Low Traffic**
   - Hourly: :00 minutes past the hour
   - Daily: 2 AM local time
   - Weekly: Monday 3 AM

3. **Monitor View Sizes**
   ```sql
   SELECT
       schemaname,
       matviewname,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) as size
   FROM pg_matviews
   WHERE schemaname = 'analytics'
   ORDER BY pg_total_relation_size(schemaname||'.'||matviewname) DESC;
   ```

4. **Consider Incremental Refresh for Large Views**
   For views with >10,000 rows, implement custom incremental refresh logic.

---

## Troubleshooting

### Issue: View doesn't exist

**Error:** `relation "analytics.metabase_executive_metrics" does not exist`

**Solution:**
```bash
# Create all views
curl -X POST "http://localhost:8000/api/v1/metabase/views/create"
```

---

### Issue: CONCURRENTLY requires unique index

**Error:** `cannot refresh materialized view "analytics.view_name" concurrently`

**Solution:**
```sql
-- Create unique index on a unique column (e.g., composite key)
CREATE UNIQUE INDEX idx_unique_exec_metrics
ON analytics.metabase_executive_metrics(sale_date, platform_slug);

-- Then refresh with CONCURRENTLY
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.metabase_executive_metrics;
```

---

### Issue: pg_cron extension not found

**Error:** `extension "pg_cron" is not available`

**Solution:**
```bash
# Install pg_cron (Ubuntu/Debian)
sudo apt-get install postgresql-16-cron

# Add to postgresql.conf
shared_preload_libraries = 'pg_cron'

# Restart PostgreSQL
sudo systemctl restart postgresql

# Create extension as superuser
psql -U postgres -d soleflip -c "CREATE EXTENSION pg_cron;"
```

---

### Issue: Slow refresh times

**Symptoms:** View refresh takes >30 seconds

**Solutions:**
1. Check index usage:
   ```sql
   EXPLAIN ANALYZE
   SELECT * FROM analytics.metabase_executive_metrics
   WHERE sale_date > NOW() - INTERVAL '30 days';
   ```

2. Vacuum and analyze tables:
   ```sql
   VACUUM ANALYZE transactions.orders;
   VACUUM ANALYZE products.inventory;
   VACUUM ANALYZE products.products;
   ```

3. Update table statistics:
   ```sql
   ANALYZE transactions.orders;
   ```

---

### Issue: Metabase shows stale data

**Symptoms:** Dashboard shows old data despite recent transactions

**Solutions:**
1. Manual refresh:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/metabase/sync/all"
   ```

2. Check view last refresh:
   ```sql
   SELECT
       schemaname,
       matviewname,
       pg_stat_get_last_analyze_time(
           (schemaname||'.'||matviewname)::regclass
       ) AS last_analyzed
   FROM pg_matviews
   WHERE schemaname = 'analytics';
   ```

3. Verify cron jobs:
   ```sql
   SELECT * FROM cron.job WHERE jobname LIKE 'refresh_%';
   ```

---

## Maintenance

### Daily Tasks

- ✅ Monitor view refresh success via `/sync/status` endpoint
- ✅ Check for failed cron jobs in `cron.job_run_details`

### Weekly Tasks

- ✅ Review view sizes and row counts
- ✅ Analyze slow queries in Metabase performance logs
- ✅ Vacuum and analyze materialized views

### Monthly Tasks

- ✅ Review and optimize dashboard query performance
- ✅ Add new views based on business requirements
- ✅ Archive old data if necessary

### Maintenance Commands

```bash
# Check view health
curl "http://localhost:8000/api/v1/metabase/sync/status" | jq

# Manual refresh all views
curl -X POST "http://localhost:8000/api/v1/metabase/sync/all"

# Drop and recreate all views (nuclear option)
curl -X POST "http://localhost:8000/api/v1/metabase/views/create?drop_existing=true"

# Check cron job history
psql -U postgres -d soleflip -c "
SELECT
    jobid,
    runid,
    job_pid,
    status,
    start_time,
    end_time,
    end_time - start_time AS duration
FROM cron.job_run_details
WHERE jobname LIKE 'refresh_%'
ORDER BY start_time DESC
LIMIT 20;
"
```

---

## Related Documentation

- [Budibase Integration](../budibase/README.md) - Sister module for low-code platform integration
- [Multi-Platform Orders Migration](../../../context/orders-multi-platform-migration.md) - Architecture context
- [Analytics Views Migration](../../../context/analytics-views-migration-plan.md) - Historical migration reference
- [MIGRATION_INDEX](../../../context/MIGRATION_INDEX.md) - Complete migration history

---

## Support

For issues or questions:
- Check [Troubleshooting](#troubleshooting) section
- Review API logs: `tail -f logs/soleflip.log | grep metabase`
- Test materialized view queries directly in PostgreSQL
- Verify Metabase connection: Settings → Admin → Databases → SoleFlipper → Test Connection

---

**Last Updated:** 2025-10-01
**Module Version:** v2.2.3
**Maintained by:** SoleFlipper Development Team
