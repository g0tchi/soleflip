# Metabase Integration - Quick Start Guide

**Version:** v2.2.3
**Created:** 2025-10-01
**Status:** ✅ Production Ready

---

## 🚀 5-Minute Setup

### 1. Create All Views (One Command)

```bash
# Using Python script (recommended)
python domains/integration/metabase/setup_metabase.py

# Or using API
curl -X POST "http://localhost:8000/api/v1/metabase/views/create?drop_existing=true"
```

Expected output: `Created 7/7 views` in ~10-15 seconds

---

### 2. Connect Metabase to Database

1. Open Metabase: http://localhost:6400
2. Go to **Settings → Admin → Databases → Add Database**
3. Configure:
   - **Type:** PostgreSQL
   - **Host:** `postgres` (Docker) or `localhost`
   - **Port:** `5432`
   - **Database:** `soleflip`
   - **Username:** Your DB user
   - **Password:** Your DB password
4. Click **Save** and wait for sync (~1-2 minutes)

---

### 3. Verify Installation

```bash
curl "http://localhost:8000/api/v1/metabase/views/status" | jq
```

Expected: All 7 views with `"exists": true`

---

## 📊 Available Views

| View Name | Purpose | Rows | Refresh |
|-----------|---------|------|---------|
| `metabase_executive_metrics` | Real-time KPIs | ~2,000 | Hourly |
| `metabase_product_performance` | Product sales analysis | ~800 | Daily |
| `metabase_brand_analytics` | Brand market share | ~40 | Daily |
| `metabase_platform_performance` | Multi-platform comparison | ~5 | Hourly |
| `metabase_inventory_status` | Stock levels & aging | ~1,500 | Hourly |
| `metabase_customer_geography` | Sales by location | ~100 | Daily |
| `metabase_supplier_performance` | Supplier ROI | ~20 | Weekly |

All views are in the `analytics` schema.

---

## 🎯 Common Tasks

### Manual Refresh All Views
```bash
curl -X POST "http://localhost:8000/api/v1/metabase/sync/all"
```

### Refresh Single View
```bash
curl -X POST "http://localhost:8000/api/v1/metabase/views/metabase_executive_metrics/refresh"
```

### Check View Status
```bash
curl "http://localhost:8000/api/v1/metabase/views/status"
```

### Get Dashboard Templates
```bash
curl "http://localhost:8000/api/v1/metabase/dashboards" | jq
```

---

## 🔄 Automated Refresh (Optional)

Requires `pg_cron` extension:

```bash
# Install pg_cron
sudo apt-get install postgresql-16-cron

# Add to postgresql.conf
echo "shared_preload_libraries = 'pg_cron'" | sudo tee -a /etc/postgresql/16/main/postgresql.conf

# Restart PostgreSQL
sudo systemctl restart postgresql

# Create extension
psql -U postgres -d soleflip -c "CREATE EXTENSION pg_cron;"

# Setup automatic refresh
curl -X POST "http://localhost:8000/api/v1/metabase/setup/refresh-schedule"
```

**Schedule:**
- **Hourly views** (executive_metrics, platform_performance, inventory_status): Every hour at :00
- **Daily views** (product_performance, brand_analytics, customer_geography): Daily at 2 AM
- **Weekly views** (supplier_performance): Monday at 3 AM

---

## 📈 Pre-built Dashboards

### 1. Executive Dashboard
**Focus:** High-level KPIs for C-level

**Key Cards:**
- Total Revenue (scalar)
- Total Profit (scalar)
- Average ROI (scalar)
- Active Orders (scalar)
- Revenue Trend (line chart - 12 months)
- Platform Performance (bar chart)
- Top Products (table)
- Geographic Distribution (map)

**Query:**
```bash
curl "http://localhost:8000/api/v1/metabase/dashboards/executive" | jq
```

---

### 2. Product Analytics Dashboard
**Focus:** Product and brand performance

**Key Cards:**
- Top Products by Revenue (bar chart)
- Top Products by Units (bar chart)
- Brand Performance (pie chart)
- Category Distribution (donut chart)
- Product Performance Table
- Price Distribution (histogram)
- Sell-Through Rate (bar chart)

**Query:**
```bash
curl "http://localhost:8000/api/v1/metabase/dashboards/product_analytics" | jq
```

---

### 3. Platform Performance Dashboard
**Focus:** Multi-platform comparison

**Key Cards:**
- Total Orders (scalar)
- Total Revenue (scalar)
- Average Fees (scalar)
- Average Payout Days (scalar)
- Revenue by Platform (bar chart)
- Fee Comparison (bar chart)
- Platform Profitability Table
- Geographic Coverage (map)

**Query:**
```bash
curl "http://localhost:8000/api/v1/metabase/dashboards/platform_performance" | jq
```

---

### 4. Inventory Management Dashboard
**Focus:** Stock status and supplier analysis

**Key Cards:**
- Current Stock Value (scalar)
- Dead Stock Count (scalar)
- Average Days in Stock (scalar)
- Slow-Moving Items (scalar)
- Inventory Aging Distribution (bar chart)
- Stock Status by Category (pie chart)
- Inventory Status Table
- Supplier Performance Table

**Query:**
```bash
curl "http://localhost:8000/api/v1/metabase/dashboards/inventory_management" | jq
```

---

## 🔍 Sample Queries

### Top 10 Products by Revenue
```sql
SELECT
    product_name,
    brand_name,
    units_sold,
    total_revenue,
    avg_sale_price
FROM analytics.metabase_product_performance
ORDER BY total_revenue DESC
LIMIT 10;
```

---

### Platform Cost Comparison
```sql
SELECT
    platform_name,
    total_orders,
    total_revenue,
    avg_fee_pct,
    avg_profit_margin
FROM analytics.metabase_platform_performance
ORDER BY total_revenue DESC;
```

---

### Dead Stock Report
```sql
SELECT
    product_name,
    brand_name,
    days_in_stock,
    current_inventory_value,
    supplier_name
FROM analytics.metabase_inventory_status
WHERE stock_category = 'Dead Stock'
ORDER BY days_in_stock DESC;
```

---

### Monthly Revenue Trend
```sql
SELECT
    sale_month,
    platform_name,
    total_revenue,
    total_profit,
    avg_roi
FROM analytics.metabase_executive_metrics
WHERE sale_month >= NOW() - INTERVAL '12 months'
ORDER BY sale_month DESC, total_revenue DESC;
```

---

### Top Suppliers by ROI
```sql
SELECT
    supplier_name,
    total_purchases,
    units_sold,
    sell_through_rate,
    avg_roi,
    total_profit_generated
FROM analytics.metabase_supplier_performance
ORDER BY avg_roi DESC
LIMIT 10;
```

---

## 🐛 Troubleshooting

### Views Not Showing in Metabase

**Cause:** Schema not selected in Metabase sync

**Fix:**
1. Go to **Settings → Admin → Databases → SoleFlipper**
2. Scroll to **Schemas**
3. Ensure `analytics` is checked
4. Click **Save**
5. Click **Sync database schema now**

---

### "Materialized view does not exist"

**Cause:** Views not created yet

**Fix:**
```bash
python domains/integration/metabase/setup_metabase.py
```

---

### Stale Data in Dashboard

**Cause:** Views not refreshed

**Fix:**
```bash
# Manual refresh all
curl -X POST "http://localhost:8000/api/v1/metabase/sync/all"

# Check last refresh
curl "http://localhost:8000/api/v1/metabase/views/status" | jq
```

---

### Slow Query Performance

**Cause:** Missing indexes or stale statistics

**Fix:**
```sql
-- Vacuum and analyze
VACUUM ANALYZE analytics.metabase_executive_metrics;
VACUUM ANALYZE analytics.metabase_product_performance;

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS times_used
FROM pg_stat_user_indexes
WHERE schemaname = 'analytics'
ORDER BY idx_scan DESC;
```

---

## 📚 Full Documentation

For complete documentation including:
- Detailed view schemas
- Performance optimization
- API reference
- Maintenance procedures

See: `domains/integration/metabase/README.md`

---

## 🔗 Related Resources

- **Budibase Integration:** `domains/integration/budibase/README.md`
- **Multi-Platform Migration:** `context/orders-multi-platform-migration.md`
- **Analytics Views Migration:** `context/analytics-views-migration-plan.md`
- **Migration Index:** `context/MIGRATION_INDEX.md`

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| Create views | `python domains/integration/metabase/setup_metabase.py` |
| Refresh all | `curl -X POST "localhost:8000/api/v1/metabase/sync/all"` |
| View status | `curl "localhost:8000/api/v1/metabase/views/status"` |
| Get dashboards | `curl "localhost:8000/api/v1/metabase/dashboards"` |
| Metabase UI | http://localhost:6400 |
| API Docs | http://localhost:8000/docs#/Metabase%20Integration |

---

**Last Updated:** 2025-10-01
**Module Version:** v2.2.3
