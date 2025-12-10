# SoleFlip n8n Workflows

This directory contains production-ready n8n workflows for automating StockX data synchronization.

## Workflows

### `stockx-sync-workflow.json` - StockX Data Sync (Every 4 Hours)

**Purpose**: Automatically fetches and syncs StockX order data every 4 hours via the SoleFlip API.

**Schedule**: Runs every 4 hours (cron: `0 */4 * * *`)

**What it syncs**:
1. **Active Orders** ("listed" items) - All current listings on StockX
2. **Sold Orders** (recent historical) - Orders completed in the last 4 hours

**Workflow Steps**:

```
┌─────────────────┐
│ Every 4 Hours   │ ──► Cron Trigger (0 */4 * * *)
│ (Schedule)      │
└─────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Fetch Active Orders         │ ──► GET /api/v1/orders/active
│ (Listed Items)              │     • 60s timeout
│                             │     • 3 retries with exponential backoff
└─────────────────────────────┘     • Automatically syncs to database
         │
         ▼
┌─────────────────────────────┐
│ Orders Fetch Success?       │
│ (Check HTTP 200)            │
└─────────────────────────────┘
    │                    │
    │ Success            │ Error
    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│ Fetch Sold      │  │ Log Orders      │
│ Orders          │  │ Error           │
│ (Recent)        │  └─────────────────┘
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Sold Orders     │
│ Success?        │
└─────────────────┘
    │            │
    │ Success    │ Error
    ▼            ▼
┌──────────┐  ┌──────────┐
│ Log      │  │ Log Sold │
│ Success  │  │ Error    │
└──────────┘  └──────────┘
```

## Installation

### Option 1: Import via n8n UI (Recommended)
1. Open your n8n instance at `http://localhost:5678`
2. Click **"Import from File"**
3. Select `stockx-sync-workflow.json`
4. Activate the workflow

### Option 2: Import via n8n CLI
```bash
# Copy workflow to n8n workflows directory
cp workflows/stockx-sync-workflow.json ~/.n8n/workflows/

# Restart n8n
docker-compose restart n8n
```

### Option 3: Deploy via API (if n8n API is enabled)
```bash
# Set your n8n API credentials
export N8N_API_URL="http://localhost:5678"
export N8N_API_KEY="your-api-key"

# Deploy the workflow
curl -X POST "$N8N_API_URL/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @workflows/stockx-sync-workflow.json
```

## Configuration

### Environment Variables
The workflow uses internal Docker network hostnames. Ensure these services are accessible:

```yaml
# docker-compose.yml
services:
  soleflip-api:
    # ... API configuration
    networks:
      - soleflip-network

  n8n:
    # ... n8n configuration
    networks:
      - soleflip-network
```

### API Endpoints Used
- `http://soleflip-api:8000/api/v1/orders/active` - Fetches active orders (listed items)
- `http://soleflip-api:8000/api/v1/orders/stockx-history` - Fetches sold orders with date range

### Error Handling
The workflow includes production-ready error handling:

✅ **Automatic Retries**: HTTP requests retry 3 times with exponential backoff (5s, 10s, 20s)
✅ **Continue on Failure**: Workflow continues even if one step fails
✅ **Structured Logging**: All success/failure events logged with timestamps
✅ **Status Validation**: Checks HTTP 200 status before proceeding

### Logging Output

**Success Log**:
```json
{
  "timestamp": "2025-12-08T10:00:00.000Z",
  "workflow": "StockX Data Sync",
  "status": "success",
  "active_orders_count": 42,
  "sold_orders_count": 8,
  "message": "Data sync completed successfully"
}
```

**Error Log**:
```json
{
  "timestamp": "2025-12-08T10:00:00.000Z",
  "workflow": "StockX Data Sync",
  "status": "error",
  "error_message": "Connection timeout",
  "failed_step": "Active Orders",
  "status_code": 0
}
```

## Monitoring

### Check Workflow Status
```bash
# View n8n logs
docker-compose logs -f n8n

# Check last execution
curl http://localhost:5678/api/v1/executions?workflowId=<workflow-id>
```

### View Synced Data in Database
```sql
-- Check recent order syncs
SELECT
  source,
  COUNT(*) as order_count,
  MAX(created_at) as last_sync
FROM transactions.orders
WHERE created_at > NOW() - INTERVAL '4 hours'
GROUP BY source;

-- Check for sync errors
SELECT * FROM integration.awin_enrichment_jobs
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 10;
```

### Metrics to Monitor
- **Execution frequency**: Should run every 4 hours
- **Success rate**: Monitor via n8n execution history
- **Order counts**: Track active_orders_count and sold_orders_count
- **API response times**: Should be < 60s
- **Database write performance**: Check transactions.orders table growth

## Customization

### Change Schedule
Edit the cron expression in the "Every 4 Hours" node:

```json
{
  "parameters": {
    "rule": {
      "interval": [
        {
          "field": "cronExpression",
          "expression": "0 */4 * * *"  // Change this
        }
      ]
    }
  }
}
```

**Common cron patterns**:
- Every 2 hours: `0 */2 * * *`
- Every 6 hours: `0 */6 * * *`
- Daily at 3am: `0 3 * * *`
- Every 30 minutes: `*/30 * * * *`

### Add Notification on Error
Add a Slack/Email node after "Log Orders Error" and "Log Sold Error" nodes:

1. Add **Slack** or **Gmail** node
2. Connect from error logging nodes
3. Configure with error details from `$json`

### Extend Historical Window
Modify the date range in "Fetch Sold Orders" node:

```json
{
  "queryParameters": {
    "parameters": [
      {
        "name": "fromDate",
        "value": "={{ $now.minus(7, 'days').toFormat('yyyy-MM-dd') }}"  // 7 days instead of 4 hours
      }
    ]
  }
}
```

## Troubleshooting

### Workflow Not Running
1. **Check if workflow is active**: Toggle in n8n UI
2. **Verify cron schedule**: Check "Every 4 Hours" node settings
3. **Check n8n container status**: `docker-compose ps n8n`

### API Connection Failed
1. **Verify network connectivity**:
   ```bash
   docker exec n8n ping soleflip-api
   ```
2. **Check API health**:
   ```bash
   curl http://localhost:8000/health
   ```
3. **Verify Docker network**: Ensure both services in same network

### No Data Synced
1. **Check StockX credentials**: Verify in database `system_config` table
2. **Review API logs**: `docker-compose logs -f soleflip-api`
3. **Test API endpoint manually**:
   ```bash
   curl http://localhost:8000/api/v1/orders/active
   ```

### High Error Rate
1. **Check StockX API rate limits**: May need to reduce frequency
2. **Verify database connection**: Check PostgreSQL is accessible
3. **Review retry settings**: May need to increase timeout/retries

## Architecture Notes

### Why Through SoleFlip API?
The workflow calls the SoleFlip API instead of StockX directly because:

1. **Authentication Handled**: SoleFlip API manages OAuth2 token refresh automatically
2. **Database Sync**: API endpoints automatically sync data to PostgreSQL
3. **Rate Limiting**: Centralized rate limiting prevents StockX 429 errors
4. **Error Handling**: API includes retry logic and exponential backoff
5. **Data Validation**: API validates and transforms data before storage

### Data Flow
```
n8n Workflow → SoleFlip API → StockX API → SoleFlip API → PostgreSQL Database
                     ↓
              Automatic Sync to:
              - transactions.orders
              - inventory.inventory_items
              - catalog.product (enrichment)
```

### Performance Considerations
- **Active Orders**: Typically returns 50-200 items (fast)
- **Sold Orders (4hr window)**: Returns 0-50 items (very fast)
- **Total execution time**: 5-30 seconds per run
- **Database impact**: Minimal (bulk upserts, indexed queries)
- **Network**: Uses internal Docker network (no external bandwidth)

## Security

### Credentials
- **No credentials needed in workflow**: All auth handled by SoleFlip API
- **StockX credentials**: Stored encrypted in `system_config` table
- **n8n access**: Restrict to internal network only

### Best Practices
✅ Use internal Docker network hostnames (not localhost)
✅ Enable n8n authentication in production
✅ Store workflow in version control
✅ Monitor execution logs for suspicious activity
✅ Regular backups of n8n workflow data

## Support

For issues or questions:
1. Check n8n execution logs in UI
2. Review SoleFlip API logs: `docker-compose logs -f soleflip-api`
3. Check database for synced data
4. Review this README for troubleshooting steps

## Related Documentation
- [StockX API Documentation](https://stockx.com/api/docs)
- [n8n Documentation](https://docs.n8n.io)
- [SoleFlip API Endpoints](/domains/orders/api/router.py)
- [Docker Compose Setup](/docker-compose.yml)
