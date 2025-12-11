# Database Maintenance n8n Workflows

## Overview

Automatische Datenbank-Wartung über n8n Workflows anstatt Cron-Jobs für bessere Verwaltung und Monitoring.

---

## 📋 Available Workflows

### 1. **Analytics Refresh** - `analytics-refresh-workflow.json`

**Schedule:** Täglich um 3:00 AM
**Function:** Materialized Views für Analytics refreshen
**Nodes:** 7

**Was macht der Workflow:**
1. ⏰ **Trigger:** Täglich um 3:00 AM
2. 🔄 **Refresh:** Führt `SELECT * FROM refresh_analytics_views()` aus
3. ✅ **Check:** Prüft ob Refresh erfolgreich war
4. 📝 **Log:** Speichert Erfolg/Fehler in `logging.system_logs`

**Refreshed Views:**
- `analytics.daily_sales_summary` - Tägliche Verkäufe pro Platform
- `analytics.current_stock_summary` - Aktueller Lagerbestand
- `analytics.platform_performance` - Platform-Performance-Metriken

**Expected Duration:** ~50ms (bei leerer DB) bis ~5 Sekunden (volle DB)

---

### 2. **Data Retention Cleanup** - `data-retention-cleanup-workflow.json`

**Schedule:** Täglich um 2:00 AM
**Function:** Alte Daten löschen/archivieren
**Nodes:** 8

**Was macht der Workflow:**
1. ⏰ **Trigger:** Täglich um 2:00 AM
2. 🗑️ **Cleanup:** Führt `SELECT * FROM cleanup_old_data()` aus
3. ✅ **Check:** Prüft ob Cleanup erfolgreich war
4. 📊 **Stats:** Zählt gelöschte Rows
5. 🚨 **Alert:** Warnung bei >10.000 Deletions oder Fehler
6. 📝 **Log:** Speichert Ergebnis in `logging.system_logs`

**Cleanup Actions:**
- ❌ **System Logs:** >30 Tage → DELETE
- ❌ **Event Store:** >60 Tage → DELETE
- ❌ **Import Batches:** >90 Tage → DELETE
- 📦 **Price History:** >12 Monate → ARCHIVE
- 🧹 **VACUUM:** Reclaim storage space

**Expected Duration:** ~100ms (keine Daten) bis ~30 Sekunden (große Datenmengen)

---

## 🚀 Setup Instructions

### **Voraussetzungen:**

1. ✅ PostgreSQL Funktionen existieren:
   - `refresh_analytics_views()` (aus Migration `32adf6568b6f`)
   - `cleanup_old_data()` (aus `scripts/retention_policy_cleanup.sql`)

2. ✅ n8n PostgreSQL Credentials konfiguriert:
   - Name: `SoleFlip Database`
   - Host: `soleflip-postgres` (oder localhost)
   - Port: `5432`
   - Database: `soleflip`
   - User: `soleflip`
   - Password: `SoleFlip2025SecureDB!`

---

### **Import in n8n:**

#### **Option 1: Via n8n UI (Empfohlen)**

1. Öffne n8n: http://localhost:5678
2. Click **"Workflows"** → **"Add Workflow"** → **"Import from File"**
3. Wähle Workflow-JSON aus:
   - `workflows/analytics-refresh-workflow.json`
   - `workflows/data-retention-cleanup-workflow.json`
4. Click **"Import"**
5. Workflow wird inactive importiert
6. **WICHTIG:** Credentials zuweisen:
   - Click auf jeden Postgres-Node
   - Select **"SoleFlip Database"** Credentials
7. **Speichern**
8. **Aktivieren:** Toggle "Active" ON

#### **Option 2: Via n8n API**

```bash
# Set your n8n API key
N8N_API_KEY="your_api_key_here"
N8N_URL="http://localhost:5678"

# Import Analytics Refresh Workflow
curl -X POST "$N8N_URL/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @workflows/analytics-refresh-workflow.json

# Import Data Retention Workflow
curl -X POST "$N8N_URL/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @workflows/data-retention-cleanup-workflow.json
```

**Note:** Credentials müssen danach manuell in der UI zugewiesen werden.

---

## ✅ Verification

### **1. Check Workflows sind aktiv:**

```bash
# Via n8n UI
http://localhost:5678/workflows

# Oder via API
curl "$N8N_URL/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.data[] | {name, active}'
```

### **2. Test Workflows manuell:**

**Analytics Refresh:**
```bash
# Via n8n UI: Click "Execute Workflow"

# Oder direkt in DB:
docker exec soleflip-postgres psql -U soleflip -d soleflip -c \
  "SELECT * FROM refresh_analytics_views();"
```

**Expected Output:**
```
            view_name            | rows_affected | execution_time_ms
---------------------------------+---------------+-------------------
 analytics.daily_sales_summary   |             X |         XX.XX
 analytics.current_stock_summary |             Y |         YY.YY
 analytics.platform_performance  |             Z |         ZZ.ZZ
```

**Data Retention:**
```bash
# Via n8n UI: Click "Execute Workflow"

# Oder direkt in DB:
docker exec soleflip-postgres psql -U soleflip -d soleflip -c \
  "SELECT * FROM cleanup_old_data();"
```

**Expected Output:**
```
         table_name          | action              | rows_affected
-----------------------------+---------------------+---------------
 logging.system_logs         | DELETE (>30 days)   |             X
 logging.event_store         | DELETE (>60 days)   |             Y
 integration.import_batches  | DELETE (>90 days)   |             Z
 pricing.price_history       | ARCHIVE (>12 months)|             W
 ALL TABLES                  | VACUUM ANALYZE      |             0
```

### **3. Check Execution History:**

```bash
# Via n8n UI
http://localhost:5678/executions

# Oder via API
curl "$N8N_URL/api/v1/executions?workflowId=WORKFLOW_ID" \
  -H "X-N8N-API-KEY: $N8N_API_KEY"
```

### **4. Check Database Logs:**

```bash
docker exec soleflip-postgres psql -U soleflip -d soleflip -c "
SELECT
  created_at,
  level,
  component,
  message,
  details->>'tables_cleaned' AS tables_cleaned,
  details->>'total_rows_deleted' AS rows_deleted
FROM logging.system_logs
WHERE component IN ('n8n-analytics-refresh', 'n8n-data-retention')
ORDER BY created_at DESC
LIMIT 10;"
```

---

## 📊 Monitoring

### **Execution Metrics:**

| Workflow | Expected Frequency | Expected Duration | Alert Threshold |
|----------|-------------------|-------------------|-----------------|
| **Analytics Refresh** | 1x daily (3 AM) | <5s | >30s |
| **Data Retention** | 1x daily (2 AM) | <30s | >60s or >10k deletions |

### **Health Checks:**

```bash
# Check if workflows ran in last 24h
docker exec soleflip-postgres psql -U soleflip -d soleflip -c "
SELECT
  component,
  COUNT(*) AS executions,
  MAX(created_at) AS last_run,
  COUNT(CASE WHEN level = 'error' THEN 1 END) AS errors
FROM logging.system_logs
WHERE component IN ('n8n-analytics-refresh', 'n8n-data-retention')
  AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY component;"
```

**Expected Output:**
```
      component          | executions |          last_run          | errors
-------------------------+------------+----------------------------+--------
 n8n-analytics-refresh   |          1 | 2025-12-11 03:00:XX.XXXXXX |      0
 n8n-data-retention      |          1 | 2025-12-11 02:00:XX.XXXXXX |      0
```

### **Alert Conditions:**

1. **❌ No execution in last 24h** → Workflow inactive or n8n down
2. **❌ Errors >0** → Check error details in logs
3. **⚠️ Duration >30s** (Analytics) → Performance issue
4. **⚠️ Duration >60s** (Retention) → Too much data to clean
5. **⚠️ Deletions >10k** → Unusually high cleanup volume

---

## 🔧 Troubleshooting

### **Problem: Workflow nicht aktiv**

```bash
# Check n8n container status
docker ps | grep n8n

# Check workflow status in UI
http://localhost:5678/workflows
```

**Solution:** Aktiviere Workflow in n8n UI (Toggle "Active")

---

### **Problem: Credentials fehlen**

**Error:** `"The credential "postgres" is missing for node "XXX"`

**Solution:**
1. Öffne Workflow in n8n UI
2. Click auf jeden Postgres-Node
3. Select "SoleFlip Database" Credentials
4. Save Workflow

---

### **Problem: PostgreSQL Funktion nicht gefunden**

**Error:** `function refresh_analytics_views() does not exist`

**Solution:**
```bash
# Apply missing migrations
cd /home/g0tchi/projects/soleflip
.venv/bin/alembic upgrade head

# Install cleanup function
cat scripts/retention_policy_cleanup.sql | \
docker exec -i soleflip-postgres psql -U soleflip -d soleflip
```

---

### **Problem: Hohe Execution Time**

**Symptom:** Workflow dauert >60 Sekunden

**Diagnosis:**
```bash
# Check table sizes
docker exec soleflip-postgres psql -U soleflip -d soleflip -c "
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname IN ('logging', 'pricing', 'analytics')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;"
```

**Solutions:**
- Increase retention policy (delete less often)
- Partition large tables
- Adjust schedule (run less frequently)

---

## 📈 Performance Optimization

### **Concurrent Refresh (No Locks):**

Materialized Views werden mit `REFRESH MATERIALIZED VIEW CONCURRENTLY` refreshed:
- ✅ **Keine Locks** - Queries laufen weiter während Refresh
- ✅ **Zero Downtime** - Analytics immer verfügbar
- ⚠️ **Requires UNIQUE Index** - Bereits in Migration `826b3e02c30d` erstellt

### **Cleanup Performance:**

- **VACUUM ANALYZE** am Ende reclaimed Speicherplatz
- Cleanup läuft um **2 AM** (low traffic)
- Analytics Refresh um **3 AM** (nach Cleanup)

---

## 🎯 Benefits vs. Cron

| Feature | Cron Jobs | n8n Workflows |
|---------|-----------|---------------|
| **Visual Management** | ❌ CLI only | ✅ GUI |
| **Execution History** | ❌ Log files | ✅ Built-in |
| **Error Handling** | ⚠️ Manual | ✅ Automatic |
| **Retry Logic** | ❌ None | ✅ Configurable |
| **Alerts** | ⚠️ Manual | ✅ Built-in |
| **Schedule Changes** | ⚠️ Server access | ✅ UI click |
| **Monitoring** | ❌ Separate tool | ✅ Integrated |
| **Dependencies** | ⚠️ System cron | ✅ Docker only |

---

## 🗂️ Files Overview

```
workflows/
├── analytics-refresh-workflow.json       # Analytics refresh (daily 3 AM)
├── data-retention-cleanup-workflow.json  # Data cleanup (daily 2 AM)
├── stockx-sync-workflow.json             # StockX sync (every 4 hours)
├── DATABASE-MAINTENANCE-WORKFLOWS.md     # This file
└── README.md                             # General workflows overview
```

---

## 📚 Related Documentation

- **Week 1 Optimizations:** `docs/SCHEMA_OPTIMIZATION_2025-12-10.md`
- **Week 2-3 Optimizations:** `docs/SCHEMA_OPTIMIZATION_WEEK2-3_2025-12-11.md` (to be created)
- **Retention Policy SQL:** `scripts/retention_policy_cleanup.sql`
- **n8n Workflows Guide:** `workflows/README.md`

---

*Last Updated: 2025-12-11*
*Created by: Claude Code (Sonnet 4.5)*
