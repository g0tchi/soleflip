# Metabase Dashboard Setup Guide

## Overview
This guide helps you create two comprehensive dashboards in Metabase for the SoleFlipper pricing and forecasting system:
1. **Pricing KPIs Dashboard** - Monitor pricing strategy performance and market positioning
2. **Sales Forecast Dashboard** - Track forecast accuracy and future sales predictions

## Prerequisites
- Metabase instance connected to your PostgreSQL database
- Database user with read access to `pricing` and `analytics` schemas
- Completed database migrations for pricing and analytics schemas

## Database Connection Setup

### 1. Create Metabase Database User
```sql
-- Connect as superuser
CREATE USER metabase_reader WITH PASSWORD 'your_secure_password';
GRANT CONNECT ON DATABASE soleflip TO metabase_reader;
GRANT USAGE ON SCHEMA public, pricing, analytics TO metabase_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public, pricing, analytics TO metabase_reader;

-- Grant future table access
ALTER DEFAULT PRIVILEGES IN SCHEMA public, pricing, analytics 
GRANT SELECT ON TABLES TO metabase_reader;
```

### 2. Add Database Connection in Metabase
1. Go to **Admin** → **Databases** → **Add Database**
2. Choose **PostgreSQL**
3. Configure connection:
   - **Name**: SoleFlipper Production
   - **Host**: your-db-host
   - **Port**: 5432
   - **Database name**: soleflip
   - **Username**: metabase_reader
   - **Password**: your_secure_password

## Dashboard 1: Pricing KPIs

### Creating the Dashboard
1. Go to **Dashboards** → **Create Dashboard**
2. Name: "Pricing KPIs"
3. Description: "Monitor pricing strategy performance, margins, and market positioning"

### Cards to Add

#### 1. Average Margin by Brand (Bar Chart)
- **Question Type**: Native Query
- **SQL**: Copy from `docs/metabase_pricing_kpis_dashboard.sql` (Query #1)
- **Visualization**: Bar Chart
- **X-axis**: brand
- **Y-axis**: avg_margin_pct

#### 2. Price Trends Over Time (Line Chart)
- **SQL**: Query #2 from pricing KPIs file
- **Visualization**: Line Chart
- **X-axis**: date
- **Y-axis**: avg_price
- **Series**: brand

#### 3. Pricing Strategy Performance (Pie Chart)
- **SQL**: Query #3 from pricing KPIs file
- **Visualization**: Pie Chart
- **Dimension**: strategy_used
- **Metric**: usage_count

#### 4. Top Performing Products (Table)
- **SQL**: Query #4 from pricing KPIs file
- **Visualization**: Table
- **Show**: All columns

#### 5. Market Price Comparison (Scatter Plot)
- **SQL**: Query #5 from pricing KPIs file
- **Visualization**: Scatter Plot
- **X-axis**: our_price
- **Y-axis**: competitor_price
- **Size**: price_difference_pct

#### 6. KPI Summary Cards (Single Values)
Create 4 separate cards using Queries #8 from the pricing KPIs file:
- Products Priced Today
- Average Margin Today  
- Price Changes This Week
- Active Pricing Rules

### Dashboard Layout
Arrange cards in this order:
```
[KPI Cards Row]        [Products Priced] [Avg Margin] [Price Changes] [Active Rules]
[Charts Row 1]         [Price Trends Over Time - Full Width]
[Charts Row 2]         [Average Margin by Brand] [Strategy Performance]
[Analysis Row]         [Market Price Comparison] [Top Products Table]
```

## Dashboard 2: Sales Forecast

### Creating the Dashboard
1. Go to **Dashboards** → **Create Dashboard**  
2. Name: "Sales Forecast"
3. Description: "Sales forecasting metrics, model performance, and demand analysis"

### Cards to Add

#### 1. 30-Day Sales Forecast by Brand (Line Chart)
- **SQL**: Query #1 from sales forecast file
- **Visualization**: Line Chart
- **X-axis**: forecast_date
- **Y-axis**: forecasted_revenue
- **Series**: brand

#### 2. Weekly Forecast Accuracy Trend (Line Chart)  
- **SQL**: Query #2 from sales forecast file
- **Visualization**: Line Chart
- **X-axis**: week
- **Y-axis**: avg_accuracy

#### 3. Model Performance Comparison (Bar Chart)
- **SQL**: Query #3 from sales forecast file
- **Visualization**: Bar Chart
- **X-axis**: model_used
- **Y-axis**: avg_accuracy

#### 4. Weekly Revenue Trend Forecast (Area Chart)
- **SQL**: Query #8 from sales forecast file
- **Visualization**: Area Chart
- **X-axis**: week  
- **Y-axis**: forecasted_revenue/actual_revenue
- **Series**: data_type

#### 5. Forecast Summary Cards (Single Values)
Create 4 cards using Query #10:
- Total Forecasted Revenue (30d)
- Average Forecast Confidence
- Active Models  
- Last Update Time

#### 6. Top Products by Forecasted Revenue (Table)
- **SQL**: Query #4 from sales forecast file
- **Visualization**: Table

### Dashboard Layout
```
[KPI Cards Row]        [Total Revenue] [Avg Confidence] [Active Models] [Last Update]
[Forecast Row]         [30-Day Sales Forecast by Brand - Full Width]
[Analysis Row 1]       [Weekly Accuracy Trend] [Model Performance]  
[Analysis Row 2]       [Weekly Revenue Trend - Full Width]
[Detail Row]           [Top Products Table - Full Width]
```

## Dashboard Filters

### Pricing KPIs Dashboard Filters
Add these dashboard-level filters:
1. **Date Range** - Apply to all time-based queries
2. **Brand** - Filter by specific brands
3. **Strategy** - Filter by pricing strategy

### Sales Forecast Dashboard Filters  
1. **Forecast Date Range** - Filter forecast period
2. **Brand** - Filter by specific brands
3. **Model** - Filter by forecasting model
4. **Channel** - Filter by sales channel

## Refresh Schedule
Set up automatic refresh for real-time data:
1. Go to dashboard settings
2. Set **Auto-refresh**: Every 1 hour for pricing, every 4 hours for forecasts
3. Configure **Cache TTL**: 1 hour

## Permissions
Create dashboard permissions:
1. **Pricing Team**: Full access to both dashboards
2. **Management**: View-only access to both dashboards  
3. **Analytics Team**: Full access + can edit queries

## Alerts
Set up alerts for key metrics:

### Pricing Alerts
- Average margin drops below 15%
- Price changes exceed 100 per day
- Pricing rule failures exceed 10%

### Forecast Alerts  
- Forecast accuracy drops below 70%
- No forecasts generated in 24 hours
- Model confidence drops below 60%

## Troubleshooting

### Common Issues
1. **"Permission Denied" Errors**
   - Verify metabase_reader has schema access
   - Check table-level permissions

2. **Empty Results**
   - Confirm data exists in pricing/analytics schemas
   - Run migrations if tables are missing

3. **Performance Issues**
   - Add indexes to commonly queried columns
   - Consider materialized views for complex aggregations

### Optimization Tips
- Use date filters to limit data ranges
- Create summary tables for heavy aggregations
- Monitor query performance in Metabase admin

## Maintenance
- Weekly: Review dashboard performance
- Monthly: Update filters and refresh schedules
- Quarterly: Review and optimize slow queries