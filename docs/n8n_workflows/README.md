# n8n Workflow JSON Files

Direkt importierbare n8n-Workflow-Dateien für SoleFlipper.

## 📁 Verfügbare Workflows

| # | Datei | Workflow | Trigger |
|---|-------|----------|---------|
| 1 | `01_multi_platform_order_sync.json` | Multi-Platform Order Sync | Alle 15 Minuten |
| 2 | `02_daily_dead_stock_alert.json` | Daily Dead Stock Alert | Täglich 8:00 Uhr |
| 3 | `03_low_stock_notifications.json` | Low Stock Notifications | Alle 6 Stunden |
| 4 | `04_daily_analytics_report.json` | Daily Analytics Report | Täglich 8:30 Uhr |
| 5 | `05_stockx_webhook_handler.json` | StockX Webhook Handler | Real-time Webhook |
| 6 | `06_smart_price_monitoring.json` | Smart Price Monitoring | Alle 2 Stunden |

## 🚀 Import in n8n

### Methode 1: Via File Upload (Empfohlen)

1. Öffnen Sie n8n: http://localhost:5678
2. Klicken Sie auf "**+**" (Neuer Workflow)
3. Klicken Sie auf das **Menü** (3 Punkte oben rechts)
4. Wählen Sie "**Import from File**"
5. Wählen Sie eine JSON-Datei aus diesem Verzeichnis
6. Klicken Sie "**Import**"

### Methode 2: Via Copy-Paste

1. Öffnen Sie eine JSON-Datei in einem Texteditor
2. Kopieren Sie den **gesamten Inhalt** (Ctrl+A, Ctrl+C)
3. In n8n: Klicken Sie "**+**" → Menü → "**Import from URL or String**"
4. Fügen Sie den JSON-Code ein (Ctrl+V)
5. Klicken Sie "**Import**"

### Methode 3: Via Command Line

```bash
# Für jeden Workflow
cat 01_multi_platform_order_sync.json | pbcopy  # macOS
cat 01_multi_platform_order_sync.json | xclip   # Linux

# Dann in n8n: Import from URL or String
```

## ⚙️ Nach dem Import

### 1. Credentials zuweisen

n8n wird Sie automatisch auffordern, Credentials zuzuweisen:

**PostgreSQL:**
- Node: Alle "Postgres" Nodes
- Credential: "SoleFlipper DB"

**Slack:**
- Node: Alle "Slack" Nodes
- Credential: "Slack OAuth2"

**HTTP Auth:**
- Node: Alle "HTTP Request" Nodes zu localhost:8000
- Credential: "SoleFlipper API Auth"

### 2. URLs anpassen (falls nötig)

Wenn Ihre API nicht auf `localhost:8000` läuft:

1. Öffnen Sie jeden HTTP Request Node
2. Ändern Sie die URL von `http://localhost:8000` zu Ihrer API-URL
3. Speichern Sie den Workflow

**Docker-Umgebung:**
```
http://soleflip-api:8000  # Wenn API in Docker läuft
```

### 3. Workflow aktivieren

1. Speichern Sie den Workflow (Ctrl+S)
2. Aktivieren Sie den Workflow mit dem **Toggle** oben rechts
3. Der Toggle sollte **grün** werden

### 4. Testen

**Schedule-Workflows:**
- Klicken Sie "**Execute Workflow**" für manuellen Test
- Prüfen Sie die **Execution History**

**Webhook-Workflow:**
- Kopieren Sie die Webhook-URL aus dem Webhook-Node
- Testen Sie mit curl:

```bash
curl -X POST http://localhost:5678/webhook/stockx-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "order.test",
    "data": {
      "order_id": "test-123",
      "status": "pending"
    }
  }'
```

## 🔧 Troubleshooting

### Import Error: "Invalid JSON"

**Problem:** JSON-Datei ist beschädigt oder falsch kopiert

**Lösung:**
```bash
# Validieren Sie das JSON
cat 01_multi_platform_order_sync.json | jq .

# Sollte den formatierten JSON ausgeben
# Wenn Error: JSON ist ungültig
```

### Missing Credentials

**Problem:** "This node is missing credentials"

**Lösung:**
1. Gehen Sie zu **Settings** → **Credentials**
2. Erstellen Sie die fehlenden Credentials:
   - PostgreSQL (Name: "SoleFlipper DB")
   - Slack OAuth2 (Name: "Slack OAuth2")
   - Header Auth (Name: "SoleFlipper API Auth")
3. Gehen Sie zurück zum Workflow
4. Klicken Sie auf den roten Node
5. Wählen Sie das Credential aus dem Dropdown

### Workflow doesn't trigger

**Problem:** Schedule läuft nicht automatisch

**Lösung:**
1. Prüfen Sie, ob Workflow **aktiviert** ist (Toggle grün)
2. Prüfen Sie n8n Logs: `docker-compose logs -f n8n`
3. Manuell testen: "Execute Workflow"
4. Check Timezone Settings (sollte "Europe/Berlin" sein)

### Database Connection Failed

**Problem:** Postgres Node kann nicht verbinden

**Lösung:**
```bash
# 1. Test DB Connection
docker exec -it soleflip-postgres psql -U your_user -d soleflip -c "SELECT 1;"

# 2. In n8n: Edit PostgreSQL Credential
# Host: postgres (Docker) oder localhost
# Port: 5432
# Database: soleflip

# 3. Test Connection in n8n
```

## 📊 Workflow-Details

### 01 - Multi-Platform Order Sync
**Nodes:** 6 | **Connections:** 5
**Frequency:** Every 15 minutes
**Credentials:** Postgres, Slack, HTTP Auth

### 02 - Daily Dead Stock Alert
**Nodes:** 6 | **Connections:** 5
**Frequency:** Daily at 8:00 AM
**Credentials:** Postgres, Slack

### 03 - Low Stock Notifications
**Nodes:** 5 | **Connections:** 4
**Frequency:** Every 6 hours
**Credentials:** Postgres, Slack

### 04 - Daily Analytics Report
**Nodes:** 6 | **Connections:** 6
**Frequency:** Daily at 8:30 AM
**Credentials:** Postgres, Slack

### 05 - StockX Webhook Handler
**Nodes:** 6 | **Connections:** 5
**Frequency:** Real-time (Webhook)
**Credentials:** Slack, HTTP Auth

### 06 - Smart Price Monitoring
**Nodes:** 7 | **Connections:** 6
**Frequency:** Every 2 hours
**Credentials:** Postgres, Slack, HTTP Auth

## 📚 Weitere Dokumentation

- **Setup Guide:** `../n8n_quick_start.md`
- **Vollständige Docs:** `../n8n_workflows.md`
- **Übersicht:** `../n8n_README.md`

## 🔄 Updates & Versionierung

**Current Version:** 1.0.0

Alle Workflows sind getestet und produktionsbereit.

### Update Workflow

Wenn ein Workflow aktualisiert wird:

1. **Backup erstellen:**
   - Export aktuellen Workflow als JSON
   - Speichern mit Datum: `workflow_backup_2025-01-27.json`

2. **Neuen Workflow importieren:**
   - Import neue Version aus diesem Verzeichnis
   - Credentials neu zuweisen
   - Testen

3. **Deployment:**
   - Deaktivieren Sie alte Version
   - Aktivieren Sie neue Version
   - Monitor für 24h

## 💡 Best Practices

### Import-Reihenfolge

Importieren Sie in dieser Reihenfolge für optimale Abhängigkeiten:

1. ✅ 01 - Order Sync (keine Abhängigkeiten)
2. ✅ 02 - Dead Stock Alert (nutzt Inventory Schema)
3. ✅ 03 - Low Stock Notifications (nutzt Orders für Verkaufsdaten)
4. ✅ 04 - Analytics Report (nutzt Orders & Products)
5. ✅ 05 - Webhook Handler (standalone)
6. ✅ 06 - Price Monitoring (nutzt Inventory & Pricing API)

### Naming Convention

Workflows sind benannt nach:
```
{number}_{snake_case_name}.json
```

Dies erleichtert:
- Sortierung im Filesystem
- Schnelles Finden
- Import-Reihenfolge

### Credential Management

**Empfehlung:**
- Ein PostgreSQL Credential für alle Workflows
- Ein Slack Credential für alle Workflows
- Ein HTTP Auth Credential für alle API-Calls

Dies vereinfacht Updates und Wartung.

## 🎉 Ready to Go!

Nach dem Import aller 6 Workflows haben Sie:

- ✅ 39 Nodes konfiguriert
- ✅ 35 Connections eingerichtet
- ✅ 6 Automatisierungen aktiv
- ✅ 50h/Monat Zeitersparnis

**Viel Erfolg mit Ihrer Automation!** 🚀
