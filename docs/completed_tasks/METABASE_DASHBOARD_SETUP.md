# Metabase Business Intelligence Dashboard Setup Guide

## 📊 Overview
Comprehensive guide for setting up professional business intelligence dashboards in Metabase for your SoleFlipper system with advanced brand normalization and supplier intelligence.

**🎯 Current Status: 8 Production-Ready Analytics Views Available**

## 🗃️ Available Analytics Views (Production-Ready)

### 🏷️ **Brand Intelligence**
- **`analytics.brand_performance`** - Complete brand analytics with market share (40 rows)
- **`analytics.product_performance`** - Individual product tracking with brand relationships (676 rows)
- **`analytics.category_analysis`** - Category distribution and performance (1 row)

### 👥 **Supplier Intelligence**  
- **`analytics.supplier_performance`** - Comprehensive supplier metrics with ratings (3 rows)
- **`analytics.legacy_supplier_analysis`** - Migration tracking (0 rows - fully migrated)

### 💰 **Financial Intelligence**
- **`analytics.financial_overview`** - Portfolio value and KPIs (1 summary row)
- **`analytics.monthly_trends`** - Purchase and activity trends (0 rows - historical data)

### 📊 **Inventory Intelligence**
- **`analytics.size_distribution`** - Size variant analytics (88 rows)

## 🚀 Dashboard Setup in Metabase

### 1. Database Connection
```
Host: 192.168.2.45
Port: 2665
Database: soleflip  
Username: metabaseuser
Password: metabasepass
Schema: analytics (for all business intelligence views)
```

### 2. Recommended Dashboard Structure

#### 📊 **Executive Business Intelligence Dashboard**

**KPI Cards from `analytics.financial_overview`:**
- Total Portfolio Items: `{{total_items}}`
- Available Inventory Value: `€{{available_inventory_value}}`
- Average Item Price: `€{{avg_item_price}}`
- Price Range: `€{{min_price}} - €{{max_price}}`

**Charts:**
- **Pie Chart**: `analytics.brand_performance`
  - Segment: `brand_name`
  - Metric: `market_share_percent`
  - Title: "Brand Market Share"
  - Filter: `total_items > 0`

- **Bar Chart**: `analytics.brand_performance`
  - X-Axis: `brand_name`
  - Y-Axis: `total_items`
  - Title: "Inventory by Brand"
  - Sort: Descending by total_items
  - Limit: Top 15

#### 🏷️ **Brand Performance Dashboard**

**Brand Intelligence Widgets:**
- **Table**: `analytics.brand_performance` (Top 20 brands)
  - Columns: `brand_name`, `total_items`, `market_share_percent`, `avg_purchase_price`
  - Title: "Brand Performance Overview"
  - Sort: By `total_items` DESC

- **Combo Chart**: `analytics.brand_performance`
  - X-Axis: `brand_name`
  - Left Y-Axis: `total_items` (bars)
  - Right Y-Axis: `market_share_percent` (line)
  - Title: "Brand Volume vs Market Share"

- **Scatter Plot**: `analytics.brand_performance`
  - X-Axis: `total_items`
  - Y-Axis: `avg_purchase_price`  
  - Size: `market_share_percent`
  - Title: "Brand Volume vs Price Analysis"

#### 👥 **Supplier Intelligence Dashboard**

**Supplier Performance Widgets:**
- **KPI Cards**: `analytics.supplier_performance`
  - Average Rating: `AVG(rating)`
  - Preferred Suppliers: `COUNT(CASE WHEN preferred = true THEN 1 END)`
  - Countries: `COUNT(DISTINCT country)`

- **Table**: `analytics.supplier_performance`
  - Columns: `supplier_name`, `country`, `rating`, `return_policy_days`, `preferred`, `brand_relationships`
  - Title: "Supplier Performance Overview"
  - Sort: By `rating` DESC

- **Geographic Map**: `analytics.supplier_performance`
  - Region: `country`
  - Metric: `rating`
  - Title: "Global Supplier Performance"

- **Bar Chart**: `analytics.supplier_performance`
  - X-Axis: `supplier_name`
  - Y-Axis: `brand_relationships`
  - Color: `rating`
  - Title: "Supplier-Brand Relationships"

#### 🎯 **Product Performance Dashboard**

**Product Intelligence Widgets:**
- **Table**: `analytics.product_performance` (Top 30)
  - Columns: `product_name`, `brand_name`, `total_inventory`, `avg_purchase_price`
  - Title: "Top Products by Inventory"
  - Sort: By `total_inventory` DESC

- **Brand Distribution**: `analytics.product_performance`
  - Group by: `brand_name`
  - Metric: `COUNT(*)`
  - Chart Type: Donut
  - Title: "Product Distribution by Brand"

- **Price Analysis**: `analytics.product_performance`
  - X-Axis: `brand_name`
  - Y-Axis: `avg_purchase_price`
  - Chart Type: Box plot
  - Title: "Price Distribution by Brand"

#### 📦 **Inventory Intelligence Dashboard**

**Size & Category Analysis:**
- **Pie Chart**: `analytics.size_distribution`
  - Segment: `category_name`
  - Metric: `item_count`
  - Title: "Inventory by Category"

- **Bar Chart**: `analytics.size_distribution` (Top 20 sizes)
  - X-Axis: `size_value`
  - Y-Axis: `item_count`
  - Color: `category_name`
  - Title: "Most Popular Sizes"
  - Sort: By `item_count` DESC

- **Table**: `analytics.size_distribution`
  - Columns: `size_value`, `category_name`, `item_count`, `size_share_percent`, `avg_price`
  - Title: "Complete Size Distribution"
  - Sort: By `item_count` DESC

#### 📈 **Trend Analysis Dashboard**

**Historical Performance:**
- **Time Series**: `analytics.monthly_trends`
  - X-Axis: `month`
  - Y-Axis: `total_spent`
  - Title: "Monthly Purchase Trends"
  - Note: Currently no data - will populate with future purchases

- **KPI Tracking**: Custom metrics for monitoring:
  - New brands added this month
  - New suppliers onboarded
  - Data quality improvements

## 📊 Critical Business KPIs to Track

### 🏷️ **Brand Intelligence KPIs**
- **Market Share Leaders**: Top 5 brands by percentage
- **Brand Concentration**: % of inventory in top 3 brands
- **Brand Diversity**: Number of active brands
- **Average Brand Price**: Price positioning analysis

### 👥 **Supplier Intelligence KPIs**
- **Supplier Quality Score**: Average rating across suppliers
- **Geographic Diversification**: Number of countries
- **Return Policy Distribution**: Average return days
- **Preferred Supplier Ratio**: % of preferred suppliers

### 💰 **Financial Intelligence KPIs**
- **Total Portfolio Value**: Current inventory worth
- **Price Distribution**: Min/Max/Average pricing
- **Value Concentration**: % of value in top categories
- **Investment Efficiency**: Value per item ratio

### 📦 **Inventory Intelligence KPIs**
- **Size Distribution**: Most/least popular sizes
- **Category Performance**: Footwear vs other categories
- **Stock Concentration**: Items per product
- **SKU Efficiency**: Products with proper SKUs

## 🔄 Advanced Dashboard Features

### **Automated Refreshing:**
- All analytics views refresh automatically (no manual refresh needed)
- Real-time data updates as inventory changes
- No caching issues - views are always current

### **Recommended Filters:**
- **Brand Filter**: Nike, Adidas, LEGO, etc.
- **Supplier Filter**: Preferred vs Standard suppliers
- **Category Filter**: Footwear, Apparel, etc.
- **Price Range Filter**: Custom price brackets
- **Market Share Filter**: Major brands (>5% share) vs niche brands

### **Interactive Features:**
- **Drill-down**: Brand → Products → Sizes
- **Cross-filtering**: Select brand to filter all widgets
- **Parameter Controls**: Dynamic date ranges, price limits

## 🎨 Professional Dashboard Design

### **Layout Best Practices:**
1. **Executive Summary**: KPI cards at top
2. **Primary Charts**: Key visualizations in prominent positions
3. **Detail Tables**: Supporting data at bottom
4. **Consistent Spacing**: Maintain visual hierarchy
5. **Mobile Responsiveness**: Ensure mobile compatibility

### **Color Scheme for Business Intelligence:**
- **Primary Blue**: `#2196F3` - Main brand colors, key metrics
- **Success Green**: `#4CAF50` - Positive performance, preferred suppliers
- **Warning Orange**: `#FF9800` - Attention needed, medium performance
- **Info Gray**: `#9E9E9E` - Secondary information, labels
- **Background**: `#FAFAFA` - Clean, professional background

### **Chart Type Recommendations:**
- **KPI Cards**: Financial overview, key numbers
- **Pie/Donut Charts**: Market share, category distribution
- **Bar Charts**: Comparisons, rankings
- **Tables**: Detailed data, top performers
- **Scatter Plots**: Correlation analysis (price vs volume)
- **Maps**: Geographic supplier distribution

## 🔧 Dashboard Maintenance & Optimization

### **Weekly Tasks:**
- [ ] Verify all analytics views are functioning
- [ ] Check for new brands requiring dashboard updates
- [ ] Monitor dashboard performance and loading times
- [ ] Review user engagement with different widgets

### **Monthly Reviews:**
- [ ] Analyze which KPIs are most valuable to users
- [ ] Update dashboard layouts based on business needs
- [ ] Add new visualizations for emerging patterns
- [ ] Optimize queries for better performance

### **Data Quality Monitoring:**
- [ ] Verify brand assignments are accurate
- [ ] Check supplier data completeness
- [ ] Monitor for duplicate or inconsistent data
- [ ] Validate financial calculations

## 📊 Advanced Analytics Queries

### **Custom Brand Analysis:**
```sql
-- Brand market dominance (>5% market share)
SELECT brand_name, total_items, market_share_percent
FROM analytics.brand_performance 
WHERE market_share_percent > 5.0
ORDER BY market_share_percent DESC;
```

### **Supplier Performance Analysis:**
```sql
-- High-performing suppliers with multiple brand relationships
SELECT supplier_name, rating, brand_relationships, return_policy_days
FROM analytics.supplier_performance 
WHERE rating >= 4.5 AND brand_relationships > 0
ORDER BY rating DESC, brand_relationships DESC;
```

### **Portfolio Value Analysis:**
```sql
-- Financial overview with key ratios
SELECT 
  total_items,
  available_inventory_value,
  avg_item_price,
  CASE 
    WHEN avg_item_price > 100 THEN 'Premium'
    WHEN avg_item_price > 50 THEN 'Mid-Range'
    ELSE 'Budget'
  END as price_category
FROM analytics.financial_overview;
```

## 🚨 Alerts & Notifications

### **Recommended Alert Setup:**
1. **Daily Business Summary** (8:00 AM)
   - Portfolio value changes
   - New inventory additions
   - Top performing brands

2. **Weekly Performance Report** (Monday 9:00 AM)
   - Brand performance trends
   - Supplier performance updates
   - Category distribution changes

3. **Monthly Executive Dashboard** (1st of month)
   - Complete business intelligence summary
   - Year-over-year comparisons
   - Strategic recommendations

## 📞 Support & Troubleshooting

### **Common Issues:**
- **Slow Loading**: Check view performance, add appropriate filters
- **No Data**: Verify database connection and view permissions
- **Incorrect Numbers**: Validate against source data in database
- **Missing Brands**: Check brand normalization process

### **Performance Optimization:**
- Use filters to limit data ranges
- Avoid complex calculations in multiple widgets
- Cache frequently accessed dashboards
- Monitor database query performance

### **Getting Help:**
- Check Metabase documentation for widget configuration
- Use the analytics views as primary data sources
- Test new widgets in development dashboard first
- Validate business logic with stakeholders

---

## 🎯 Success Metrics

**Your dashboards are successful when they:**
- ✅ Load quickly (<3 seconds)
- ✅ Provide actionable business insights
- ✅ Are used daily by stakeholders
- ✅ Lead to data-driven decisions
- ✅ Reduce time spent on manual reporting

**🚀 Ready to build professional business intelligence dashboards with your comprehensive SoleFlipper analytics infrastructure!**

---

*Built for sneaker reselling professionals who demand comprehensive business intelligence and data-driven decision making.*