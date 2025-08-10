# SoleFlipper n8n-Modul - Implementierungsanleitung

## 📋 Übersicht

Das n8n-Modul für SoleFlipper ermöglicht die nahtlose Integration zwischen der SoleFlipper-API und externen Systemen wie Notion über n8n-Workflows. Dieses Modul erweitert die bestehende SoleFlipper-API um spezielle Endpoints, die für n8n-Automatisierung optimiert sind.

## 🏗️ Architektur

### Modulstruktur
```
domains/integration/api/
├── webhooks.py          # Haupt-API-Endpoints
├── __init__.py
└── services/
    ├── import_processor.py
    ├── transformers.py
    └── validators.py
```

### Integration in SoleFlipper
Das Modul wird automatisch beim Start der FastAPI-Anwendung geladen:
```python
# main.py - Zeile 61-65
from domains.integration.api.webhooks import webhook_router
app.include_router(webhook_router, prefix="/api/v1/integration", tags=["Integration"])
```

## 🔧 Installation & Setup

### 1. Voraussetzungen
- SoleFlipper-System läuft bereits
- PostgreSQL-Datenbank mit Analytics-Views
- Python 3.11+ mit FastAPI
- n8n-Instance (lokal oder cloud)

### 2. Modul aktivieren
Das Modul ist bereits in SoleFlipper integriert. Beim Start der Anwendung werden die n8n-Endpoints automatisch verfügbar:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Überprüfung der verfügbaren Endpoints:
```bash
curl http://localhost:8000/docs
```

### 3. Endpoints verifizieren
```bash
# Test Brand-Export
curl "http://localhost:8000/api/v1/integration/n8n/brands/export"

# Test Analytics Dashboard
curl "http://localhost:8000/api/v1/integration/n8n/analytics/dashboard"
```

## 📡 API-Endpoints Referenz

### 1. Inventar-Export
```
GET /api/v1/integration/n8n/inventory/export
```

**Parameter:**
- `limit` (optional): Anzahl Datensätze (default: 1000)
- `brand_filter` (optional): Filter nach Markenname
- `modified_since` (optional): ISO-Datum für Updates seit

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "sku": "NIKE-001",
      "product_name": "Air Jordan 1 Retro High",
      "brand": "Nike",
      "size": "42",
      "quantity": 1,
      "purchase_price": 150.00,
      "purchase_date": "2025-01-15T00:00:00",
      "status": "available",
      "title": "Nike Air Jordan 1 Retro High",
      "full_description": "Nike Air Jordan 1 Retro High - Size 42 - Qty: 1"
    }
  ],
  "meta": {
    "total_records": 1,
    "export_timestamp": "2025-08-05T10:30:00"
  }
}
```

### 2. Brand-Analytics-Export
```
GET /api/v1/integration/n8n/brands/export
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "nike",
      "slug": "nike",
      "product_count": 1181,
      "market_share_percent": 54.3,
      "average_price": 145.50,
      "title": "Nike",
      "description": "Nike - 1181 products - 54.3% market share"
    }
  ]
}
```

### 3. Analytics Dashboard
```
GET /api/v1/integration/n8n/analytics/dashboard
```

**Response:**
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
    "top_brand_market_share": 54.3,
    "supplier_count": 3,
    "avg_supplier_rating": 4.7,
    "system_status": "operational"
  }
}
```

### 4. Bidirektionaler Sync
```
POST /api/v1/integration/n8n/notion/sync
```

**Request Body:**
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

## 🔄 n8n-Integration

### n8n HTTP Request Node Konfiguration

#### Inventar-Export Node:
```json
{
  "method": "GET",
  "url": "http://soleflip-api:8000/api/v1/integration/n8n/inventory/export",
  "parameters": {
    "limit": "500",
    "modified_since": "{{ $now.minus({days: 1}).toISO() }}"
  },
  "options": {
    "timeout": 30000,
    "retry": {
      "enabled": true,
      "maxRetries": 3
    }
  }
}
```

#### Brand-Analytics Node:
```json
{
  "method": "GET", 
  "url": "http://soleflip-api:8000/api/v1/integration/n8n/brands/export",
  "authentication": "none"
}
```

### Datenaufbereitung für Notion

#### Transform Node (JavaScript):
```javascript
// Transform SoleFlipper data for Notion
const items = $input.all();
const notionData = [];

for (const item of items) {
  const data = item.json.data;
  
  for (const record of data) {
    notionData.push({
      // Notion Database Properties
      "Title": record.title,
      "Brand": record.brand,
      "Size": record.size,
      "Price": record.purchase_price,
      "Status": record.status,
      "SKU": record.sku,
      "Last Updated": new Date().toISOString()
    });
  }
}

return notionData.map(item => ({ json: item }));
```

## 🗄️ Notion-Integration

### Datenbank-Setup

#### Inventar-Datenbank Properties:
```
Title: Title (Text)
Brand: Select (Nike, Adidas, LEGO, etc.)
Model: Text
Size: Text  
Condition: Select (new, used, deadstock)
Purchase Price: Number
Purchase Date: Date
Status: Select (available, sold, reserved)
SKU: Text
Notes: Text
Sync Status: Select (synced, pending, error)
Last Updated: Date
```

#### Brand-Analytics-Datenbank:
```
Brand Name: Title (Text)
Product Count: Number
Market Share: Number (%)
Average Price: Number (€)
Status: Select (active, inactive)
Last Updated: Date
Description: Text
```

### Notion API Node Konfiguration:
```json
{
  "authentication": "oAuth2",
  "operation": "updateDatabaseItem", 
  "databaseId": "your-notion-database-id",
  "updateFields": {
    "Title": "={{ $json.Title }}",
    "Brand": "={{ $json.Brand }}",
    "Size": "={{ $json.Size }}",
    "Price": "={{ $json.Price }}",
    "Status": "={{ $json.Status }}"
  }
}
```

## 🚨 Fehlerbehandlung

### HTTP Error Codes
- `400`: Ungültige Parameter oder Request-Format
- `404`: Endpoint nicht gefunden  
- `500`: Interne Server-Fehler (Datenbank-Probleme)

### Retry-Logic in n8n:
```json
{
  "retry": {
    "enabled": true,
    "maxRetries": 3,
    "retryInterval": 1000,
    "retryMultiplier": 2
  }
}
```

### Error Handler Node:
```javascript
// n8n Error Handler
if ($input.first().error) {
  return {
    json: {
      error: true,
      message: $input.first().error.message,
      timestamp: new Date().toISOString(),
      endpoint: $workflow.name
    }
  };
}
```

## 📊 Monitoring & Logging

### API-seitige Logs
Das Modul verwendet strukturiertes Logging:
```python
logger.info(
    "n8n inventory export requested",
    brand_filter=brand_filter,
    limit=limit,
    modified_since=modified_since
)
```

### n8n Workflow Monitoring
- Execution History prüfen
- Error-Rates überwachen  
- Performance-Metriken tracken

### Health Check:
```bash
curl "http://localhost:8000/health"
```

## 🔧 Erweiterte Konfiguration

### Custom Filter Implementation:
```python
# Erweiterte Filter in webhooks.py
if category_filter:
    conditions.append(
        Category.name.ilike(f"%{category_filter}%")
    )

if price_range:
    min_price, max_price = price_range.split(',')
    conditions.append(
        InventoryItem.purchase_price.between(float(min_price), float(max_price))
    )
```

### Rate Limiting (optional):
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@limiter.limit("100/minute")
async def n8n_inventory_export(...):
    # Endpoint logic
```

## 🚀 Production Deployment

### Environment Variables:
```bash
# .env
DATABASE_URL=postgresql://user:pass@host:port/db
N8N_WEBHOOK_SECRET=your-secret-key
LOG_LEVEL=INFO
```

### Docker Deployment:
```yaml
# docker-compose.yml
version: '3.8'
services:
  soleflip-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - db
      
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=password
    volumes:
      - n8n_data:/root/.n8n
```

### Health Checks:
```bash
# API Health
curl -f http://localhost:8000/health || exit 1

# n8n Health  
curl -f http://localhost:5678/healthz || exit 1
```

## 📈 Performance Optimierung

### Database Query Optimization:
- Verwendung von Indizes auf häufig gefilterten Feldern
- LIMIT und OFFSET für Pagination
- JOIN-Optimierung mit EXPLAIN ANALYZE

### Caching (optional):
```python
from functools import lru_cache

@lru_cache(maxsize=100, ttl=300)  # 5 Minuten Cache
async def get_brands_cached():
    # Brand-Export mit Caching
    pass
```

### Batch Processing:
```python
# Große Datensätze in Chunks verarbeiten
async def export_inventory_batched(limit=1000):
    offset = 0
    while True:
        batch = await get_inventory_batch(offset, 1000)
        if not batch:
            break
        yield batch
        offset += 1000
```

## 🧪 Testing

### Unit Tests:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_inventory_export():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/integration/n8n/inventory/export?limit=5")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) <= 5
```

### Integration Tests:
```bash
# Test kompletter Workflow
curl -X GET "http://localhost:8000/api/v1/integration/n8n/brands/export" | \
jq '.data[0]' | \
curl -X POST "http://n8n:5678/webhook/test" -d @-
```

## 📚 Weitere Ressourcen

### Dokumentation:
- `N8N_NOTION_INTEGRATION_GUIDE.md` - Detaillierte Workflow-Konfiguration
- FastAPI Docs: `http://localhost:8000/docs`
- OpenAPI Schema: `http://localhost:8000/openapi.json`

### Support:
- SoleFlipper API-Logs: `logs/soleflip.log`
- n8n Execution History: n8n Web Interface
- Database Queries: PostgreSQL Logs

---

## 🎯 Zusammenfassung

Das n8n-Modul bietet:
- **4 produktionsreife API-Endpoints** für Datenexport und -sync
- **Nahtlose n8n-Integration** mit vorkonfigurierten Node-Beispielen  
- **Notion-optimierte Datenformate** für direkte Database-Updates
- **Comprehensive Error Handling** und Monitoring
- **Skalierbare Architektur** für große Datenmengen

**Das Modul ist sofort einsatzbereit und ermöglicht professionelle Automatisierung zwischen SoleFlipper und externen Systemen über n8n.**