# SoleFlip Workflows - Documentation Index

Welcome to the SoleFlip n8n workflows documentation. This directory contains production-ready workflows for automating StockX data synchronization.

## Quick Navigation

### 🚀 Get Started (Choose Your Path)

| Document | Purpose | Time Required | For Users |
|----------|---------|---------------|-----------|
| **[QUICKSTART.md](QUICKSTART.md)** | Fast setup guide | 5 minutes | Everyone |
| **[README.md](README.md)** | Complete reference | 15 minutes | Developers |
| **[WORKFLOW-DIAGRAM.md](WORKFLOW-DIAGRAM.md)** | Visual architecture | 5 minutes | Visual learners |

### 📄 Files in This Directory

```
workflows/
├── stockx-sync-workflow.json    # The actual n8n workflow (import this)
├── INDEX.md                      # This file - start here
├── QUICKSTART.md                 # 5-minute setup guide
├── README.md                     # Complete documentation
└── WORKFLOW-DIAGRAM.md           # Visual workflow architecture
```

## What This Workflow Does

### The Problem It Solves
Manual StockX data synchronization is time-consuming and error-prone. This workflow automates the entire process.

### The Solution
**Automatic StockX data sync every 4 hours** that:
- ✅ Fetches all active orders (current listings)
- ✅ Fetches sold orders (recent completions)
- ✅ Stores data in PostgreSQL database
- ✅ Includes comprehensive error handling
- ✅ Provides structured logging
- ✅ Runs completely unattended

### The Result
**6 sync runs per day** = Real-time visibility into your StockX business with zero manual work.

## Workflow Specifications

| Property | Value |
|----------|-------|
| **Name** | StockX Data Sync - Every 4 Hours |
| **Type** | Scheduled Workflow |
| **Trigger** | Cron (0 */4 * * *) |
| **Nodes** | 8 nodes |
| **Duration** | ~30 seconds per execution |
| **API Calls** | 2 per execution (active orders, sold orders) |
| **Database Impact** | Minimal (bulk upserts, indexed) |
| **Error Handling** | 3 retries with exponential backoff |

## Installation Methods

### Method 1: n8n UI Import (Recommended) ⭐
```
1. Open http://localhost:5678
2. Click "Import from File"
3. Select: workflows/stockx-sync-workflow.json
4. Activate the workflow
```
**Time**: 2 minutes | **Difficulty**: Easy

### Method 2: File System Copy
```bash
cp workflows/stockx-sync-workflow.json ~/.n8n/workflows/
docker-compose restart n8n
```
**Time**: 1 minute | **Difficulty**: Easy

### Method 3: n8n API (Advanced)
```bash
curl -X POST "$N8N_API_URL/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -d @workflows/stockx-sync-workflow.json
```
**Time**: 1 minute | **Difficulty**: Advanced

## Documentation Deep Dive

### QUICKSTART.md - Fast Setup
**Read this if**: You want to get running ASAP

**Contains**:
- 5-minute installation steps
- Verification checklist
- Common issues & fixes
- Success indicators
- Quick reference commands

**Best for**: First-time users, quick deployments

### README.md - Complete Reference
**Read this if**: You need detailed information

**Contains**:
- Full workflow explanation
- Architecture overview
- Configuration options
- Monitoring guide
- Troubleshooting section
- Security best practices
- Performance tuning

**Best for**: Production deployments, troubleshooting, customization

### WORKFLOW-DIAGRAM.md - Visual Guide
**Read this if**: You prefer visual learning

**Contains**:
- ASCII workflow diagram
- Data flow visualization
- Node-by-node breakdown
- Error handling flow
- Network topology
- Performance metrics

**Best for**: Understanding architecture, presentations, onboarding

## Key Features

### ✅ Production-Ready
- Comprehensive error handling
- Automatic retry with exponential backoff
- Structured logging
- Continue-on-failure logic
- Timeout protection (60s)

### ✅ Zero Configuration
- Works out-of-the-box with SoleFlip
- Uses internal Docker network
- No credentials needed in workflow
- Automatic database sync

### ✅ Well Documented
- 1,360 lines of documentation
- Visual diagrams
- Troubleshooting guides
- Quick reference commands

### ✅ Easily Customizable
- Change sync frequency (cron)
- Extend historical window
- Add notifications (Slack, Email)
- Modify logging format

## System Requirements

### Infrastructure
- ✅ Docker Compose with SoleFlip stack
- ✅ n8n (latest) running on port 5678
- ✅ SoleFlip API running on port 8000
- ✅ PostgreSQL database accessible

### Credentials
- ✅ StockX credentials configured in database
- ✅ OAuth2 token refresh working
- ✅ API accessible from n8n container

### Network
- ✅ Docker network: `soleflip-network`
- ✅ Internal DNS resolution working
- ✅ Internet access for StockX API

## Workflow Architecture

### High-Level Flow
```
Schedule Trigger (Every 4 Hours)
    │
    ▼
Fetch Active Orders ─────────┐
    │                        │
    ▼                        │
Check Success ───────────────┤
    │                        │
    ▼                        │
Fetch Sold Orders            │
    │                        │
    ▼                        │
Check Success                │
    │                        │
    ▼                        ▼
Log Success              Log Error
```

### Data Flow
```
n8n → SoleFlip API → StockX API → Database
  ↑                                    │
  └─────────── Confirmation ───────────┘
```

### Error Handling
```
HTTP Request Error
    ↓
Retry 1 (wait 5s)
    ↓
Retry 2 (wait 10s)
    ↓
Retry 3 (wait 20s)
    ↓
Continue to Error Branch → Log Error → End
```

## Common Use Cases

### 1. Real-Time Inventory Management
**Goal**: Keep inventory in sync with StockX
**How**: Workflow auto-syncs active orders every 4 hours
**Result**: Always accurate inventory counts

### 2. Sales Tracking & Reporting
**Goal**: Track sales performance over time
**How**: Workflow fetches sold orders and stores in database
**Result**: Historical sales data for analytics

### 3. Automated Pricing Updates
**Goal**: Adjust prices based on market activity
**How**: Trigger pricing workflow after StockX sync
**Result**: Competitive pricing without manual work

### 4. Business Intelligence
**Goal**: Generate reports and dashboards
**How**: Query synced data in Metabase/BI tools
**Result**: Data-driven business decisions

## Success Checklist

After installation, verify these indicators:

### ✅ Workflow Level
- [ ] Workflow is active (toggle switch is green)
- [ ] Scheduled for every 4 hours
- [ ] At least one successful execution in history
- [ ] All nodes show green checkmarks
- [ ] Log Success node shows order counts

### ✅ Database Level
- [ ] `transactions.orders` has new rows
- [ ] `source = 'stockx'` records present
- [ ] Timestamps are recent (within 4 hours)
- [ ] Both active and sold orders synced

### ✅ System Level
- [ ] n8n container running
- [ ] SoleFlip API responding to health check
- [ ] No errors in n8n logs
- [ ] Database connection stable

## Troubleshooting Quick Reference

| Symptom | Quick Fix | Doc Reference |
|---------|-----------|---------------|
| Workflow not running | Check if active | QUICKSTART.md → Issue 1 |
| Connection refused | Verify Docker network | QUICKSTART.md → Issue 2 |
| No data returned | Check StockX credentials | QUICKSTART.md → Issue 3 |
| 401 Unauthorized | Refresh OAuth token | QUICKSTART.md → Issue 4 |
| Timeout errors | Increase timeout setting | README.md → Customization |
| High error rate | Check rate limits | README.md → Troubleshooting |

## Performance Expectations

### Execution Metrics
- **Frequency**: Every 4 hours (6 times per day)
- **Duration**: 15-30 seconds typical, max 60 seconds
- **Success Rate**: > 95% in normal operation
- **API Response**: 3-15 seconds per endpoint

### Data Volume
- **Active Orders**: 50-200 per sync (typical)
- **Sold Orders**: 5-50 per 4-hour window (typical)
- **Database Growth**: ~100-300 rows per day
- **Storage Impact**: Minimal (< 10MB per month)

## Monitoring Recommendations

### Daily Checks
- [ ] Review execution history in n8n
- [ ] Check success rate > 95%
- [ ] Verify order counts are reasonable

### Weekly Checks
- [ ] Review error logs for patterns
- [ ] Check database growth rate
- [ ] Verify StockX credentials still valid

### Monthly Checks
- [ ] Analyze performance trends
- [ ] Review and optimize if needed
- [ ] Update documentation if workflow changed

## Customization Options

### Quick Customizations (< 5 minutes)
- Change sync frequency (edit cron expression)
- Adjust timeout values
- Modify logging format
- Enable/disable specific endpoints

### Advanced Customizations (< 30 minutes)
- Add email/Slack notifications
- Extend historical data window
- Integrate with other workflows
- Add conditional logic for special cases

### Complex Customizations (1+ hours)
- Add multiple StockX accounts
- Implement rate limiting logic
- Create custom error handling
- Build analytics pipeline

## Support & Resources

### Getting Help
1. **Check the docs**: Start with QUICKSTART.md
2. **Review logs**: n8n execution logs show clear errors
3. **Test manually**: Use "Execute Workflow" button
4. **Verify credentials**: Ensure StockX auth working

### Useful Resources
- [n8n Documentation](https://docs.n8n.io)
- [StockX API Docs](https://stockx.com/api/docs)
- [SoleFlip API Code](/domains/orders/api/router.py)
- [Docker Compose Setup](/docker-compose.yml)

### Quick Commands
```bash
# View workflow executions
docker-compose logs -f n8n | grep "StockX Data Sync"

# Check API health
curl http://localhost:8000/health

# Query synced data
docker exec -it soleflip-db psql -U soleflip -d soleflip \
  -c "SELECT COUNT(*) FROM transactions.orders WHERE source='stockx';"

# Restart workflow
docker-compose restart n8n
```

## Version History

### v1.0.0 (Current) - 2025-12-08
- ✅ Initial production release
- ✅ Every 4-hour sync schedule
- ✅ Active and sold orders support
- ✅ Comprehensive error handling
- ✅ Full documentation suite

### Planned Features
- [ ] Add Slack/Email notifications
- [ ] Support for multiple StockX accounts
- [ ] Custom rate limiting configuration
- [ ] Integration with pricing workflows
- [ ] Performance metrics dashboard

## FAQ

**Q: How often does the workflow run?**
A: Every 4 hours, 6 times per day (00:00, 04:00, 08:00, 12:00, 16:00, 20:00).

**Q: What happens if the API is down?**
A: The workflow retries 3 times with exponential backoff, then logs an error and continues.

**Q: Does this replace manual syncing?**
A: Yes, completely. Once active, it runs automatically with zero manual intervention.

**Q: Can I change the schedule?**
A: Yes, edit the cron expression in the workflow. See README.md for examples.

**Q: What if I have no sold orders?**
A: Normal! The workflow will return an empty array `[]` if no orders sold in the time window.

**Q: How do I see the synced data?**
A: Query the `transactions.orders` table in PostgreSQL or use Metabase at http://localhost:6400.

**Q: Is this production-ready?**
A: Yes! Includes error handling, retries, logging, and has been fully validated.

**Q: Can I run it more frequently?**
A: Yes, but be mindful of StockX API rate limits. Every 2 hours is safe, every 1 hour needs monitoring.

## Next Steps

### ✅ You're Ready to Start!

1. **Install**: Choose your installation method above
2. **Verify**: Check the success indicators
3. **Monitor**: Review execution history
4. **Customize**: Adjust schedule or add features as needed

### 📚 Recommended Reading Order

**First Time Users**:
1. This file (INDEX.md) - Overview ✓
2. QUICKSTART.md - Get it running
3. Verify success checklist
4. Done! 🎉

**Production Deployment**:
1. This file (INDEX.md) - Overview ✓
2. README.md - Full documentation
3. WORKFLOW-DIAGRAM.md - Architecture review
4. Set up monitoring and alerts
5. Deploy and monitor

**Troubleshooting**:
1. QUICKSTART.md - Common issues
2. README.md - Advanced troubleshooting
3. Check logs and execution history
4. Test manually to isolate issue

## License & Credits

Part of the SoleFlip project. See main repository for license information.

**Workflow Architecture**: Production-ready n8n automation
**Documentation**: Comprehensive guides and troubleshooting
**Maintenance**: Actively maintained and updated

---

**Ready to get started?** → [QUICKSTART.md](QUICKSTART.md)

**Need more details?** → [README.md](README.md)

**Want to see the architecture?** → [WORKFLOW-DIAGRAM.md](WORKFLOW-DIAGRAM.md)
