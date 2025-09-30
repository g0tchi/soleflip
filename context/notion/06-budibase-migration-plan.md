# Budibase Migration Plan: Replacing Notion as Data Entry UI

**Created:** 2025-09-30
**Status:** Strategic Planning Document
**Target Date:** Q1 2025 Completion
**Priority:** High

## Strategic Context

### Why Migrate from Notion?

**Current Pain Points:**
1. **External Dependency:** Notion is 3rd-party SaaS, subject to pricing changes and outages
2. **Monthly Cost:** Ongoing subscription fees for Notion workspace
3. **API Limitations:** Rate limits, webhook reliability issues
4. **Data Sovereignty:** Data stored in Notion's infrastructure, not self-hosted
5. **Integration Complexity:** Requires MCP integration layer, additional abstraction
6. **Vendor Lock-in:** Difficult to migrate historical data out of Notion format

**Self-Hosted Stack Benefits:**
1. **Cost Savings:** One-time setup vs monthly Notion subscription
2. **Full Control:** Self-hosted on NAS/server, complete data ownership
3. **Direct PostgreSQL Integration:** No sync layer needed
4. **Customization:** Unlimited UI/UX customization
5. **Performance:** LAN-speed access, no internet dependency
6. **Scalability:** No per-user pricing, unlimited seats

### Target Architecture: B-M-N Stack

**B**udibase (Data Entry UI) + **M**etabase (Analytics) + **n8n** (Automation)

```
┌─────────────────────────────────────────────────────────────┐
│                    Self-Hosted Stack (B-M-N)                 │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Budibase   │    │   Metabase   │    │      n8n     │
│  Port 6400   │    │  Port 3000   │    │  Port 5678   │
│              │    │              │    │              │
│ • Sale Forms │    │ • Dashboards │    │ • Workflows  │
│ • Supplier   │    │ • KPIs       │    │ • StockX API │
│ • Inventory  │    │ • Reports    │    │ • Scheduling │
│ • Orders     │    │ • Analytics  │    │ • Alerts     │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       │ Direct Write      │ Read Only         │ Read/Write
       └───────────────────┼───────────────────┘
                           ↓
                  ┌─────────────────┐
                  │   PostgreSQL    │
                  │  NAS (10.0.0.2) │
                  │                 │
                  │ Single Source   │
                  │   of Truth      │
                  └─────────────────┘
```

## Migration Phases

### Phase 0: FAST TRACK - Historical Data Migration (Day 1-2) ⚡

**SHORTCUT:** We already have a working sync script from the successful test!

**File:** `bulk_sync_notion_sales.py`

This script reuses the proven logic from `insert_stockx_sale_55476797.py` and extends it for bulk processing:

#### What It Does:
1. **Searches Notion** for all sales with "Sale Platform = StockX"
2. **Duplicate Detection** - Skips already-synced sales
3. **StockX Enrichment** - Gets real Product ID from `/api/v1/products/search-stockx`
4. **Complete Entity Creation:**
   - Suppliers (get or create)
   - Products (get or create)
   - Sizes (get or create)
   - Inventory items
   - StockX listings
   - StockX orders
5. **Progress Tracking** - Detailed stats and logging

#### Usage:
```bash
# Start API server first (for StockX Product ID lookup)
uvicorn main:app --reload

# Run bulk sync (separate terminal)
python bulk_sync_notion_sales.py
```

#### Expected Output:
```
Starting bulk Notion sales sync...
Found 347 sales in Notion

Syncing sale: 55476797-55376556 (HQ4276)
  ✓ Supplier: 43einhalb
  ✓ Product: Adidas HQ4276
  ✓ StockX Product ID: fa671f11-b94d-4596-a4fe-d91e0bd995a0
  ✓ Order created

Syncing sale: 55482891-55383221 (DZ5485-612)
  ✓ Supplier: Footlocker (created)
  ✓ Product: Nike DZ5485-612 (created)
  ✓ StockX Product ID: 8a34f2c1-9b4d-4321-a1fe-e82d9bd123a0
  ✓ Order created

...

================================================================================
BULK SYNC SUMMARY
================================================================================
Total sales found in Notion:  347
Already synced (skipped):     1
Newly synced:                 342
Failed:                       4
New suppliers created:        12
New products created:         238
================================================================================

Success Rate: 98.6%
```

#### Time Savings:
- **Before:** Week 1 (40 hours) building service layer
- **After:** Day 1-2 (4 hours) adapting existing script
- **Savings:** 36 hours = €1,800 (at €50/hour)

#### Next Step (Replace Notion MCP Mock):
Currently uses mock data. To sync real Notion data, replace line 237-260 with:
```python
# Real Notion MCP integration
from mcp import notion_client

notion_sales = await notion_client.query_database(
    database_id="YOUR_NOTION_SALES_DB_ID",
    filter={
        "property": "Sale Platform",
        "select": {"equals": "StockX"}
    }
)
```

**Result:** All historical Notion data in PostgreSQL within 2 days instead of 1 week! 🚀

### Phase 1: Setup Budibase (Week 1-2)

#### Installation & Configuration
```bash
# Docker Compose for Budibase (already in docker-compose.yml)
services:
  budibase:
    image: budibase/budibase:latest
    ports:
      - "6400:80"
    environment:
      - POSTGRES_HOST=10.0.0.2
      - POSTGRES_PORT=5432
      - POSTGRES_DB=soleflip
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - BUDIBASE_ENVIRONMENT=production
    volumes:
      - budibase_data:/data
    restart: unless-stopped
```

#### Database Connection Setup
1. Add PostgreSQL data source in Budibase
2. Configure connection with read/write permissions
3. Test connectivity to all schemas (core, products, platforms, analytics)
4. Set up database roles/permissions for security

#### Initial Screen Development

**Screen 1: Sale Entry Form**
```
┌────────────────────────────────────────────────────┐
│  📦 New Sale Entry                          [Save] │
├────────────────────────────────────────────────────┤
│                                                    │
│  StockX Order Number: [___________________]       │
│                                                    │
│  Product (SKU):      [▼ HQ4276 - Adidas...]       │
│                      ↑ Dropdown from products     │
│                                                    │
│  Size:              [▼ US 8.5        ]            │
│                      ↑ Filtered by category       │
│                                                    │
│  Supplier:          [▼ 43einhalb     ]            │
│                      ↑ Autocomplete               │
│                                                    │
│  Purchase Details:                                │
│  ├─ Net Buy:        [€ 23.53  ]                  │
│  ├─ Gross Buy:      [€ 28.00  ] (incl. VAT)      │
│  └─ Purchase Date:  [📅 2023-08-27]              │
│                                                    │
│  Sale Details:                                    │
│  ├─ Net Sale:       [€ 24.07  ]                  │
│  ├─ Sale Date:      [📅 2023-09-17]              │
│  └─ Profit:         € 0.54 (auto-calc)           │
│                                                    │
│  ROI: 2.3% ✅                    Shelf Life: 17d  │
│                                                    │
└────────────────────────────────────────────────────┘
```

**Key Features:**
- **SKU Dropdown:** Populated from `products.products` table
- **Size Dropdown:** Dynamically filtered by product category
- **Supplier Autocomplete:** Search from `core.suppliers`
- **Auto-Calculations:**
  - `profit = net_sale - net_buy`
  - `roi = (profit / net_buy) * 100`
  - `shelf_life = sale_date - purchase_date (days)`
- **Validation Rules:**
  - StockX Order Number unique (check duplicates)
  - Sale date >= Purchase date
  - Profit calculation matches input
  - All required fields filled

**Screen 2: Sales List View**
```
┌────────────────────────────────────────────────────────────┐
│  📊 All Sales                    [🔍 Search] [+ New Sale]  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Filters: [All Suppliers ▼] [Last 30 Days ▼] [All SKUs ▼] │
│                                                            │
│  ┌──────────┬─────────┬──────────┬─────────┬──────────┐   │
│  │ Order #  │ SKU     │ Supplier │ Profit  │ Status   │   │
│  ├──────────┼─────────┼──────────┼─────────┼──────────┤   │
│  │ 55476... │ HQ4276  │ 43einh.. │ €0.54   │ ✅ Paid  │   │
│  │ 55482... │ DZ5485  │ Foot... │ €12.30  │ ✅ Paid  │   │
│  │ 55491... │ FB9922  │ ASOS    │ €-2.10  │ ⚠️ Loss  │   │
│  └──────────┴─────────┴──────────┴─────────┴──────────┘   │
│                                                            │
│  Total Profit: €245.80     Avg ROI: 8.3%    Total: 47     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Features:**
- Paginated table from `platforms.stockx_orders` JOIN inventory
- Real-time search & filters
- Click row to view/edit details
- Export to CSV functionality
- Bulk actions (delete, mark as paid)

**Screen 3: Supplier Management**
```
┌────────────────────────────────────────────────────┐
│  🏪 Suppliers                        [+ Add New]   │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌────────────┬──────────┬─────────┬──────────┐   │
│  │ Name       │ Type     │ Orders  │ Avg ROI  │   │
│  ├────────────┼──────────┼─────────┼──────────┤   │
│  │ 43einhalb  │ Retail   │ 87      │ 6.2%     │   │
│  │ Footlocker │ Retail   │ 124     │ 8.7%     │   │
│  │ ASOS       │ Outlet   │ 43      │ 3.1%     │   │
│  └────────────┴──────────┴─────────┴──────────┘   │
│                                                    │
└────────────────────────────────────────────────────┘
```

### Phase 2: Budibase ↔ PostgreSQL Integration (Week 3-4)

#### Database Triggers for n8n Automation

**Create PostgreSQL Trigger:**
```sql
-- Trigger to notify n8n when new sale created
CREATE OR REPLACE FUNCTION notify_new_sale()
RETURNS TRIGGER AS $$
BEGIN
    -- Send notification to n8n via pg_notify
    PERFORM pg_notify(
        'new_sale_created',
        json_build_object(
            'order_number', NEW.stockx_order_number,
            'product_id', NEW.listing_id,
            'created_at', NEW.created_at
        )::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER new_sale_trigger
AFTER INSERT ON platforms.stockx_orders
FOR EACH ROW
EXECUTE FUNCTION notify_new_sale();
```

#### n8n Workflow: PostgreSQL Trigger → StockX Enrichment

**Workflow Steps:**
1. **PostgreSQL Trigger Node:** Listen to `new_sale_created` channel
2. **Get Sale Details:** Query full sale data from DB
3. **StockX Product Search:** Get Product ID via SKU
4. **Update Listing:** Set real StockX Product ID (replace placeholder)
5. **Fetch Market Data:** Get current prices for analytics
6. **Update Marketplace Data:** Insert into `analytics.marketplace_data`
7. **Send Notification:** Slack message with sale summary

**n8n Configuration:**
```json
{
  "nodes": [
    {
      "name": "PostgreSQL Trigger",
      "type": "n8n-nodes-base.postgresTrigger",
      "parameters": {
        "host": "10.0.0.2",
        "database": "soleflip",
        "channel": "new_sale_created"
      }
    },
    {
      "name": "Get Sale Data",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT * FROM platforms.stockx_orders WHERE stockx_order_number = $1::stockx_order_number"
      }
    },
    {
      "name": "StockX Product Search",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "GET",
        "url": "http://localhost:8000/api/v1/products/search-stockx",
        "qs": {
          "query": "={{ $json.sku }}"
        }
      }
    },
    {
      "name": "Update StockX Product ID",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "operation": "update",
        "table": "platforms.stockx_listings",
        "updateKey": "stockx_listing_id",
        "columns": "stockx_product_id"
      }
    },
    {
      "name": "Slack Notification",
      "type": "n8n-nodes-base.slack",
      "parameters": {
        "channel": "#sales-alerts",
        "text": "✅ New Sale: {{ $json.sku }} - Profit: €{{ $json.profit }}"
      }
    }
  ]
}
```

### Phase 3: User Migration (Week 5-6)

#### Training Materials

**User Guide: Budibase vs Notion Comparison**

| Feature | Notion (Old) | Budibase (New) |
|---------|--------------|----------------|
| **Access URL** | notion.so/workspace | http://10.0.0.2:6400 |
| **Data Entry** | Notion database form | Budibase custom form |
| **Auto-Complete** | Limited | Full autocomplete |
| **Validation** | Manual | Automatic (real-time) |
| **Speed** | Internet-dependent | LAN-speed (instant) |
| **Offline Access** | ❌ No | ✅ Yes (PWA) |
| **Mobile Access** | ✅ Yes | ✅ Yes (responsive) |

#### Migration Checklist

**Week 5: Alpha Users (3-5 users)**
- [ ] Select power users for alpha testing
- [ ] 1-hour training session (screen sharing)
- [ ] Test 10 real sales in Budibase
- [ ] Collect feedback (form + interview)
- [ ] Fix critical UI/UX issues
- [ ] Verify data accuracy in PostgreSQL

**Week 6: Beta Rollout (All Users)**
- [ ] Deploy fixes from alpha feedback
- [ ] Send migration announcement email
- [ ] Schedule team training session (30 min)
- [ ] Distribute quick reference guide (PDF/Video)
- [ ] Enable Budibase for all users
- [ ] Monitor Slack for questions/issues
- [ ] Keep Notion read-only as backup

**Week 7: Full Cutover**
- [ ] 100% of new sales via Budibase
- [ ] Disable Notion write access (read-only)
- [ ] Monitor error rates (should be <1%)
- [ ] Address remaining feedback
- [ ] Celebrate migration success! 🎉

### Phase 4: Notion Data Archive (Week 8)

#### Historical Data Export

**Export All Notion Sales to CSV:**
```python
# scripts/export_notion_historical_sales.py
"""
Export all Notion sales to CSV for archival
Then verify all data exists in PostgreSQL
"""
import asyncio
import csv
from datetime import datetime

async def export_notion_to_csv():
    # Use Notion MCP to fetch all sales
    all_sales = await notion_client.query_database(
        database_id="YOUR_SALES_DB_ID",
        page_size=100  # Paginate
    )

    # Write to CSV
    with open('notion_sales_archive_2025-09-30.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'order_number', 'sku', 'supplier', 'net_buy', 'net_sale',
            'profit', 'roi', 'purchase_date', 'sale_date'
        ])
        writer.writeheader()

        for sale in all_sales:
            writer.writerow({
                'order_number': sale['properties']['Sale ID']['title'][0]['text']['content'],
                'sku': sale['properties']['Name']['title'][0]['text']['content'],
                # ... extract all fields
            })

    print(f"✅ Exported {len(all_sales)} sales to CSV")
    print(f"File: notion_sales_archive_2025-09-30.csv")
    print(f"Size: {os.path.getsize('notion_sales_archive_2025-09-30.csv') / 1024:.2f} KB")

if __name__ == "__main__":
    asyncio.run(export_notion_to_csv())
```

**Verify Data Completeness:**
```sql
-- Compare Notion export count vs PostgreSQL count
SELECT COUNT(*) as pg_sales FROM platforms.stockx_orders;
-- Expected: Should match CSV row count

-- Check for missing orders
-- (Cross-reference CSV order numbers with DB)
```

**Archive Notion Workspace:**
1. Export full Notion workspace (Settings → Export all workspace content)
2. Download as Markdown & CSV (includes all pages, databases, files)
3. Store backup on NAS: `/backups/notion_workspace_2025-09-30.zip`
4. Keep Notion workspace in read-only mode for 3 months
5. After 3 months: Cancel Notion subscription

### Phase 5: Enhancements (Week 9+)

#### Advanced Budibase Features

**1. Auto-Listing Workflow Integration**
- Button in sale form: "🚀 List on StockX"
- Triggers n8n workflow to create listing via StockX API
- Pre-fills price from smart pricing algorithm
- Shows current market price (Lowest Ask)

**2. Supplier Performance Dashboard**
```
┌────────────────────────────────────────────────────┐
│  📈 Supplier ROI Comparison                        │
├────────────────────────────────────────────────────┤
│                                                    │
│  🥇 43einhalb        8.7% ROI   (87 orders)        │
│  🥈 Footlocker       7.2% ROI   (124 orders)       │
│  🥉 ASOS             3.1% ROI   (43 orders)        │
│                                                    │
│  ⚠️  Low Performers:                               │
│  • Nike.com         -1.2% ROI   (15 orders)        │
│  • Zalando           0.8% ROI   (22 orders)        │
│                                                    │
│  💡 Recommendation: Focus on 43einhalb & Footlocker│
└────────────────────────────────────────────────────┘
```

**3. Dead Stock Alerts**
- Query inventory for items unsold > 90 days
- Display in Budibase dashboard
- Auto-suggest price reduction (15% below market)
- Button to auto-list at reduced price

**4. Profit Calculator**
- Side panel widget in sale entry form
- Input: Purchase price
- Output: Recommended listing price (target 10% ROI)
- Shows StockX fees, shipping costs
- Real-time market data

**5. Mobile PWA**
- Install Budibase as Progressive Web App
- Offline data entry (sync when back online)
- Barcode scanner for SKU input
- Photo upload for product condition

## Cost-Benefit Analysis

### Costs

**One-Time Implementation Costs:**
| Item | Effort | Cost |
|------|--------|------|
| Budibase setup & screens | 16 hours | €800 |
| PostgreSQL triggers | 4 hours | €200 |
| n8n workflow configuration | 8 hours | €400 |
| User training & docs | 4 hours | €200 |
| Testing & QA | 8 hours | €400 |
| **Total One-Time** | **40 hours** | **€2,000** |

**Ongoing Costs:**
| Item | Frequency | Cost/Year |
|------|-----------|-----------|
| NAS hosting (electricity) | Monthly | €50 |
| Server maintenance | Quarterly | €100 |
| **Total Annual** | - | **€150** |

### Savings

**Notion Subscription Savings:**
- Current: €10/user/month × 5 users = €50/month
- Annual: €50 × 12 = **€600/year saved**

**Time Savings:**
- Manual data entry: 15 min/sale → 5 min/sale
- Monthly sales: ~50 sales
- Time saved: 10 min × 50 = **500 min/month = 8.3 hours/month**
- Annual value: 8.3 hours × 12 × €50/hour = **€4,980/year saved**

**Total Annual Savings:** €600 + €4,980 = **€5,580/year**

**Break-Even:** €2,000 / €5,580 = **4.3 months**

**3-Year ROI:** (€5,580 × 3) - €2,000 - (€150 × 3) = **€14,290 net profit**

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Budibase downtime | Low | Medium | Self-hosted on stable NAS, easy to restart |
| PostgreSQL data loss | Very Low | Critical | Daily automated backups to external drive |
| User adoption resistance | Medium | Medium | Thorough training, gradual migration |
| n8n workflow failure | Low | Low | Retry logic, Slack alerts, manual fallback |
| Data sync issues | Low | Medium | Validation scripts, monitoring dashboards |

### Rollback Plan

**If migration fails (Week 6-7):**
1. Immediately re-enable Notion write access
2. Notify users to revert to Notion
3. Debug Budibase/PostgreSQL issues
4. Fix issues in staging environment
5. Retry migration in 2 weeks

**Notion remains active for 3 months as safety net.**

## Success Criteria

**Phase 1 Success (Week 4):**
- [ ] Notion webhook syncs 100% of sales to PostgreSQL
- [ ] Zero data loss or corruption
- [ ] Sync latency < 2 minutes
- [ ] Metabase dashboards show real-time data

**Phase 2 Success (Week 8):**
- [ ] Budibase forms functional for all use cases
- [ ] 100% of users trained and migrated
- [ ] Zero critical bugs in production
- [ ] User satisfaction > 80% (survey)
- [ ] Data accuracy 100% (PostgreSQL matches Notion)

**Phase 3 Success (Week 12+):**
- [ ] Notion subscription cancelled
- [ ] All historical data archived securely
- [ ] No user complaints about missing features
- [ ] Performance improvements documented
- [ ] Cost savings realized (€600/year)

## Technical Dependencies

### Required Infrastructure
- [x] PostgreSQL database (soleflip) - Already running on NAS
- [x] Budibase container - Already in docker-compose.yml
- [x] n8n container - Already running (port 5678)
- [x] Metabase container - Already running (port 6400)
- [ ] PostgreSQL LISTEN/NOTIFY support (requires pg_notify extension)

### API Endpoints Required
- [x] `/api/v1/products/search-stockx` - Already implemented
- [x] `/api/v1/integration/sale/sync` - Needs implementation (Week 1)
- [ ] `/api/v1/integration/budibase/webhook` - New endpoint (Week 5)

### Database Schema Requirements
- [x] `platforms.stockx_orders` - Already exists
- [x] `products.inventory` - Already exists
- [x] `core.suppliers` - Already exists
- [x] `core.sizes` - Already exists
- [ ] `integration.sale_sync_log` - Migration needed (Week 1)
- [ ] PostgreSQL triggers - Migration needed (Week 3)

## Monitoring & Maintenance

### Daily Checks (Automated)
- Budibase container health check
- PostgreSQL connection test
- n8n workflow execution count
- Data sync success rate

### Weekly Reviews
- User feedback collection (Slack)
- Error log review (identify patterns)
- Performance metrics (response times)
- Backup verification (test restore)

### Monthly Reports
- Sales entry count (Budibase vs historical)
- Time savings measurement
- Cost savings validation
- Feature requests prioritization

## Future Enhancements (Beyond Migration)

### Quarter 2 2025
- [ ] Budibase mobile app optimization
- [ ] Advanced analytics dashboards (Metabase)
- [ ] Auto-pricing algorithm integration
- [ ] Bulk CSV import via Budibase
- [ ] Supplier performance recommendations

### Quarter 3 2025
- [ ] Multi-marketplace support (GOAT, eBay, Klekt)
- [ ] Inventory forecasting (ML-based)
- [ ] Automated reordering from top suppliers
- [ ] Profit optimization engine
- [ ] Public API for external integrations

## Conclusion

The migration from Notion to the self-hosted B-M-N stack (Budibase + Metabase + n8n) is a **strategic investment** with clear benefits:

✅ **Cost Savings:** €5,580/year recurring
✅ **Data Sovereignty:** Full control over business data
✅ **Performance:** LAN-speed access, no internet dependency
✅ **Scalability:** Unlimited users, no per-seat pricing
✅ **Customization:** Tailored UI/UX for specific workflows
✅ **Integration:** Direct PostgreSQL access, no sync layer

**Recommended Timeline:** 10-12 weeks total
**Break-Even Point:** 4.3 months
**3-Year ROI:** €14,290 net profit

**Next Step:** Begin Phase 1 implementation (Notion Bridge) to validate architecture before full migration.

---

**Document Owner:** Engineering Team
**Last Updated:** 2025-09-30
**Related Documents:**
- `automation-strategy-notion-stockx-sync.md` (Phase 1 implementation)
- `stockx-product-search-api-discovery.md` (API capabilities)
- `notion-stockx-sale-integration-test.md` (Proof of concept)