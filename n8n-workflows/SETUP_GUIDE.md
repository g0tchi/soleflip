# StockX Profit Checker - Setup Guide

## Overview

This n8n workflow analyzes StockX market data to identify profitable sneaker opportunities by comparing retail prices against current market prices, accounting for StockX's 10% seller fee.

## Architecture

```
Chat Trigger → Parse Input → Search StockX → Get Market Data → Calculate Profit → Format Response
```

### Workflow Nodes

1. **Chat Trigger** - Public chat interface for user input
2. **Parse Input** - Extracts SKU and retail price from message
3. **Search StockX** - Searches for product by SKU via local API
4. **Product Found?** - Validates product exists
5. **Get Market Data** - Fetches all size variants and prices
6. **Calculate Profit** - Computes profit/margin for each size
7. **Has Profitable?** - Checks if any opportunities exist
8. **Format Response** - Creates user-friendly output

## Prerequisites

### 1. Running Services

Ensure all services are running:

```bash
# Start all services (API, PostgreSQL, n8n)
cd /home/g0tchi/projects/soleflip
docker-compose up -d

# Verify services
docker-compose ps
```

**Expected services:**
- API: `http://localhost:8000` (or `http://host.docker.internal:8000` from within Docker)
- PostgreSQL: `localhost:5432`
- n8n: `http://localhost:5678`
- Metabase: `http://localhost:6400`

### 2. API Endpoints

The workflow uses these API endpoints:

```bash
# Search for product by SKU
GET http://host.docker.internal:8000/products/search-stockx?query={sku}

# Get market data for product
GET http://host.docker.internal:8000/products/{productId}/stockx-market-data?currencyCode=EUR
```

**Test endpoints manually:**

```bash
# Test search endpoint
curl "http://localhost:8000/products/search-stockx?query=KI6956"

# Test market data (use productId from search result)
curl "http://localhost:8000/products/{productId}/stockx-market-data?currencyCode=EUR"
```

### 3. Database Access

The workflow doesn't directly access the database, but the API does:

- **Host**: `host.docker.internal:5432` (from Docker) or `localhost:5432` (from host)
- **Database**: `soleflip`
- **User**: `soleflip`
- **Schema**: `catalog`

## Installation Steps

### Step 1: Import Workflow to n8n

1. **Access n8n**:
   ```bash
   # If not running, start it:
   docker-compose up -d n8n

   # Access at:
   open http://localhost:5678
   ```

2. **Import the workflow**:
   - Click **"Add workflow"** → **"Import from File"**
   - Select: `/home/g0tchi/projects/soleflip/n8n-workflows/stockx-profit-checker.json`
   - Click **"Import"**

3. **Alternative: Import via CLI** (if n8n CLI is available):
   ```bash
   n8n import:workflow --input=/home/g0tchi/projects/soleflip/n8n-workflows/stockx-profit-checker.json
   ```

### Step 2: Activate the Workflow

1. In n8n, open the **"StockX Profit Checker"** workflow
2. Click the **"Active"** toggle in the top-right corner
3. The workflow is now live and ready to receive chat messages

### Step 3: Get the Chat URL

1. Click on the **"Chat Trigger"** node
2. In the right panel, you'll see:
   - **Production URL**: `https://your-n8n-instance.com/webhook/stockx-profit-checker`
   - **Test URL**: `https://your-n8n-instance.com/webhook-test/stockx-profit-checker`

3. For local testing, the URL will be:
   ```
   http://localhost:5678/webhook/stockx-profit-checker
   ```

### Step 4: Access the Chat Interface

1. **Via n8n UI** (easiest for testing):
   - Click on the **"Chat Trigger"** node
   - Click **"Open Chat"** button
   - A chat window will open

2. **Via Browser** (for public access):
   - Navigate to: `http://localhost:5678/webhook/stockx-profit-checker`
   - You'll see the chat interface

3. **Embed on Website** (optional):
   ```html
   <iframe
     src="http://localhost:5678/webhook/stockx-profit-checker"
     width="400"
     height="600"
     style="border: none; border-radius: 8px;"
   ></iframe>
   ```

## Usage Examples

### Example 1: Basic Profit Check

**User Input:**
```
Check KI6956 at 129.95
```

**Expected Response:**
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

2. Size US W 8
   • StockX Price: €175.00
   • Net Proceeds: €157.50
   • Profit: €27.55 (21.2%)

3. Size US W 9
   • StockX Price: €170.00
   • Net Proceeds: €153.00
   • Profit: €23.05 (17.7%)

💡 Best Opportunity: Size US W 8.5 with 24.7% margin (€32.05 profit)
```

### Example 2: Different Message Formats

All of these will work:

```
Check KI6956 at 129.95
check ki6956 at 129.95
Check SKU KI6956 retail price 129.95
KI6956 129.95
```

The parser extracts:
- **SKU**: First alphanumeric sequence (5-10 chars)
- **Price**: First decimal number

### Example 3: No Profitable Opportunities

**User Input:**
```
Check DZ5485 at 180
```

**Expected Response:**
```
🔍 StockX Analysis: Nike Air Force 1 Low

📊 Summary
• SKU: DZ5485
• Retail: €180.00
• Total Variants: 12

❌ No Profitable Opportunities

Unfortunately, none of the 12 size variants are profitable at the retail price of €180.00.

Suggestions:
• Wait for StockX prices to increase
• Look for discounted retail prices
• Try different colorways or models
```

## Testing the Workflow

### Manual Test via n8n UI

1. **Open the workflow** in n8n
2. Click **"Execute Workflow"** (play button)
3. In the **Chat Trigger** node, click **"Open Chat"**
4. Send a test message: `Check KI6956 at 129.95`
5. Check each node's output by clicking on them
6. The final response appears in the chat

### Test via API Client (Postman/curl)

```bash
# Send chat message via webhook
curl -X POST http://localhost:5678/webhook/stockx-profit-checker \
  -H "Content-Type: application/json" \
  -d '{
    "action": "sendMessage",
    "sessionId": "test-session",
    "chatInput": "Check KI6956 at 129.95"
  }'
```

### Debug Node Outputs

If something goes wrong, check each node's output:

1. **Parse Input** should output:
   ```json
   {
     "sku": "KI6956",
     "retailPrice": 129.95,
     "originalMessage": "Check KI6956 at 129.95"
   }
   ```

2. **Search StockX** should return:
   ```json
   {
     "productId": "uuid-here",
     "name": "Samba OG Cow Print",
     "brand": "adidas"
   }
   ```

3. **Get Market Data** returns all variants with prices

4. **Calculate Profit** outputs structured profit analysis

## Troubleshooting

### Issue 1: "Could not parse your message"

**Cause**: Invalid input format

**Solution**: Ensure message contains:
- A SKU (5-10 alphanumeric characters)
- A price (decimal number)

**Example fix**: `Check KI6956 at 129.95`

### Issue 2: "Product Not Found"

**Cause**: SKU doesn't exist in database or API error

**Solutions**:
1. Verify SKU exists in your database:
   ```sql
   SELECT * FROM catalog.products WHERE sku = 'KI6956';
   ```

2. Check API is running:
   ```bash
   curl http://localhost:8000/health
   ```

3. Test search endpoint:
   ```bash
   curl "http://localhost:8000/products/search-stockx?query=KI6956"
   ```

### Issue 3: API Connection Refused

**Cause**: API not accessible from n8n container

**Solutions**:

1. **If n8n is in Docker**, use `host.docker.internal`:
   ```
   http://host.docker.internal:8000
   ```

2. **If n8n is on host**, use `localhost`:
   ```
   http://localhost:8000
   ```

3. **Check Docker network**:
   ```bash
   docker network inspect soleflip_default
   ```

4. **Verify API is accessible**:
   ```bash
   # From inside n8n container
   docker exec -it soleflip-n8n-1 curl http://host.docker.internal:8000/health
   ```

### Issue 4: Workflow Not Responding

**Cause**: Workflow not activated or webhook not registered

**Solutions**:
1. Ensure workflow is **Active** (toggle in top-right)
2. Check n8n logs:
   ```bash
   docker-compose logs n8n
   ```
3. Restart n8n:
   ```bash
   docker-compose restart n8n
   ```

### Issue 5: Timeout Errors

**Cause**: API taking too long to respond

**Solutions**:
1. Increase timeout in HTTP Request nodes (currently 30 seconds)
2. Check API performance:
   ```bash
   time curl "http://localhost:8000/products/search-stockx?query=KI6956"
   ```
3. Optimize database queries (add indexes if needed)

## Customization Options

### 1. Change Currency

Edit the **Get Market Data** node URL:
```
http://host.docker.internal:8000/products/{{ $json.productId }}/stockx-market-data?currencyCode=USD
```

Supported: `EUR`, `USD`, `GBP`, etc.

### 2. Adjust StockX Fee Percentage

Edit the **Calculate Profit** node, line 18:
```javascript
// Change from 90% to different value (e.g., 88% for 12% fee)
const netProceeds = stockxPrice * 0.90;
```

### 3. Change Number of Top Opportunities

Edit the **Calculate Profit** node, line 41:
```javascript
// Change from 5 to show more/fewer opportunities
const topOpportunities = profitableVariants.slice(0, 5);
```

### 4. Customize Chat Interface

Edit the **Chat Trigger** node parameters:
```json
{
  "title": "🔍 Your Custom Title",
  "subtitle": "Your custom subtitle",
  "inputPlaceholder": "Your custom placeholder",
  "initialMessages": "Your custom welcome message"
}
```

### 5. Add Discord Bot (Future Enhancement)

Replace **Chat Trigger** with **Discord Trigger**:
1. Create Discord bot in Discord Developer Portal
2. Add **Discord Trigger** node
3. Configure bot token and channel
4. Keep rest of workflow unchanged

## Performance Optimization

### 1. Enable Caching

Add a **Redis** node before HTTP requests to cache results:
```javascript
// Check cache first
const cacheKey = `stockx:${sku}`;
// ... implement Redis GET/SET
```

### 2. Batch Processing

If processing multiple SKUs, use **Loop Over Items** node.

### 3. Parallel Execution

For multiple products, use **Split Out** and process in parallel.

## Security Considerations

### 1. Rate Limiting

Add rate limiting to prevent abuse:
- Use n8n's built-in rate limiter
- Or add **Rate Limit** node

### 2. Input Validation

The workflow validates:
- ✅ SKU format (5-10 alphanumeric)
- ✅ Price format (positive decimal)
- ⚠️ Consider adding: SQL injection prevention (already handled by API)

### 3. Authentication

Currently public. To add authentication:
1. Edit **Chat Trigger** node
2. Set **Authentication** to **Basic Auth** or **n8n User Auth**
3. Configure credentials

## Monitoring & Logging

### View Execution History

1. In n8n, go to **Executions**
2. Filter by workflow: **StockX Profit Checker**
3. Click on any execution to see detailed logs

### Enable Debug Logging

Add **Function** nodes with console.log:
```javascript
console.log('Debug:', $input.all());
return $input.all();
```

### Monitor API Health

```bash
# Check API health
curl http://localhost:8000/health

# Monitor API logs
docker-compose logs -f api
```

## Next Steps

### 1. Add More Features

- **Historical price charts**: Show price trends
- **Alerts**: Notify when profit opportunity appears
- **Bulk checking**: Process multiple SKUs at once
- **Size recommendations**: Suggest which sizes to stock

### 2. Integration with Other Systems

- **Inventory management**: Check stock availability
- **Automated purchasing**: Trigger buy orders
- **Accounting**: Export profit calculations
- **CRM**: Log opportunities for sales team

### 3. Deploy to Production

1. **Use HTTPS**: Configure SSL certificate
2. **Add authentication**: Protect chat interface
3. **Scale n8n**: Use n8n cloud or cluster mode
4. **Monitor performance**: Set up alerting

## Support

### Documentation
- n8n docs: https://docs.n8n.io
- API docs: http://localhost:8000/docs

### Logs
```bash
# n8n logs
docker-compose logs n8n

# API logs
docker-compose logs api

# All logs
docker-compose logs -f
```

### Database Queries

```sql
-- Check products table
SELECT * FROM catalog.products WHERE sku LIKE 'KI%' LIMIT 10;

-- Check market data
SELECT * FROM catalog.stockx_market_data LIMIT 10;
```

---

**Last Updated**: 2025-11-19
**Version**: 1.0
**Author**: SoleFlip Team
