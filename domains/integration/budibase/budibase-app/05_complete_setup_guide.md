# SoleFlipper Budibase Integration - Complete Setup Guide

*Complete Business Intelligence Dashboard with Direct PostgreSQL Access*

## 🎯 Overview

This guide provides a complete setup for integrating Budibase with SoleFlipper using **direct PostgreSQL access** for optimal performance. Instead of API calls, we connect directly to the database for lightning-fast queries and real-time analytics.

## 🏗️ Architecture Benefits

### **Direct Database Access Advantages:**
- ✅ **10x Faster Performance** - No API latency
- ✅ **Real-time Data** - No caching delays
- ✅ **SQL Power** - Complex joins, aggregations, analytics
- ✅ **Lower Resource Usage** - No API server overhead
- ✅ **Better Reliability** - Fewer failure points

### **Container Network Architecture:**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│    Budibase     │◄──►│   PostgreSQL    │◄──►│   SoleFlipper   │
│   (Port 10000)  │    │   (Port 5432)   │    │   (Port 8000)   │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │                 │
                    │     Redis       │
                    │   (Port 6379)   │
                    │                 │
                    └─────────────────┘
```

## 📋 Prerequisites

### **1. Verify SoleFlipper is Running**
```bash
# Check if SoleFlipper API is accessible
curl http://localhost:8000/health

# Verify database connectivity
curl http://localhost:8000/api/v1/inventory/items?limit=1
```

### **2. Docker Environment Check**
```bash
# Verify Docker network exists
docker network ls | grep soleflip

# If not exists, create it:
docker network create soleflip_network
```

### **3. Database Access Verification**
```bash
# Test PostgreSQL connection (adjust credentials as needed)
docker exec -it postgres_container_name psql -U soleflip_user -d soleflip -c "SELECT COUNT(*) FROM inventory.items;"
```

## 🚀 Installation Steps

### **Step 1: Prepare Environment**

Create a `.env` file in your project root:
```bash
# PostgreSQL Configuration
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_USER=soleflip_user
POSTGRES_DB=soleflip

# Budibase Security Keys
JWT_SECRET=your-jwt-secret-minimum-32-characters-long
INTERNAL_API_KEY=your-internal-api-key-here
ENCRYPTION_KEY=your-encryption-key-32-characters

# Optional: File Storage
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Optional: Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### **Step 2: Deploy Business Intelligence Views**

Execute the SQL views to create optimized dashboard queries:

```bash
# Copy the BI views to your database
cd domains/integration/budibase/budibase-app

# Apply the business intelligence views
docker exec -i postgres_container_name psql -U soleflip_user -d soleflip < 02_business_intelligence_views.sql
```

### **Step 3: Launch Budibase**

```bash
# Start Budibase with direct database access
docker-compose -f domains/integration/budibase/budibase-app/04_docker_budibase_setup.yml up -d

# Monitor startup logs
docker-compose -f domains/integration/budibase/budibase-app/04_docker_budibase_setup.yml logs -f budibase
```

### **Step 4: Access Budibase**

1. **Open Budibase**: http://localhost:10000
2. **Create Admin Account** (first-time setup)
3. **Create New App**: "SoleFlipper Business Intelligence"

## 🔧 Data Source Configuration

### **1. Add PostgreSQL Data Source**

In Budibase → Data → Add Data Source:

```
Name: SoleFlipper Database
Type: PostgreSQL
Host: postgres
Port: 5432
Database: soleflip
Username: soleflip_user
Password: [from your .env file]
Schema: public
SSL: Disabled (for local development)
```

### **2. Test Connection**

Click "Test Connection" - should show green checkmark.

### **3. Import Queries**

Use the pre-built queries from `01_database_queries.sql`:

#### **Essential Queries to Add:**

1. **inventory_overview** - Dashboard KPIs
2. **inventory_items_filtered** - Main inventory table with filters
3. **brand_analytics** - Brand performance metrics
4. **size_distribution** - Size analysis
5. **financial_trends** - Daily investment trends
6. **dead_stock_analysis** - Items older than 90 days
7. **supplier_performance** - Supplier analytics
8. **get_brands**, **get_sizes**, **get_statuses** - Filter dropdowns

## 📊 Dashboard Creation

### **Dashboard 1: Executive Overview**

**Components:**
- **KPI Cards**: Total Items, Listed Items, Total Value, Unique Brands
- **Brand Chart**: Top 10 brands by value (bar chart)
- **Size Distribution**: Size popularity (pie chart)
- **Recent Trends**: 30-day investment trend (line chart)

**Key Metrics:**
```sql
-- Total inventory value
SELECT SUM(purchase_price * quantity) as total_value
FROM inventory.items WHERE status = 'listed'

-- Items added this week
SELECT COUNT(*) FROM inventory.items
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
```

### **Dashboard 2: Inventory Management**

**Features:**
- **Search Bar**: Product/brand name search
- **Filter Dropdowns**: Brand, Status, Size
- **Data Table**: Sortable, paginated inventory list
- **Export Function**: CSV/Excel export

**Advanced Filters:**
- Price range sliders
- Date range pickers
- Stock age categories
- Supplier filters

### **Dashboard 3: Business Analytics**

**Analytics Views:**
- **Brand Performance**: Revenue, margins, turnover rates
- **Size Analytics**: Demand patterns, price variations
- **Supplier Analysis**: Performance, reliability, diversity
- **Financial Trends**: Daily/weekly/monthly patterns

### **Dashboard 4: Alerts & Monitoring**

**Alert Categories:**
- **Dead Stock**: Items > 90 days old
- **High Value at Risk**: Premium items sitting too long
- **Low Stock**: Items with quantity = 1
- **New Inventory**: Recent additions requiring attention

## 🔍 Advanced Features

### **1. Real-time Dashboards**

Enable auto-refresh for real-time monitoring:
```javascript
// Auto-refresh every 30 seconds
setInterval(() => {
  budibase.refreshData('inventory_overview');
}, 30000);
```

### **2. Custom Business Logic**

Create calculated fields for advanced analytics:
```sql
-- Profit margin calculation (when you have sales data)
SELECT
  product_name,
  purchase_price,
  avg_sell_price,
  (avg_sell_price - purchase_price) / purchase_price * 100 as profit_margin_percent
FROM inventory_with_sales_data;
```

### **3. Automated Reports**

Set up daily/weekly automated reports:
- Email summaries
- Slack notifications
- Export generation

### **4. Role-based Access**

Configure user roles:
- **Admin**: Full access, can modify data
- **Manager**: View all data, limited modifications
- **Viewer**: Read-only dashboard access

## 📈 Performance Optimization

### **1. Database Indexes**

Create indexes for better query performance:
```sql
-- Essential indexes for Budibase queries
CREATE INDEX IF NOT EXISTS idx_inventory_brand_status
ON inventory.items(brand_name, status);

CREATE INDEX IF NOT EXISTS idx_inventory_created_at
ON inventory.items(created_at);

CREATE INDEX IF NOT EXISTS idx_inventory_price_range
ON inventory.items(purchase_price);
```

### **2. Query Optimization**

Use the pre-built views for complex analytics:
```sql
-- Instead of complex joins, use optimized views
SELECT * FROM budibase_brand_performance
WHERE total_items > 10;

-- Use parameterized queries for filters
SELECT * FROM budibase_inventory_analytics
WHERE brand_name = $1 AND status = $2;
```

### **3. Caching Strategy**

- Use Budibase built-in caching for static data
- Refresh critical data every 5-10 minutes
- Cache filter options (brands, sizes, statuses)

## 🔒 Security Configuration

### **1. Database Security**

- Create dedicated Budibase database user
- Grant only necessary permissions
- Use connection pooling

```sql
-- Create dedicated Budibase user
CREATE USER budibase_readonly WITH PASSWORD 'secure_password';

-- Grant read-only access to necessary schemas
GRANT CONNECT ON DATABASE soleflip TO budibase_readonly;
GRANT USAGE ON SCHEMA inventory TO budibase_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA inventory TO budibase_readonly;
```

### **2. Network Security**

- Use internal Docker networks
- Disable external database access
- Configure firewall rules

### **3. Application Security**

- Enable Budibase authentication
- Configure HTTPS with SSL certificates
- Set up backup strategies

## 🚨 Troubleshooting

### **Common Issues:**

1. **Connection Failed**
   ```bash
   # Check network connectivity
   docker exec budibase_container ping postgres

   # Verify database credentials
   docker exec postgres_container psql -U soleflip_user -d soleflip -c "\l"
   ```

2. **Queries Failing**
   ```sql
   -- Test basic connectivity
   SELECT 1 as test;

   -- Check table permissions
   SELECT * FROM inventory.items LIMIT 1;
   ```

3. **Performance Issues**
   ```sql
   -- Check query execution plans
   EXPLAIN ANALYZE SELECT * FROM budibase_inventory_analytics LIMIT 100;

   -- Monitor active connections
   SELECT * FROM pg_stat_activity WHERE datname = 'soleflip';
   ```

## 📊 Sample Dashboard Queries

### **Executive KPIs**
```sql
SELECT
  (SELECT COUNT(*) FROM inventory.items) as total_items,
  (SELECT COUNT(*) FROM inventory.items WHERE status = 'listed') as active_items,
  (SELECT ROUND(SUM(purchase_price * quantity)) FROM inventory.items WHERE status = 'listed') as total_value,
  (SELECT COUNT(DISTINCT brand_name) FROM inventory.items) as total_brands;
```

### **Top Performing Brands**
```sql
SELECT
  brand_name,
  COUNT(*) as item_count,
  ROUND(SUM(purchase_price * quantity)) as total_value,
  ROUND(AVG(purchase_price)) as avg_price
FROM inventory.items
WHERE status = 'listed'
GROUP BY brand_name
ORDER BY total_value DESC
LIMIT 10;
```

### **Inventory Health Check**
```sql
SELECT
  'Dead Stock (90+ days)' as metric,
  COUNT(*) as count
FROM inventory.items
WHERE status = 'listed'
  AND created_at < NOW() - INTERVAL '90 days'
UNION ALL
SELECT
  'High Value Items ($500+)' as metric,
  COUNT(*) as count
FROM inventory.items
WHERE status = 'listed'
  AND purchase_price > 500;
```

## 🎯 Next Steps

### **Phase 1: Basic Setup** ✅
- [x] Database connection established
- [x] Core queries implemented
- [x] Basic dashboards created

### **Phase 2: Advanced Analytics**
- [ ] Profit margin tracking (requires sales data)
- [ ] Predictive analytics
- [ ] Market trend analysis
- [ ] Automated reordering suggestions

### **Phase 3: Integration Expansion**
- [ ] Mobile app integration
- [ ] API webhooks for real-time updates
- [ ] Third-party integrations (QuickBooks, etc.)
- [ ] Advanced reporting automation

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review Budibase documentation
3. Verify database connectivity
4. Check container logs

## 🔄 Maintenance

### **Regular Tasks:**
- **Weekly**: Review dashboard performance
- **Monthly**: Update database statistics
- **Quarterly**: Review and optimize queries

### **Backup Strategy:**
- Daily database backups
- Weekly full system backups
- Monthly disaster recovery tests

---

**🎉 You now have a complete Business Intelligence solution with direct database access for optimal performance!**

Access your new dashboards at: **http://localhost:10000**

*Total setup time: ~30 minutes*
*Expected performance: Sub-second query responses for 10,000+ inventory items*