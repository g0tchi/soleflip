# n8n Workflows für SoleFlipper

## StockX Profit Checker Workflow

Automatischer Workflow der alle 6 Stunden:
1. Produkte aus dem Catalog abruft
2. Aktuelle StockX Marktpreise holt
3. Profit-Margen berechnet
4. Profitable Deals (>25% ROI) identifiziert
5. Alerts speichert

### Installation

#### 1. SQL-Tabelle erstellen
```bash
docker exec -i soleflip-postgres psql -U soleflip -d soleflip < n8n-workflows/profit_alerts_table.sql
```

#### 2. PostgreSQL Credential in n8n einrichten
1. Öffne n8n: http://localhost:5678
2. Gehe zu Settings → Credentials
3. Klicke "Add Credential" → "Postgres"
4. Name: `SoleFlipper PostgreSQL`
5. Konfiguration:
   - Host: `soleflip-postgres` (Docker network)
   - Database: `soleflip`
   - User: `soleflip`
   - Password: `SoleFlip2025SecureDB!`
   - Port: `5432`
   - SSL: Disabled
6. Speichern

#### 3. Workflow importieren
1. In n8n: Workflows → Import
2. Datei auswählen: `n8n-workflows/stockx-profit-checker.json`
3. Import bestätigen
4. Workflow aktivieren (Toggle oben rechts)

### Workflow-Logik

**Nodes:**
- **Every 6 Hours**: Schedule Trigger (alle 6 Stunden)
- **Get Products**: Holt bis zu 20 enrichte Produkte aus catalog.product
- **Get StockX Market Data**: Ruft aktuelle Preise von StockX API
- **Calculate Profits**: JavaScript-Berechnung mit:
  - Durchschnittlicher EK: €55
  - StockX Gebühren: 12.5%
  - Min ROI Filter: 25%
  - Alert Priority: HIGH (>50%), MEDIUM (>35%), LOW (>25%)

**Output:**
Alle profitable Deals werden mit folgenden Infos ausgegeben:
- product_name, sku, variant_id
- lowest_ask, sell_faster, earn_more
- estimated_cost, stockx_fees, net_proceeds
- profit, roi_percentage, alert_priority

### Profit Alerts abfragen

```sql
-- Alle High-Priority Deals der letzten 24h
SELECT * FROM analytics.profit_opportunities
WHERE alert_priority = 'HIGH'
AND checked_at > NOW() - INTERVAL '24 hours'
ORDER BY roi_percentage DESC;

-- Top 10 profitable Deals
SELECT
    product_name,
    sku,
    lowest_ask,
    profit,
    roi_percentage,
    alert_priority
FROM analytics.profit_opportunities
ORDER BY roi_percentage DESC
LIMIT 10;
```

### Anpassungen

**EK ändern** (Code Node, Zeile 6):
```javascript
const avgPurchasePrice = 55; // Dein durchschnittlicher Einkaufspreis
```

**Min ROI ändern** (Code Node, Zeile 8):
```javascript
const minROI = 25; // Minimum ROI % für Alert
```

**Schedule ändern** (Schedule Trigger):
- Täglich: `{"field": "days", "daysInterval": 1}`
- Stündlich: `{"field": "hours", "hoursInterval": 1}`
- Alle 12h: `{"field": "hours", "hoursInterval": 12}`

### Erweiterte Workflows (Coming Soon)

- **Price Drop Alerts**: Benachrichtigung bei Preissenkungen
- **Inventory Auto-Sync**: Automatisches Hinzufügen zu Inventory
- **Multi-Platform Checker**: eBay + GOAT Integration
- **Telegram Notifications**: Real-time Alerts auf Telegram

## Troubleshooting

**Workflow läuft nicht?**
- Check PostgreSQL Credential ist korrekt
- Verify soleflip-api Container läuft
- Test: `curl http://localhost:8000/health`

**Keine Ergebnisse?**
- Prüfe ob Produkte im Catalog sind mit `sku IS NOT NULL`
- Min ROI zu hoch? Senke auf 20% oder 15%
- Erhöhe LIMIT in "Get Products" Node

**Fehler in Code Node?**
- Check Browser Console in n8n
- Validate JSON output from StockX API
