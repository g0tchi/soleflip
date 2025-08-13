# 💰 Transaction Integration Guide

## 📋 Overview

This document explains how StockX and Alias CSV imports are now fully integrated into the `sales.transactions` table, creating a complete sales tracking system.

## 🔄 Complete Import Pipeline

### Before (❌ Incomplete)
```
CSV Import → Validation → Transformation → import_records ✅
                                       ↘ transactions ❌ (missing!)
```

### After (✅ Complete)
```
CSV Import → Validation → Transformation → import_records ✅
                                       ↗ products ✅
                                       ↗ transactions ✅ (NEW!)
                                       ↗ inventory_items ✅ (auto-created)
```

## 🏗️ Architecture Components

### 1. **TransactionProcessor** (`domains/sales/services/transaction_processor.py`)
- **Purpose**: Creates sales transactions from validated import data
- **Features**:
  - ✅ Automatic platform resolution (StockX, Alias, etc.)
  - ✅ Product and inventory item creation
  - ✅ Duplicate transaction detection
  - ✅ Fee calculation and net profit computation
  - ✅ Size normalization and management

### 2. **Enhanced Import Pipeline** 
- **Product Extraction**: Creates product catalog entries
- **Transaction Creation**: Creates sales transaction records  
- **Inventory Management**: Auto-creates inventory items for tracking

### 3. **Database Schema Integration**
```sql
-- Complete data flow through schemas
core.platforms (StockX, Alias, GOAT, etc.)
     ↓
products.products (extracted from sales data)  
     ↓
products.inventory (auto-created items)
     ↓  
sales.transactions (financial tracking)
     ↓
integration.import_records (audit trail)
```

## 📊 StockX Integration Details

### **StockX CSV Fields → Transaction Mapping**

| StockX CSV Field | Transaction Field | Notes |
|------------------|-------------------|-------|
| `Order Number` | `external_id` | Unique transaction identifier |
| `Sale Date` | `transaction_date` | When the sale occurred |
| `Listing Price` | `sale_price` | Gross sale amount |
| `Seller Fee` | `platform_fee` | StockX commission |
| `Shipping Fee` | `shipping_cost` | Shipping charges |
| `Total Payout` | `net_profit` | Final amount received |
| `Item` | → `Product.name` | Product catalog entry |
| `Style` | → `Product.sku` | Product SKU |
| `Sku Size` | → `Size.value` | Size management |

### **Example StockX Transaction Creation**
```python
# From StockX CSV row:
{
    "Order Number": "39230274-39130033",
    "Sale Date": "2022-07-08 00:46:09 +00", 
    "Item": "Taschen Sneaker Freaker. The Ultimate Sneaker Book",
    "Listing Price": "45",
    "Seller Fee": "1.35", 
    "Shipping Fee": "5",
    "Total Payout": "30.65"
}

# Creates Transaction:
Transaction(
    platform_id=stockx_platform.id,
    sale_price=Decimal("45.00"),
    platform_fee=Decimal("1.35"),
    shipping_cost=Decimal("5.00"), 
    net_profit=Decimal("30.65"),
    external_id="stockx_39230274-39130033",
    status="completed"
)
```

## 🎯 Alias Integration Details

### **Alias CSV Fields → Transaction Mapping**

| Alias CSV Field | Transaction Field | Notes |
|------------------|-------------------|-------|
| `ORDER_NUMBER` | `external_id` | Unique transaction identifier |
| `CREDIT_DATE` | `transaction_date` | When payment was received |
| `PRODUCT_PRICE_CENTS_SALE_PRICE` | `sale_price` | Sale amount (USD, not cents!) |
| `NAME` | → `Product.name` | Product catalog entry |
| `SKU` | → `Product.sku` | Product SKU |
| `SIZE` | → `Size.value` | Size management |
| `USERNAME` | → `InventoryItem.supplier` | Seller information |

### **Alias Special Handling**
- ✅ **No Platform Fees**: Alias transactions have `platform_fee = 0.00`
- ✅ **Brand Extraction**: Automatically extracts brands from product names
- ✅ **Date Format**: Handles DD/MM/YY format correctly
- ✅ **Size Intelligence**: Differentiates shoe vs. clothing sizes

### **Example Alias Transaction Creation**
```python
# From Alias CSV row:
{
    "ORDER_NUMBER": "586612181",
    "CREDIT_DATE": "20/12/24",
    "NAME": "Travis Scott x Air Jordan 1 Retro Low OG SP 'Reverse Olive'",
    "PRODUCT_PRICE_CENTS_SALE_PRICE": "399",
    "SKU": "DM7866 200",
    "SIZE": "18"
}

# Creates Transaction:
Transaction(
    platform_id=alias_platform.id,
    sale_price=Decimal("399.00"),  # Direct USD amount
    platform_fee=Decimal("0.00"),  # Alias has no fees
    net_profit=Decimal("399.00"),  # Full amount = profit
    external_id="alias_586612181", 
    status="completed"
)
```

## 🎛️ Transaction Processing Features

### 1. **Platform Resolution**
```python
# Automatic platform detection and creation
platforms = {
    'stockx': {'fee_percentage': 9.5, 'supports_fees': True},
    'alias': {'fee_percentage': 0.0, 'supports_fees': False},
    'goat': {'fee_percentage': 9.5, 'supports_fees': True},
    'manual': {'fee_percentage': 0.0, 'supports_fees': False}
}
```

### 2. **Duplicate Prevention**
- ✅ Checks `external_id` for exact duplicates
- ✅ Cross-references platform + order number
- ✅ Prevents double-importing same transactions

### 3. **Auto Product/Inventory Creation**
```python
# Creates complete product catalog entry
Product(
    sku="DM7866 200",
    name="Travis Scott x Air Jordan 1 Retro Low OG SP 'Reverse Olive'",
    category="Footwear"  # Auto-detected
)

# Creates inventory tracking
InventoryItem(
    product_id=product.id,
    size="18",
    status="sold",  # Imported sales are already sold
    supplier="g0tchi"  # From Alias USERNAME
)

# Links to transaction
Transaction(
    inventory_id=inventory_item.id,
    platform_id=platform.id,
    # ... financial data
)
```

### 4. **Financial Calculations**
```python
# StockX: Full fee breakdown
net_profit = sale_price - platform_fee - shipping_cost

# Alias: No fees, full amount is profit  
net_profit = sale_price  # (platform_fee = 0, shipping_cost = 0)
```

## 🚀 Usage Examples

### **Import StockX CSV with Transaction Creation**
```bash
curl -X POST "http://localhost:8000/api/v1/integration/stockx/upload" \
  -F "file=@stockx_sales_report.csv" \
  -F "batch_size=1000"

# Results in:
# ✅ Products extracted and cataloged
# ✅ Transactions created in sales.transactions  
# ✅ Inventory items auto-created
# ✅ Complete audit trail in integration.import_records
```

### **Import Alias CSV with Transaction Creation**
```bash
curl -X POST "http://localhost:8000/api/v1/integration/alias/upload" \
  -F "file=@alias_sales_report.csv" \
  -F "batch_size=1000"

# Results in:
# ✅ Brands extracted from product names
# ✅ Transactions created (zero platform fees)
# ✅ StockX name prioritization applied
# ✅ Size normalization (shoes vs. clothing)
```

### **Query Transaction Data**
```sql
-- Get all transactions with platform and product info
SELECT 
    t.transaction_date,
    p.name as platform,
    pr.name as product,
    t.sale_price,
    t.platform_fee,
    t.net_profit,
    t.external_id
FROM sales.transactions t
JOIN core.platforms p ON t.platform_id = p.id
JOIN products.inventory i ON t.inventory_id = i.id  
JOIN products.products pr ON i.product_id = pr.id
ORDER BY t.transaction_date DESC;

-- Platform performance analysis
SELECT 
    p.name as platform,
    COUNT(*) as transaction_count,
    SUM(t.sale_price) as total_sales,
    SUM(t.platform_fee) as total_fees,
    SUM(t.net_profit) as total_profit,
    AVG(t.net_profit) as avg_profit
FROM sales.transactions t
JOIN core.platforms p ON t.platform_id = p.id
GROUP BY p.name
ORDER BY total_profit DESC;
```

## 📈 Analytics & Reporting Benefits

### **Complete Sales Tracking**
- ✅ **Revenue Analysis**: Total sales by platform, time period, product
- ✅ **Profitability**: Net profit after all fees and costs
- ✅ **Platform Comparison**: StockX vs. Alias performance
- ✅ **Product Performance**: Best/worst selling items
- ✅ **Fee Impact**: How platform fees affect profitability

### **Inventory Intelligence**  
- ✅ **Sell-Through Rate**: How quickly items sell
- ✅ **Size Analysis**: Popular sizes by category
- ✅ **Supplier Performance**: Best suppliers (Alias usernames)
- ✅ **Inventory Valuation**: Current stock value vs. sold items

### **Business Intelligence**
- ✅ **Trend Analysis**: Sales patterns over time
- ✅ **Brand Performance**: Nike vs. Adidas vs. New Balance
- ✅ **Seasonality**: Peak selling periods
- ✅ **ROI Calculation**: Purchase vs. sale price analysis

## ✅ Verification & Testing

### **Database Verification**
```sql
-- Check transaction creation
SELECT COUNT(*) FROM sales.transactions;

-- Verify platform linkage  
SELECT p.name, COUNT(t.id) 
FROM core.platforms p
LEFT JOIN sales.transactions t ON p.id = t.platform_id
GROUP BY p.name;

-- Check data completeness
SELECT 
    COUNT(*) as total_transactions,
    COUNT(CASE WHEN external_id IS NOT NULL THEN 1 END) as with_external_id,
    COUNT(CASE WHEN platform_fee > 0 THEN 1 END) as with_fees,
    COUNT(CASE WHEN net_profit > 0 THEN 1 END) as profitable
FROM sales.transactions;
```

### **API Testing**
```bash
# Upload test file and monitor logs
curl -X POST "http://localhost:8000/api/v1/integration/stockx/upload" \
  -F "file=@test_stockx.csv" \
  -F "validate_only=false"

# Check import status
curl "http://localhost:8000/api/v1/integration/import-status"

# Verify transaction creation in logs:
# "Transaction creation completed", transactions_created: 10
```

## 🎉 Benefits Achieved

### **Complete Data Integration**
- ✅ Sales data flows from CSV → Products → Inventory → Transactions
- ✅ No data silos - everything is connected and queryable
- ✅ Full audit trail maintained throughout pipeline

### **Business Intelligence Ready**  
- ✅ Metabase can now create complete sales dashboards
- ✅ Revenue, profitability, and performance analytics
- ✅ Platform comparison and optimization insights

### **Scalable Architecture**
- ✅ New platforms can be easily added
- ✅ Transaction processing handles any volume
- ✅ Duplicate prevention ensures data integrity

The transaction integration transforms SoleFlipper from a simple import tool into a complete sales analytics platform! 🚀