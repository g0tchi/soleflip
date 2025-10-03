# 🚀 Supplier Price Import - 5 Minute Quick Start

**Version:** v2.2.4
**Date:** 2025-10-03

---

## ✅ You Have Everything You Need!

Die Budibase-Screens für Supplier-Preisimport sind **fertig konfiguriert** und bereit zum Importieren.

---

## 📦 Was ist enthalten?

### **3 Neue Dateien:**

1. **`07_price_import_screen.json`** - Upload Interface
   - Drag & Drop CSV Upload
   - Supplier Source Konfiguration
   - Import History Tabelle
   - CSV Format Guide

2. **`08_quickflip_opportunities_screen.json`** - Analyse Dashboard
   - KPI Cards (Opportunities, Margin, Profit)
   - Filter (Source, Margin %, Profit €, Search)
   - Opportunities Tabelle (Top 100)
   - Product Details Modal

3. **`09_SUPPLIER_PRICE_IMPORT_SETUP.md`** - Ausführliche Anleitung
   - Komplettes Setup-Tutorial
   - Troubleshooting
   - Customization Guide

---

## ⚡ 5-Minuten-Setup

### **Schritt 1: Budibase öffnen** (30 Sekunden)

```bash
# Budibase starten (falls nicht läuft)
cd domains/integration/budibase/budibase-app
docker-compose -f 04_docker_budibase_setup.yml up -d

# Browser öffnen
open http://localhost:10000
```

### **Schritt 2: API Data Source hinzufügen** (1 Minute)

1. **Data** → **Add Data Source**
2. Typ: **REST API**
3. Name: `SoleFlipper API`
4. Base URL: `http://host.docker.internal:8000`
5. **Save**

### **Schritt 3: Screen 1 importieren** (2 Minuten)

1. **Design** → **Screens** → **Create New Screen**
2. Name: `Supplier Price Import`
3. Route: `/price-import`
4. Öffne `07_price_import_screen.json`
5. Kopiere **gesamten Inhalt** von `screen.components`
6. Paste in Budibase Screen Builder
7. **Save**

### **Schritt 4: Screen 2 importieren** (2 Minuten)

1. **Create New Screen**
2. Name: `QuickFlip Opportunities`
3. Route: `/quickflip-opportunities`
4. Öffne `08_quickflip_opportunities_screen.json`
5. Kopiere **gesamten Inhalt** von `screen.components`
6. Paste in Budibase
7. **Save**

### **Schritt 5: Queries hinzufügen** (30 Sekunden)

Für jede Query in den JSON-Dateien:

1. **Data** → **Queries** → **Create New Query**
2. Wähle Data Source (Postgres oder API)
3. Kopiere SQL/Config aus JSON
4. **Save**

**Queries aus 07_price_import_screen.json:**
- `query_import_statistics`
- `query_recent_imports`
- `api_import_market_prices`
- `api_delete_source_prices`

**Queries aus 08_quickflip_opportunities_screen.json:**
- `query_quickflip_kpis`
- `query_quickflip_opportunities`
- `query_available_sources`

---

## 🎯 Fertig! Jetzt testen:

### **Test 1: CSV Upload**

1. Gehe zu `/price-import`
2. Erstelle Test-CSV:
   ```csv
   id,title,brand,price
   TEST001,Nike Air Max 90,Nike,50.00
   TEST002,Adidas Ultraboost,Adidas,75.00
   ```
3. Upload mit Source: `test_supplier`
4. Check Import History → 2 Produkte ✅

### **Test 2: QuickFlip Opportunities**

1. Gehe zu `/quickflip-opportunities`
2. Filter: Source = `test_supplier`
3. Min Margin = 15%
4. **Apply Filters**
5. Siehst du profitable Produkte? ✅

---

## 📋 CSV Format

**Minimal (Required):**
```csv
id,title,price
12345,Nike Air Max 90,89.99
```

**Vollständig (Empfohlen):**
```csv
id,title,brand,price,gtin,availability,stock_qty,link,program_name
12345,Nike Air Max 90,Nike,89.99,0883419123456,in_stock,25,https://supplier.com/p/123,Supplier XYZ
```

---

## 🔧 Troubleshooting

### Upload funktioniert nicht?

**Check API:**
```bash
curl http://localhost:8000/health
```

**Check Budibase → API Connection:**
- URL muss `http://host.docker.internal:8000` sein (Docker Desktop)
- NICHT `localhost` (funktioniert nicht aus Container)

### Keine Opportunities?

**Check:**
1. Produkte haben `retail_price` > `buy_price`?
2. Minimum Margin zu hoch? (senke auf 5%)
3. Source Name korrekt? (Groß-/Kleinschreibung!)

### Import History leer?

**Refresh:**
1. F5 drücken
2. Oder Refresh-Button klicken

---

## 📚 Weitere Hilfe

**Vollständige Anleitung:**
- `09_SUPPLIER_PRICE_IMPORT_SETUP.md` (ausführlich)

**Budibase Grundlagen:**
- `05_complete_setup_guide.md`

**API Dokumentation:**
- http://localhost:8000/docs (FastAPI Swagger)

---

## ✨ Was du jetzt hast:

✅ **Drag & Drop CSV Upload** für Supplier-Preislisten
✅ **Automatisches Product Matching** (GTIN, SKU, Name+Brand)
✅ **QuickFlip Dashboard** mit KPIs und Filtern
✅ **Export-Funktion** für profitable Produkte
✅ **Professional UI** mit Budibase

**Total Setup Zeit:** ~5-10 Minuten
**Komplexität:** Niedrig (Copy-Paste)
**Value:** Sehr hoch! 🚀

---

**Viel Erfolg!** 🎉

Bei Fragen: Siehe `09_SUPPLIER_PRICE_IMPORT_SETUP.md`
