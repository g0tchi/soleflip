# n8n Workflows for SoleFlip

This directory contains n8n workflow automations for the SoleFlip sneaker resale platform.

## 📁 Contents

### Workflows

1. **stockx-profit-checker.json**
   - Analyzes StockX market data to identify profitable sneaker opportunities
   - Chat interface for easy interaction
   - Real-time profit calculation with StockX fee accounting
   - **Status**: ✅ Production Ready

### Documentation

- **QUICK_START.md** - 5-minute setup guide for immediate deployment
- **SETUP_GUIDE.md** - Comprehensive setup, configuration, and troubleshooting guide
- **README.md** - This file (overview and index)

## 🚀 Quick Start

```bash
# 1. Start services
cd /home/g0tchi/projects/soleflip
docker-compose up -d

# 2. Import workflow to n8n
# Open http://localhost:5678
# Add workflow → Import from File → Select stockx-profit-checker.json

# 3. Activate workflow
# Toggle "Active" switch in n8n UI

# 4. Test it
# Click "Chat Trigger" node → "Open Chat"
# Message: "Check KI6956 at 129.95"
```

See **QUICK_START.md** for detailed instructions.

## 📊 Available Workflows

### StockX Profit Checker

**Purpose**: Identify profitable sneaker arbitrage opportunities

**Features**:
- 💬 Chat-based interface (can extend to Discord, Slack, etc.)
- 🔍 Real-time StockX market data lookup
- 💰 Automatic profit calculation (accounts for 10% StockX fee)
- 📈 Top 5 most profitable size opportunities
- 📊 Margin percentage and net profit analysis
- ✅ Product validation and error handling

**Input Format**:
```
Check [SKU] at [RETAIL_PRICE]
Example: Check KI6956 at 129.95
```

**Output**:
- Product name and brand
- Retail price
- Top 5 most profitable sizes with:
  - StockX price
  - Net proceeds (after fee)
  - Profit amount
  - Margin percentage
- Best opportunity highlight

**Technical Details**:
- **Nodes**: 10 (trigger + 9 processing nodes)
- **API Endpoints**: 2 (search + market data)
- **Validation**: ✅ Passes workflow validation
- **Error Handling**: Comprehensive error paths
- **Performance**: ~2-5 seconds per query

## 🏗️ Architecture Overview

### Service Integration

```
┌─────────────────┐
│  n8n Workflow   │
│  (localhost:    │
│   5678)         │
└────────┬────────┘
         │
         │ HTTP Requests
         ▼
┌─────────────────┐
│  SoleFlip API   │
│  (host.docker.  │
│   internal:8000)│
└────────┬────────┘
         │
         │ SQL Queries
         ▼
┌─────────────────┐
│  PostgreSQL     │
│  Database       │
│  (catalog       │
│   schema)       │
└─────────────────┘
```

### Workflow Flow

```
Chat Input → Parse SKU/Price → Search StockX API
                                      ↓
                            Product Found? ───No──→ Error Message
                                      ↓ Yes
                            Get Market Data
                                      ↓
                            Calculate Profits (All Sizes)
                                      ↓
                            Has Profitable? ───No──→ No Profit Message
                                      ↓ Yes
                            Format Response (Top 5)
                                      ↓
                            Display to User
```

## 🔧 Configuration

### Environment Variables

Required for workflow operation:

```bash
# API Configuration
API_BASE_URL=http://host.docker.internal:8000  # From Docker
# Or: http://localhost:8000                     # From host

# Database Configuration (used by API)
DATABASE_URL=postgresql://soleflip:password@localhost:5432/soleflip

# n8n Configuration
N8N_HOST=localhost
N8N_PORT=5678
N8N_PROTOCOL=http
```

### API Endpoints Used

1. **Search StockX**:
   ```
   GET /products/search-stockx?query={sku}
   Returns: { productId, name, brand, ... }
   ```

2. **Get Market Data**:
   ```
   GET /products/{productId}/stockx-market-data?currencyCode=EUR
   Returns: { variants: [{ shoeSize, market: { lowestAsk } }] }
   ```

### Customization Options

1. **Currency**: Change `EUR` to `USD`, `GBP`, etc. in "Get Market Data" node
2. **StockX Fee**: Modify `0.90` multiplier in "Calculate Profit" node (default: 10% fee)
3. **Top Opportunities**: Change `.slice(0, 5)` to show more/fewer results
4. **Chat Branding**: Customize title, subtitle, placeholder in "Chat Trigger" node

## 🧪 Testing

### Unit Test Each Node

1. **Parse Input**: Test with various message formats
   ```
   Check KI6956 at 129.95
   check ki6956 129.95
   KI6956 at 129.95 EUR
   ```

2. **Search StockX**: Verify API connection
   ```bash
   curl "http://localhost:8000/products/search-stockx?query=KI6956"
   ```

3. **Calculate Profit**: Test with mock market data
   ```json
   {
     "variants": [
       {"shoeSize": "US M 9", "market": {"lowestAsk": 180}},
       {"shoeSize": "US M 10", "market": {"lowestAsk": 175}}
     ]
   }
   ```

### Integration Testing

```bash
# 1. Check all services are running
docker-compose ps

# 2. Test API health
curl http://localhost:8000/health

# 3. Test workflow via chat UI
# Open: http://localhost:5678/webhook/stockx-profit-checker
# Send: "Check KI6956 at 129.95"

# 4. Check execution history in n8n
# Navigate to: Executions → Filter by workflow name
```

### Expected Results

**Valid Product (Profitable)**:
- ✅ SKU parsed correctly
- ✅ Product found in database
- ✅ Market data retrieved (15+ variants)
- ✅ Profit calculation completed
- ✅ Formatted response with top 5 opportunities
- ⏱️ Response time: 2-5 seconds

**Valid Product (Not Profitable)**:
- ✅ SKU parsed correctly
- ✅ Product found
- ✅ Market data retrieved
- ✅ Profit calculation completed
- ℹ️ "No Profitable Opportunities" message
- ⏱️ Response time: 2-5 seconds

**Invalid Product**:
- ✅ SKU parsed correctly
- ❌ Product not found
- ℹ️ "Product Not Found" error message
- ⏱️ Response time: 1-2 seconds

**Invalid Input**:
- ❌ Parse error
- ℹ️ "Could not parse your message" error
- ⏱️ Response time: <1 second

## 🐛 Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Chat not responding | Workflow not active | Toggle "Active" switch in n8n |
| "Connection refused" | API not accessible | Check `docker-compose ps`, use `host.docker.internal` |
| "Product Not Found" | SKU doesn't exist | Verify SKU in database: `SELECT * FROM catalog.products WHERE sku='...'` |
| "Parse error" | Invalid message format | Use format: `Check [SKU] at [PRICE]` |
| Timeout errors | API too slow | Increase timeout in HTTP Request nodes (currently 30s) |
| Wrong currency | Hardcoded EUR | Change `currencyCode=EUR` in "Get Market Data" node |

### Debug Commands

```bash
# Check n8n logs
docker-compose logs n8n -f

# Check API logs
docker-compose logs api -f

# Test API manually
curl "http://localhost:8000/products/search-stockx?query=KI6956"

# Check database
docker-compose exec postgres psql -U soleflip -d soleflip \
  -c "SELECT sku, name, brand FROM catalog.products LIMIT 10;"

# Restart services
docker-compose restart n8n api
```

### Validation Warnings

The workflow passes validation with these warnings (non-critical):

- ⚠️ Code nodes lack error handling (by design - errors throw to chat)
- ⚠️ HTTP Request nodes use typeVersion 4.2 (latest: 4.3, but compatible)
- ⚠️ IF nodes could use `onError: 'continueErrorOutput'` (optional enhancement)

These warnings don't affect functionality but can be addressed for production hardening.

## 📈 Performance Metrics

### Expected Performance

- **Chat Response Time**: 2-5 seconds
- **API Response Time**: 500ms-2s per endpoint
- **Database Query Time**: 50-200ms
- **Total Workflow Execution**: 3-7 seconds

### Bottlenecks

1. **StockX API calls** (if implemented): External API latency
2. **Database queries**: Unindexed SKU lookups
3. **Network latency**: Docker → Host communication

### Optimization Strategies

1. **Add Redis caching**: Cache market data for 5-10 minutes
2. **Database indexes**: Add index on `catalog.products.sku`
3. **Batch processing**: Process multiple SKUs in parallel
4. **CDN for static data**: Cache product metadata

## 🚀 Future Enhancements

### Planned Features

1. **Discord Bot Integration**
   - Replace Chat Trigger with Discord Trigger
   - Support slash commands: `/profit check KI6956 129.95`
   - Multi-server support

2. **Slack Integration**
   - Team notifications for high-margin opportunities
   - Daily digest of profitable products

3. **Automated Alerts**
   - Monitor price changes
   - Notify when margin exceeds threshold
   - Email/SMS alerts for hot deals

4. **Bulk Analysis**
   - Upload CSV with SKUs
   - Batch process 100+ products
   - Export results to spreadsheet

5. **Historical Tracking**
   - Store profit calculations in database
   - Track margin trends over time
   - Predict optimal buy/sell timing

6. **Multi-Currency Support**
   - Auto-detect user region
   - Show prices in local currency
   - Consider currency conversion fees

7. **Advanced Filtering**
   - Filter by size availability
   - Exclude certain brands/categories
   - Set minimum margin threshold

## 📚 Related Documentation

### Internal Docs
- `/docs/guides/stockx_auth_setup.md` - StockX API authentication
- `/docs/guides/database_migration.md` - Database schema management
- `CLAUDE.md` - Project development guidelines

### External Resources
- [n8n Documentation](https://docs.n8n.io)
- [n8n Workflow Templates](https://n8n.io/workflows)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [PostgreSQL Docs](https://www.postgresql.org/docs)

## 🤝 Contributing

### Adding New Workflows

1. Create workflow in n8n UI
2. Export as JSON
3. Save to this directory: `n8n-workflows/workflow-name.json`
4. Add documentation in this README
5. Create setup guide if complex
6. Test thoroughly before committing

### Workflow Naming Convention

```
{purpose}-{action}.json

Examples:
- stockx-profit-checker.json
- inventory-sync.json
- price-alert-monitor.json
- order-status-tracker.json
```

### Documentation Standards

Each workflow should have:
- ✅ Purpose and features description
- ✅ Input/output specifications
- ✅ Setup instructions
- ✅ Configuration options
- ✅ Testing procedures
- ✅ Troubleshooting guide

## 🔐 Security Considerations

### Best Practices

1. **Never commit secrets**: Use n8n credentials system
2. **Validate inputs**: Sanitize SKU and price inputs
3. **Rate limiting**: Add rate limiter for public chat
4. **Authentication**: Use Basic Auth or n8n User Auth for production
5. **Error messages**: Don't expose internal system details

### Production Checklist

- [ ] Enable authentication on Chat Trigger
- [ ] Set up HTTPS/SSL certificates
- [ ] Configure rate limiting
- [ ] Enable logging and monitoring
- [ ] Restrict network access (firewall rules)
- [ ] Regular security updates
- [ ] Backup workflow configurations

## 📞 Support

### Getting Help

1. **Check documentation**: SETUP_GUIDE.md and QUICK_START.md
2. **View logs**: `docker-compose logs -f`
3. **Test API**: Use `/docs` endpoint for interactive testing
4. **n8n Forum**: https://community.n8n.io
5. **GitHub Issues**: Report bugs and feature requests

### Workflow Issues

- **Parse errors**: Check message format matches expected pattern
- **API errors**: Verify service health and connectivity
- **Performance issues**: Check database indexes and caching
- **Deployment issues**: Review Docker logs and network configuration

---

**Maintained by**: SoleFlip Development Team
**Last Updated**: 2025-11-19
**Version**: 1.0
**License**: Internal Use
