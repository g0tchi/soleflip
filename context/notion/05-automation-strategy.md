# Automation Strategy: StockX Sale Data Integration

**Created:** 2025-09-30
**Updated:** 2025-09-30
**Status:** Design Document
**Priority:** High

## Executive Summary

Based on the successful manual integration test (see `notion-stockx-sale-integration-test.md`), this document outlines a production-ready automation strategy for syncing StockX sales to PostgreSQL.

**Strategic Vision:** Migrate away from Notion dependency towards a self-hosted stack (Metabase + Budibase + n8n + PostgreSQL).

**Short-Term Goal (Phase 1):** Bridge existing Notion data to PostgreSQL while maintaining backward compatibility.

**Long-Term Goal (Phase 2-3):** Replace Notion with Budibase as primary data entry interface, making PostgreSQL the single source of truth.

## Current Manual Process (Tested Successfully)

1. Search Notion for sale by StockX Order Number
2. Extract supplier, purchase price, sale data
3. Query StockX API for product details
4. Create database entities in correct order:
   - Supplier (if new)
   - Size (if new)
   - Inventory item
   - StockX listing
   - StockX order
5. Update StockX Product ID from API

**Time Investment:** ~15-20 minutes per sale (manual)
**Error Rate:** High (schema complexity, FK constraints)
**Scalability:** Not feasible for bulk imports

## Migration Strategy: 3-Phase Approach

### Phase 1: Notion Bridge (Weeks 1-4) - CURRENT
**Goal:** Sync existing Notion sales to PostgreSQL without disrupting current workflow
**Status:** Temporary solution during migration period

**Components:**
- Notion MCP integration (read-only)
- n8n workflows for Notion webhooks
- PostgreSQL as primary data store
- Metabase for reporting (replaces Notion dashboards)

**User Flow:**
- Users continue entering sales in Notion
- n8n automatically syncs to PostgreSQL
- Metabase dashboards show real-time PostgreSQL data
- **Duration:** 1-2 months (parallel running)

### Phase 2: Budibase Data Entry (Weeks 5-8)
**Goal:** Replace Notion forms with Budibase UI for new sales entry
**Status:** Next implementation phase

**Components:**
- Budibase forms connected directly to PostgreSQL
- n8n workflows for StockX API enrichment (triggered by PostgreSQL insert)
- Gradual user migration from Notion → Budibase
- Notion remains read-only for historical data

**User Flow:**
- New sales entered via Budibase interface
- Direct write to PostgreSQL (no Notion middleman)
- n8n enriches data from StockX API
- Metabase shows unified view (historical + new)
- **Duration:** 1 month (user training + migration)

### Phase 3: Notion Deprecation (Week 9+)
**Goal:** Complete independence from Notion
**Status:** Future state

**Components:**
- Budibase as sole data entry UI
- PostgreSQL as single source of truth
- n8n for all automation workflows
- Metabase for analytics & reporting
- Historical Notion data archived in PostgreSQL

**User Flow:**
- All operations via Budibase
- Notion workspace archived/read-only
- No ongoing Notion subscription needed
- **Duration:** Ongoing maintenance mode

## Architecture Comparison

### Current State (Notion-Dependent)
```
┌─────────────┐
│   Notion    │  ← Users enter data here
│  (External) │  ← Monthly subscription cost
└──────┬──────┘
       │ Webhook
       ↓
┌─────────────┐     ┌──────────────┐
│     n8n     │────→│  PostgreSQL  │
│  (Sync)     │     │  (Mirror)    │
└─────────────┘     └──────────────┘
```

### Target State (Self-Hosted)
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Budibase   │────→│  PostgreSQL  │←────│     n8n     │
│  (Data UI)  │     │   (Source)   │     │ (Workflows) │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │                      ↑
                           ↓                      │
                    ┌──────────────┐     ┌───────┴──────┐
                    │   Metabase   │     │  StockX API  │
                    │ (Analytics)  │     │ (Enrichment) │
                    └──────────────┘     └──────────────┘
```

## Phase 1 Implementation: Notion Bridge (RECOMMENDED FOR NOW)

### Option 1: Event-Driven Webhook

**Trigger:** Notion page created/updated webhook → n8n workflow → FastAPI endpoint
**Purpose:** Temporary bridge during migration period

**Advantages:**
- Real-time sync (< 1 minute latency)
- No polling overhead
- Event-driven architecture aligns with existing system
- n8n already deployed (port 5678)

**Architecture Flow:**
```
┌──────────────┐      Webhook       ┌──────────────┐
│    Notion    │ ───────────────→   │     n8n      │
│  New Sale    │                    │   Workflow   │
└──────────────┘                    └──────┬───────┘
                                           │ HTTP POST
                                           ↓
                                    ┌──────────────┐
                                    │   FastAPI    │
                                    │   Endpoint   │
                                    │ /integration │
                                    │ /notion-sale │
                                    └──────┬───────┘
                                           │
                        ┌──────────────────┼──────────────────┐
                        ↓                  ↓                  ↓
                 ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
                 │   Notion    │   │   StockX    │   │  PostgreSQL │
                 │  MCP Read   │   │  API Query  │   │   Insert    │
                 └─────────────┘   └─────────────┘   └─────────────┘
```

**n8n Workflow Steps:**
1. **Notion Trigger** - Listen for database item created/updated
2. **Filter Node** - Only process sales with `Sale Platform = StockX`
3. **Extract Data** - Parse StockX Order Number, SKU, Supplier, Prices
4. **HTTP Request** - POST to `/api/v1/integration/notion-sale`
5. **Error Handler** - Log failures to Notion comments or Slack

**Implementation Effort:** 2-3 days
- n8n workflow configuration: 4 hours
- FastAPI endpoint development: 8 hours
- Testing & error handling: 4 hours

### Option 2: Scheduled Batch Sync

**Trigger:** Cron job every 15 minutes → Scan Notion for new sales → Process batch

**Advantages:**
- Simpler to implement
- No webhook configuration needed
- Batch processing can optimize database operations

**Disadvantages:**
- 15-minute sync delay
- Polling overhead (API rate limits)
- Potentially processes same sale multiple times

**Architecture Flow:**
```
┌──────────────┐
│  Cron Job    │  Every 15min
│  (Celery)    │
└──────┬───────┘
       │
       ↓
┌──────────────┐    Filter: last_edited_time     ┌──────────────┐
│ Notion Query │ ─────────────────────────────→  │ Recent Sales │
│ All Sales DB │    > last_sync_timestamp        │   (New/Mod)  │
└──────────────┘                                  └──────┬───────┘
                                                         │
                                                         ↓
                                                  ┌──────────────┐
                                                  │  Process Each│
                                                  │  Sale + Skip │
                                                  │  if exists   │
                                                  └──────────────┘
```

**Implementation Effort:** 1-2 days
- Background task service: 4 hours
- Celery beat schedule: 2 hours
- Duplicate detection logic: 2 hours

### Option 3: Hybrid Approach (BEST FOR PRODUCTION)

Combine both methods:
- **Webhook for new sales** (real-time)
- **Daily batch sync** (catches missed events, reconciliation)

**Advantages:**
- Real-time processing with safety net
- Handles webhook failures gracefully
- Daily reconciliation ensures data integrity

**Implementation Effort:** 3-4 days

## Recommended Implementation: Hybrid Approach

### Phase 1: Core Service Layer (Week 1)

**Create:** `domains/integration/services/notion_sale_sync_service.py`

```python
class NotionSaleSyncService:
    """
    Orchestrates Notion → PostgreSQL sale synchronization
    """

    async def sync_sale_by_order_number(
        self,
        stockx_order_number: str,
        force_update: bool = False
    ) -> SaleSyncResult:
        """
        Main sync method - idempotent and safe to retry

        Steps:
        1. Check if sale already exists in DB (skip if exists and not force_update)
        2. Fetch sale data from Notion MCP
        3. Enrich with StockX API data (Product ID, pricing validation)
        4. Validate data integrity (profit calc, date logic)
        5. Create/update database entities in transaction
        6. Return detailed sync result
        """
        pass

    async def _get_or_create_supplier(self, name: str, type: str) -> Supplier:
        """Get existing supplier or create new one"""
        pass

    async def _get_or_create_size(
        self,
        value: str,
        region: str,
        category_id: UUID
    ) -> Size:
        """Get existing size or create new one"""
        pass

    async def _create_inventory_item(
        self,
        product_id: UUID,
        size_id: UUID,
        supplier_id: UUID,
        purchase_price: Decimal,
        stockx_order_number: str
    ) -> InventoryItem:
        """Create inventory item with sold status"""
        pass

    async def _create_stockx_listing_and_order(
        self,
        product_id: UUID,
        stockx_order_number: str,
        stockx_product_id: str,
        sale_price: Decimal,
        net_proceeds: Decimal,
        profit: Decimal,
        roi: Decimal,
        sold_at: date
    ) -> tuple[StockXListing, StockXOrder]:
        """Create listing and order in single transaction"""
        pass

    async def validate_sale_data(self, data: dict) -> list[str]:
        """
        Validate sale data integrity
        Returns list of validation errors (empty if valid)
        """
        errors = []

        # Check profit calculation
        calculated_profit = data['net_sale'] - data['net_buy']
        if abs(calculated_profit - data['profit']) > 0.01:
            errors.append(f"Profit mismatch: {calculated_profit} vs {data['profit']}")

        # Check ROI calculation
        calculated_roi = (data['profit'] / data['net_buy'])
        if abs(calculated_roi - data['roi']) > 0.001:
            errors.append(f"ROI mismatch: {calculated_roi} vs {data['roi']}")

        # Check date logic
        if data.get('buy_date') and data.get('sale_date'):
            if data['buy_date'] >= data['sale_date']:
                errors.append("Buy date must be before sale date")

        return errors
```

**Key Design Principles:**
1. **Idempotency** - Safe to run multiple times, checks for existing data
2. **Transactional** - All-or-nothing database operations
3. **Validation** - Financial calculations verified before insert
4. **Logging** - Structured logs for audit trail
5. **Error Recovery** - Partial failures don't corrupt database

### Phase 2: API Endpoint (Week 1)

**Create:** `domains/integration/api/notion_sync_router.py`

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

router = APIRouter()

class NotionSaleWebhook(BaseModel):
    """Webhook payload from n8n/Notion"""
    stockx_order_number: str
    notion_page_id: str | None = None
    trigger: str  # 'webhook' or 'scheduled'

class SaleSyncResponse(BaseModel):
    success: bool
    stockx_order_number: str
    entities_created: dict[str, str]  # {entity_type: id}
    validation_warnings: list[str]
    sync_time_ms: int

@router.post(
    "/notion-sale/sync",
    response_model=SaleSyncResponse,
    summary="Sync Notion Sale to PostgreSQL",
)
async def sync_notion_sale(
    webhook: NotionSaleWebhook,
    background_tasks: BackgroundTasks,
    sync_service: NotionSaleSyncService = Depends(get_notion_sync_service),
):
    """
    Webhook endpoint called by n8n when new Notion sale detected

    Process:
    1. Validate webhook payload
    2. Trigger sync service (foreground for real-time, background for batch)
    3. Return sync result immediately
    4. Background task: Update Notion page with sync status
    """
    result = await sync_service.sync_sale_by_order_number(
        webhook.stockx_order_number
    )

    # Optional: Update Notion page with sync status
    if webhook.notion_page_id and result.success:
        background_tasks.add_task(
            update_notion_page_sync_status,
            webhook.notion_page_id,
            "✅ Synced to Database"
        )

    return result

@router.post(
    "/notion-sale/batch-sync",
    summary="Batch Sync Recent Notion Sales",
)
async def batch_sync_recent_sales(
    hours: int = 24,
    sync_service: NotionSaleSyncService = Depends(get_notion_sync_service),
):
    """
    Scheduled job endpoint - syncs all sales modified in last N hours
    Called by Celery beat or manual trigger
    """
    results = await sync_service.batch_sync_recent_sales(hours=hours)

    return {
        "total_found": len(results),
        "successful": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "results": results
    }
```

### Phase 3: n8n Workflow Configuration (Week 2)

**Workflow Name:** `Notion StockX Sale → PostgreSQL`

**Trigger Configuration:**
```json
{
  "nodes": [
    {
      "name": "Notion Trigger",
      "type": "n8n-nodes-base.notionTrigger",
      "parameters": {
        "databaseId": "YOUR_NOTION_SALES_DB_ID",
        "event": "created",
        "filters": {
          "property": "Sale Platform",
          "condition": "equals",
          "value": "StockX"
        }
      }
    },
    {
      "name": "Extract Fields",
      "type": "n8n-nodes-base.set",
      "parameters": {
        "values": {
          "stockx_order_number": "={{ $json.properties['Sale ID'].title[0].text.content }}",
          "sku": "={{ $json.properties.Name.title[0].text.content }}",
          "notion_page_id": "={{ $json.id }}"
        }
      }
    },
    {
      "name": "Call FastAPI Sync",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8000/api/v1/integration/notion-sale/sync",
        "jsonParameters": true,
        "options": {
          "timeout": 30000
        }
      }
    },
    {
      "name": "Update Notion Status",
      "type": "n8n-nodes-base.notion",
      "parameters": {
        "operation": "update",
        "pageId": "={{ $('Extract Fields').item.json.notion_page_id }}",
        "properties": {
          "Sync Status": {
            "type": "rich_text",
            "rich_text": [
              {
                "text": {
                  "content": "✅ Synced to Database"
                }
              }
            ]
          }
        }
      }
    },
    {
      "name": "Error Handler",
      "type": "n8n-nodes-base.slack",
      "parameters": {
        "channel": "#stockx-alerts",
        "text": "Sale sync failed: {{ $json.stockx_order_number }}\nError: {{ $json.error }}"
      }
    }
  ]
}
```

### Phase 4: Scheduled Batch Sync (Week 2)

**Create:** `domains/integration/tasks/notion_sync_tasks.py`

```python
from celery import shared_task
from shared.logging.logger import get_logger

logger = get_logger(__name__)

@shared_task(name="sync_recent_notion_sales", bind=True, max_retries=3)
def sync_recent_notion_sales(self, hours: int = 24):
    """
    Celery task: Sync all Notion sales modified in last N hours
    Runs daily at 2 AM as safety net for missed webhooks
    """
    try:
        from domains.integration.services.notion_sale_sync_service import get_notion_sync_service
        import asyncio

        sync_service = get_notion_sync_service()
        results = asyncio.run(
            sync_service.batch_sync_recent_sales(hours=hours)
        )

        logger.info(
            "Batch sync completed",
            total=len(results),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success)
        )

        return {
            "status": "success",
            "results": [r.dict() for r in results]
        }

    except Exception as e:
        logger.error("Batch sync failed", error=str(e))
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes
```

**Celery Beat Schedule:**
```python
# In shared/config/celery_config.py
CELERYBEAT_SCHEDULE = {
    'sync-notion-sales-daily': {
        'task': 'sync_recent_notion_sales',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        'args': (24,)  # Last 24 hours
    },
}
```

## Data Validation & Integrity

### Pre-Insert Validation Rules

1. **Duplicate Detection:**
   ```sql
   SELECT COUNT(*) FROM platforms.stockx_orders
   WHERE stockx_order_number = :order_number
   ```
   If exists: Skip or update based on `force_update` flag

2. **Financial Calculations:**
   ```python
   # Verify profit
   assert sale_price - purchase_price == profit, "Profit mismatch"

   # Verify ROI
   calculated_roi = (profit / purchase_price) * 100
   assert abs(calculated_roi - roi) < 0.1, "ROI mismatch"
   ```

3. **Date Logic:**
   ```python
   assert buy_date < sale_date, "Invalid date sequence"
   assert delivery_date >= buy_date, "Delivery before purchase"
   ```

4. **StockX Product ID Validation:**
   ```python
   # Always fetch from API, never use placeholder
   product_id = await stockx_service.get_product_id_by_sku(sku)
   if not product_id:
       raise ValueError(f"StockX Product ID not found for SKU: {sku}")
   ```

### Post-Insert Verification

**Create:** Database trigger or scheduled validation job

```sql
-- Check orphaned inventory items (no order)
SELECT i.id, i.product_id, i.external_ids->>'stockx_order_number' as order_num
FROM products.inventory i
LEFT JOIN platforms.stockx_orders o
    ON o.stockx_order_number = i.external_ids->>'stockx_order_number'
WHERE i.status = 'sold'
  AND o.id IS NULL;

-- Check profit calculation accuracy
SELECT
    o.stockx_order_number,
    o.sale_price,
    i.purchase_price,
    o.net_profit as stored_profit,
    (o.sale_price - i.purchase_price) as calculated_profit,
    ABS(o.net_profit - (o.sale_price - i.purchase_price)) as difference
FROM platforms.stockx_orders o
JOIN platforms.stockx_listings l ON o.listing_id = l.id
JOIN products.inventory i ON l.product_id = i.product_id
WHERE ABS(o.net_profit - (o.sale_price - i.purchase_price)) > 0.01;
```

## Error Handling Strategy

### Error Categories

1. **Notion Data Missing** (HTTP 404)
   - Log warning
   - Skip sale
   - Send notification to user

2. **StockX API Failure** (HTTP 502)
   - Retry 3 times with exponential backoff
   - Use placeholder Product ID if API unavailable
   - Schedule background job to update later

3. **Database Constraint Violation** (FK, NOT NULL)
   - Log full stack trace
   - Rollback transaction
   - Send alert to Slack #tech-alerts
   - Do NOT retry automatically (requires manual fix)

4. **Validation Errors** (Profit/ROI mismatch)
   - Log as WARNING (not ERROR)
   - Insert data anyway with warning flag
   - Add Notion comment: "⚠️ Data validation warning: {error}"

### Retry Policy

```python
# Webhook endpoint
@router.post("/notion-sale/sync")
async def sync_notion_sale(...):
    try:
        result = await sync_service.sync_sale_by_order_number(...)
        return result
    except StockXAPIException as e:
        # Retry in background after 5 minutes
        background_tasks.add_task(
            retry_sync_with_backoff,
            stockx_order_number,
            retry_count=0,
            max_retries=3
        )
        raise HTTPException(status_code=503, detail="StockX API unavailable, will retry")
    except Exception as e:
        logger.error("Sale sync failed", error=str(e), order=stockx_order_number)
        raise HTTPException(status_code=500, detail=str(e))
```

## Monitoring & Observability

### Metrics to Track

1. **Sync Success Rate:**
   ```python
   sync_success_total = Counter("notion_sale_sync_success", "Successful syncs")
   sync_failed_total = Counter("notion_sale_sync_failed", "Failed syncs")
   sync_duration_seconds = Histogram("notion_sale_sync_duration", "Sync duration")
   ```

2. **Data Quality Metrics:**
   - Validation warning count
   - Missing StockX Product ID count
   - Profit calculation mismatch count

3. **Performance Metrics:**
   - Average sync time per sale
   - Database transaction time
   - StockX API response time

### Logging Strategy

```python
logger.info(
    "Sale sync started",
    stockx_order_number=order_number,
    trigger="webhook",  # or "scheduled"
    notion_page_id=page_id
)

logger.info(
    "Sale sync completed",
    stockx_order_number=order_number,
    entities_created={
        "supplier": str(supplier_id),
        "size": str(size_id),
        "inventory": str(inventory_id),
        "listing": str(listing_id),
        "order": str(order_id)
    },
    sync_time_ms=elapsed_ms,
    validation_warnings=warnings
)
```

### Alerting Rules

**Slack Alerts:**
- Sync failure rate > 10% (last 1 hour)
- StockX API unavailable for > 15 minutes
- Database constraint violations

**Email Alerts (Critical):**
- Batch sync job failed 3 times consecutively
- More than 50 sales unsynced for > 24 hours

## Database Migration Requirements

### New Tables

**Create:** `integration.notion_sale_sync_log`
```sql
CREATE TABLE integration.notion_sale_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stockx_order_number VARCHAR(100) NOT NULL,
    notion_page_id VARCHAR(100),
    sync_status VARCHAR(20) NOT NULL,  -- 'success', 'failed', 'warning'
    trigger_type VARCHAR(20) NOT NULL,  -- 'webhook', 'scheduled', 'manual'
    entities_created JSONB,  -- {supplier_id, size_id, inventory_id, ...}
    validation_warnings TEXT[],
    error_message TEXT,
    sync_duration_ms INTEGER,
    synced_at TIMESTAMP NOT NULL DEFAULT NOW(),
    synced_by VARCHAR(100)  -- 'system', 'user_id'
);

CREATE INDEX idx_notion_sync_order ON integration.notion_sale_sync_log(stockx_order_number);
CREATE INDEX idx_notion_sync_status ON integration.notion_sale_sync_log(sync_status);
CREATE INDEX idx_notion_sync_date ON integration.notion_sale_sync_log(synced_at DESC);
```

### Schema Updates

**Update:** `products.inventory` - Add index for faster duplicate detection
```sql
CREATE INDEX idx_inventory_external_stockx_order
ON products.inventory USING GIN (external_ids);
```

**Update:** `platforms.stockx_orders` - Add unique constraint
```sql
ALTER TABLE platforms.stockx_orders
ADD CONSTRAINT uq_stockx_order_number UNIQUE (stockx_order_number);
```

## Testing Strategy

### Unit Tests

```python
# tests/integration/test_notion_sale_sync_service.py

async def test_sync_sale_creates_all_entities():
    """Test successful sync creates all required database entities"""
    service = NotionSaleSyncService()

    result = await service.sync_sale_by_order_number("55476797-55376556")

    assert result.success is True
    assert "supplier" in result.entities_created
    assert "inventory" in result.entities_created
    assert "order" in result.entities_created

async def test_sync_sale_skips_duplicate():
    """Test sync skips already-synced sale"""
    service = NotionSaleSyncService()

    # First sync
    result1 = await service.sync_sale_by_order_number("TEST-ORDER-001")
    assert result1.success is True

    # Second sync (should skip)
    result2 = await service.sync_sale_by_order_number("TEST-ORDER-001")
    assert result2.skipped is True
    assert result2.reason == "Sale already exists in database"

async def test_validation_catches_profit_mismatch():
    """Test validation detects incorrect profit calculation"""
    service = NotionSaleSyncService()

    invalid_data = {
        'net_buy': 100.00,
        'net_sale': 120.00,
        'profit': 25.00  # Should be 20.00
    }

    errors = await service.validate_sale_data(invalid_data)
    assert len(errors) > 0
    assert "profit mismatch" in errors[0].lower()
```

### Integration Tests

```python
# tests/integration/test_notion_api_integration.py

async def test_notion_mcp_connection():
    """Test Notion MCP can retrieve sale data"""
    # Uses real Notion connection
    result = await notion_client.search("55476797-55376556")
    assert len(result) > 0
    assert result[0]['properties']['Sale ID'] == "55476797-55376556"

async def test_stockx_api_product_search():
    """Test StockX API can retrieve product details"""
    # Uses real StockX API (with rate limiting)
    product = await stockx_service.search_product("HQ4276")
    assert product is not None
    assert product['id'] == "fa671f11-b94d-4596-a4fe-d91e0bd995a0"
```

### End-to-End Tests

```python
# tests/e2e/test_notion_sale_full_flow.py

async def test_full_sync_flow():
    """Test complete flow: Notion → API → Database → Verification"""
    # 1. Create test sale in Notion
    notion_page = await create_test_notion_sale(...)

    # 2. Trigger sync
    response = await client.post(
        "/api/v1/integration/notion-sale/sync",
        json={"stockx_order_number": "TEST-E2E-001"}
    )
    assert response.status_code == 200

    # 3. Verify database entities exist
    async with db_manager.get_session() as session:
        order = await session.execute(
            select(StockXOrder).where(
                StockXOrder.stockx_order_number == "TEST-E2E-001"
            )
        )
        assert order.scalar_one_or_none() is not None

    # 4. Cleanup
    await delete_test_notion_sale(notion_page.id)
```

## Performance Optimization

### Batch Processing Optimization

For large volumes (> 100 sales/day):

1. **Bulk Insert Strategy:**
   ```python
   # Instead of individual inserts
   async def batch_sync_sales(self, order_numbers: list[str]):
       """Process multiple sales in single transaction"""

       # Step 1: Fetch all data concurrently
       notion_data = await asyncio.gather(*[
           self.fetch_notion_data(order_num)
           for order_num in order_numbers
       ])

       # Step 2: Bulk insert suppliers (avoid duplicates)
       suppliers = await self._bulk_create_suppliers(
           [data['supplier'] for data in notion_data]
       )

       # Step 3: Bulk insert inventory + orders
       async with db_manager.get_session() as session:
           inventory_items = [
               InventoryItem(...) for data in notion_data
           ]
           session.add_all(inventory_items)
           await session.flush()

           orders = [
               StockXOrder(...) for data in notion_data
           ]
           session.add_all(orders)
           await session.commit()
   ```

2. **Database Connection Pooling:**
   - Increase pool size for sync operations: `pool_size=20`
   - Use separate connection pool for background jobs

3. **Caching:**
   ```python
   # Cache supplier/size lookups to avoid repeated DB queries
   @lru_cache(maxsize=1000)
   async def get_supplier_by_name(self, name: str) -> Supplier | None:
       # Cache results for 1 hour
       pass
   ```

## Rollout Plan: ACCELERATED Migration Timeline

### Phase 0: FAST TRACK - Historical Data Migration (Day 1-2) ⚡

**BREAKTHROUGH:** Reuse existing test script for bulk sync!

**File Created:** `bulk_sync_notion_sales.py`
- Extends proven `insert_stockx_sale_55476797.py` logic
- Adds bulk processing, duplicate detection, progress tracking
- Gets StockX Product ID from `/api/v1/products/search-stockx`

**Day 1: Bulk Sync Execution**
- [ ] Connect Notion MCP to script (replace mock data)
- [ ] Run: `python bulk_sync_notion_sales.py`
- [ ] Expected: 347 sales synced in ~10-15 minutes
- [ ] Monitor: Progress logs, error handling

**Day 2: Validation**
- [ ] Verify counts match (Notion vs PostgreSQL)
- [ ] Check StockX Product IDs (replace placeholders if needed)
- [ ] Spot-check financial calculations (profit, ROI)
- [ ] Generate summary report

**Time Savings:** Week 1 eliminated = 36 hours = €1,800 saved!

### Phase 1: Notion Bridge (Weeks 1-3) - SHORTENED

**Week 1: Real-Time Sync (n8n Webhook)**
- [ ] Configure n8n webhook (Notion → FastAPI)
- [ ] Create API endpoint `/api/v1/integration/sale/sync`
- [ ] Reuse `NotionSaleSyncService` from bulk script
- [ ] Test with 5 new sales

**Week 2: Integration & Testing**
- [ ] Configure n8n webhook workflow (Notion → FastAPI)
- [ ] Test end-to-end flow with 10 historical sales
- [ ] Set up monitoring dashboards (Metabase + Grafana)
- [ ] Configure Slack alerting

**Week 3: Batch Sync & Historical Data**
- [ ] Implement Celery scheduled task
- [ ] Bulk import all Notion historical sales (~500 sales)
- [ ] Performance optimization (if needed)
- [ ] Documentation for operations team

**Week 4: Production Rollout**
- [ ] Deploy to staging environment
- [ ] Run parallel processing (manual + automated) for 1 week
- [ ] Validate 100% data accuracy
- [ ] Go-live: Enable webhook for all new sales
- [ ] Monitor for 48 hours, rollback if issues

### Phase 2: Budibase Transition (Weeks 5-8)

**Week 5: Budibase UI Development**
- [ ] Design Budibase form for sale entry
  - SKU dropdown (from PostgreSQL products table)
  - Supplier autocomplete (from suppliers table)
  - Date pickers (purchase date, sale date)
  - Price inputs (net buy, gross sale, profit)
  - Auto-calculate ROI field
- [ ] Connect Budibase directly to PostgreSQL
- [ ] Test Budibase → PostgreSQL direct write
- [ ] Create user documentation

**Week 6: n8n Workflow Migration**
- [ ] Create n8n workflow: PostgreSQL Insert Trigger → StockX Enrichment
  - Listen to PostgreSQL trigger (new row in stockx_orders)
  - Query StockX API for product details
  - Update marketplace_data table
  - Send Slack notification on success/failure
- [ ] Test workflow with Budibase entries
- [ ] Configure error handling & retries

**Week 7: Parallel Running & User Training**
- [ ] Run Notion + Budibase in parallel
- [ ] Train team on Budibase interface
- [ ] Collect user feedback
- [ ] Fix UI/UX issues
- [ ] Compare data accuracy (Notion vs Budibase entries)

**Week 8: Migration & Validation**
- [ ] Migrate 50% of users to Budibase
- [ ] Monitor for issues
- [ ] Migrate remaining 50% of users
- [ ] Notion becomes read-only
- [ ] Validate all historical data visible in Metabase

### Phase 3: Notion Deprecation (Week 9+)

**Week 9: Final Cutover**
- [ ] Disable Notion webhooks
- [ ] Archive Notion workspace (export all data)
- [ ] Update all documentation to reference Budibase
- [ ] Remove Notion MCP integration code (mark as deprecated)
- [ ] Cancel Notion subscription (cost savings)

**Week 10+: Optimization & Enhancement**
- [ ] Optimize Budibase forms based on user feedback
- [ ] Add advanced Metabase dashboards
- [ ] Implement n8n automation workflows (auto-pricing, dead stock alerts)
- [ ] Performance tuning
- [ ] Monitoring & maintenance mode

## Success Metrics

**Target Performance:**
- Sync latency: < 30 seconds (webhook) or < 15 minutes (batch)
- Success rate: > 99%
- Data accuracy: 100% (profit/ROI calculations)
- API uptime: > 99.5%

**Cost Savings:**
- Manual time saved: ~15 min/sale → 0 min/sale
- Monthly volume: ~50 sales → 12.5 hours saved/month
- Error reduction: ~10% manual errors → < 1% automated errors

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Notion API rate limits | Medium | High | Implement exponential backoff, cache data |
| StockX API downtime | Low | Medium | Use placeholder IDs, update later via batch job |
| n8n webhook failures | Low | High | Daily batch sync as safety net |
| Database deadlocks | Low | Medium | Retry with jitter, use optimistic locking |
| Data validation errors | Medium | Low | Log warnings, insert data anyway with flag |

## Future Enhancements (Phase 2)

1. **ML-Powered Validation:**
   - Detect anomalies in pricing (profit too high/low)
   - Flag suspicious supplier prices
   - Predict shelf life based on historical data

2. **Real-Time Dashboard:**
   - Live sync status indicator in Notion
   - Daily summary email: "X sales synced, Y warnings"

3. **Historical Data Migration:**
   - Bulk import all historical Notion sales (2020-2024)
   - Estimated: ~500-1000 sales × 30 seconds = 4-8 hours

4. **Bidirectional Sync:**
   - PostgreSQL → Notion (update payout status, profit, ROI)
   - Keeps Notion as source of truth while DB is operational system

## Appendix: Manual Sync Script

For emergency manual sync or one-off imports:

```python
# scripts/manual_notion_sync.py
"""
Emergency manual sync script
Usage: python scripts/manual_notion_sync.py 55476797-55376556
"""
import sys
import asyncio
from domains.integration.services.notion_sale_sync_service import get_notion_sync_service

async def manual_sync(order_number: str):
    service = get_notion_sync_service()
    result = await service.sync_sale_by_order_number(
        order_number,
        force_update=True  # Override duplicate check
    )

    if result.success:
        print(f"SUCCESS: Sale {order_number} synced")
        print(f"Entities: {result.entities_created}")
    else:
        print(f"FAILED: {result.error_message}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manual_notion_sync.py <stockx_order_number>")
        sys.exit(1)

    asyncio.run(manual_sync(sys.argv[1]))
```

---

**Document Owner:** Engineering Team
**Last Updated:** 2025-09-30
**Status:** Ready for Implementation Review