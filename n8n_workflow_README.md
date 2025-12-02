# SoleFlipper n8n Workflow - Automated Inventory Monitoring

## 📋 Übersicht

Dieser n8n Workflow automatisiert das Inventory Monitoring und Stock Management für SoleFlipper.

**Workflow Datei**: `soleflip_inventory_monitoring_workflow.json`

## 🚀 Installation

### 1. n8n öffnen
```bash
http://localhost:5678
```

### 2. Workflow importieren
1. In n8n: Klick auf **"+"** → **"Import from File"**
2. Wähle: `soleflip_inventory_monitoring_workflow.json`
3. Workflow wird importiert mit Namen: **"SoleFlipper - Automated Inventory Monitoring & Stock Management"**

### 3. Workflow aktivieren
1. Toggle-Switch oben rechts auf **"Active"** stellen
2. Workflow ist nun aktiviert

## 🎯 Features

### Automatische Checks
- **Täglicher Schedule**: Läuft automatisch alle 24 Stunden
- **Manueller Trigger**: Webhook für manuelle Ausführung

### API Endpoints (Phase 2 Integration)

#### 1. **Stock Metrics** ✅
```
GET http://localhost:8000/api/v1/inventory/metrics
```
Liefert:
- Total items
- Items in stock
- Items sold
- Items listed
- Total value
- Average purchase price

#### 2. **Low Stock Detection** ✅
```
GET http://localhost:8000/api/v1/inventory/low-stock?threshold=5
```
Findet Items mit verfügbarer Menge < Threshold (berücksichtigt Reservierungen)

#### 3. **Stock Reservation** ✅
```
POST http://localhost:8000/api/v1/inventory/items/{item_id}/reserve?quantity=1&reason=xyz
```
**Wichtig**: Benötigt `Content-Type: application/json` Header

#### 4. **Release Reservation** ✅
```
POST http://localhost:8000/api/v1/inventory/items/{item_id}/release?quantity=1&reason=xyz
```
**Wichtig**: Benötigt `Content-Type: application/json` Header

#### 5. **StockX Sync**
```
POST http://localhost:8000/api/v1/inventory/sync-from-stockx
```

#### 6. **Smart Pricing**
```
POST http://localhost:8000/api/v1/pricing/calculate
```

## 🔧 Manuelle Ausführung

### Test Mode (vor Aktivierung)
1. Im Workflow Editor: Klick auf **"Execute Workflow"** Button
2. Webhook ist dann 1x für Test-Aufruf bereit
3. Test mit:
```bash
curl -X POST http://localhost:5678/webhook-test/soleflip-inventory-check
```

### Production Mode (nach Aktivierung)
```bash
curl -X POST http://localhost:5678/webhook/soleflip-inventory-check
```

## 📊 Workflow Logic

```
Trigger (Schedule/Webhook)
    ↓
Get Stock Metrics
    ↓
Get Low Stock Items (threshold: 5)
    ↓
Check if Low Stock Exists
    ↓
    ├─→ YES:
    │   ├─→ Prepare Alert Data
    │   ├─→ Extract Item Details
    │   ├─→ Get Product Details
    │   ├─→ Reserve Stock (optional)
    │   ├─→ Sync from StockX
    │   ├─→ Calculate Smart Pricing
    │   └─→ Send Slack Notification
    │
    └─→ NO:
        └─→ No Action Required (healthy inventory)
```

## 🔔 Slack Notifications

Um Slack Notifications zu aktivieren:

1. Öffne Node: **"Send Slack Notification"**
2. Ersetze URL:
```json
"url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
```
3. Mit deiner Slack Webhook URL

## ✅ Aktueller Status (Phase 2)

**API Status**: ✅ Läuft auf http://localhost:8000
- ✅ Metrics Endpoint getestet
- ✅ Low-Stock Endpoint getestet
- ✅ Reserve Endpoint getestet
- ✅ Release Endpoint getestet

**Workflow Status**: ✅ Bereit zur Verwendung
- ✅ Alle Endpoints korrekt mit `/api/v1/` Prefix
- ✅ Content-Type Headers konfiguriert
- ✅ Query Parameters für Reserve/Release Endpoints

**Datenbank**:
- 1172 total inventory items
- 1110 verkaufte Items
- Ø Einkaufspreis: €160.23

## 🐛 Troubleshooting

### Workflow nicht erreichbar
```bash
# Prüfe ob n8n läuft
curl http://localhost:5678

# Prüfe Workflow Status in n8n UI
```

### API Fehler
```bash
# Prüfe ob SoleFlipper API läuft
curl http://localhost:8000/health

# API Logs checken
tail -f logs/soleflip.log
```

### "Unsupported content type" Fehler
- POST Requests brauchen `Content-Type: application/json` Header
- Bereits in Workflow konfiguriert ✅

## 📝 Nächste Schritte

1. **Workflow testen** mit manuellem Trigger
2. **Slack Webhook** konfigurieren (optional)
3. **Schedule anpassen** falls 24h zu lang/kurz ist
4. **Threshold anpassen** (aktuell: 5) je nach Business-Anforderungen

## 🔗 Weitere Dokumentationen

- API Docs: http://localhost:8000/docs
- n8n Docs: https://docs.n8n.io/
- Phase 2 Git Commits: `git log --oneline | grep "Phase 2"`
