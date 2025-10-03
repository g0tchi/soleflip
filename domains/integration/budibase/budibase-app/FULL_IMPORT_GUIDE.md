# 🎯 Budibase Full Import - Komplette Anleitung (Alle Features)

**Version:** v2.2.4
**Geschätzte Zeit:** 30-60 Minuten
**Schwierigkeit:** Mittel
**Ergebnis:** Vollständiger Supplier Price Import + QuickFlip Dashboard

---

## 📋 Inhaltsverzeichnis

1. [Vorbereitung](#vorbereitung) (5 Min)
2. [Data Sources einrichten](#data-sources) (5 Min)
3. [Queries erstellen](#queries) (15 Min)
4. [Screen 1: Price Import](#screen-1) (20 Min)
5. [Screen 2: QuickFlip Opportunities](#screen-2) (20 Min)
6. [Testing](#testing) (5 Min)

---

## 🚀 Vorbereitung

### **Schritt 1: Budibase starten**

```bash
cd domains/integration/budibase/budibase-app
docker-compose -f 04_docker_budibase_setup.yml up -d
```

**Warte bis Budibase bereit ist:**
```bash
docker-compose -f 04_docker_budibase_setup.yml logs -f budibase
# Warte auf: "Budibase running on port 10000"
```

### **Schritt 2: Budibase öffnen**

Browser öffnen: `http://localhost:10000`

**Falls noch nicht eingerichtet:**
- Account erstellen (Admin)
- App erstellen: "SoleFlipper BI"

### **Schritt 3: Dateien bereithalten**

Öffne in deinem Editor:
- `07_price_import_screen.json`
- `08_quickflip_opportunities_screen.json`

**Du wirst daraus kopieren!**

---

## 🔌 Data Sources einrichten

### **Data Source 1: PostgreSQL (sollte schon existieren)**

**Prüfen:**
```
Budibase → Data → Data Sources
Suche: "SoleFlipper Database" oder ähnlich
```

**Falls nicht vorhanden:**
```
Add Data Source → PostgreSQL
Name: SoleFlipper Database
Host: postgres
Port: 5432
Database: soleflip
User: soleflip_user
Password: [dein Passwort]
Schema: public
SSL: false
→ Save & Test Connection
```

**Wichtig:** Notiere dir den internen Namen (z.B. `ds_soleflip_postgres`)

---

### **Data Source 2: REST API (neu erstellen)**

```
Budibase → Data → Data Sources → Add Data Source
```

**Konfiguration:**
```
Type: REST API
Name: SoleFlipper API
Base URL: http://host.docker.internal:8000
Default Headers:
  - Accept: application/json
  - Content-Type: application/json
```

**Wichtig für Docker Desktop:**
- **Windows/Mac:** `http://host.docker.internal:8000`
- **Linux:** `http://172.17.0.1:8000` (oder API Container Name)

**Save & Test:**
```
Test URL: /health
Erwartete Response: {"status": "healthy"}
```

**✅ Checkpoint:** Du hast jetzt 2 Data Sources:
- PostgreSQL (SoleFlipper Database)
- REST API (SoleFlipper API)

---

## 📊 Queries erstellen

### **Query-Übersicht**

**Für Screen 1 (Price Import):**
1. `query_import_statistics` - Statistik-KPIs
2. `query_recent_imports` - Import-Historie
3. `api_import_market_prices` - Upload-API
4. `api_delete_source_prices` - Löschen

**Für Screen 2 (QuickFlip):**
5. `query_quickflip_kpis` - Dashboard-KPIs
6. `query_quickflip_opportunities` - Profitable Produkte
7. `query_available_sources` - Source-Dropdown

---

### **Query 1: Import Statistics**

```
Budibase → Data → Queries → Create New Query
```

**Konfiguration:**
```
Name: Import Statistics Summary
Data Source: SoleFlipper Database (PostgreSQL)
Query Type: SQL
```

**SQL (kopiere komplett):**
```sql
SELECT
    COUNT(DISTINCT source) as total_sources,
    COUNT(*) as total_products,
    ROUND(AVG(buy_price)::numeric, 2) as avg_price,
    TO_CHAR(MAX(updated_at), 'DD Mon YYYY') as last_import_date
FROM finance.source_prices
WHERE source IS NOT NULL
```

**Fields (Output Schema):**
```
total_sources: Number
total_products: Number
avg_price: Number
last_import_date: Text
```

**→ Save Query**

**Test ausführen:**
```
→ Run Query
Erwartetes Ergebnis:
{
  "total_sources": 0,
  "total_products": 0,
  "avg_price": null,
  "last_import_date": null
}
```

---

### **Query 2: Recent Imports**

```
Create New Query
Name: Recent Imports by Source
Data Source: SoleFlipper Database (PostgreSQL)
```

**SQL:**
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

**→ Save & Test**

---

### **Query 3: API Import (REST)**

```
Create New Query
Name: Import Market Prices API
Data Source: SoleFlipper API (REST API)
```

**Konfiguration:**
```
Method: POST
URL Path: /api/v1/quickflip/import-market-prices
Headers:
  Content-Type: multipart/form-data
Body Type: Form Data
```

**Body/Form Fields:**

**Wichtig:** Budibase Form Data Setup variiert je nach Version!

**Option A: Bindings Tab**
```
Bindings:
  - Name: file
    Type: File
    Binding: {{ file }}

  - Name: source
    Type: Text
    Binding: {{ source }}
```

**Option B: Body Tab (falls Form Data verfügbar)**
```
Form Data:
  file: {{ file }}
  source: {{ source }}
```

**Option C: Als multipart/form-data (manuell)**
```
Raw Body:
------WebKitFormBoundary
Content-Disposition: form-data; name="file"

{{ file }}
------WebKitFormBoundary
Content-Disposition: form-data; name="source"

{{ source }}
```

**Transformer (optional):**
```javascript
return {
  success: data.success,
  stats: data.stats,
  message: data.message
}
```

**→ Save Query**

**Hinweis:** Dieser Query wird später vom Form getriggert, nicht manuell getestet!

---

### **Query 4: Delete Source Prices**

```
Create New Query
Name: Delete Source Prices
Data Source: SoleFlipper Database (PostgreSQL)
```

**SQL:**
```sql
DELETE FROM finance.source_prices
WHERE source = {{ source }}
```

**Bindings/Parameters:**
```
Name: source
Type: Text
Required: Yes
Default: (empty)
```

**→ Save Query**

**NICHT TESTEN** (würde Daten löschen!)

---

### **Query 5: QuickFlip KPIs**

```
Create New Query
Name: QuickFlip Opportunities KPIs
Data Source: SoleFlipper Database (PostgreSQL)
```

**SQL:**
```sql
SELECT
    COUNT(*) as total_opportunities,
    ROUND(AVG((p.retail_price - sp.buy_price) / sp.buy_price * 100)::numeric, 2) as avg_margin,
    ROUND(SUM(p.retail_price - sp.buy_price)::numeric, 2) as total_potential_profit,
    ROUND(MAX((p.retail_price - sp.buy_price) / sp.buy_price * 100)::numeric, 2) as max_margin
FROM products.products p
JOIN finance.source_prices sp ON sp.product_id = p.id
WHERE p.retail_price > sp.buy_price
  AND ({{ source }} IS NULL OR sp.source = {{ source }})
  AND ((p.retail_price - sp.buy_price) / sp.buy_price * 100) >= 15
```

**Bindings:**
```
Name: source
Type: Text
Required: No
Default: null
```

**→ Save & Test**

---

### **Query 6: QuickFlip Opportunities List**

```
Create New Query
Name: QuickFlip Opportunities List
Data Source: SoleFlipper Database (PostgreSQL)
```

**SQL:**
```sql
SELECT
    p.id,
    p.name as product_name,
    p.sku,
    b.name as brand_name,
    sp.source,
    sp.buy_price,
    p.retail_price as market_price,
    (p.retail_price - sp.buy_price) as profit,
    ROUND(((p.retail_price - sp.buy_price) / sp.buy_price * 100)::numeric, 2) as margin_percent,
    sp.availability,
    sp.stock_qty,
    sp.product_url
FROM products.products p
JOIN finance.source_prices sp ON sp.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE p.retail_price > sp.buy_price
  AND ({{ source }} IS NULL OR sp.source = {{ source }})
  AND ((p.retail_price - sp.buy_price) / sp.buy_price * 100) >= COALESCE({{ min_margin }}, 15)
  AND (p.retail_price - sp.buy_price) >= COALESCE({{ min_profit }}, 10)
  AND ({{ search }} IS NULL OR p.name ILIKE '%' || {{ search }} || '%' OR b.name ILIKE '%' || {{ search }} || '%')
ORDER BY margin_percent DESC
LIMIT 100
```

**Bindings:**
```
1. source: Text, Not Required, Default: null
2. min_margin: Number, Not Required, Default: 15
3. min_profit: Number, Not Required, Default: 10
4. search: Text, Not Required, Default: null
```

**→ Save & Test**

---

### **Query 7: Available Sources**

```
Create New Query
Name: Available Supplier Sources
Data Source: SoleFlipper Database (PostgreSQL)
```

**SQL:**
```sql
SELECT DISTINCT
    source,
    source || ' (' || COUNT(*) || ' products)' as source_label
FROM finance.source_prices
WHERE source IS NOT NULL
GROUP BY source
ORDER BY source
```

**→ Save & Test**

---

**✅ Checkpoint: Queries fertig!**

Du solltest jetzt **7 Queries** haben:
- ✅ Import Statistics Summary
- ✅ Recent Imports by Source
- ✅ Import Market Prices API
- ✅ Delete Source Prices
- ✅ QuickFlip Opportunities KPIs
- ✅ QuickFlip Opportunities List
- ✅ Available Supplier Sources

---

## 🎨 Screen 1: Supplier Price Import

### **Screen erstellen**

```
Budibase → Design → Screens → Create New Screen
```

**Einstellungen:**
```
Screen Name: Supplier Price Import
Route: /price-import
Access Level: Admin (role_admin)
Layout: Standard
Navigation: Show in navigation
Icon: Upload
```

**→ Create Screen**

**Screen Builder öffnet sich.**

---

### **Component-Struktur aufbauen**

**Root Container:**
```
Add Component → Container

Settings:
├─ Direction: Column (vertical)
├─ Max Width: 1400px
├─ Margin: 0 auto
├─ Padding: 32px
├─ Background: #f8f9fa
└─ Gap: 24px
```

Dieser Container ist dein **Main Container** - alles kommt da rein!

---

### **Component 1: Heading**

```
Im Main Container → Add Component → Heading

Settings:
├─ Text: 📊 Supplier Price Import
├─ Size: Extra Large (XL)
├─ Color: #1a1a1a
├─ Margin Bottom: 8px
└─ Font Weight: Bold
```

---

### **Component 2: Subtitle**

```
Add Component → Paragraph

Settings:
├─ Text: Upload CSV files with supplier price lists to find profitable QuickFlip opportunities
├─ Color: #666666
├─ Font Size: 16px
└─ Margin Bottom: 32px
```

---

### **Component 3: Divider**

```
Add Component → Divider

Settings:
└─ Margin Bottom: 24px
```

---

### **Component 4: Upload Section (Container)**

```
Add Component → Container

Settings:
├─ Direction: Row (horizontal)
├─ Gap: 24px
├─ Margin Bottom: 32px
└─ Align Items: Stretch
```

**In diesem Container kommen 2 Spalten:**

---

#### **Spalte 1: Upload Form (in Upload Section Container)**

```
Add Component → Container

Settings:
├─ Flex: 2 (nimmt 2/3 der Breite)
├─ Background: white
├─ Padding: 24px
├─ Border Radius: 8px
└─ Box Shadow: 0 2px 4px rgba(0,0,0,0.1)
```

**In diesem Container → Add Heading:**
```
Text: Upload Price List
Size: Medium (M)
Margin Bottom: 16px
```

**In diesem Container → Add Form:**

```
Add Component → Form

Settings:
├─ Data Source: (leer lassen)
├─ Button Text: Import Prices
├─ Button Position: Bottom
└─ Schema: (automatisch)
```

**Im Form → Add Field Group:**

```
Add Component → Field Group
```

**Im Field Group → Add Field 1: Source Name**

```
Add Component → Text Field

Settings:
├─ Field: source
├─ Label: Supplier Source Name
├─ Placeholder: e.g., supplier_xyz, awin, webgains
├─ Required: Yes
├─ Help Text: Unique identifier for this supplier (lowercase, no spaces)
└─ Validation:
    ├─ Type: Regex
    ├─ Pattern: ^[a-z0-9_-]+$
    └─ Error: Only lowercase letters, numbers, underscores and hyphens allowed
```

**Im Field Group → Add Field 2: File Upload**

```
Add Component → Attachment/File Upload

Settings:
├─ Field: file
├─ Label: CSV Price List
├─ Required: Yes
├─ File Types: .csv
├─ Max Size: 100 (MB)
└─ Help Text: Maximum file size: 100MB. Required columns: id, title, price
```

**Im Field Group → Add Field 3: Import Mode**

```
Add Component → Options Picker / Select

Settings:
├─ Field: import_mode
├─ Label: Import Mode
├─ Type: Select (Dropdown)
├─ Options: (Manual)
│   ├─ Option 1:
│   │   ├─ Label: Create & Update (Default)
│   │   └─ Value: upsert
│   ├─ Option 2:
│   │   ├─ Label: Create Only (Skip Existing)
│   │   └─ Value: create
│   └─ Option 3:
│       ├─ Label: Update Only (Existing Prices)
│       └─ Value: update
├─ Default Value: upsert
└─ Help Text: Choose how to handle existing products
```

**Form Submit Action konfigurieren:**

```
Form Component → Settings → Actions → On Submit

Action 1: Execute Query
├─ Query: Import Market Prices API
├─ Bindings:
│   ├─ source: {{ Form.Fields.source }}
│   └─ file: {{ Form.Fields.file }}
└─ Store Response: Yes

Action 2: Show Notification
├─ Type: Success
├─ Message: Import started successfully!
├─ Duration: 5000ms
└─ Position: Top Right

Action 3: Refresh Data Source
└─ Data Source: Recent Imports by Source (Query)

Action 4: Reset Form
└─ (Clear form fields)
```

---

#### **Spalte 2: Format Guide (in Upload Section Container)**

```
Add Component → Container

Settings:
├─ Flex: 1 (nimmt 1/3 der Breite)
├─ Background: #fff3cd
├─ Padding: 20px
├─ Border Radius: 8px
└─ Border: 1px solid #ffc107
```

**In diesem Container → Add Heading:**
```
Text: 📋 CSV Format
Size: Small (S)
Color: #856404
Margin Bottom: 12px
```

**Add Paragraph:**
```
Text: **Required Columns:**
Font Weight: Bold
Margin Bottom: 8px
```

**Add Markdown Component:**
```
Add Component → Markdown/Rich Text

Content:
• `id` - Supplier product ID
• `title` - Product name
• `price` - Buy price (EUR)

**Optional Columns:**
• `brand` - Brand name
• `gtin` / `ean` - For better matching
• `availability` - Stock status
• `stock_qty` - Quantity available
• `link` - Product URL
• `program_name` - Supplier name

Font Size: 13px
Line Height: 1.6
```

**Add Divider:**
```
Margin: 12px 0
```

**Add Paragraph:**
```
Text: **Example:**
Font Weight: Bold
```

**Add Code Block:**
```
Add Component → Code Block

Language: csv
Content:
id,title,brand,price,gtin
12345,Nike Air Max 90,Nike,89.99,0883419123456
67890,Adidas Ultraboost,Adidas,149.99,4060512345678

Font Size: 12px
Background: white
Padding: 8px
Border Radius: 4px
```

---

### **Component 5: Divider (nach Upload Section)**

```
Add Component → Divider (im Main Container)
Margin Bottom: 24px
```

---

### **Component 6: Import History Section**

```
Add Component → Container (im Main Container)

Settings:
├─ Background: white
├─ Padding: 24px
├─ Border Radius: 8px
└─ Box Shadow: 0 2px 4px rgba(0,0,0,0.1)
```

**In diesem Container → Add Heading:**
```
Text: 📊 Import History & Statistics
Size: Medium (M)
Margin Bottom: 16px
```

---

#### **Statistics Cards (Data Provider + Stats)**

```
Add Component → Data Provider

Settings:
└─ Data Source: Import Statistics Summary (Query)
```

**Im Data Provider → Add Container:**
```
Direction: Row
Gap: 16px
Margin Bottom: 24px
```

**Im Row Container → Add 4 Statistic Cards:**

**Statistic Card 1:**
```
Add Component → Statistic Card

Settings:
├─ Title: Total Sources
├─ Value: {{ Data.total_sources }}
├─ Icon: Database
├─ Color: Blue
└─ Size: Medium
```

**Statistic Card 2:**
```
Title: Total Products
Value: {{ Data.total_products }}
Icon: ShoppingBag
Color: Green
```

**Statistic Card 3:**
```
Title: Avg Price
Value: €{{ Data.avg_price }}
Icon: Euro
Color: Orange
```

**Statistic Card 4:**
```
Title: Last Import
Value: {{ Data.last_import_date }}
Icon: Clock
Color: Purple
```

---

#### **Import History Table**

```
Add Component → Data Provider (im Import History Container)

Settings:
└─ Data Source: Recent Imports by Source (Query)
```

**Im Data Provider → Add Container (für Filter Row):**
```
Direction: Row
Gap: 12px
Margin Bottom: 16px
```

**Im Filter Row → Add Search Field:**
```
Add Component → Text Field

Settings:
├─ Placeholder: Search by source name...
├─ Flex: 1
└─ On Change:
    └─ Update State: search_filter = {{ value }}
```

**Im Filter Row → Add Refresh Button:**
```
Add Component → Button

Settings:
├─ Text: Refresh
├─ Icon: Refresh
├─ Type: Secondary
└─ On Click:
    └─ Refresh Data Source: Recent Imports by Source
```

**Im Data Provider → Add Table:**

```
Add Component → Table

Settings:
├─ Title: Recent Imports by Source
├─ Data Source: (inherited from Data Provider)
├─ Show Pagination: Yes
├─ Page Size: 10
├─ Sortable: Yes
└─ Default Sort: last_updated DESC
```

**Table Columns konfigurieren:**

**Column 1: Source**
```
Name: source
Label: Supplier Source
Width: 20%
Sortable: Yes
```

**Column 2: Total Products**
```
Name: total_products
Label: Products
Width: 10%
Align: Center
Sortable: Yes
```

**Column 3: Avg Price**
```
Name: avg_price
Label: Avg Price
Width: 12%
Align: Right
Display Format: €{{ value }}
Sortable: Yes
```

**Column 4: Min Price**
```
Name: min_price
Label: Min Price
Width: 12%
Align: Right
Display Format: €{{ value }}
Sortable: Yes
```

**Column 5: Max Price**
```
Name: max_price
Label: Max Price
Width: 12%
Align: Right
Display Format: €{{ value }}
Sortable: Yes
```

**Column 6: Last Updated**
```
Name: last_updated
Label: Last Updated
Width: 18%
Display Format: {{ value | date:'dd MMM yyyy HH:mm' }}
Sortable: Yes
```

**Column 7: Actions (Custom Column)**
```
Name: actions
Label: Actions
Width: 16%
Type: Custom Column
```

**Im Custom Column Template → Add Container:**
```
Direction: Row
Gap: 8px
```

**Im Container → Add Button 1:**
```
Add Component → Button

Settings:
├─ Text: View Opportunities
├─ Size: Small
├─ Type: Secondary
└─ On Click:
    └─ Navigate To: /quickflip-opportunities
        └─ Query Params: source={{ row.source }}
```

**Im Container → Add Button 2:**
```
Add Component → Button

Settings:
├─ Text: Delete
├─ Size: Small
├─ Type: Danger
├─ Icon: Delete
└─ On Click:
    ├─ Action 1: Execute Query
    │   ├─ Query: Delete Source Prices
    │   └─ Bindings: source={{ row.source }}
    ├─ Action 2: Show Notification
    │   ├─ Message: Source prices deleted successfully
    │   └─ Type: Success
    └─ Action 3: Refresh Data Source
        └─ Data Source: Recent Imports by Source
```

---

**✅ Screen 1 fertig!**

**Preview:**
```
Preview Button → Teste ob alles angezeigt wird
```

---

## 🚀 Screen 2: QuickFlip Opportunities

### **Screen erstellen**

```
Budibase → Design → Screens → Create New Screen

Name: QuickFlip Opportunities
Route: /quickflip-opportunities
Access: Manager (role_manager)
Icon: TrendingUp
Navigation: Show
```

---

### **Main Container**

```
Add Component → Container

Settings:
├─ Max Width: 1600px
├─ Margin: 0 auto
├─ Padding: 32px
├─ Background: #f8f9fa
└─ Gap: 24px
```

---

### **Heading & Subtitle**

```
Add Heading:
├─ Text: 🚀 QuickFlip Opportunities
├─ Size: XL
└─ Margin Bottom: 8px

Add Paragraph:
├─ Text: Find profitable products by comparing supplier prices with market prices
└─ Color: #666
```

**Add Divider**

---

### **KPI Cards Section**

```
Add Component → Container
Direction: Row
Gap: 16px
Margin Bottom: 32px
```

**Im Container → Add Data Provider:**
```
Data Source: QuickFlip Opportunities KPIs (Query)
Filter: source = {{ State.selected_source }}
```

**Im Data Provider → Add Container (für Cards):**
```
Direction: Row
Gap: 16px
Width: 100%
```

**Im Cards Container → Add 4 Statistic Cards:**

```
Card 1:
├─ Title: Opportunities
├─ Value: {{ Data.total_opportunities }}
├─ Icon: ShoppingCart
└─ Color: Green

Card 2:
├─ Title: Avg Margin
├─ Value: {{ Data.avg_margin }}%
├─ Icon: TrendingUp
└─ Color: Blue

Card 3:
├─ Title: Total Potential Profit
├─ Value: €{{ Data.total_potential_profit }}
├─ Icon: Euro
└─ Color: Orange

Card 4:
├─ Title: Best Margin
├─ Value: {{ Data.max_margin }}%
├─ Icon: Star
└─ Color: Purple
```

---

### **Filters Section**

```
Add Component → Container (im Main Container)

Settings:
├─ Background: white
├─ Padding: 20px
├─ Border Radius: 8px
├─ Box Shadow: 0 2px 4px rgba(0,0,0,0.1)
└─ Margin Bottom: 24px
```

**Add Heading:**
```
Text: 🔍 Filters
Size: Small
Margin Bottom: 16px
```

**Add Container (Filter Row):**
```
Direction: Row
Gap: 16px
Flex Wrap: Wrap
```

**Im Filter Row → Add Components:**

**Filter 1: Source Dropdown**
```
Add Component → Data Provider
Data Source: Available Supplier Sources (Query)

Im Data Provider → Add Select:
├─ Field: source_filter
├─ Label: Supplier Source
├─ Options Source: Data Provider
├─ Value Column: source
├─ Label Column: source_label
├─ Placeholder: All Sources
├─ Min Width: 200px
└─ On Change:
    ├─ Update State: selected_source = {{ value }}
    └─ Refresh Data Source: QuickFlip Opportunities List
```

**Filter 2: Min Margin**
```
Add Component → Number Field

Settings:
├─ Field: min_margin
├─ Label: Min Margin %
├─ Placeholder: 0
├─ Default Value: 15
├─ Min: 0
├─ Max: 1000
├─ Width: 150px
└─ On Change:
    └─ Update State: min_margin_filter = {{ value }}
```

**Filter 3: Min Profit**
```
Add Component → Number Field

Settings:
├─ Field: min_profit
├─ Label: Min Profit €
├─ Placeholder: 0
├─ Default Value: 10
├─ Min: 0
├─ Width: 150px
└─ On Change:
    └─ Update State: min_profit_filter = {{ value }}
```

**Filter 4: Search**
```
Add Component → Text Field

Settings:
├─ Field: search_query
├─ Label: Search Products
├─ Placeholder: Nike, Adidas, Air Max...
├─ Flex: 1
├─ Min Width: 250px
└─ On Change:
    └─ Update State: search_filter = {{ value }}
```

**Filter 5: Apply Button**
```
Add Component → Button

Settings:
├─ Text: Apply Filters
├─ Type: CTA (Primary)
├─ Icon: Filter
└─ On Click:
    └─ Refresh Data Source: QuickFlip Opportunities List
```

**Filter 6: Reset Button**
```
Add Component → Button

Settings:
├─ Text: Reset
├─ Type: Secondary
├─ Icon: Refresh
└─ On Click:
    ├─ Update State: selected_source = null
    ├─ Update State: min_margin_filter = 15
    ├─ Update State: min_profit_filter = 10
    ├─ Update State: search_filter = ""
    └─ Refresh Data Source: QuickFlip Opportunities List
```

---

### **Opportunities Table Section**

```
Add Component → Container (im Main Container)

Settings:
├─ Background: white
├─ Padding: 24px
├─ Border Radius: 8px
└─ Box Shadow: 0 2px 4px rgba(0,0,0,0.1)
```

**Add Heading:**
```
Text: 💰 Profitable Products
Size: Medium
Margin Bottom: 16px
```

**Add Data Provider:**
```
Data Source: QuickFlip Opportunities List (Query)
Bindings:
├─ source: {{ State.selected_source }}
├─ min_margin: {{ State.min_margin_filter || 15 }}
├─ min_profit: {{ State.min_profit_filter || 10 }}
└─ search: {{ State.search_filter }}
```

**Im Data Provider → Add Table:**

```
Add Component → Table

Settings:
├─ Page Size: 25
├─ Show Pagination: Yes
├─ Sortable: Yes
├─ Default Sort: margin_percent DESC
├─ Exportable: Yes
└─ Export Formats: CSV, JSON
```

**Table Columns:**

**Column 1: Product**
```
Name: product_name
Label: Product
Width: 25%
Sortable: Yes
```

**Column 2: Brand**
```
Name: brand_name
Label: Brand
Width: 12%
Sortable: Yes
```

**Column 3: SKU**
```
Name: sku
Label: SKU
Width: 10%
Sortable: Yes
```

**Column 4: Buy Price**
```
Name: buy_price
Label: Buy Price
Width: 10%
Align: Right
Display: €{{ value }}
Sortable: Yes
```

**Column 5: Market Price**
```
Name: market_price
Label: Market Price
Width: 10%
Align: Right
Display: €{{ value }}
Sortable: Yes
```

**Column 6: Profit**
```
Name: profit
Label: Profit
Width: 10%
Align: Right
Display: €{{ value }}
Sortable: Yes
Color: {{ value >= 50 ? 'green' : value >= 20 ? 'blue' : 'default' }}
```

**Column 7: Margin %**
```
Name: margin_percent
Label: Margin %
Width: 10%
Align: Right
Display: {{ value }}%
Type: Badge
Badge Color: {{ value >= 50 ? 'green' : value >= 30 ? 'blue' : value >= 15 ? 'orange' : 'default' }}
Sortable: Yes
```

**Column 8: Stock**
```
Name: availability
Label: Stock
Width: 8%
Align: Center
Type: Badge
Badge Color: {{ value == 'in_stock' ? 'green' : 'red' }}
Sortable: Yes
```

**Column 9: Actions (Custom)**
```
Name: actions
Label: Actions
Width: 15%
Type: Custom Column

Im Template → Add Container:
├─ Direction: Row
├─ Gap: 8px

Add Button 1:
├─ Text: View
├─ Size: Small
├─ Icon: Eye
└─ On Click:
    ├─ Update State: selected_product = {{ row }}
    └─ Open Modal: modal_product_details

Add Link:
├─ Text: Supplier
├─ URL: {{ row.product_url }}
├─ Open in New Tab: Yes
├─ Size: Small
└─ Type: Secondary
```

---

### **Product Details Modal**

```
Budibase → Design → Modals → Create New Modal

Settings:
├─ Modal ID: modal_product_details
├─ Title: Product Details
├─ Size: Large
└─ Close Button: Yes
```

**Im Modal → Add Container:**
```
Padding: 24px
```

**Add Heading:**
```
Text: {{ State.selected_product.product_name }}
Size: Large
```

**Add Divider:**
```
Margin: 16px 0
```

**Add Container (2 Spalten):**
```
Direction: Row
Gap: 32px
```

**Spalte 1: Product Info**
```
Add Container:
├─ Flex: 1

Add Heading:
├─ Text: Product Information
├─ Size: Small
└─ Margin Bottom: 12px

Add Key-Value List:
Data:
├─ Brand: {{ State.selected_product.brand_name }}
├─ SKU: {{ State.selected_product.sku }}
├─ Source: {{ State.selected_product.source }}
├─ Availability: {{ State.selected_product.availability }}
└─ Stock Quantity: {{ State.selected_product.stock_qty || 'N/A' }}
```

**Spalte 2: Pricing Analysis**
```
Add Container:
├─ Flex: 1

Add Heading:
├─ Text: Pricing Analysis
├─ Size: Small
└─ Margin Bottom: 12px

Add Key-Value List:
Data:
├─ Buy Price: €{{ State.selected_product.buy_price }}
├─ Market Price: €{{ State.selected_product.market_price }}
├─ Profit: €{{ State.selected_product.profit }}
├─ Margin: {{ State.selected_product.margin_percent }}%
└─ ROI: {{ (State.selected_product.profit / State.selected_product.buy_price * 100).toFixed(2) }}%
```

**Add Divider:**
```
Margin: 24px 0
```

**Add Container (Buttons):**
```
Direction: Row
Gap: 12px
Justify Content: Flex End

Add Link:
├─ Text: View on Supplier Site
├─ URL: {{ State.selected_product.product_url }}
├─ Open in New Tab: Yes
├─ Type: CTA
└─ Enabled: {{ State.selected_product.product_url != null }}

Add Button:
├─ Text: Close
├─ Type: Secondary
└─ On Click:
    └─ Close Modal: modal_product_details
```

---

**✅ Screen 2 fertig!**

---

## 🧪 Testing

### **Test 1: CSV Upload**

**Erstelle Test-CSV:**

```csv
id,title,brand,price,gtin,availability
TEST001,Nike Air Max 90,Nike,50.00,0883419123456,in_stock
TEST002,Adidas Ultraboost,Adidas,75.00,4060512345678,in_stock
TEST003,Jordan 1 High,Jordan,90.00,0193145297425,in_stock
```

Speichere als `test_import.csv`

**Upload testen:**

1. Gehe zu `/price-import`
2. Source Name: `test_supplier`
3. Datei hochladen: `test_import.csv`
4. Import Mode: Create & Update
5. **Import Prices** klicken
6. Warte auf Success Notification ✅
7. Check Import History → sollte `test_supplier` mit 3 Products zeigen

---

### **Test 2: QuickFlip Opportunities**

1. Gehe zu `/quickflip-opportunities`
2. Filter: Source = `test_supplier`
3. Min Margin: 15%
4. **Apply Filters** klicken
5. Solltest profitable Produkte sehen (falls StockX Preise höher sind)
6. Klicke **View** auf einem Produkt
7. Modal sollte Details zeigen
8. **Supplier** Link sollte öffnen (falls vorhanden)

---

### **Test 3: Export**

1. In QuickFlip Opportunities Table
2. Klicke **Export** Button
3. Wähle CSV
4. Download sollte starten
5. Öffne CSV → sollte alle gefilterten Opportunities enthalten

---

## ✅ Fertig! 🎉

**Du hast jetzt:**

✅ **2 vollständige Screens** mit allen Features
✅ **7 Queries** für Daten und API
✅ **KPI Dashboards** mit Live-Daten
✅ **Advanced Filtering** mit State Management
✅ **Modal Details** mit Product Info
✅ **Export Functionality** für CSV/JSON
✅ **Professional UI** mit Color-Coding

---

## 🔧 Troubleshooting

### **Problem: API Query funktioniert nicht**

**Check:**
```bash
# API erreichbar?
curl http://localhost:8000/health

# Budibase kann API erreichen?
# Im Budibase Data Source Test
Test URL: /health
```

**Lösung:**
- Windows/Mac: `http://host.docker.internal:8000`
- Linux: `http://172.17.0.1:8000`

---

### **Problem: Queries zeigen keine Daten**

**Check:**
```sql
-- PostgreSQL direkt testen
SELECT COUNT(*) FROM finance.source_prices;
```

**Falls 0:**
- Noch keine Daten importiert
- Erst CSV hochladen

---

### **Problem: Form Submit funktioniert nicht**

**Check:**
1. Query `api_import_market_prices` korrekt?
2. Form Bindings korrekt: `{{ Form.Fields.source }}`?
3. File Upload Field Name = `file`?

---

### **Problem: Modal öffnet nicht**

**Check:**
1. Modal ID = `modal_product_details`?
2. Button Action: Open Modal mit korrekter ID?
3. State `selected_product` wird gesetzt?

---

## 📚 Nächste Schritte

**Jetzt wo alles läuft:**

1. **Echte Daten importieren**
   - CSV vom Supplier
   - Source Name vergeben
   - Import starten

2. **Opportunities analysieren**
   - Filter nutzen
   - Profitable Produkte finden
   - Exportieren für Bestellung

3. **Erweitern**
   - Weitere Supplier hinzufügen
   - Margin Thresholds anpassen
   - Automationen erstellen (Email bei neuen Opportunities)

4. **Team einbinden**
   - User Rollen konfigurieren
   - Kollegen einladen
   - Training durchführen

---

**Geschafft!** Du hast jetzt ein vollständiges Supplier Price Import & QuickFlip Analysis System! 🚀

**Fragen?** Check die anderen Markdown-Dateien im Verzeichnis.

**Viel Erfolg!** 💪
