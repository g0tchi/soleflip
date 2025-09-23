# 🚀 SoleFlipper StockX API Budibase App - Setup Guide

## 📋 Überblick

Diese Anleitung führt dich durch die Einrichtung einer vollständigen Budibase App für StockX API-Integration mit deiner bestehenden SoleFlipper-Infrastruktur.

## 🎯 App-Features

✅ **StockX Product Search** - Direkte Produktsuche über StockX API
✅ **QuickFlip Opportunities** - Arbitrage-Möglichkeiten Dashboard
✅ **Price Monitor** - Echtzeit-Preisüberwachung
✅ **Inventory Management** - Produktverwaltung
✅ **Analytics Dashboard** - Verkaufs- und Gewinn-Analyse

## 🔧 Setup-Schritte

### 1. Budibase App erstellen

1. **Neue App erstellen:**
   ```
   Budibase Builder → Create new app → "SoleFlipper StockX API"
   ```

2. **App-Konfiguration importieren:**
   - Importiere `stockx-api-app.json` als App-Template
   - Oder erstelle die App manuell mit den bereitgestellten Konfigurationen

### 2. Datenquellen einrichten

#### A) PostgreSQL Datenbank (bereits vorhanden)
```json
{
  "name": "SoleFlipper Database",
  "type": "postgres",
  "host": "localhost",
  "port": 5432,
  "database": "soleflip",
  "username": "{{ env.DB_USER }}",
  "password": "{{ env.DB_PASSWORD }}",
  "ssl": false
}
```

**Tabellen hinzufügen:**
- `products.products`
- `integration.market_prices`
- `sales.transactions`
- `inventory.stock_levels`

#### B) StockX REST API
```json
{
  "name": "StockX REST API",
  "type": "rest",
  "url": "https://gateway.stockx.com/api",
  "authentication": "Bearer Token",
  "token": "{{ env.STOCKX_API_TOKEN }}"
}
```

**Queries hinzufügen:** (siehe `stockx-api-connector.json`)
- `searchProducts`
- `getProductDetails`
- `getProductMarketData`
- `getProductHistory`
- `searchByBrand`

#### C) SoleFlipper Backend API
```json
{
  "name": "SoleFlipper Backend API",
  "type": "rest",
  "url": "http://127.0.0.1:8000/api/v1",
  "authentication": "None"
}
```

**Queries hinzufügen:** (siehe `soleflip-backend-connector.json`)
- `getQuickFlipOpportunities`
- `getOpportunitySummary`
- `getInventorySummary`
- `getDashboardData`

### 3. Environment Variables

Setze diese Umgebungsvariablen in Budibase:

```bash
# StockX API
STOCKX_API_TOKEN=your_stockx_api_token_here
STOCKX_CLIENT_ID=your_client_id
STOCKX_CLIENT_SECRET=your_client_secret

# Database
DB_USER=soleflip_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=soleflip

# SoleFlipper Backend
SOLEFLIP_API_URL=http://127.0.0.1:8000/api/v1
```

### 4. Screens erstellen

#### A) Dashboard Screen (`/`)
**Komponenten:**
- Header mit App-Titel
- 3-spaltige Card-Layout für KPIs
- QuickFlip Opportunities Summary
- Inventory Status
- Market Prices Overview

#### B) StockX Search Screen (`/stockx-search`)
**Komponenten:**
- Search Form (Product name/SKU)
- Filter Options (Brand, Category, Price range)
- Results Table mit StockX-Daten
- Product Detail Modal

#### C) QuickFlip Opportunities Screen (`/quickflip`)
**Komponenten:**
- Filter Form (Profit margin, Max price, Sources)
- Opportunities Table
- Profit Charts
- Action Buttons (Mark as acted)

#### D) Price Monitor Screen (`/price-monitor`)
**Komponenten:**
- Market Prices Table
- Source Filter
- Price History Charts
- Alert Configuration

#### E) Inventory Management Screen (`/inventory`)
**Komponenten:**
- Products Table
- Add/Edit Product Forms
- Stock Level Indicators
- Category Management

### 5. Automation & Workflows

#### A) Price Update Automation
```javascript
// Trigger: Webhook from SoleFlipper Backend
// Action: Refresh price monitor data
{
  "trigger": "webhook",
  "webhook_url": "/webhooks/price-update",
  "actions": [
    {
      "type": "refresh_datasource",
      "datasource": "postgres",
      "table": "integration.market_prices"
    },
    {
      "type": "send_notification",
      "message": "Price data updated"
    }
  ]
}
```

#### B) Opportunity Alert
```javascript
// Trigger: Scheduled (every 15 minutes)
// Action: Check for new high-profit opportunities
{
  "trigger": "schedule",
  "interval": "15 minutes",
  "actions": [
    {
      "type": "query_api",
      "datasource": "soleflip_api",
      "query": "getQuickFlipOpportunities",
      "parameters": {
        "min_profit_margin": 50
      }
    },
    {
      "type": "conditional",
      "condition": "{{ data.length > 0 }}",
      "true_action": {
        "type": "send_email",
        "subject": "High-Profit Opportunities Found!",
        "body": "{{ data.length }} opportunities with >50% margin"
      }
    }
  ]
}
```

### 6. Navigation & Routing

**Navigation Menu:**
```json
[
  {"text": "Dashboard", "url": "/", "icon": "Home"},
  {"text": "StockX Search", "url": "/stockx-search", "icon": "Search"},
  {"text": "QuickFlip", "url": "/quickflip", "icon": "TrendingUp"},
  {"text": "Price Monitor", "url": "/price-monitor", "icon": "BarChart"},
  {"text": "Inventory", "url": "/inventory", "icon": "Package"}
]
```

### 7. Styling & Theming

**Empfohlenes Theme:** `Midnight` oder `Business`

**Custom CSS:**
```css
/* QuickFlip Opportunity Cards */
.quickflip-card {
  border-left: 4px solid #10b981;
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
}

.high-profit {
  border-left-color: #059669 !important;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
}

/* Price Monitor Table */
.price-table {
  font-family: 'Monaco', 'Menlo', monospace;
}

.price-up { color: #059669; }
.price-down { color: #dc2626; }
.price-stable { color: #6b7280; }
```

### 8. Testing & Validierung

#### A) Datenquelle testen
1. **PostgreSQL**: Query auf `products.products` ausführen
2. **StockX API**: Produktsuche mit "Jordan 1" testen
3. **SoleFlipper API**: QuickFlip Summary abrufen

#### B) Screen-Funktionalität
1. Dashboard lädt alle KPI-Cards
2. StockX Search gibt Ergebnisse zurück
3. QuickFlip Table zeigt Opportunities
4. Filter funktionieren korrekt

#### C) Performance
- Queries unter 2 Sekunden
- Tables laden max. 100 Rows initial
- Pagination für große Datensätze

### 9. Deployment & Produktion

#### A) Environment Setup
```bash
# Production Environment Variables
NODE_ENV=production
STOCKX_API_TOKEN=prod_token_here
DB_HOST=prod_db_host
ENABLE_ANALYTICS=true
```

#### B) Security
- API Rate Limiting aktivieren
- CORS korrekt konfigurieren
- Sensitive Daten über Environment Variables

#### C) Monitoring
- API Response Times überwachen
- Error Rates tracken
- User Activity Analytics

## 🔄 Wartung & Updates

### Regelmäßige Tasks
- **Täglich**: Price Data Sync prüfen
- **Wöchentlich**: API Rate Limits überwachen
- **Monatlich**: Performance Review

### Backup & Recovery
- Database Backups automatisieren
- Budibase App Export regelmäßig erstellen
- API Credentials sicher speichern

## 🆘 Troubleshooting

### Häufige Probleme

**1. StockX API Connection Failed**
```bash
# Lösung: Token prüfen
curl -H "Authorization: Bearer $STOCKX_API_TOKEN" https://gateway.stockx.com/api/health
```

**2. PostgreSQL Connection Error**
```bash
# Lösung: DB-Credentials validieren
psql -h localhost -U soleflip_user -d soleflip -c "SELECT version();"
```

**3. QuickFlip Opportunities leer**
```bash
# Lösung: Market Prices prüfen
curl http://127.0.0.1:8000/api/v1/quickflip/import/stats
```

### Debug-Modus
```javascript
// In Budibase Console
console.log("StockX Response:", {{ stockx_data }});
console.log("QuickFlip Data:", {{ quickflip_data }});
```

## 📞 Support

Bei Problemen:
1. Budibase Logs prüfen
2. SoleFlipper Backend Logs checken
3. StockX API Status überprüfen
4. GitHub Issues für Budibase-spezifische Probleme

---

**🎉 Viel Erfolg mit deiner SoleFlipper StockX API Budibase App!**