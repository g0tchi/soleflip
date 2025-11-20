# StockX Profit Checker - Quick Start

## 🚀 5-Minute Setup

### 1. Start Services
```bash
cd /home/g0tchi/projects/soleflip
docker-compose up -d
```

### 2. Import Workflow
1. Open http://localhost:5678
2. Click **"Add workflow"** → **"Import from File"**
3. Select: `n8n-workflows/stockx-profit-checker.json`
4. Click **"Import"**

### 3. Activate Workflow
1. Toggle **"Active"** switch (top-right)
2. Workflow is now live ✅

### 4. Test It
1. Click **"Chat Trigger"** node
2. Click **"Open Chat"** button
3. Send message: `Check KI6956 at 129.95`
4. View results! 🎉

## 📝 Quick Test Commands

### Format
```
Check [SKU] at [RETAIL_PRICE]
```

### Examples
```
Check KI6956 at 129.95
Check DZ5485 at 180
Check FD0744 at 95.50
```

## 🔍 What It Does

1. **Parses** your message to extract SKU and retail price
2. **Searches** StockX via local API
3. **Fetches** market data for all size variants
4. **Calculates** profit = (StockX price × 0.90) - retail
5. **Shows** top 5 most profitable opportunities

## 💰 Profit Calculation

```
Net Proceeds = StockX Price × 90% (after 10% fee)
Profit = Net Proceeds - Retail Price
Margin % = (Profit / Retail Price) × 100
```

## ✅ Expected Output

### Profitable Example
```
🔍 StockX Analysis: adidas Samba OG Cow Print

📊 Summary
• SKU: KI6956
• Retail: €129.95
• Profitable Sizes: 8 of 15

✅ Top Opportunities (Net profit after 10% StockX fee)

1. Size US W 8.5
   • StockX Price: €180.00
   • Net Proceeds: €162.00
   • Profit: €32.05 (24.7%)

💡 Best Opportunity: Size US W 8.5 with 24.7% margin
```

### No Profit Example
```
🔍 StockX Analysis: Nike Air Force 1

📊 Summary
• SKU: DZ5485
• Retail: €180.00
• Total Variants: 12

❌ No Profitable Opportunities

Suggestions:
• Wait for StockX prices to increase
• Look for discounted retail prices
```

## 🐛 Troubleshooting

### Error: "Could not parse your message"
❌ **Wrong**: `check profit for KI6956`
✅ **Right**: `Check KI6956 at 129.95`

### Error: "Product Not Found"
Check if product exists:
```bash
curl "http://localhost:8000/products/search-stockx?query=KI6956"
```

### Error: "Connection refused"
Verify API is running:
```bash
curl http://localhost:8000/health
docker-compose ps
```

### Workflow not responding
1. Check if workflow is **Active** (toggle on)
2. Restart n8n: `docker-compose restart n8n`
3. Check logs: `docker-compose logs n8n`

## 🔗 URLs

| Service | URL |
|---------|-----|
| n8n | http://localhost:5678 |
| Chat Interface | http://localhost:5678/webhook/stockx-profit-checker |
| API Docs | http://localhost:8000/docs |
| API Health | http://localhost:8000/health |
| Metabase | http://localhost:6400 |

## 🛠️ Quick Customization

### Change Currency (EUR → USD)
Edit **"Get Market Data"** node URL:
```
?currencyCode=USD
```

### Change StockX Fee (10% → 12%)
Edit **"Calculate Profit"** node:
```javascript
const netProceeds = stockxPrice * 0.88; // Was 0.90
```

### Show More Opportunities (5 → 10)
Edit **"Calculate Profit"** node:
```javascript
const topOpportunities = profitableVariants.slice(0, 10); // Was 5
```

## 📊 Test with Real Data

### Step 1: Find a SKU
```bash
# Query your database
docker-compose exec postgres psql -U soleflip -d soleflip -c \
  "SELECT sku, name, brand FROM catalog.products LIMIT 10;"
```

### Step 2: Get Market Data
```bash
# Test API endpoint
curl "http://localhost:8000/products/search-stockx?query=YOUR_SKU"
```

### Step 3: Use in Chat
```
Check YOUR_SKU at RETAIL_PRICE
```

## 🎯 Success Criteria

✅ Chat interface opens
✅ Message is parsed correctly
✅ Product is found in database
✅ Market data is fetched
✅ Profit calculation completes
✅ Formatted response is displayed

## 📚 Full Documentation

For detailed setup, customization, and troubleshooting:
- **Full Guide**: `n8n-workflows/SETUP_GUIDE.md`
- **Workflow JSON**: `n8n-workflows/stockx-profit-checker.json`

## 🚀 Next Steps

1. ✅ **Test workflow** with sample SKUs
2. 🔍 **Monitor executions** in n8n UI
3. 🎨 **Customize** chat interface branding
4. 🤖 **Add Discord bot** (future enhancement)
5. 📊 **Set up alerts** for high-margin opportunities

---

**Need Help?**
- Check logs: `docker-compose logs -f`
- API docs: http://localhost:8000/docs
- n8n docs: https://docs.n8n.io
