# n8n Workflow Setup - Webgains Batch Profitability Import

## Übersicht

Dieser Workflow importiert automatisch profitable Produkte aus dem Webgains Feed in den SoleFlipper Katalog mit automatischer StockX Preis-Anreicherung.

## Workflow: Webgains Batch Profitability Import

**Datei**: `n8n-webgains-batch-profitability-workflow.json`

### Funktionsweise

1. **Schedule Trigger** - Läuft täglich um 2:00 Uhr morgens
2. **Fetch Webgains Feed** - Ruft Produktfeed von Webgains ab (Kategorie: Sneakers)
3. **Extract from File** - Extrahiert CSV Daten
4. **Map Feed Fields** - Mapped Webgains Felder zu internem Format
5. **Split in Batches** - Teilt in 500er Batches für effiziente Verarbeitung
6. **Prepare Batch** - Formatiert Daten für Profitability-Check
7. **Check Profitability** - Prüft Rentabilität via `/api/v1/pricing/evaluate-profitability-batch`
8. **Filter Profitable** - Filtert nur profitable Produkte (should_import=true)
9. **Import to Catalog** - Importiert in Katalog via `/api/v1/products/`

### Automatische Preis-Anreicherung

Der Endpoint `/api/v1/products/` enriched Produkte automatisch:

- **Mit market_price**: Nutzt den vom Profitability-Check berechneten Marktpreis
- **Ohne market_price + Premium Brand**: Fragt StockX API ab für:
  - Nike, Jordan, Adidas, Yeezy, New Balance, Asics
  - Puma, Reebok, Vans, Converse
  - Supreme, Off-White, Balenciaga, Gucci, Louis Vuitton, Dior, Prada

## Installation in n8n

1. Öffne n8n Interface (http://localhost:5678)
2. Klicke auf "+" → "Import from File"
3. Wähle `n8n-webgains-batch-profitability-workflow.json`
4. Workflow wird importiert und ist sofort einsatzbereit

## Konfiguration

### API Endpoint URL

Der Workflow nutzt: `http://157.90.21.65:8000`

Falls die API auf einer anderen URL läuft, passe diese Nodes an:
- **Check Profitability** (Node 7): `/api/v1/pricing/evaluate-profitability-batch`
- **Import to Catalog** (Node 9): `/api/v1/products/`

### Webgains Credentials

**Feed URL**: `https://platform-api.webgains.com/auth/publishers/78499/campaigns/173269/feeds/products`

Query Parameter:
- `feedIds[]=2211` - Specific Feed ID
- `format=csv` - CSV Format
- `categories[]=187` - Kategorie: Sneakers

### Schedule Anpassung

Standard: Täglich um 2:00 Uhr (`0 2 * * *`)

Zum Ändern:
1. Öffne **Schedule Trigger** Node
2. Passe Cron Expression an:
   - Jede Stunde: `0 * * * *`
   - Alle 6 Stunden: `0 */6 * * *`
   - Nur Werktags 2 Uhr: `0 2 * * 1-5`

## Testing

### Manueller Test

1. Öffne Workflow in n8n
2. Klicke "Execute Workflow"
3. Workflow läuft durch alle Nodes
4. Prüfe Output in jedem Node

### Test mit einzelnem Produkt

```bash
curl -X POST 'http://157.90.21.65:8000/api/v1/products/' \
  -H 'Content-Type: application/json' \
  -d '{
    "brand": "Nike",
    "model": "Air Jordan 1 Test",
    "sku": "TEST_123",
    "ean": "1234567890123",
    "supplier_price": 100,
    "currency": "EUR",
    "source": "webgains",
    "market_price": 150,
    "margin_percent": 33.3
  }'
```

**Erwartetes Ergebnis**:
```json
{
  "id": "uuid-here",
  "brand": "Nike",
  "name": "Air Jordan 1 Test",
  "sku": "TEST_123",
  "ean": "1234567890123",
  "retail_price": 150.0,
  "enriched": false,
  "message": "Product created"
}
```

## Monitoring

### Workflow Status in n8n

- **Executions** Tab zeigt alle Durchläufe
- Grün = Erfolgreich
- Rot = Fehler
- Klicke auf Execution für Details

### API Logs

```bash
# Live Logs ansehen
tail -f /var/log/soleflip/api.log

# Fehler filtern
grep ERROR /var/log/soleflip/api.log
```

### Datenbank Überprüfung

```sql
-- Anzahl importierter Produkte heute
SELECT COUNT(*)
FROM catalog.product
WHERE DATE(created_at) = CURRENT_DATE;

-- Neu importierte Produkte mit retail_price
SELECT COUNT(*)
FROM catalog.product
WHERE DATE(created_at) = CURRENT_DATE
  AND retail_price IS NOT NULL;

-- Durchschnittlicher Preis der heutigen Imports
SELECT AVG(retail_price) as avg_price,
       MIN(retail_price) as min_price,
       MAX(retail_price) as max_price
FROM catalog.product
WHERE DATE(created_at) = CURRENT_DATE;
```

## Troubleshooting

### Workflow startet nicht

1. Prüfe ob n8n läuft: `docker ps | grep n8n`
2. Prüfe Workflow Aktivierung: Toggle in n8n Interface
3. Prüfe Schedule Trigger Konfiguration

### Keine Produkte importiert

1. **Prüfe Webgains Feed**:
   ```bash
   curl "https://platform-api.webgains.com/auth/publishers/78499/campaigns/173269/feeds/products?feedIds[]=2211&format=csv&categories[]=187"
   ```

2. **Prüfe Profitability Endpoint**:
   ```bash
   curl -X POST 'http://157.90.21.65:8000/api/v1/pricing/evaluate-profitability-batch' \
     -H 'Content-Type: application/json' \
     -d '{"products": [{"ean": "test", "sku": "test", "supplier_price": 50, "brand": "Nike", "model": "Test"}]}'
   ```

3. **Prüfe Product Import Endpoint**:
   - Siehe "Test mit einzelnem Produkt" oben

### API Fehler 500

- Prüfe API Logs: `docker logs soleflip-api`
- Prüfe Datenbank Verbindung: `docker exec soleflip-api python -c "from shared.database.connection import db_manager; import asyncio; asyncio.run(db_manager.initialize())"`

### StockX Enrichment funktioniert nicht

1. **Prüfe StockX Credentials**:
   - `STOCKX_CLIENT_ID` in `.env`
   - `STOCKX_CLIENT_SECRET` in `.env`

2. **Test StockX API direkt**:
   ```python
   python -c "
   import asyncio
   from domains.integration.services.stockx_service import StockXService
   async def test():
       async with db_manager.get_session() as session:
           service = StockXService(session)
           await service.get_access_token()
   asyncio.run(test())
   "
   ```

3. **Rate Limiting**: StockX API hat Limits (60 req/min)
   - Workflow verarbeitet max 20 Produkte/Minute (3 API calls pro Produkt)

## Performance

### Erwartete Durchlaufzeiten

- **500 Produkte Feed**: ~5-10 Minuten
  - Fetch: ~10 Sekunden
  - Profitability Check: ~1 Sekunde (Batch)
  - Import: ~3-5 Minuten (mit StockX enrichment)

- **StockX Enrichment**: ~3 Sekunden pro Premium Brand Produkt
  - 3 API Calls: search (1s) + variants (1s) + market_data (1s)

### Batch Sizes

- **Split in Batches**: 500 Produkte pro Batch
  - Optimal für Memory und Performance
  - Bei größeren Feeds (>2000) auf 250 reduzieren

- **Profitability Check**: Max 1000 Produkte pro Request
  - Workflow sendet 500, Endpoint unterstützt bis 1000

## Erweiterungen

### Zusätzliche Supplier hinzufügen

1. Dupliziere Workflow
2. Ändere **Fetch Feed** Node URL
3. Passe **Map Feed Fields** für neues Format an
4. Ändere `source` Parameter in **Import to Catalog**

### Slack/Email Benachrichtigungen

Füge nach **Import to Catalog** Node hinzu:

1. **Function Node** für Summary:
```javascript
const imported = $input.all().length;
return [{json: {
  message: `✅ ${imported} profitable products imported`,
  timestamp: new Date().toISOString()
}}];
```

2. **Slack Node** oder **Email Node** für Notification

### Fehler-Handling

Füge **Error Trigger** Workflow hinzu:
1. Erstelle neuen Workflow: "Webgains Import - Error Handler"
2. Trigger: "Error Trigger" → Select "Webgains Batch Profitability Import"
3. Actions: Log to database, Send notification, etc.

## Wartung

### Regelmäßige Checks

- **Wöchentlich**: Prüfe Execution History in n8n
- **Monatlich**: Prüfe Import-Statistiken in Datenbank
- **Quartalsweise**: Review StockX Enrichment Rate

### Updates

- **Workflow**: Exportiere vor Änderungen → Sichere alte Version
- **API Endpoints**: Teste erst in Staging bevor Production Workflow updated wird
- **Dependencies**: n8n Updates können Node-Versionen betreffen

## Support

Bei Problemen:
1. Prüfe n8n Execution Logs
2. Prüfe API Logs (`/var/log/soleflip/`)
3. Prüfe Database für inkonsistente Daten
4. GitHub Issues: https://github.com/your-repo/issues
