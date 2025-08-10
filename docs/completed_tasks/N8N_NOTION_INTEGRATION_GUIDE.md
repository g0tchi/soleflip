# n8n-Notion Integration Guide für SoleFlipper

## 🔄 Übersicht

Diese Anleitung beschreibt die Integration zwischen SoleFlipper und Notion über n8n. Das System ermöglicht bidirektionale Synchronisation von Inventardaten, Brands und Analytics zwischen der SoleFlipper-API und Notion-Datenbanken.

**🎯 Verfügbare n8n-kompatible Endpoints:**
- ✅ Inventar-Export für Notion-Sync
- ✅ Brand-Analytics-Export
- ✅ Business Intelligence Dashboard
- ✅ Bidirektionale Sync-Webhooks

## 📊 Verfügbare API-Endpoints

### 1. **Inventar-Export** 
```
GET /api/v1/integration/webhooks/n8n/inventory/export
```

**Parameter:**
- `limit` (optional, default: 1000) - Anzahl der Datensätze
- `brand_filter` (optional) - Filter nach Brand-Namen
- `modified_since` (optional) - ISO-Format Datum für Updates

**Antwort-Format:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "sku": "ABC123",
      "product_name": "Air Jordan 1 Retro High",
      "brand": "Nike",
      "model": "Air Jordan 1",
      "colorway": "Bred",
      "size": "42",
      "condition": "new",
      "purchase_price": 150.00,
      "purchase_date": "2025-01-15T00:00:00",
      "status": "available",
      "title": "Nike Air Jordan 1 Retro High",
      "full_description": "Nike Air Jordan 1 Retro High - Size 42 - new"
    }
  ],
  "meta": {
    "total_records": 1,
    "export_timestamp": "2025-08-05T10:30:00"
  }
}
```

### 2. **Brand-Analytics-Export**
```
GET /api/v1/integration/webhooks/n8n/brands/export
```

**Antwort mit Business Intelligence:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "nike",
      "display_name": "Nike",
      "product_count": 380,
      "market_share_percent": 55.2,
      "average_price": 145.50,
      "title": "Nike",
      "description": "Nike - 380 products - 55.2% market share"
    }
  ]
}
```

### 3. **Analytics Dashboard**
```
GET /api/v1/integration/webhooks/n8n/analytics/dashboard
```

**KPI-Übersicht für Notion:**
```json
{
  "success": true,
  "data": {
    "title": "SoleFlipper Analytics Dashboard",
    "total_inventory_items": 2173,
    "portfolio_value": 125000.00,
    "average_item_price": 57.50,
    "active_brands": 40,
    "top_brand": "Nike",
    "top_brand_market_share": 55.2,
    "supplier_count": 3,
    "avg_supplier_rating": 4.7,
    "system_status": "operational"
  }
}
```

### 4. **Bidirektionale Sync**
```
POST /api/v1/integration/webhooks/n8n/notion/sync
```

**Payload für Updates:**
```json
{
  "action": "update_inventory",
  "item_id": "uuid",
  "updates": {
    "status": "sold",
    "notes": "Verkauft über StockX"
  }
}
```

## 🔧 n8n Workflow-Konfigurationen

### Workflow 1: **Inventar zu Notion sync**

**Trigger:** Zeitgesteuert (täglich)
```yaml
Workflow-Schritte:
1. HTTP Request → GET /api/v1/integration/webhooks/n8n/inventory/export
2. Notion (Update Database) → Sync zu Notion-Datenbank
3. Error Handling → Bei Fehlern E-Mail senden
```

**n8n HTTP Request Node:**
```json
{
  "method": "GET",
  "url": "http://soleflip-api:8000/api/v1/integration/webhooks/n8n/inventory/export",
  "parameters": {
    "limit": "500",
    "modified_since": "{{ $now.minus({days: 1}).toISO() }}"
  }
}
```

**Notion Database Properties:**
```
Title: Text (product_name)
Brand: Select (brand)
Size: Text (size)
Condition: Select (condition)
Price: Number (purchase_price)
Status: Select (status)
SKU: Text (sku)
Notes: Text (notes)
Updated: Date (updated_at)
```

### Workflow 2: **Brand-Analytics zu Notion**

**Trigger:** Zeitgesteuert (wöchentlich)
```yaml
1. HTTP Request → GET /api/v1/integration/webhooks/n8n/brands/export
2. Notion (Update Database) → Brand-Performance-Datenbank
3. Analytics Dashboard → GET /api/v1/integration/webhooks/n8n/analytics/dashboard
4. Notion (Update Page) → Dashboard-Seite aktualisieren
```

### Workflow 3: **Notion zu SoleFlipper sync**

**Trigger:** Notion Database Trigger (bei Updates)
```yaml
1. Notion Trigger → Erkennt Änderungen in Notion-DB
2. Transform Data → Daten für SoleFlipper formatieren
3. HTTP Request → POST /api/v1/integration/webhooks/n8n/notion/sync
4. Status Update → Bestätigung in Notion
```

## 📋 Notion-Datenbank-Setup

### 1. **Hauptinventar-Datenbank**

**Erforderliche Properties:**
```
Title: Text - Produktname
Brand: Select - Nike, Adidas, LEGO, etc.
Model: Text - Produktmodell
Size: Text - Größe
Condition: Select - new, used, deadstock
Purchase Price: Number - Einkaufspreis
Purchase Date: Date - Kaufdatum
Status: Select - available, sold, reserved
SKU: Text - Artikelnummer
Notes: Text - Notizen
Sync Status: Select - synced, pending, error
```

### 2. **Brand-Analytics-Datenbank**

**Properties:**
```
Brand Name: Title - Markenname
Product Count: Number - Anzahl Produkte
Market Share: Number - Marktanteil in %
Average Price: Number - Durchschnitts-Einkaufspreis
Last Updated: Date - Letzte Aktualisierung
Status: Select - active, inactive
```

### 3. **Dashboard-Page**

**Eingebettete Datenbank-Views:**
- Inventar-Übersicht (gefiltert nach Status)
- Top-Brands (sortiert nach Market Share)
- Neueste Zugänge (letzte 30 Tage)
- KPI-Callout-Boxes mit Portfolio-Werten

## ⚙️ n8n Node-Konfigurationen

### HTTP Request Node (für SoleFlipper API):
```json
{
  "authentication": "none",
  "requestMethod": "GET",
  "url": "http://soleflip-api:8000/api/v1/integration/webhooks/n8n/inventory/export",
  "options": {
    "timeout": 30000,
    "retry": {
      "enabled": true,
      "maxRetries": 3
    }
  }
}
```

### Notion Node (Database Update):
```json
{
  "authentication": "oAuth2",
  "operation": "updateDatabaseItem",
  "databaseId": "your-notion-database-id",
  "updateFields": {
    "Title": "={{ $json.title }}",
    "Brand": "={{ $json.brand }}",
    "Size": "={{ $json.size }}",
    "Price": "={{ $json.purchase_price }}",
    "Status": "={{ $json.status }}"
  }
}
```

### Error Handling Node:
```json
{
  "name": "Error Handler",
  "type": "n8n-nodes-base.emailSend",
  "parameters": {
    "subject": "SoleFlipper Sync Error",
    "text": "Error in workflow: {{ $json.error }}"
  }
}
```

## 🔄 Sync-Strategien

### 1. **Unidirectional (SoleFlipper → Notion)**
- Täglich: Inventar-Updates
- Wöchentlich: Brand-Analytics
- Monatlich: Vollständiger Datenabgleich

### 2. **Bidirectional (beide Richtungen)**
- Status-Updates von Notion zurück zu SoleFlipper
- Notizen und Kommentare synchronisieren
- Condition-Changes bidirektional

### 3. **Conflict Resolution**
- SoleFlipper ist "Source of Truth" für Preise/Daten
- Notion ist "Source of Truth" für Status/Notizen
- Timestamps für Last-Modified-Wins-Strategie

## 📈 Monitoring & Logging

### n8n Execution Monitoring:
```yaml
Success Rate: > 95%
Execution Time: < 30 Sekunden
Error Handling: E-Mail bei Fehlern
Retry Logic: 3 Versuche mit exponential backoff
```

### SoleFlipper API Logs:
```python
logger.info(
    "n8n sync completed",
    records_processed=len(items),
    sync_duration=duration,
    success_rate=success_rate
)
```

## 🚨 Fehlerbehandlung

### Häufige Probleme:

1. **API-Timeout:**
   - Lösung: Batch-Size reduzieren (limit Parameter)
   - Monitoring: Response Times überwachen

2. **Notion Rate Limits:**
   - Lösung: Delays zwischen Requests einbauen
   - n8n: Wait Node mit 1-2 Sekunden

3. **Datenformat-Konflikte:**
   - Lösung: Data Transformation Nodes in n8n
   - Validation vor Notion-Update

4. **Authentication Failure:**
   - Lösung: OAuth2 Token erneuern
   - n8n: Automatic token refresh aktivieren

## 🎯 Best Practices

### 1. **Performance Optimization:**
- Limit auf 500-1000 Datensätze pro Request
- modified_since Filter für incrementelle Updates
- Parallel processing für unabhängige Operationen

### 2. **Data Integrity:**
- Unique-IDs für Mapping zwischen Systemen
- Checksums für Datenintegrität
- Rollback-Mechanismen bei Fehlern

### 3. **Security:**
- API-Keys in n8n Environment Variables
- HTTPS für alle Requests
- Input Validation in SoleFlipper API

## 📊 Reporting & Analytics

### Notion Dashboard Widgets:
```
KPI Cards:
- Gesamtwert Portfolio
- Anzahl verfügbare Items
- Top-performing Brand
- Durchschnittlicher Item-Preis

Charts:
- Brand-Marktanteile (Pie Chart)
- Monatliche Käufe (Line Chart)
- Kategorie-Verteilung (Bar Chart)
- Size-Distribution (Table)
```

### n8n Workflow Metrics:
- Sync-Häufigkeit und -erfolg
- Datenvolumen pro Sync
- Error-Rates nach Endpoint
- Performance-Trends über Zeit

## 🚀 Deployment Checklist

### Vorbereitung:
- [ ] SoleFlipper API läuft und ist erreichbar
- [ ] Notion-Workspace eingerichtet mit Datenbanken
- [ ] n8n Instance konfiguriert und verbunden
- [ ] OAuth2-Authentication für Notion eingerichtet

### Testing:
- [ ] Manueller Test jeder API-Endpoint
- [ ] n8n Workflow-Tests mit Testdaten
- [ ] End-to-End-Test der kompletten Sync-Pipeline
- [ ] Error-Handling-Tests

### Production:
- [ ] Monitoring und Alerting eingerichtet
- [ ] Backup-Strategien für Notion-Daten
- [ ] Documentation für Team-Mitglieder
- [ ] Rollback-Pläne bei Problemen

---

## 💡 Erweiterte Funktionen

### Geplante Features:
1. **Real-time Webhooks** - Sofortige Updates bei Änderungen
2. **Conflict Resolution UI** - Interface für manuelle Konfliktlösung
3. **Advanced Filtering** - Komplexe Filter für Notion-Sync
4. **Bulk Operations** - Batch-Updates von Notion zurück zu SoleFlipper

### Custom Workflows:
1. **Sales Reporting** - Automatische Verkaufsberichte in Notion
2. **Inventory Alerts** - Benachrichtigungen bei niedrigen Beständen
3. **Price Updates** - Marktpreis-Monitoring und Updates
4. **Supplier Integration** - Supplier-Performance-Tracking in Notion

---

**🎯 Diese Integration ermöglicht eine nahtlose, bidirektionale Synchronisation zwischen SoleFlipper und Notion über n8n mit vollständiger Business Intelligence und Analytics-Unterstützung.**