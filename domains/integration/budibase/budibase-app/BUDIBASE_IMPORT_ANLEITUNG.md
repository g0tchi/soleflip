# 🎯 Budibase Import - Korrekte Anleitung

**Version:** v2.2.4
**Status:** Verifiziert mit JSON-Struktur

---

## ⚠️ Wichtig: JSON-Struktur verstehen

Die JSON-Dateien enthalten **NICHT nur Screen-Components**, sondern:

```json
{
  "screen": { ... },        // Screen-Definition + Components
  "queries": { ... },       // Datenbank-Queries
  "datasources": { ... },   // API-Konfiguration
  "automations": [ ... ]    // Email-Benachrichtigungen
}
```

**Du kannst NICHT die gesamte Datei kopieren!**
Du musst **jeden Teil separat** in Budibase importieren.

---

## 🎯 Korrekte Vorgehensweise

### **Option 1: Manuelle Import (Schritt-für-Schritt)** ✅ Empfohlen

#### **Teil A: Datasources erstellen**

**1. API Data Source hinzufügen**

```
Budibase → Data → Add Data Source
├─ Type: REST API
├─ Name: SoleFlipper API
├─ Base URL: http://host.docker.internal:8000
└─ Save
```

Öffne `07_price_import_screen.json` und suche nach:
```json
"datasources": {
  "ds_soleflip_api": { ... }
}
```

**Kopiere die Config:**
- URL: `http://host.docker.internal:8000`
- Headers: `{ "Accept": "application/json" }`

#### **Teil B: Queries erstellen**

Öffne `07_price_import_screen.json` → Suche `"queries":`

**Für jede Query:**

1. **query_import_statistics**
   ```
   Budibase → Data → Queries → Create New Query
   ├─ Name: Import Statistics Summary
   ├─ Data Source: SoleFlipper Database (PostgreSQL)
   ├─ SQL: (kopiere aus JSON)
   └─ Save
   ```

   **SQL aus JSON:**
   ```sql
   SELECT
     COUNT(DISTINCT source) as total_sources,
     COUNT(*) as total_products,
     ROUND(AVG(buy_price)::numeric, 2) as avg_price,
     TO_CHAR(MAX(updated_at), 'DD Mon YYYY') as last_import_date
   FROM finance.source_prices
   WHERE source IS NOT NULL
   ```

2. **query_recent_imports**
   ```
   Name: Recent Imports by Source
   Data Source: PostgreSQL
   SQL: (kopiere aus JSON - Zeile ~450)
   ```

3. **api_import_market_prices**
   ```
   Name: Import Market Prices API
   Data Source: SoleFlipper API
   Method: POST
   URL: /api/v1/quickflip/import-market-prices
   Body Type: form
   Fields:
     - file: {{ file }}
     - source: {{ source }}
   ```

4. **api_delete_source_prices**
   ```
   Name: Delete Source Prices
   Data Source: PostgreSQL
   SQL: DELETE FROM finance.source_prices WHERE source = $1
   Parameter: source (string, required)
   ```

#### **Teil C: Screen Components erstellen**

**Jetzt der Screen selbst:**

```
Budibase → Design → Screens → Create New Screen
├─ Name: Supplier Price Import
├─ Route: /price-import
├─ Access: Admin (role_admin)
└─ Create
```

**Screen Builder öffnet sich.**

**Hier gibt es 2 Wege:**

**Weg 1: JSON Mode (falls verfügbar)**
1. Klicke auf Screen Settings (⚙️)
2. Suche nach "JSON" oder "Advanced"
3. Falls JSON-Editor verfügbar:
   - Öffne `07_price_import_screen.json`
   - Kopiere `screen.components` Array
   - Paste in JSON-Editor
   - Save

**Weg 2: Manuelle Component-Erstellung** (falls kein JSON-Editor)

**Das ist aufwendig, aber funktioniert immer:**

1. **Main Container hinzufügen**
   ```
   Add Component → Container
   ├─ Max Width: 1400px
   ├─ Margin: 0 auto
   ├─ Padding: 32px
   └─ Background: #f8f9fa
   ```

2. **Heading hinzufügen**
   ```
   Add Component → Heading
   ├─ Text: 📊 Supplier Price Import
   ├─ Size: XL
   └─ Color: #1a1a1a
   ```

3. **Form hinzufügen**
   ```
   Add Component → Form
   ├─ Data Source: None
   └─ Submit Button: Import Prices
   ```

4. **Im Form: Fields hinzufügen**

   **Field 1: Source Name**
   ```
   Add Field → Text Field
   ├─ Field: source
   ├─ Label: Supplier Source Name
   ├─ Placeholder: e.g., supplier_xyz
   ├─ Required: Yes
   └─ Validation Pattern: ^[a-z0-9_-]+$
   ```

   **Field 2: File Upload**
   ```
   Add Field → File Upload
   ├─ Field: file
   ├─ Label: CSV Price List
   ├─ Required: Yes
   ├─ Allowed Extensions: .csv
   └─ Max Size: 100MB
   ```

5. **Form Submit Action konfigurieren**
   ```
   Form Settings → On Submit
   ├─ Action 1: Execute Query
   │   └─ Query: api_import_market_prices
   │       ├─ source: {{ form.fields.source }}
   │       └─ file: {{ form.fields.file }}
   ├─ Action 2: Show Notification
   │   ├─ Message: Import started successfully!
   │   └─ Type: Success
   └─ Action 3: Refresh Data Source
       └─ Data Source: query_recent_imports
   ```

6. **Table für Import History**
   ```
   Add Component → Data Provider
   ├─ Data Source: query_recent_imports
   └─ Add Child → Table
       ├─ Columns: source, total_products, avg_price, last_updated
       ├─ Page Size: 10
       └─ Sortable: Yes
   ```

**Das ist sehr aufwendig!** 😅

---

### **Option 2: Vereinfachter Screen** ⚡ Schnellste Lösung

Falls Option 1 zu komplex ist, hier ein **Minimal-Screen** den du in 2 Minuten erstellen kannst:

**1. Screen erstellen**
```
Name: Supplier Price Import
Route: /price-import
```

**2. Nur das Wichtigste hinzufügen:**

```
┌─ Container
│  ├─ Heading: "Supplier Price Import"
│  ├─ Form
│  │  ├─ Text Field (source)
│  │  ├─ File Upload (.csv)
│  │  └─ Submit → Execute Query (api_import_market_prices)
│  └─ Table
│     └─ Data: query_recent_imports
└─ Ende
```

**Das funktioniert sofort und hat die Kernfunktionalität!**

---

### **Option 3: Budibase App Import (falls unterstützt)**

Einige Budibase-Versionen unterstützen kompletten App-Import:

```bash
# Budibase CLI installieren
npm install -g @budibase/cli

# Login
budi login http://localhost:10000

# App importieren (falls unterstützt)
budi import app 07_price_import_screen.json
```

**Hinweis:** Das funktioniert nur bei neueren Budibase-Versionen mit CLI-Support.

---

## 🎯 Meine Empfehlung

**Für dich am besten: Option 2 (Vereinfachter Screen)**

**Warum?**
- ✅ 2 Minuten Setup
- ✅ Alle Kernfunktionen
- ✅ Kein komplexes JSON-Mapping
- ✅ Du kannst später erweitern

**Schritt-für-Schritt:**

1. **Queries erstellen** (5 Minuten)
   - Kopiere SQL aus JSON
   - 4 Queries anlegen

2. **Minimal-Screen bauen** (2 Minuten)
   - Form mit 2 Fields
   - Table mit Import History
   - Submit Action zu API

3. **Testen** (1 Minute)
   - Test-CSV hochladen
   - Check Table zeigt Import

4. **Fertig!** ✅

**Später erweitern:**
- CSV Format Guide hinzufügen
- Filters hinzufügen
- KPIs hinzufügen
- Styling verbessern

---

## 📋 Queries - Quick Reference

### **Query 1: Import Statistics**
```sql
SELECT
  COUNT(DISTINCT source) as total_sources,
  COUNT(*) as total_products,
  ROUND(AVG(buy_price)::numeric, 2) as avg_price,
  TO_CHAR(MAX(updated_at), 'DD Mon YYYY') as last_import_date
FROM finance.source_prices
WHERE source IS NOT NULL
```

### **Query 2: Recent Imports**
```sql
SELECT
  source,
  COUNT(*) as total_products,
  ROUND(AVG(buy_price)::numeric, 2) as avg_price,
  ROUND(MIN(buy_price)::numeric, 2) as min_price,
  ROUND(MAX(buy_price)::numeric, 2) as max_price,
  MAX(updated_at) as last_updated,
  MAX(created_at) as first_import
FROM finance.source_prices
WHERE source IS NOT NULL
GROUP BY source
ORDER BY last_updated DESC
```

### **Query 3: API Import (REST)**
```
Method: POST
URL: /api/v1/quickflip/import-market-prices
Headers: Content-Type: multipart/form-data
Body:
  - file: {{ binding.file }}
  - source: {{ binding.source }}
```

### **Query 4: Delete Source**
```sql
DELETE FROM finance.source_prices WHERE source = $1
-- Parameter: source (string)
```

---

## 🧪 Test-CSV

Zum Testen:

```csv
id,title,brand,price,gtin,availability
TEST001,Nike Air Max 90,Nike,89.99,0883419123456,in_stock
TEST002,Adidas Ultraboost,Adidas,149.99,4060512345678,in_stock
TEST003,Jordan 1 High,Jordan,120.00,0193145297425,in_stock
```

Speichere als `test_import.csv`

---

## ❓ Welche Option wählst du?

**Option 1:** Volle Features, komplexe manuelle Erstellung (30-60 Min)
**Option 2:** ⭐ Minimal aber funktional (7 Minuten) ← **Empfohlen!**
**Option 3:** CLI Import (falls verfügbar, 2 Minuten)

**Mein Tipp:** Starte mit Option 2, es funktioniert sofort!

---

## 🆘 Brauchst du Hilfe?

**Wenn du Option 2 wählst, kann ich dir:**
1. ✅ Genaue Klick-Anweisungen geben
2. ✅ Screenshots der Budibase-UI zeigen (falls du welche schickst)
3. ✅ SQL-Queries direkt kopierbar bereitstellen
4. ✅ Eine noch einfachere Version erstellen

**Sag mir einfach:** "Ich brauche Option 2 Schritt-für-Schritt" und ich erstelle dir eine ultra-detaillierte Anleitung! 🚀
