# Metabase Setup Guide for SoleFlipper

## Overview
This guide helps you set up Metabase analytics dashboards for the SoleFlipper sneaker management system.

## Prerequisites
- SoleFlipper database is running and populated
- Metabase instance is accessible
- Database user with read access to all schemas

## 1. Database Connection Setup

### Connection Parameters
```
Database Type: PostgreSQL
Host: localhost (or your database host)
Port: 5432
Database Name: soleflip
Username: metabase_user (recommended dedicated user)
Password: [secure password]
```

### Create Dedicated Metabase User
```sql
-- Create read-only user for Metabase
CREATE ROLE metabase_user WITH LOGIN PASSWORD 'your_secure_password';

-- Grant access to all schemas
GRANT USAGE ON SCHEMA core TO metabase_user;
GRANT USAGE ON SCHEMA products TO metabase_user;
GRANT USAGE ON SCHEMA sales TO metabase_user;
GRANT USAGE ON SCHEMA integration TO metabase_user;
GRANT USAGE ON SCHEMA logging TO metabase_user;
GRANT USAGE ON SCHEMA analytics TO metabase_user;

-- Grant read access to all tables
GRANT SELECT ON ALL TABLES IN SCHEMA core TO metabase_user;
GRANT SELECT ON ALL TABLES IN SCHEMA products TO metabase_user;
GRANT SELECT ON ALL TABLES IN SCHEMA sales TO metabase_user;
GRANT SELECT ON ALL TABLES IN SCHEMA integration TO metabase_user;
GRANT SELECT ON ALL TABLES IN SCHEMA logging TO metabase_user;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO metabase_user;

-- Grant access to future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA core GRANT SELECT ON TABLES TO metabase_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA products GRANT SELECT ON TABLES TO metabase_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA sales GRANT SELECT ON TABLES TO metabase_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA integration GRANT SELECT ON TABLES TO metabase_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA logging GRANT SELECT ON TABLES TO metabase_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO metabase_user;
```

## 2. Import Analytics Views

Run the SQL from `metabase_annotations.sql` to create optimized views:

```bash
psql -h localhost -U postgres -d soleflip -f docs/metabase_annotations.sql
```

## 3. Data Model Configuration

### Field Type Settings
Configure these field types in Metabase Admin -> Data Model:

| Table | Field | Type | Format |
|-------|-------|------|--------|
| products.products | retail_price | Currency | USD |
| inventory_items | purchase_price | Currency | USD |
| transactions | sale_price | Currency | USD |
| transactions | platform_fee | Currency | USD |
| transactions | net_profit | Currency | USD |
| import_batches | processing_time_ms | Duration | milliseconds |
| sales_performance | profit_margin_percent | Percentage | 1 decimal |

### Field Display Names
Update display names for better readability:

| Field | Display Name |
|-------|-------------|
| sku | SKU |
| retail_price | Retail Price |
| purchase_price | Purchase Price |
| net_profit | Net Profit |
| profit_margin_percent | Profit Margin % |
| transaction_date | Sale Date |
| processing_time_ms | Processing Time |

## 4. Dashboard Creation

### Dashboard 1: Business Overview
**Purpose**: High-level business metrics and trends

**Questions to create**:
1. **Total Inventory Value** (Number card)
   - Query: `SELECT SUM(inventory_value) FROM analytics.inventory_overview`
   - Visualization: Number
   - Format: Currency

2. **Monthly Profit Trend** (Line chart)
   - Query: Use `analytics.monthly_summary` view
   - X-axis: month
   - Y-axis: net_profit
   - Visualization: Line chart

3. **Top 10 Brands by Profit** (Bar chart)
   - Query: Brand profit analysis from `metabase_annotations.sql`
   - X-axis: brand
   - Y-axis: total_profit
   - Visualization: Bar chart

4. **Recent Sales** (Table)
   - Query: `SELECT * FROM analytics.sales_performance WHERE time_period = 'Last 30 Days' ORDER BY transaction_date DESC LIMIT 20`
   - Visualization: Table

### Dashboard 2: Inventory Management
**Purpose**: Inventory tracking and management insights

**Questions to create**:
1. **Inventory Status Distribution** (Pie chart)
   - Query: Status counts from inventory_items
   - Visualization: Pie chart

2. **Size Distribution** (Bar chart)
   - Query: Size analysis from `metabase_annotations.sql`
   - Visualization: Bar chart

3. **Inventory by Brand** (Bar chart)
   - Query: `SELECT brand, SUM(total_units) as units FROM analytics.inventory_overview GROUP BY brand ORDER BY units DESC`
   - Visualization: Bar chart

4. **Low Stock Alert** (Table)
   - Query: Products with inventory count < 3
   - Visualization: Table
   - Conditional formatting: Red for count < 2

### Dashboard 3: Import Monitoring
**Purpose**: Data pipeline health and import tracking

**Questions to create**:
1. **Import Success Rate** (Bar chart)
   - Query: Success rate by source from `metabase_annotations.sql`
   - Visualization: Bar chart
   - Y-axis: success_rate (percentage)

2. **Processing Time Trends** (Line chart)
   - Query: `SELECT DATE_TRUNC('day', created_at) as date, AVG(processing_time_ms) FROM analytics.import_activity GROUP BY date ORDER BY date`
   - Visualization: Line chart

3. **Daily Import Volume** (Bar chart)
   - Query: Daily import counts
   - Visualization: Bar chart

4. **Failed Imports** (Table)
   - Query: `SELECT * FROM analytics.import_activity WHERE status = 'failed' ORDER BY created_at DESC`
   - Visualization: Table

### Dashboard 4: Profitability Analysis
**Purpose**: Deep dive into profit margins and performance

**Questions to create**:
1. **Profit Margin Distribution** (Histogram)
   - Query: `SELECT profit_margin_percent FROM analytics.sales_performance`
   - Visualization: Histogram
   - Bins: 10

2. **Most Profitable Products** (Table)
   - Query: Top products by total profit
   - Visualization: Table

3. **Platform Performance** (Bar chart)
   - Query: Profit by platform
   - Visualization: Bar chart

4. **Seasonal Trends** (Line chart)
   - Query: Monthly sales with year-over-year comparison
   - Visualization: Line chart
   - Grouping: By year

## 5. Filters and Parameters

### Global Filters
Set up these filters for cross-dashboard use:

1. **Date Range Filter**
   - Type: Date range
   - Default: Last 90 days
   - Apply to: All date fields

2. **Brand Filter**
   - Type: Category
   - Source: core.brands.name
   - Apply to: Brand-related questions

3. **Status Filter**
   - Type: Category
   - Source: inventory_items.status
   - Apply to: Inventory questions

### Dashboard-Specific Filters

**Business Overview**:
- Time period selector (Last 30 days, Last 90 days, This year)

**Inventory Management**:
- Brand filter
- Category filter
- Status filter

**Import Monitoring**:
- Source type filter
- Date range filter

**Profitability Analysis**:
- Brand filter
- Platform filter
- Profit margin range

## 6. Automated Refresh Schedule

Configure refresh schedules in Metabase:

### Real-time (Every 5 minutes)
- Import activity monitoring
- Current inventory status

### Hourly
- Inventory overview
- Sales performance metrics

### Daily
- Monthly summaries
- Historical analysis

### Weekly
- Long-term trend analysis
- Comparative reports

## 7. Alerts and Notifications

Set up alerts for critical metrics:

1. **Low Inventory Alert**
   - Condition: Any product with < 2 units in stock
   - Frequency: Daily
   - Recipients: Inventory managers

2. **Import Failure Alert**
   - Condition: Any import batch with status = 'failed'
   - Frequency: Immediate
   - Recipients: Technical team

3. **Daily Profit Alert**
   - Condition: Daily profit drops below threshold
   - Frequency: Daily
   - Recipients: Business team

## 8. Performance Optimization

### Database Indexes
Ensure these indexes exist for optimal Metabase performance:

```sql
-- Analytics view optimization
CREATE INDEX CONCURRENTLY idx_inventory_items_status ON products.inventory_items(status);
CREATE INDEX CONCURRENTLY idx_transactions_date ON sales.transactions(transaction_date);
CREATE INDEX CONCURRENTLY idx_import_batches_created_at ON integration.import_batches(created_at);
CREATE INDEX CONCURRENTLY idx_products_brand_id ON products.products(brand_id);

-- Composite indexes for common queries
CREATE INDEX CONCURRENTLY idx_transactions_status_date ON sales.transactions(status, transaction_date);
CREATE INDEX CONCURRENTLY idx_inventory_items_product_status ON products.inventory_items(product_id, status);
```

### Query Caching
- Enable question caching with 1 hour TTL for most queries
- Use 5-minute TTL for real-time monitoring queries
- Set daily refresh for historical trend queries

## 9. User Access and Permissions

### User Groups
Create these user groups in Metabase:

1. **Executives**
   - Access: Business Overview dashboard
   - Permissions: View only

2. **Operations**
   - Access: All dashboards
   - Permissions: View and create questions

3. **Technical**
   - Access: Import Monitoring, all dashboards
   - Permissions: Full access

4. **Finance**
   - Access: Business Overview, Profitability Analysis
   - Permissions: View and create questions

## 10. Troubleshooting

### Common Issues

**Slow Dashboard Loading**:
- Check database indexes
- Optimize query complexity
- Reduce dashboard question count

**Data Not Updating**:
- Verify database sync schedule
- Check user permissions
- Validate query syntax

**Missing Data**:
- Confirm analytics views are created
- Check data pipeline status
- Verify import batch completion

### Monitoring Queries

```sql
-- Check dashboard performance
SELECT 
    question_id,
    AVG(running_time) as avg_runtime_ms,
    COUNT(*) as execution_count
FROM query_execution 
WHERE executed_at >= NOW() - INTERVAL '24 hours'
GROUP BY question_id
ORDER BY avg_runtime_ms DESC;

-- Monitor data freshness
SELECT 
    MAX(created_at) as latest_import,
    NOW() - MAX(created_at) as time_since_last_import
FROM integration.import_batches;
```

## 11. Maintenance

### Daily Tasks
- Check dashboard load times
- Verify data freshness
- Review alert notifications

### Weekly Tasks
- Analyze question performance
- Update dashboard layouts
- Review user access logs

### Monthly Tasks
- Archive old import data
- Update analytics views
- Performance optimization review