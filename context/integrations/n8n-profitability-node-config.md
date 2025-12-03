# n8n Profitability Check Node Configuration

## Overview

This document describes how to integrate the `/pricing/evaluate-profitability` endpoint into your n8n workflow for pre-import filtering.

---

## API Endpoint Details

**Endpoint:** `POST http://localhost:8000/pricing/evaluate-profitability`

**Authentication:** Optional (use `httpHeaderAuth` if API key is configured)

**Request Body:**
```json
{
  "ean": "0194953025890",
  "supplier_price": 85.99,
  "brand": "Nike",
  "model": "Air Max 90 Essential",
  "size": "US 10"
}
```

**Response:**
```json
{
  "profitable": true,
  "margin_percent": 28.35,
  "absolute_profit": 29.00,
  "supplier_price": 85.99,
  "market_price": 119.99,
  "should_import": true,
  "reason": "Profitable: 28.4% margin (min: 15.0%)",
  "min_margin_threshold": 15.0
}
```

---

## n8n Node Configuration

### Node 1: HTTP Request - Check Profitability

**Node Type:** `HTTP Request`
**Node Name:** `Check Product Profitability`

#### Settings:

```json
{
  "method": "POST",
  "url": "http://localhost:8000/pricing/evaluate-profitability",
  "authentication": "predefinedCredentialType",
  "nodeCredentialType": "httpHeaderAuth",
  "sendBody": true,
  "specifyBody": "json",
  "jsonBody": "={{ {\n  \"ean\": $json.ean,\n  \"supplier_price\": $json.price,\n  \"brand\": $json.brand,\n  \"model\": $json.product_name,\n  \"size\": $json.size || null\n} }}",
  "options": {
    "timeout": 10000,
    "retry": {
      "enabled": true,
      "maxRetries": 2,
      "waitBetween": 1000
    }
  }
}
```

#### Code Version (alternative):

```javascript
// HTTP Request Node - Body Parameters
{
  "ean": "={{ $json.ean }}",
  "supplier_price": {{ $json.price }},
  "brand": "={{ $json.brand }}",
  "model": "={{ $json.product_name }}",
  "size": "={{ $json.size || null }}"
}
```

---

### Node 2: Switch - Route by Profitability

**Node Type:** `Switch`
**Node Name:** `Route: Profitable?`

#### Rules Configuration:

```json
{
  "rules": {
    "rules": [
      {
        "conditions": {
          "boolean": [
            {
              "value1": "={{ $json.profitable }}",
              "value2": true
            }
          ]
        },
        "renameOutput": true,
        "outputKey": "profitable"
      },
      {
        "conditions": {
          "boolean": [
            {
              "value1": "={{ $json.profitable }}",
              "value2": false
            }
          ]
        },
        "renameOutput": true,
        "outputKey": "unprofitable"
      }
    ]
  }
}
```

#### Outputs:
1. **profitable** → Continue to import
2. **unprofitable** → Skip or log

---

### Node 3a: Continue to Import (Profitable Path)

**Node Type:** `HTTP Request` (or existing "Create Product in SoleFlip" node)
**Node Name:** `Import Profitable Product`

```javascript
// This continues with your existing import logic
// Just ensure you pass through the profitability data

{
  "brand": "={{ $json.brand }}",
  "name": "={{ $json.product_name }}",
  "ean": "={{ $json.ean }}",
  "price": {{ $json.price }},
  // Add profitability metadata
  "supplier_price": {{ $('Check Product Profitability').item.json.supplier_price }},
  "market_price": {{ $('Check Product Profitability').item.json.market_price }},
  "profit_margin": {{ $('Check Product Profitability').item.json.margin_percent }},
  "profitability_status": "profitable"
}
```

---

### Node 3b: Log Unprofitable (Unprofitable Path)

**Node Type:** `Data Table` (Insert)
**Node Name:** `Log Unprofitable Product`

**Data Table:** `unprofitable_products_review`

```json
{
  "operation": "insert",
  "dataTable": "unprofitable_products_review",
  "fields": {
    "mappings": [
      {
        "fieldName": "ean",
        "fieldValue": "={{ $json.ean }}"
      },
      {
        "fieldName": "brand",
        "fieldValue": "={{ $json.brand }}"
      },
      {
        "fieldName": "product_name",
        "fieldValue": "={{ $json.product_name }}"
      },
      {
        "fieldName": "supplier_price",
        "fieldValue": "={{ $('Check Product Profitability').item.json.supplier_price }}"
      },
      {
        "fieldName": "market_price",
        "fieldValue": "={{ $('Check Product Profitability').item.json.market_price }}"
      },
      {
        "fieldName": "margin_percent",
        "fieldValue": "={{ $('Check Product Profitability').item.json.margin_percent }}"
      },
      {
        "fieldName": "reason",
        "fieldValue": "={{ $('Check Product Profitability').item.json.reason }}"
      },
      {
        "fieldName": "import_id",
        "fieldValue": "={{ $json.import_id }}"
      },
      {
        "fieldName": "reviewed",
        "fieldValue": 0
      }
    ]
  }
}
```

---

## Complete Node Flow

```
[...existing filtering nodes...]
    ↓
Normalize Product Data
    ↓
Get All Fingerprints
    ↓
Check for Duplicates
    ↓
┌─────────────────────────────────────┐
│ NEW: Check Product Profitability    │
│ (HTTP Request)                      │
│ POST /pricing/evaluate-profitability│
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Route: Profitable?                  │
│ (Switch Node)                       │
└─────────────────────────────────────┘
    ↓
┌──────────┬──────────────────────┐
│ ✅       │ ❌                   │
│ Profit   │ Unprofitable         │
│ able     │                      │
└──────────┴──────────────────────┘
    ↓              ↓
[Continue    [Log to Review
 to Import]   Table & Skip]
    ↓
Route: New vs Duplicate (existing logic)
    ↓
Create Product in SoleFlip
    ↓
[...rest of existing workflow...]
```

---

## Error Handling

### Handle API Errors

Add an `IF` node after the profitability check to handle errors:

```javascript
// IF Node: Check if API call succeeded
if ($json.error || !$json.hasOwnProperty('profitable')) {
  // Error occurred - decide what to do
  // Option 1: Import anyway (optimistic)
  // Option 2: Skip and log error
  // Option 3: Use fallback heuristic (already done in API)
}
```

### Retry Configuration

The HTTP Request node already has retry logic configured (2 retries, 1s wait).

---

## Statistics Tracking

Update your `import_log` table to include profitability stats:

```javascript
// In "Aggregate Statistics" node
const workflowData = $getWorkflowStaticData('global');

// Add new counters
workflowData.currentImport.profitable_count = 0;
workflowData.currentImport.unprofitable_count = 0;
workflowData.currentImport.avg_margin = 0;

// Count profitable items
const profitableItems = $('Import Profitable Product').all();
workflowData.currentImport.profitable_count = profitableItems.length;

// Count unprofitable items
const unprofitableItems = $('Log Unprofitable Product').all();
workflowData.currentImport.unprofitable_count = unprofitableItems.length;

// Calculate average margin
if (profitableItems.length > 0) {
  const totalMargin = profitableItems.reduce((sum, item) => {
    return sum + parseFloat(item.json.profit_margin || 0);
  }, 0);
  workflowData.currentImport.avg_margin = (totalMargin / profitableItems.length).toFixed(2);
}
```

---

## Configuration Options

### Environment Variables

Add to `.env`:

```bash
# Profitability Thresholds
MIN_PROFIT_MARGIN_PERCENT=15.0     # Minimum margin to import
OPERATIONAL_COST_PER_UNIT=5.00     # Fixed cost per item (€)

# Optional: Override in workflow
WEBGAINS_MIN_MARGIN=20.0           # Higher threshold for Webgains
AWIN_MIN_MARGIN=15.0               # Lower threshold for Awin
```

### Dynamic Threshold per Brand

Add a Code node before profitability check to adjust thresholds:

```javascript
// Adjust minimum margin based on brand
const brand = $json.brand.toLowerCase();

let minMargin = 15.0;  // Default

if (['nike', 'jordan', 'adidas'].includes(brand)) {
  minMargin = 20.0;  // Higher margin for premium brands
} else if (['new balance', 'asics'].includes(brand)) {
  minMargin = 15.0;  // Standard margin
} else {
  minMargin = 12.0;  // Lower margin for lesser-known brands
}

// Store for later use
$json.min_margin_override = minMargin;
```

---

## Testing

### Test with Sample Data

```bash
# Test the endpoint directly
curl -X POST http://localhost:8000/pricing/evaluate-profitability \
  -H "Content-Type: application/json" \
  -d '{
    "ean": "0194953025890",
    "supplier_price": 85.99,
    "brand": "Nike",
    "model": "Air Max 90 Essential",
    "size": "US 10"
  }'
```

**Expected Response:**
```json
{
  "profitable": true,
  "margin_percent": 28.35,
  "absolute_profit": 29.00,
  "supplier_price": 85.99,
  "market_price": 119.99,
  "should_import": true,
  "reason": "Profitable: 28.4% margin (min: 15.0%)",
  "min_margin_threshold": 15.0
}
```

### Test in n8n Workflow

1. Open workflow in n8n
2. Click "Execute Workflow" with manual trigger
3. Check "Check Product Profitability" node output
4. Verify routing works correctly
5. Check Data Tables for logged products

---

## Monitoring

### Track Profitability Stats

Add to your import summary:

```javascript
// In "Format Summary" node
const stats = $json;

const summary = `
🎯 Webgains Product Import Complete

📊 Statistics:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Total Products: ${stats.totalProducts}
🏷️  Brand Filtered: ${stats.brandFiltered}
📂 Category Filtered: ${stats.categoryFiltered}
🔄 Duplicates: ${stats.duplicatesFound}

💰 Profitability Check:
   ✅ Profitable: ${stats.profitable_count}
   ❌ Unprofitable: ${stats.unprofitable_count}
   📈 Avg Margin: ${stats.avg_margin}%

✅ Imported: ${stats.newProducts}
❌ Errors: ${stats.errors}
⏱️  Duration: ${Math.round((Date.now() - stats.startTime) / 1000)}s

🎯 Final Filter Rate: ${((stats.newProducts / stats.totalProducts) * 100).toFixed(2)}% kept
🎯 Profitability Rate: ${((stats.profitable_count / (stats.profitable_count + stats.unprofitable_count)) * 100).toFixed(2)}%

Import ID: ${stats.importId}
`;

return [{ json: { summary, stats } }];
```

---

## Troubleshooting

### Issue: All products marked as unprofitable

**Cause:** No market data available

**Solutions:**
1. Check if products exist in catalog (need EAN match)
2. Implement StockX EAN lookup (requires API enhancement)
3. Use Data Table with manual market prices
4. Adjust heuristic multiplier (currently 1.25x)

### Issue: API returns 500 error

**Check:**
1. SoleFlip API is running: `curl http://localhost:8000/health`
2. Database connection is working
3. Check logs: `docker-compose logs -f api`

### Issue: Profitability check is slow

**Optimize:**
1. Cache market prices in Data Table (update weekly)
2. Batch profitability checks (10-50 products at once)
3. Use existing catalog prices instead of API calls

---

**Last Updated:** 2025-12-03
**Version:** 1.0.0
