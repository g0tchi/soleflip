# Quick Start: StockX Data Sync Workflow

Get the StockX data sync workflow running in 5 minutes.

## Prerequisites

✅ Docker Compose running with SoleFlip stack
✅ n8n accessible at `http://localhost:5678`
✅ SoleFlip API running at `http://localhost:8000`
✅ StockX credentials configured in database

## Installation Steps

### 1. Import Workflow

**Via n8n UI (Easiest)**:
```bash
# 1. Open n8n in your browser
open http://localhost:5678

# 2. Click "Import from File" in the top-right corner
# 3. Select: workflows/stockx-sync-workflow.json
# 4. Click "Save" when prompted
```

### 2. Activate Workflow

In the n8n UI:
1. Open the imported workflow
2. Toggle the switch in the top-right to **"Active"**
3. You should see: ✅ **"Workflow activated"**

### 3. Test the Workflow

**Option A: Manual Test (Recommended First Time)**
```
1. Click the "Execute Workflow" button (play icon)
2. Watch the execution in real-time
3. Check each node for green checkmarks ✅
4. Review the output in "Log Success" node
```

**Option B: Wait for Scheduled Run**
```
Next execution: Every 4 hours at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
```

### 4. Verify Data Sync

**Check Database**:
```sql
-- Connect to PostgreSQL
docker exec -it soleflip-db psql -U soleflip -d soleflip

-- Check synced orders
SELECT
  source,
  status,
  COUNT(*) as count,
  MAX(created_at) as last_sync
FROM transactions.orders
WHERE source = 'stockx'
GROUP BY source, status;

-- Expected output:
--  source  | status  | count | last_sync
-- ---------|---------|-------|----------------------
--  stockx  | active  |   42  | 2025-12-08 10:00:00
--  stockx  | sold    |    8  | 2025-12-08 10:00:00
```

**Check API Health**:
```bash
# Test the API endpoints directly
curl http://localhost:8000/api/v1/orders/active | jq '.[0:3]'
```

## Workflow Overview

### What Gets Synced

| Data Type | Endpoint | Frequency | Description |
|-----------|----------|-----------|-------------|
| **Active Orders** | `/api/v1/orders/active` | Every 4 hours | Current listings on StockX |
| **Sold Orders** | `/api/v1/orders/stockx-history` | Every 4 hours | Orders completed in last 4 hours |

### Execution Schedule

```
00:00 ──► Sync Run 1
04:00 ──► Sync Run 2
08:00 ──► Sync Run 3
12:00 ──► Sync Run 4
16:00 ──► Sync Run 5
20:00 ──► Sync Run 6
```

**6 syncs per day** = Full coverage of StockX activity

## Success Indicators

✅ **Workflow Execution**:
- Green checkmarks on all nodes
- No red error indicators
- "Log Success" node shows order counts

✅ **Database Updates**:
- `transactions.orders` table has new rows
- `created_at` timestamps are recent
- Both active and sold orders present

✅ **API Responses**:
- HTTP 200 status codes
- JSON arrays with order data
- No timeout errors

## Common Issues & Fixes

### Issue 1: "Workflow not executing"

**Symptom**: No executions in history

**Fix**:
```bash
# 1. Check if workflow is active
# Look for toggle switch in n8n UI - should be GREEN

# 2. Verify n8n is running
docker-compose ps n8n

# 3. Check n8n logs
docker-compose logs -f n8n | grep "StockX Data Sync"
```

### Issue 2: "Connection refused to soleflip-api"

**Symptom**: HTTP request fails with connection error

**Fix**:
```bash
# 1. Verify API is running
docker-compose ps soleflip-api

# 2. Test network connectivity from n8n
docker exec soleflip-n8n ping -c 3 soleflip-api

# 3. Check API health endpoint
curl http://localhost:8000/health

# 4. Verify both services in same Docker network
docker network inspect soleflip_soleflip-network
```

### Issue 3: "No data returned from API"

**Symptom**: HTTP 200 but empty array `[]`

**Possible Causes**:
- No active orders on StockX (normal if nothing listed)
- No sold orders in last 4 hours (normal during slow periods)
- StockX credentials need refresh

**Check StockX Credentials**:
```sql
-- Connect to database
docker exec -it soleflip-db psql -U soleflip -d soleflip

-- Check credentials exist
SELECT key, updated_at
FROM system_config
WHERE key LIKE 'stockx%';

-- Should show 4 rows:
-- stockx_client_id
-- stockx_client_secret
-- stockx_refresh_token
-- stockx_api_key
```

### Issue 4: "401 Unauthorized from StockX"

**Symptom**: StockX API returns 401 error

**Fix**:
```bash
# The API automatically refreshes tokens, but you may need to:

# 1. Check StockX service logs
docker-compose logs soleflip-api | grep -i "stockx\|401\|auth"

# 2. Verify credentials in database (see Issue 3)

# 3. Manual token refresh via API
curl -X POST http://localhost:8000/api/v1/integration/stockx/refresh-token
```

## Monitoring

### View Execution History

**In n8n UI**:
1. Click "Executions" in left sidebar
2. Filter by workflow name: "StockX Data Sync"
3. Review success/failure rates

**Via API** (if enabled):
```bash
# Get recent executions
curl http://localhost:5678/api/v1/executions?workflowId=<id>&limit=10
```

### View Logs in Real-Time

```bash
# n8n workflow logs
docker-compose logs -f n8n

# SoleFlip API logs (shows StockX API calls)
docker-compose logs -f soleflip-api | grep "StockX\|orders"

# Database query logs (if enabled)
docker-compose logs -f postgres | grep "orders"
```

### Key Metrics to Track

| Metric | How to Check | Healthy Range |
|--------|--------------|---------------|
| **Execution frequency** | n8n Executions tab | Every 4 hours |
| **Success rate** | n8n Executions tab | > 95% |
| **Orders per sync** | Log Success node | 10-200 active, 0-50 sold |
| **Response time** | n8n Execution duration | < 30 seconds |
| **Database growth** | Row count in orders table | Steady increase |

## Customization

### Change Sync Frequency

Edit the cron expression in workflow JSON:

```json
{
  "field": "cronExpression",
  "expression": "0 */2 * * *"  // Every 2 hours instead of 4
}
```

Common patterns:
- `0 */1 * * *` - Every hour
- `0 */6 * * *` - Every 6 hours
- `0 3 * * *` - Daily at 3am
- `*/30 * * * *` - Every 30 minutes

### Add Email Notifications

1. Add **Gmail** node after "Log Error" nodes
2. Configure with your credentials
3. Set email body to: `{{ $json.error_message }}`

### Extend Historical Data Window

In "Fetch Sold Orders" node, change:
```json
{
  "name": "fromDate",
  "value": "={{ $now.minus(7, 'days').toFormat('yyyy-MM-dd') }}"
}
```

## Next Steps

✅ **You're Done!** The workflow is now syncing StockX data automatically.

### Optional Enhancements:

1. **Add Monitoring Dashboard**
   - Create Metabase dashboard at `http://localhost:6400`
   - Query `transactions.orders` for analytics
   - Track order trends over time

2. **Set Up Alerts**
   - Add Slack/Email notifications on errors
   - Monitor sync success rates
   - Alert on unusual order volumes

3. **Integrate with Other Workflows**
   - Trigger auto-pricing updates after sync
   - Update inventory based on sold orders
   - Generate sales reports

4. **Scale for Production**
   - Enable n8n authentication
   - Set up workflow backups
   - Configure proper monitoring/alerting
   - Review rate limits and adjust frequency

## Support

### Getting Help

1. **Check the logs**: Most issues show clear error messages
2. **Review README.md**: Detailed troubleshooting guide
3. **Test manually**: Use n8n "Execute Workflow" to debug
4. **Verify credentials**: Ensure StockX auth is working

### Useful Commands

```bash
# Restart n8n if needed
docker-compose restart n8n

# View all container logs
docker-compose logs -f

# Check database connection
docker exec -it soleflip-db psql -U soleflip -d soleflip -c "SELECT version();"

# Test API endpoint
curl -v http://localhost:8000/api/v1/orders/active

# Restart entire stack (last resort)
docker-compose down && docker-compose up -d
```

## Success! 🎉

Your StockX data is now syncing automatically every 4 hours. Check the n8n executions tab to monitor progress, and query the database to see your data growing.

**What's happening now**:
- ⏰ n8n triggers every 4 hours
- 📡 Fetches active orders from StockX
- 📡 Fetches sold orders from last 4 hours
- 💾 Automatically saves to PostgreSQL
- 📊 Ready for analytics and reporting

**No further action needed** - the workflow runs automatically! 🚀
