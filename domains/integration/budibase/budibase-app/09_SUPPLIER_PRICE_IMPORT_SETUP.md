# Supplier Price Import - Budibase Setup Guide

**Version:** v2.2.4
**Date:** 2025-10-03
**Status:** Ready to Deploy

---

## 📋 Overview

This guide shows you how to add **Supplier Price Import** functionality to your Budibase dashboard with a beautiful drag-and-drop interface for uploading CSV price lists and analyzing QuickFlip opportunities.

**What you get:**
- ✅ **File Upload Screen** - Drag-and-drop CSV import
- ✅ **Import History** - Track all supplier imports
- ✅ **QuickFlip Opportunities** - Analyze profitable products
- ✅ **Real-time Filtering** - By source, margin, profit
- ✅ **Export Capabilities** - Export opportunities to CSV

---

## 🚀 Quick Setup (15 minutes)

### **Step 1: Copy Screen Configurations**

The following JSON files contain the complete screen configurations:

1. **`07_price_import_screen.json`** - Upload interface
2. **`08_quickflip_opportunities_screen.json`** - Analysis dashboard

### **Step 2: Import into Budibase**

#### **Option A: Manual Import (Recommended)**

1. **Access Budibase**
   ```bash
   # Navigate to Budibase directory
   cd domains/integration/budibase/budibase-app

   # Start Budibase (if not running)
   docker-compose -f 04_docker_budibase_setup.yml up -d

   # Open in browser
   http://localhost:10000
   ```

2. **Create API Data Source**
   - Go to **Data** → **Add Data Source**
   - Select **REST API**
   - Name: `SoleFlipper API`
   - Base URL: `http://host.docker.internal:8000` (or your API URL)
   - Save

3. **Import Price Import Screen**
   - Go to **Design** → **Screens**
   - Click **Create New Screen**
   - Select **Blank Screen**
   - Name: `Supplier Price Import`
   - Route: `/price-import`
   - Copy components from `07_price_import_screen.json` → `screen.components`
   - Paste into the screen builder

4. **Import QuickFlip Screen**
   - Create another screen
   - Name: `QuickFlip Opportunities`
   - Route: `/quickflip-opportunities`
   - Copy components from `08_quickflip_opportunities_screen.json` → `screen.components`
   - Paste into the screen builder

5. **Add Queries**
   - Go to **Data** → **Queries**
   - For each query in the JSON files:
     - Click **Create New Query**
     - Select data source (Postgres or API)
     - Copy SQL/config from JSON
     - Save

#### **Option B: Automated Import (Advanced)**

Use Budibase CLI to import screens:

```bash
# Install Budibase CLI
npm install -g @budibase/cli

# Login to your instance
budi login http://localhost:10000

# Import screens (if supported by your Budibase version)
budi import screens 07_price_import_screen.json
budi import screens 08_quickflip_opportunities_screen.json
```

---

## 📊 Features Breakdown

### **Screen 1: Supplier Price Import** (`/price-import`)

**Components:**
1. **Upload Form**
   - Supplier name input (lowercase validation)
   - CSV file upload (max 100MB)
   - Import mode selector (create/update/upsert)

2. **CSV Format Guide**
   - Required columns display
   - Example CSV preview
   - Validation hints

3. **Import History Table**
   - All sources with statistics
   - Last updated timestamps
   - Quick actions (View Opportunities, Delete)

**Queries Used:**
- `query_import_statistics` - Summary stats
- `query_recent_imports` - Import history
- `api_import_market_prices` - Upload endpoint
- `api_delete_source_prices` - Delete source

---

### **Screen 2: QuickFlip Opportunities** (`/quickflip-opportunities`)

**Components:**
1. **KPI Cards**
   - Total opportunities
   - Average margin %
   - Total potential profit
   - Best margin product

2. **Advanced Filters**
   - Supplier source dropdown
   - Minimum margin % slider
   - Minimum profit € input
   - Product search box

3. **Opportunities Table**
   - Product name, brand, SKU
   - Buy price vs. Market price
   - Profit calculation
   - Margin percentage (color-coded badges)
   - Stock availability
   - Quick actions (View details, Open supplier link)

4. **Product Details Modal**
   - Complete product information
   - Pricing analysis breakdown
   - ROI calculation
   - Direct supplier link

**Queries Used:**
- `query_quickflip_kpis` - Dashboard KPIs
- `query_quickflip_opportunities` - Profitable products
- `query_available_sources` - Source dropdown

---

## 🔧 Database Requirements

The screens expect the following database structure:

### **Table: `finance.source_prices`**
```sql
CREATE TABLE finance.source_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products.products(id),
    source VARCHAR(100),           -- Supplier identifier
    external_id VARCHAR(255),      -- Supplier product ID
    supplier_name VARCHAR(255),    -- Supplier display name
    buy_price DECIMAL(10,2),       -- Purchase price
    currency VARCHAR(3) DEFAULT 'EUR',
    availability VARCHAR(50),      -- in_stock, out_of_stock, etc.
    stock_qty INTEGER,             -- Available quantity
    product_url TEXT,              -- Supplier product page
    raw_data JSONB,                -- Complete CSV row
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_source_prices_source ON finance.source_prices(source);
CREATE INDEX idx_source_prices_product_id ON finance.source_prices(product_id);
```

### **Required Joins:**
- `products.products` - Product catalog
- `core.brands` - Brand information

---

## 🎯 Usage Workflow

### **1. Upload Supplier Price List**

**Navigate to:** `/price-import`

**Steps:**
1. Enter supplier name (e.g., `supplier_xyz`)
2. Upload CSV file with format:
   ```csv
   id,title,brand,price,gtin,availability,stock_qty,link,program_name
   12345,Nike Air Max 90,Nike,89.99,0883419123456,in_stock,25,https://...,Supplier XYZ
   ```
3. Select import mode (default: Create & Update)
4. Click **Import Prices**
5. Wait for success notification
6. View in Import History table

### **2. Analyze Opportunities**

**Navigate to:** `/quickflip-opportunities`

**Steps:**
1. Select supplier source from dropdown
2. Set minimum margin % (e.g., 15%)
3. Set minimum profit € (e.g., 10€)
4. Optional: Search for specific products
5. Click **Apply Filters**
6. Review opportunities table
7. Click **View** for detailed analysis
8. Click **Supplier** to open product page

### **3. Export Opportunities**

1. Filter opportunities as desired
2. Click **Export** button on table
3. Select format (CSV or JSON)
4. Download for external analysis

---

## 🎨 Customization

### **Change Margin Thresholds**

Edit `08_quickflip_opportunities_screen.json`:

```json
{
  "type": "numberfield",
  "id": "field_min_margin",
  "defaultValue": 15,  // Change default minimum margin
  "min": 0,
  "max": 1000
}
```

### **Adjust Color Coding**

Modify badge colors in table columns:

```json
{
  "name": "margin_percent",
  "badgeColor": "{{ value >= 50 ? 'green' : value >= 30 ? 'blue' : 'orange' }}"
}
```

**Color Thresholds:**
- Green: ≥ 50% margin
- Blue: 30-49% margin
- Orange: 15-29% margin

### **Add Custom Columns**

In QuickFlip table, add new columns:

```json
{
  "name": "roi",
  "label": "ROI %",
  "width": "10%",
  "displayName": "{{ (row.profit / row.buy_price * 100).toFixed(2) }}%"
}
```

---

## 🔐 Security & Permissions

### **Role Access**

**Admin Role:**
- Full access to Price Import screen
- Can upload, delete, and manage imports

**Manager Role:**
- Read-only access to QuickFlip Opportunities
- Can view and export data

**Viewer Role:**
- Read-only access to QuickFlip Opportunities
- Cannot export

### **Configure in Budibase:**

```json
{
  "roleId": "role_admin",  // Change to restrict access
  "permissions": ["read", "write", "admin"]
}
```

---

## 🧪 Testing

### **Test Import**

1. Create test CSV:
   ```csv
   id,title,brand,price
   TEST001,Nike Test Shoe,Nike,50.00
   TEST002,Adidas Test Shoe,Adidas,75.00
   ```

2. Upload via Price Import screen
3. Check Import History shows 2 products
4. Navigate to QuickFlip Opportunities
5. Verify test products appear with calculated margins

### **Test Filters**

1. Set min margin to 20%
2. Verify only products with ≥20% margin show
3. Search for "Nike"
4. Verify only Nike products show
5. Reset filters
6. Verify all products return

---

## 📊 Performance Tips

### **Large Imports (>10,000 products)**

1. **Batch Processing**
   - Split CSV into smaller files (5,000 rows each)
   - Upload sequentially

2. **Database Optimization**
   - Ensure indexes are created (see Database Requirements)
   - Run `VACUUM ANALYZE finance.source_prices;` after large imports

3. **Query Optimization**
   - Limit QuickFlip results to top 100 (already set)
   - Use source filter to reduce dataset

### **Budibase Performance**

1. **Enable Caching**
   - In Budibase settings: Enable query caching
   - Set cache TTL to 5 minutes

2. **Pagination**
   - Tables use 25 rows/page by default
   - Reduce if experiencing slow loads

---

## 🐛 Troubleshooting

### **Upload Not Working**

**Problem:** File upload fails or hangs

**Solutions:**
1. Check file size < 100MB
2. Verify CSV format is correct
3. Check API is running: `curl http://localhost:8000/health`
4. Check Budibase can reach API:
   - Use `host.docker.internal:8000` (Docker Desktop)
   - Use container name if in same network

### **No Opportunities Showing**

**Problem:** QuickFlip Opportunities table is empty

**Solutions:**
1. Check products have `retail_price` > `buy_price`
2. Lower minimum margin filter
3. Verify source name matches import
4. Check database has products: `SELECT COUNT(*) FROM finance.source_prices;`

### **Import History Empty**

**Problem:** Recent imports don't show

**Solutions:**
1. Refresh page (F5)
2. Click **Refresh** button on table
3. Check database: `SELECT DISTINCT source FROM finance.source_prices;`
4. Verify PostgreSQL connection in Budibase

### **Permissions Error**

**Problem:** "Access denied" or similar

**Solutions:**
1. Check user role (Admin required for imports)
2. Verify Budibase role mapping
3. Check PostgreSQL user permissions

---

## 📚 Related Documentation

- **API Endpoint:** `domains/integration/api/quickflip_router.py:252`
- **Import Service:** `domains/integration/services/market_price_import_service.py`
- **Database Schema:** `alembic/versions/` (migrations)
- **Budibase Guide:** `05_complete_setup_guide.md`

---

## 🎯 Next Steps

### **Immediate (Production Ready)**
1. Import screens into Budibase
2. Test with sample CSV
3. Configure user permissions
4. Train team on workflow

### **Future Enhancements**
1. **Automated Imports**
   - Schedule daily imports via Budibase automations
   - Email notifications on completion

2. **Advanced Analytics**
   - Brand performance comparison
   - Historical margin trends
   - Supplier reliability scoring

3. **Integration**
   - Auto-purchase top opportunities
   - StockX listing automation
   - Inventory sync

---

## ✅ Success Checklist

Before going live, verify:

- [ ] Both screens imported and visible in Budibase
- [ ] PostgreSQL data source connected
- [ ] API data source configured (http://host.docker.internal:8000)
- [ ] All queries created and working
- [ ] Test CSV uploaded successfully
- [ ] Import History shows data
- [ ] QuickFlip Opportunities displays results
- [ ] Filters working correctly
- [ ] Export functionality tested
- [ ] User roles configured
- [ ] Team trained on usage

---

**Setup Time:** ~15 minutes
**Complexity:** Medium
**Value:** High - Automated supplier price comparison

**Status:** ✅ Ready to Deploy

---

**Questions?** Check `README.md` or review API documentation at `/docs`
