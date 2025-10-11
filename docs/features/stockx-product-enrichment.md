# StockX Product Enrichment - Feature Documentation

**Version:** 2.2.7
**Date:** 2025-10-10
**Status:** ✅ Production Ready

## 📋 Übersicht

Das StockX Product Enrichment System ermöglicht die automatische Anreicherung von Produktdaten mit detaillierten Informationen aus der StockX Catalog API v2. Es werden Produktdetails, Varianten (Größen), Marktdaten und Preisempfehlungen abgerufen und in der Datenbank gespeichert.

## 🎯 Features

### 1. **Catalog Search API**
- Suche nach Produkten via SKU, GTIN, Style-ID oder Freitext
- Paginierte Ergebnisse (max 50 pro Seite)
- Kein Datenbank-Update - reine Suchfunktion

### 2. **Product Enrichment**
- Vollautomatische Anreicherung mit einem API-Call
- Speichert alle Daten in der Datenbank
- Optional: Marktdaten für spezifische Größe

### 3. **Product Details API**
- Detaillierte Produktinformationen
- Brand, Style-Code, Release-Date, Retail Price
- Product Attributes (Gender, Color, Colorway)

### 4. **Product Variants API**
- Alle verfügbaren Größen für ein Produkt
- Complete Size Charts (US, UK, EU, CM, KR)
- GTINs (UPC/EAN) für jede Größe
- Flex & Direct Eligibility Status

### 5. **Market Data API**
- Live-Marktdaten für spezifische Größe
- Lowest Ask & Highest Bid
- StockX Preisempfehlungen:
  - **Sell Faster:** Schneller verkaufen
  - **Earn More:** Maximaler Gewinn
- Unterstützt mehrere Währungen (EUR, USD, GBP, etc.)

## 🗄️ Datenbank Schema

### Neue Felder in `products.products` Tabelle

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `stockx_product_id` | VARCHAR(100) | StockX Produkt-ID |
| `style_code` | VARCHAR(200) | Hersteller Style-Code (z.B. Nike/Adidas) |
| `enrichment_data` | JSONB | Komplette StockX Daten (Details, Varianten, etc.) |
| `lowest_ask` | NUMERIC(10,2) | Aktueller niedrigster Ask-Preis |
| `highest_bid` | NUMERIC(10,2) | Aktueller höchster Bid-Preis |
| `recommended_sell_faster` | NUMERIC(10,2) | StockX Empfehlung für schnellen Verkauf |
| `recommended_earn_more` | NUMERIC(10,2) | StockX Empfehlung für maximalen Gewinn |
| `last_enriched_at` | TIMESTAMP | Zeitstempel der letzten Anreicherung |

**Indexes:**
- `ix_products_stockx_product_id` - Schnelle Lookups
- `ix_products_last_enriched_at` - Identifikation veralteter Daten

## 🔌 API Endpoints

### Base URL
```
http://localhost:8000/api/v1/products
```

### 1. Search Catalog

**Endpoint:** `GET /catalog/search`

**Parameter:**
- `query` (required) - SKU, GTIN, Style-ID oder Produktname
- `page_number` (optional, default: 1) - Seitennummer
- `page_size` (optional, default: 10, max: 50) - Ergebnisse pro Seite

**Beispiel:**
```bash
curl "http://localhost:8000/api/v1/products/catalog/search?query=JH9768&page_size=3"
```

**Response:**
```json
{
    "success": true,
    "query": "JH9768",
    "pagination": {
        "page_number": 1,
        "page_size": 3,
        "total_results": 12,
        "has_next_page": true
    },
    "products": [
        {
            "productId": "d9c9178b-730c-4085-8911-0efb94257fd7",
            "title": "adidas Campus 00s Leopard Black (Women's)",
            "brand": "adidas",
            "styleId": "JH9768",
            "productType": "sneakers"
        }
    ]
}
```

---

### 2. Enrich Product by SKU

**Endpoint:** `POST /catalog/enrich-by-sku`

**Parameter:**
- `sku` (required) - Produkt-SKU
- `size` (optional) - Spezifische Größe für Marktdaten

**Header:**
- `Content-Type: application/json`

**Beispiel:**
```bash
curl -X POST \
  "http://localhost:8000/api/v1/products/catalog/enrich-by-sku?sku=JH9768&size=38" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
    "success": true,
    "message": "Product enrichment completed successfully",
    "data": {
        "sku": "JH9768",
        "stockx_product_id": "d9c9178b-730c-4085-8911-0efb94257fd7",
        "product_title": "adidas Campus 00s Leopard Black (Women's)",
        "brand": "adidas",
        "total_variants": 15,
        "market_data_available": true,
        "lowest_ask": 75.00,
        "enrichment_timestamp": "2025-10-10T19:30:00Z"
    },
    "full_data": {
        "product_details": { ... },
        "variants": [ ... ],
        "market_data": { ... }
    }
}
```

---

### 3. Get Product Details

**Endpoint:** `GET /catalog/products/{product_id}`

**Beispiel:**
```bash
curl "http://localhost:8000/api/v1/products/catalog/products/d9c9178b-730c-4085-8911-0efb94257fd7"
```

**Response:**
```json
{
    "success": true,
    "product": {
        "productId": "d9c9178b-730c-4085-8911-0efb94257fd7",
        "brand": "adidas",
        "styleId": "JH9768",
        "title": "adidas Campus 00s Leopard Black (Women's)",
        "productType": "sneakers",
        "productAttributes": {
            "gender": "women",
            "releaseDate": "2025-01-30",
            "retailPrice": 120,
            "colorway": "Core White/Core Black/Footwear White"
        },
        "isFlexEligible": true,
        "isDirectEligible": true
    }
}
```

---

### 4. Get Product Variants

**Endpoint:** `GET /catalog/products/{product_id}/variants`

**Beispiel:**
```bash
curl "http://localhost:8000/api/v1/products/catalog/products/d9c9178b-730c-4085-8911-0efb94257fd7/variants"
```

**Response:**
```json
{
    "success": true,
    "product_id": "d9c9178b-730c-4085-8911-0efb94257fd7",
    "total_variants": 15,
    "variants": [
        {
            "variantId": "cc38fede-f0e6-4a3c-8267-dddbdc413b5b",
            "variantValue": "6.5W",
            "sizeChart": {
                "defaultConversion": {"size": "6.5W", "type": "us w"},
                "availableConversions": [
                    {"size": "US W 6.5", "type": "us w"},
                    {"size": "UK 5", "type": "uk"},
                    {"size": "EU 38", "type": "eu"},
                    {"size": "CM 23.5", "type": "cm"}
                ]
            },
            "gtins": [
                {"identifier": "197611157695", "type": "UPC"},
                {"identifier": "4067898529262", "type": "EAN-13"}
            ],
            "isFlexEligible": true,
            "isDirectEligible": true
        }
    ]
}
```

---

### 5. Get Market Data for Variant

**Endpoint:** `GET /catalog/products/{product_id}/variants/{variant_id}/market-data`

**Parameter:**
- `currency_code` (optional, default: EUR) - Währung (EUR, USD, GBP, etc.)

**Beispiel:**
```bash
curl "http://localhost:8000/api/v1/products/catalog/products/d9c9178b-730c-4085-8911-0efb94257fd7/variants/cc38fede-f0e6-4a3c-8267-dddbdc413b5b/market-data?currency_code=EUR"
```

**Response:**
```json
{
    "success": true,
    "product_id": "d9c9178b-730c-4085-8911-0efb94257fd7",
    "variant_id": "cc38fede-f0e6-4a3c-8267-dddbdc413b5b",
    "currency": "EUR",
    "market_data": {
        "lowest_ask": "63",
        "highest_bid": null,
        "sell_faster_price": "22",
        "earn_more_price": "58",
        "flex_lowest_ask": null
    },
    "full_data": {
        "standardMarketData": { ... },
        "flexMarketData": { ... },
        "directMarketData": { ... }
    }
}
```

## 🚀 Bulk Enrichment

### Script für Bulk-Verarbeitung

**Location:** `scripts/bulk_enrich_last_30_products.py`

**Features:**
- Automatisches Enrichment mehrerer Produkte
- Rate Limiting (1.2s zwischen Requests)
- Detaillierte Fortschrittsanzeige
- Error Handling & Retry Logic
- Zusammenfassung am Ende

**Verwendung:**
```bash
python -m scripts.bulk_enrich_last_30_products
```

**Output:**
```
================================================================================
StockX Catalog Bulk Enrichment - Last 30 Products
================================================================================

[1/30] Enriching: TW2V50800U8 - Timex Timex Camper...
  [OK] SUCCESS: Timex Camper x Stranger Things TW2V50800YB
    StockX ID: f424f1cc-426e-4f99-8d0d-6fbb27ad8a52
    Variants: 1

[2/30] Enriching: 1203A388-100 - Asics Gel-Kayano 20...
  [OK] SUCCESS: ASICS Gel-Kayano 20 White Pure Silver
    StockX ID: b0103b1c-e821-45c9-90f7-ccca22152054
    Variants: 20

...

================================================================================
ENRICHMENT COMPLETE
================================================================================
Total products processed: 30
  [OK] Successfully enriched: 23
  [X] Not found on StockX: 5
  [X] Errors: 2

Duration: 42.3 seconds (0.7 minutes)
Average: 1.4 seconds per product
```

## 📊 Test Ergebnisse

### Erfolgreiche Tests

**Datum:** 2025-10-10

| Test | Status | Details |
|------|--------|---------|
| Catalog Search | ✅ | 96,601 Ergebnisse für "0329475-7" |
| Product Enrichment | ✅ | The North Face Nuptse Jacket enriched |
| Product Details | ✅ | adidas Campus 00s Details abgerufen |
| Product Variants | ✅ | 15 Varianten geladen |
| Market Data | ✅ | Live-Preise für Größe 6.5W (EUR 63) |
| Bulk Enrichment | ✅ | 23 von 30 Produkten erfolgreich |

### Enrichment Statistik

**Aktueller Stand:**
- **23 von 905 Produkten** enriched (2.5%)
- **Durchschnittliche Dauer:** 1.4 Sekunden pro Produkt
- **Rate Limit Einhaltung:** 1.2 Sekunden zwischen Requests
- **Erfolgsrate:** 77% (23 von 30 getesteten Produkten)

### Beispiel-Produkte

| SKU | Produkt | Varianten | Status |
|-----|---------|-----------|--------|
| TW2V50800U8 | Timex Camper x Stranger Things | 1 | ✅ |
| 1203A388-100 | ASICS Gel-Kayano 20 | 20 | ✅ |
| JH9768 | adidas Campus 00s Leopard Black | 15 | ✅ |
| 845053-201-v2 | Nike Air Force 1 Low Linen | 27 | ✅ |
| 0329475-7 | The North Face 1996 Retro Nuptse | 8 | ✅ |

## ⚠️ Rate Limits

**StockX API Rate Limits:**
- **25,000 Requests pro 24 Stunden**
- **1 Request pro Sekunde**

**Unser System:**
- ✅ 1.2 Sekunden zwischen Requests (20% Buffer)
- ✅ Automatisches Token Refresh
- ✅ Error Handling bei Rate Limit Überschreitung

**Berechnung:**
- Bei 1.2s pro Request: **72,000 Sekunden = 20 Stunden** für alle 905 Produkte
- **Sicher innerhalb des 24-Stunden-Limits**

## 🔧 Service-Architektur

### StockXCatalogService

**Location:** `domains/integration/services/stockx_catalog_service.py`

**Methoden:**
```python
# Suche
async def search_catalog(query, page_number=1, page_size=10) -> Dict

# Produktdetails
async def get_product_details(product_id) -> Dict

# Varianten
async def get_product_variants(product_id) -> List[Dict]

# Marktdaten
async def get_market_data(product_id, variant_id, currency_code="EUR") -> Dict

# Vollständiges Enrichment
async def enrich_product_by_sku(sku, size=None, db_session=None) -> Dict
```

## 🐛 Bekannte Probleme & Lösungen

### 1. Style-Code zu lang
**Problem:** Manche Produkte haben sehr lange Style-Codes (>50 Zeichen)
**Lösung:** ✅ Feld vergrößert auf VARCHAR(200) (Migration: `1eecf0cb7df3`)

**Beispiel:**
```
The North Face Nuptse: NF0A3C8DLE41/NF0A3C8DJK3/NFOA3C8DLE4-M/NF0A3C8D4G3/NF0A3C8DGOE1/NF0A3C8DGOE
```

### 2. Produkt nicht auf StockX gefunden
**Problem:** Manche SKUs existieren nicht in der StockX Datenbank
**Lösung:** ✅ Fehler wird abgefangen, Script macht mit nächstem Produkt weiter

### 3. Content-Type Header fehlt
**Problem:** POST-Requests ohne Content-Type Header werden abgelehnt
**Lösung:** ✅ Immer `Content-Type: application/json` Header setzen

## 📈 Nächste Schritte

### Geplante Erweiterungen

1. **Automatisches Re-Enrichment**
   - Tägliche Aktualisierung der Marktdaten
   - Priorisierung nach `last_enriched_at`

2. **Batch-Enrichment mit Prioritäten**
   - Zuerst: Produkte ohne Enrichment
   - Dann: Veraltete Enrichment-Daten (>7 Tage)

3. **Dashboard Integration**
   - Enrichment-Status Anzeige
   - Manuelle Trigger-Buttons
   - Fortschritts-Tracking

4. **Webhook-Support**
   - Benachrichtigung bei erfolgreicher Enrichment
   - Fehler-Alerts

## 🔐 Sicherheit

- ✅ API Keys verschlüsselt in Datenbank
- ✅ Automatisches Token Refresh
- ✅ Rate Limiting eingehalten
- ✅ SQL Injection Prevention (Parameterized Queries)
- ✅ Error Handling ohne sensitive Daten in Logs

## 📝 Migrations

### Migration: `e6afd519c0a5` - Add Product Enrichment Fields
**Datum:** 2025-10-10 19:11
**Beschreibung:** Fügt 8 neue Felder für Enrichment-Daten hinzu

### Migration: `1eecf0cb7df3` - Increase Style Code Length
**Datum:** 2025-10-10 20:02
**Beschreibung:** Vergrößert `style_code` von VARCHAR(50) auf VARCHAR(200)

## 🎓 Verwendungsbeispiele

### Use Case 1: Einzelnes Produkt enrichen
```python
from domains.integration.services.stockx_service import StockXService
from domains.integration.services.stockx_catalog_service import StockXCatalogService

# Initialize
stockx_service = StockXService(db_session=session)
catalog_service = StockXCatalogService(stockx_service)

# Enrich
result = await catalog_service.enrich_product_by_sku(
    sku="JH9768",
    size="38",
    db_session=session
)
```

### Use Case 2: Nur Suchen (kein DB-Update)
```python
# Search only
results = await catalog_service.search_catalog(
    query="Nike Air Force 1",
    page_size=20
)

for product in results['products']:
    print(f"{product['title']} - {product['styleId']}")
```

### Use Case 3: Marktdaten für alle Größen
```python
# Get all variants
variants = await catalog_service.get_product_variants(product_id)

# Get market data for each
for variant in variants:
    market_data = await catalog_service.get_market_data(
        product_id=product_id,
        variant_id=variant['variantId'],
        currency_code="EUR"
    )
    print(f"Size {variant['variantValue']}: {market_data['lowestAskAmount']} EUR")
```

## 📞 Support

**Dokumentation:** `/docs/features/stockx-product-enrichment.md`
**API Docs:** `http://localhost:8000/docs` (FastAPI Swagger UI)
**Logs:** Check `structlog` output für detaillierte Informationen

---

**Erstellt:** 2025-10-10
**Version:** 2.2.7
**Status:** ✅ Production Ready
