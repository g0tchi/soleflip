# n8n Quick Start Guide für SoleFlipper

Schnelleinstieg für die Implementierung der n8n-Workflows.

## 🚀 Installation & Setup (5 Minuten)

### 1. n8n starten

n8n ist bereits in Ihrer `docker-compose.yml` konfiguriert:

```bash
# Starten Sie alle Services inkl. n8n
docker-compose up -d

# Oder nur n8n
docker-compose up -d n8n

# Zugriff auf n8n UI
open http://localhost:5678
```

### 2. Initiales Setup in n8n UI

Bei erstem Start:
1. Erstellen Sie einen Owner-Account (Email + Passwort)
2. Sie werden zum Dashboard weitergeleitet

## 🔑 Credentials einrichten (10 Minuten)

### PostgreSQL Connection

**Path:** Settings → Credentials → Add Credential → Postgres

```
Name: SoleFlipper DB
Host: postgres (für Docker) oder localhost
Port: 5432
Database: soleflip
User: <your_db_user>
Password: <your_db_password>
SSL: Disabled (für lokales Development)
```

**Test:** Klicken Sie "Test Connection" - sollte grün sein ✅

### Slack Integration

**Path:** Settings → Credentials → Add Credential → Slack OAuth2 API

1. **Erstellen Sie eine Slack App:**
   - Gehen Sie zu https://api.slack.com/apps
   - Klicken Sie "Create New App" → "From scratch"
   - App Name: "SoleFlipper Bot"
   - Workspace: Ihr Workspace

2. **Bot Token Scopes hinzufügen:**
   - Gehen Sie zu "OAuth & Permissions"
   - Unter "Bot Token Scopes" fügen Sie hinzu:
     - `chat:write` (Nachrichten senden)
     - `channels:read` (Channels lesen)
     - `channels:join` (Channels beitreten)

3. **App installieren:**
   - Klicken Sie "Install to Workspace"
   - Autorisieren Sie die App

4. **Token in n8n einfügen:**
   - Kopieren Sie "Bot User OAuth Token" (beginnt mit `xoxb-`)
   - In n8n:
     - OAuth Token Type: `OAuth2`
     - Access Token: `<Ihr Bot Token>`

5. **Bot zu Channels einladen:**
   ```
   /invite @SoleFlipper Bot
   ```
   In folgenden Channels:
   - `#orders`
   - `#inventory-alerts`
   - `#pricing-alerts`
   - `#daily-reports`

### HTTP Header Auth (für API-Calls)

**Path:** Settings → Credentials → Add Credential → Header Auth

```
Name: SoleFlipper API Auth
Header Name: Authorization
Header Value: Bearer YOUR_API_KEY
```

**API Key generieren:**
```bash
# In Ihrem SoleFlipper Backend
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Speichern Sie den Key in `.env`:
```bash
API_KEY=<generated_key>
```

## 📥 Workflows importieren (5 Minuten)

### Methode 1: Via UI (Empfohlen)

1. Öffnen Sie n8n: http://localhost:5678
2. Klicken Sie "+" (Neuer Workflow)
3. Klicken Sie auf Menü (3 Punkte) → "Import from File"
4. Wählen Sie Workflow JSON aus `docs/n8n_workflows.md`
5. Credentials zuweisen (n8n fragt automatisch)
6. Workflow aktivieren (Toggle oben rechts)

### Methode 2: Via JSON

1. Kopieren Sie Workflow JSON aus `docs/n8n_workflows.md`
2. In n8n: Menü → "Import from URL or String"
3. JSON einfügen → "Import"

### Reihenfolge

Importieren Sie in dieser Reihenfolge:

1. ✅ **Multi-Platform Order Sync** (Workflow 1)
2. ✅ **Daily Dead Stock Alert** (Workflow 2)
3. ✅ **Low Stock Notifications** (Workflow 3)
4. ✅ **Daily Analytics Report** (Workflow 4)
5. ✅ **StockX Webhook Handler** (Workflow 5)
6. ✅ **Smart Price Monitoring** (Workflow 6)

## ✅ Workflows testen

### 1. Multi-Platform Order Sync

**Manueller Test:**
1. Öffnen Sie Workflow
2. Klicken Sie "Execute Workflow"
3. Prüfen Sie Execution Log

**Erwartetes Ergebnis:**
- API-Calls zu StockX/eBay erfolgreich
- DB Query zeigt neue Orders
- Slack-Benachrichtigung in `#orders` (falls neue Orders)

### 2. Dead Stock Alert

**Manueller Test:**
```sql
-- Erstellen Sie Test-Daten (alte Inventory Items)
INSERT INTO inventory.inventory_items (id, product_id, status, created_at, purchase_cost)
VALUES
  (gen_random_uuid(), '<existing_product_id>', 'available', NOW() - INTERVAL '100 days', 50.00);
```

**Execute Workflow:**
- Sollte Dead Stock finden
- Slack Alert in `#inventory-alerts`

### 3. Low Stock Notifications

**Manueller Test:**
```sql
-- Reduzieren Sie Stock für beliebtes Produkt
UPDATE inventory.inventory_items
SET status = 'sold'
WHERE product_id = '<popular_product_id>'
  AND status = 'available'
LIMIT 5;
```

**Execute Workflow:**
- Findet Low Stock Items
- Alert in `#inventory-alerts`

### 4. Daily Analytics Report

**Manueller Test:**
- Execute Workflow
- Prüfen Sie Report in `#daily-reports`
- Sollte KPIs von gestern zeigen

### 5. StockX Webhook

**Test mit curl:**
```bash
# Webhook URL aus n8n kopieren (siehe Workflow Node)
curl -X POST http://localhost:5678/webhook/stockx-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "order.shipped",
    "data": {
      "order_id": "test-order-123",
      "status": "shipped",
      "tracking_number": "1Z999AA10123456784"
    }
  }'
```

**Erwartetes Ergebnis:**
- Webhook verarbeitet Event
- Slack-Nachricht in `#orders`
- Response: `{"status":"success"}`

### 6. Price Monitoring

**Manueller Test:**
```sql
-- Stellen Sie sicher, dass Sie gelistete Produkte haben
UPDATE inventory.inventory_items
SET status = 'listed', listed_price = 150.00
WHERE status = 'available'
LIMIT 5;
```

**Execute Workflow:**
- Ruft Marktpreise ab
- Vergleicht mit Listen-Preisen
- Alert bei Abweichungen

## 📊 Monitoring Dashboard

### Execution History

**Path:** Executions → Past Executions

Hier sehen Sie:
- ✅ Erfolgreiche Runs (grün)
- ❌ Fehlgeschlagene Runs (rot)
- ⏸️ Wartende Runs (gelb)

**Best Practice:**
- Prüfen Sie täglich die Failed Executions
- Aktivieren Sie Email-Benachrichtigungen bei Failures

### Workflow Status

**Aktive Workflows Dashboard:**
```
Multi-Platform Order Sync      🟢 Active   Last: 5 min ago
Dead Stock Alert               🟢 Active   Last: 2 hours ago
Low Stock Notifications        🟢 Active   Last: 4 hours ago
Daily Analytics Report         🟢 Active   Last: 8:30 AM
StockX Webhook Handler         🟢 Active   Listening
Smart Price Monitoring         🟢 Active   Last: 1 hour ago
```

## 🔧 Troubleshooting

### "Database connection failed"

**Lösung:**
```bash
# 1. Prüfen Sie, ob PostgreSQL läuft
docker-compose ps postgres

# 2. Test DB Connection
docker exec -it soleflip-postgres psql -U your_user -d soleflip -c "SELECT 1;"

# 3. Prüfen Sie Credentials in n8n
# Settings → Credentials → SoleFlipper DB → Test Connection
```

### "Slack API error: not_in_channel"

**Lösung:**
```bash
# Bot muss zu Channels eingeladen werden
# In jedem Channel:
/invite @SoleFlipper Bot
```

### "API endpoint not found"

**Lösung:**
```bash
# 1. Prüfen Sie, ob SoleFlipper API läuft
curl http://localhost:8000/health

# 2. Prüfen Sie API URLs in Workflows
# Sollten sein: http://localhost:8000/api/...
# Für Docker: http://soleflip-api:8000/api/...
```

### Workflow hängt bei "Executing"

**Lösung:**
1. Stop Workflow (X Button)
2. Check Node Configuration
3. Test einzelne Nodes mit "Test Step"
4. Prüfen Sie Timeouts (sollten 15-30 Sekunden sein)

## 📈 Nächste Schritte

### 1. Passen Sie Schedules an

Editieren Sie Schedule Trigger Nodes:
```javascript
// Beispiel: Order Sync alle 30 Minuten statt 15
"minutesInterval": 30

// Dead Stock Alert um 9 Uhr statt 8 Uhr
"triggerAtHour": 9
```

### 2. Erweitern Sie Workflows

**Ideen:**
- Email-Benachrichtigungen zusätzlich zu Slack
- WhatsApp-Integration für kritische Alerts
- Discord-Benachrichtigungen für Team
- Auto-Restock bei Low Stock (API-Call zu Supplier)

### 3. Erstellen Sie Custom Workflows

**Template:**
```json
{
  "name": "My Custom Workflow",
  "nodes": [
    {
      "parameters": { ... },
      "name": "Trigger Node",
      "type": "n8n-nodes-base.scheduleTrigger",
      ...
    }
  ],
  "connections": { ... }
}
```

### 4. Backup Workflows

**Manuell:**
- Settings → Workflows → Export (JSON)
- Speichern Sie in Git Repository

**Automatisch:**
```bash
# n8n Backup Script
docker exec n8n n8n export:workflow --all --output=/backup/workflows.json
```

## 📚 Ressourcen

- **n8n Docs:** https://docs.n8n.io
- **SoleFlipper API Docs:** http://localhost:8000/docs
- **n8n Community:** https://community.n8n.io
- **Workflow Templates:** https://n8n.io/workflows

## 🎉 Fertig!

Ihre n8n-Workflows sind jetzt aktiv und automatisieren:
- ✅ Order Synchronization (alle 15 min)
- ✅ Inventory Monitoring (täglich + alle 6h)
- ✅ Price Monitoring (alle 2h)
- ✅ Daily Reports (täglich 8:30 Uhr)
- ✅ Real-time Webhooks (StockX Events)

**Genießen Sie Ihre Automatisierung!** 🚀
