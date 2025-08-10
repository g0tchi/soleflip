# 🚀 Metabase Dashboard Import Guide

## 📋 Schritt-für-Schritt Anleitung

### 1. Metabase vorbereiten
```bash
# Metabase URL öffnen
http://192.168.2.45:3000

# Login mit Admin-Account
```

### 2. Datenbank-Verbindung prüfen
- **Settings** → **Admin** → **Databases**
- **Add Database** falls noch nicht vorhanden:
  - **Database Type:** PostgreSQL
  - **Host:** 192.168.2.45
  - **Port:** 2665
  - **Database name:** soleflip
  - **Username:** metabaseuser
  - **Password:** metabasepass

### 3. Schema-Sync
- **Sync Database Schema** klicken
- Warten bis alle `analytics.*` Views erkannt werden

## 📁 Collection-Struktur Setup

### 4. Collections anlegen (empfohlene Struktur):

#### 🏠 Main Collection erstellen:
1. **"Browse Data"** → **"New"** → **"Collection"**
2. **Name:** "SoleFlipper Analytics"  
3. **Description:** "Business Intelligence Dashboards für SoleFlipper"

#### 📊 Sub-Collections erstellen:
Innerhalb "SoleFlipper Analytics" folgende Collections anlegen:

```
📁 SoleFlipper Analytics/
├── 📊 Executive Dashboards/        (Management KPIs)
├── 🏷️ Brand Analytics/             (Marken-Analyse)
├── 🎯 Product Performance/         (Produkt-Insights)
├── 🏪 Platform Analytics/          (StockX Performance)
├── 🌍 Geographic Analytics/        (Länder-Analyse)
└── ⏰ Time Analytics/              (Zeit-Trends)
```

#### 🔐 Permissions Setup:
- **Admin Access:** Vollzugriff auf alle Collections
- **Management:** Executive Dashboards (Vollzugriff), Rest (Nur ansehen)
- **Operations:** Product/Platform Analytics (Vollzugriff), Rest (Nur ansehen)

### 5. Dashboard-Prioritäten:

#### **Priorität 1 - Täglich genutzt:**
- 📊 **Executive Overview** (in Executive Dashboards/)
- 🏷️ **Brand Deep Dive - Nike Focus** (in Brand Analytics/)

#### **Priorität 2 - Wöchentlich genutzt:**  
- 🎯 **Product Performance** (in Product Performance/)
- 🏷️ **Brand Overview** (in Brand Analytics/)
- 🏪 **StockX Performance** (in Platform Analytics/)

#### **Priorität 3 - Monatlich genutzt:**
- 🌍 **Sales by Location** (in Geographic Analytics/)
- ⏰ **Weekly Trends** (in Time Analytics/)

## 📊 Dashboard Manual Setup

### 🧠 Dashboard-Logik und Zweck:

#### **Fokussierte Dashboard-Strategie:**
- **Executive Overview:** Management KPIs - schneller Überblick
- **Product Performance:** Nur produktbezogene Insights (Top Seller, Preise, Trends)  
- **Brand Overview:** Marken-Vergleich und Marktanteile
- **Brand Deep Dive - Nike:** Nike-spezifische Tiefenanalyse (53.8% Marktanteil)
- **StockX Performance:** Platform-spezifische Metriken und Gebühren
- **Geographic/Time Analytics:** Spezialisierte Analysen

#### **Warum diese Aufteilung?**
- ✅ **Klare Trennung:** Jedes Dashboard hat einen spezifischen Fokus
- ✅ **Keine Verwirrung:** Product Performance zeigt nur Produkt-Metriken
- ✅ **Nike-Fokus:** Separates Dashboard für wichtigste Marke (53.8% Anteil)
- ✅ **Skalierbar:** Weitere Brand Deep Dives (Adidas, etc.) einfach hinzufügbar

Jedes Dashboard wird in die entsprechende Collection eingeordnet:

### Dashboard 1: 📊 Executive Overview
**Collection:** Executive Dashboards/  
**Beschreibung:** Wichtigste KPIs für das Management  
**Update-Frequenz:** Täglich um 9:00 Uhr

#### KPI Cards (Reihe 1):
1. **Gesamt-Umsatz (Scalar Card)**
   ```sql
   SELECT ROUND(total_revenue::numeric, 2) as "Gesamt-Umsatz €"
   FROM analytics.executive_dashboard
   ```
   - **Position:** Oben links
   - **Format:** Currency (€)

2. **Anzahl Transaktionen (Scalar Card)**
   ```sql
   SELECT total_transactions as "Transaktionen"
   FROM analytics.executive_dashboard
   ```
   - **Position:** Oben Mitte-links

3. **Durchschnittlicher Bestellwert (Scalar Card)**
   ```sql
   SELECT ROUND(avg_order_value::numeric, 2) as "Ø Bestellwert €"
   FROM analytics.executive_dashboard
   ```
   - **Position:** Oben Mitte-rechts

4. **Täglicher Ø Umsatz (Scalar Card)**
   ```sql
   SELECT ROUND(avg_daily_revenue::numeric, 2) as "Ø Täglicher Umsatz €"
   FROM analytics.executive_dashboard
   ```
   - **Position:** Oben rechts

#### Charts (Reihe 2):
5. **Monatlicher Umsatz-Trend (Line Chart)**
   ```sql
   SELECT 
     month as "Monat",
     gross_revenue as "Umsatz €"
   FROM analytics.monthly_revenue 
   ORDER BY month
   ```
   - **X-Achse:** Monat
   - **Y-Achse:** Umsatz €
   - **Größe:** 2/3 der Breite

6. **Umsatzwachstum % (Bar Chart)**
   ```sql
   SELECT 
     TO_CHAR(month, 'YYYY-MM') as "Monat",
     revenue_growth_percent as "Wachstum %"
   FROM analytics.revenue_growth 
   WHERE revenue_growth_percent IS NOT NULL
   ORDER BY month DESC 
   LIMIT 12
   ```
   - **X-Achse:** Monat
   - **Y-Achse:** Wachstum %
   - **Größe:** 1/3 der Breite

#### Table (Reihe 3):
7. **Letzte Transaktionen (Table)**
   ```sql
   SELECT 
     transaction_date as "Datum",
     product_name as "Produkt",
     platform_name as "Plattform", 
     sale_price as "Preis €",
     buyer_destination_country as "Land"
   FROM analytics.recent_transactions 
   LIMIT 15
   ```

### Dashboard 2: 🎯 Product Performance
**Collection:** Product Performance/  
**Beschreibung:** Fokus auf Produktleistung, Bestseller und Preisanalyse  
**Update-Frequenz:** Täglich

#### Top Products Analysis:
1. **Top 20 Products by Revenue (Table)**
   ```sql
   SELECT 
     product_name as "Produkt",
     brand_name as "Marke",
     total_sales as "Verkäufe",
     ROUND(total_revenue::numeric, 2) as "Umsatz €",
     ROUND(avg_sale_price::numeric, 2) as "Ø Preis €",
     first_sale::date as "Erster Verkauf",
     last_sale::date as "Letzter Verkauf"
   FROM analytics.top_products_revenue 
   ORDER BY total_revenue DESC
   LIMIT 20
   ```

#### Product Performance Charts:
2. **Top 10 Products by Sales Volume (Bar Chart)**
   ```sql
   SELECT 
     CASE 
       WHEN LENGTH(product_name) > 30 THEN LEFT(product_name, 30) || '...'
       ELSE product_name 
     END as "Produkt",
     total_sales as "Verkäufe"
   FROM analytics.top_products_revenue 
   ORDER BY total_sales DESC 
   LIMIT 10
   ```

3. **Product Price Distribution (Bar Chart)**
   ```sql
   SELECT 
     CASE 
       WHEN avg_sale_price < 50 THEN '€0-49'
       WHEN avg_sale_price < 100 THEN '€50-99'
       WHEN avg_sale_price < 150 THEN '€100-149'
       WHEN avg_sale_price < 200 THEN '€150-199'
       ELSE '€200+'
     END as "Preisbereich",
     COUNT(*) as "Anzahl Produkte",
     SUM(total_sales) as "Total Verkäufe"
   FROM analytics.top_products_revenue
   GROUP BY 1
   ORDER BY 
     CASE 
       WHEN avg_sale_price < 50 THEN 1
       WHEN avg_sale_price < 100 THEN 2
       WHEN avg_sale_price < 150 THEN 3
       WHEN avg_sale_price < 200 THEN 4
       ELSE 5
     END
   ```

4. **Recent Top Sellers (Last 30 Days)**
   ```sql
   SELECT 
     p.product_name as "Produkt",
     COUNT(t.id) as "Verkäufe (30 Tage)",
     ROUND(SUM(t.sale_price)::numeric, 2) as "Umsatz €",
     ROUND(AVG(t.sale_price)::numeric, 2) as "Ø Preis €"
   FROM sales.transactions t
   JOIN products.inventory i ON t.inventory_id = i.id
   JOIN products.products p ON i.product_id = p.id
   WHERE t.transaction_date >= CURRENT_DATE - INTERVAL '30 days'
   GROUP BY p.product_name
   ORDER BY COUNT(t.id) DESC
   LIMIT 15
   ```

### Dashboard 3: 🏷️ Brand Overview
**Collection:** Brand Analytics/  
**Beschreibung:** Marken-Performance Übersicht und Vergleiche  
**Update-Frequenz:** Täglich

#### Brand Performance Analysis:
1. **Brand Market Share (Donut Chart)**
   ```sql
   SELECT 
     brand_name as "Marke",
     total_revenue as "Umsatz €"
   FROM analytics.brand_performance 
   WHERE brand_name IS NOT NULL
   ORDER BY total_revenue DESC 
   LIMIT 8
   ```

2. **Brand Performance Comparison (Table)**
   ```sql
   SELECT 
     brand_name as "Marke",
     total_sales as "Verkäufe",
     ROUND(total_revenue::numeric, 2) as "Umsatz €",
     ROUND(avg_sale_price::numeric, 2) as "Ø Preis €",
     unique_products as "Produkte"
   FROM analytics.brand_performance 
   WHERE brand_name IS NOT NULL
   ORDER BY total_revenue DESC 
   LIMIT 15
   ```

3. **Brand Sales Volume (Bar Chart)**
   ```sql
   SELECT 
     brand_name as "Marke",
     total_sales as "Verkäufe"
   FROM analytics.brand_performance 
   WHERE brand_name IS NOT NULL
   ORDER BY total_sales DESC 
   LIMIT 10
   ```

4. **Brand Average Price Comparison (Bar Chart)**
   ```sql
   SELECT 
     brand_name as "Marke",
     ROUND(avg_sale_price::numeric, 2) as "Ø Preis €"
   FROM analytics.brand_performance 
   WHERE brand_name IS NOT NULL AND total_sales >= 5
   ORDER BY avg_sale_price DESC 
   LIMIT 10
   ```

### Dashboard 4: 🏷️ Brand Deep Dive - Nike Focus
**Collection:** Brand Analytics/  
**Beschreibung:** Detaillierte Nike-Analyse (Dunk, Jordan, etc.)  
**Update-Frequenz:** Wöchentlich Montag 9:00 Uhr

#### Brand Overview:
1. **Brand Marktanteil (Donut Chart)**
   ```sql
   SELECT 
     extracted_brand as "Marke",
     total_revenue as "Umsatz €"
   FROM analytics.brand_deep_dive_overview 
   ORDER BY total_revenue DESC
   ```

2. **Brand Performance Table**
   ```sql
   SELECT 
     extracted_brand as "Marke",
     total_transactions as "Transaktionen",
     unique_products as "Produkte",
     ROUND(total_revenue::numeric, 2) as "Umsatz €",
     ROUND(avg_sale_price::numeric, 2) as "Ø Preis €"
   FROM analytics.brand_deep_dive_overview 
   ORDER BY total_revenue DESC
   ```

#### Nike Deep Dive:
3. **Nike Produktlinien (Table)**
   ```sql
   SELECT 
     nike_line as "Nike Linie",
     total_sales as "Verkäufe",
     ROUND(total_revenue::numeric, 2) as "Umsatz €",
     ROUND(avg_price::numeric, 2) as "Ø Preis €",
     unique_products as "Produkte"
   FROM analytics.nike_product_breakdown 
   ORDER BY total_revenue DESC
   ```

4. **Nike Line Performance (Bar Chart)**
   ```sql
   SELECT 
     nike_line as "Nike Linie",
     total_revenue as "Umsatz €"
   FROM analytics.nike_product_breakdown 
   ORDER BY total_revenue DESC
   ```

#### Brand Trends:
5. **Brand Monatstrends (Line Chart)**
   ```sql
   SELECT 
     month as "Monat",
     extracted_brand as "Marke",
     revenue as "Umsatz €"
   FROM analytics.brand_monthly_performance 
   WHERE month >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months')
     AND extracted_brand IN ('Nike', 'Nike Jordan', 'Adidas', 'Mattel', 'Off-White')
   ORDER BY month
   ```
   - **X-Achse:** Monat
   - **Y-Achse:** Umsatz €
   - **Series:** Marke

### Dashboard 5: 🏪 StockX Performance
**Collection:** Platform Analytics/  
**Beschreibung:** StockX Performance-Tracking und Gebühren-Analyse  
**Update-Frequenz:** Täglich

#### KPI Cards:
1. **StockX Umsatz (Scalar)**
   ```sql
   SELECT ROUND(total_revenue::numeric, 2) as "StockX Umsatz €"
   FROM analytics.platform_performance 
   WHERE LOWER(platform_name) = 'stockx'
   ```

2. **StockX Transaktionen (Scalar)**
   ```sql
   SELECT total_transactions as "StockX Transaktionen"
   FROM analytics.platform_performance 
   WHERE LOWER(platform_name) = 'stockx'
   ```

3. **Ø Transaktionswert (Scalar)**
   ```sql
   SELECT ROUND(avg_transaction_value::numeric, 2) as "Ø Transaktionswert €"
   FROM analytics.platform_performance 
   WHERE LOWER(platform_name) = 'stockx'
   ```

#### Charts:
4. **Platform Performance Table**
   ```sql
   SELECT 
     platform_name as "Plattform",
     total_transactions as "Transaktionen",
     ROUND(total_revenue::numeric, 2) as "Umsatz €",
     ROUND(avg_transaction_value::numeric, 2) as "Ø Wert €",
     ROUND(total_fees_paid::numeric, 2) as "Gebühren €"
   FROM analytics.platform_performance 
   ORDER BY total_revenue DESC
   ```

### Dashboard 6: 🌍 Sales by Location
**Collection:** Geographic Analytics/  
**Beschreibung:** Verkäufe nach Ländern und Regionen  
**Update-Frequenz:** Wöchentlich

#### Geographic Analysis:
1. **Top Zielländer (Table)**
   ```sql
   SELECT 
     destination_country as "Land",
     total_sales as "Verkäufe",
     ROUND(total_revenue::numeric, 2) as "Umsatz €",
     ROUND(avg_order_value::numeric, 2) as "Ø Bestellwert €"
   FROM analytics.sales_by_country 
   WHERE destination_country != 'Unknown'
   ORDER BY total_revenue DESC 
   LIMIT 20
   ```

2. **Revenue nach Land (Bar Chart)**
   ```sql
   SELECT 
     destination_country as "Land",
     total_revenue as "Umsatz €"
   FROM analytics.sales_by_country 
   WHERE destination_country != 'Unknown'
   ORDER BY total_revenue DESC 
   LIMIT 15
   ```

### Dashboard 7: ⏰ Daily & Weekly Trends
**Collection:** Time Analytics/  
**Beschreibung:** Zeitbasierte Performance-Analyse  
**Update-Frequenz:** Täglich

#### Time-based Charts:
1. **Täglicher Umsatz - Letzte 30 Tage (Line Chart)**
   ```sql
   SELECT 
     sale_date as "Datum",
     gross_revenue as "Umsatz €"
   FROM analytics.daily_revenue 
   WHERE sale_date >= CURRENT_DATE - INTERVAL '30 days'
   ORDER BY sale_date
   ```

2. **Umsatz nach Wochentag (Bar Chart)**
   ```sql
   SELECT 
     day_of_week_name as "Wochentag",
     ROUND(total_revenue::numeric, 2) as "Umsatz €"
   FROM analytics.sales_by_weekday 
   ORDER BY day_of_week_num
   ```

3. **Transaktionen nach Wochentag (Bar Chart)**
   ```sql
   SELECT 
     day_of_week_name as "Wochentag",
     total_sales as "Transaktionen"
   FROM analytics.sales_by_weekday 
   ORDER BY day_of_week_num
   ```

## 🎨 Design-Tipps

### Layout Guidelines:
- **KPI Cards:** Immer oben, 3-4 Cards pro Reihe
- **Main Charts:** Mittlerer Bereich, 50-70% der Breite
- **Detail Tables:** Unterer Bereich, volle Breite
- **Spacing:** 1 Einheit Abstand zwischen Cards

### Farb-Schema:
- **Grün (#059669):** Positive KPIs, Umsatz
- **Blau (#3B82F6):** Neutrale Metriken, Transaktionen  
- **Orange (#F59E0B):** Warnung, niedrige Performance
- **Rot (#DC2626):** Negative Werte, Verluste

### Filter Setup:
- **Zeitraum-Filter:** Letzte 7/30/90 Tage
- **Brand-Filter:** Nike, Adidas, etc.
- **Platform-Filter:** StockX, Alias (GOAT)

## 🔄 Automatisierung

### Email Subscriptions einrichten:
1. **Dashboard öffnen** → **Sharing Icon** → **Subscriptions**
2. **Add a subscription**
3. **Schedule:** 
   - Executive Dashboard: Täglich 9:00 Uhr
   - Brand Deep Dive: Wöchentlich Montag 9:00 Uhr
   - Monthly Reports: 1. des Monats 9:00 Uhr

### Alerts einrichten:
- **Täglicher Umsatz < €200:** Email Alert
- **Keine Transaktionen seit 24h:** Slack Alert
- **Top 5 Produkte Änderung:** Wöchentlicher Report

## ✅ Qualitätskontrolle

### Nach Dashboard-Erstellung prüfen:
- [ ] Alle Metriken laden korrekt
- [ ] Zeitfilter funktionieren
- [ ] Charts sind responsive
- [ ] Farben sind konsistent
- [ ] Tooltips sind informativ
- [ ] Export funktioniert (PDF/PNG)

---

## 🎯 Implementierungs-Roadmap

### Phase 1: Foundation (Tag 1-2)
1. **Collections anlegen** nach oben beschriebener Struktur
2. **Executive Overview Dashboard** erstellen (Priorität 1)
3. **Basis-Permissions** einrichten

### Phase 2: Core Analytics (Tag 3-5)  
4. **Product Performance Dashboard** erstellen (Priorität 1)
5. **Brand Overview Dashboard** erstellen 
6. **Brand Deep Dive - Nike Focus** erstellen
7. **StockX Performance Dashboard** erstellen

### Phase 3: Advanced Analytics (Tag 6-7)
8. **Geographic Analytics Dashboard** erstellen
9. **Time Analytics Dashboard** erstellen
10. **Email Subscriptions** einrichten

### Phase 4: Optimization (Woche 2)
11. **Dashboard-Performance** optimieren
12. **User Feedback** sammeln und umsetzen
13. **Alerts und Monitoring** einrichten
14. **Team-Training** durchführen

## 📋 Quick Start Checklist

### Vorbereitung:
- [ ] Metabase geöffnet (http://192.168.2.45:3000)
- [ ] Database Schema gesynct  
- [ ] Alle `analytics.*` Views verfügbar

### Collection Setup:
- [ ] Main Collection "SoleFlipper Analytics" erstellt
- [ ] 6 Sub-Collections angelegt
- [ ] Permissions konfiguriert

### Dashboard Erstellung (Priorität):
- [ ] 📊 Executive Overview (Collection: Executive Dashboards/)
- [ ] 🎯 Product Performance (Collection: Product Performance/)
- [ ] 🏷️ Brand Overview (Collection: Brand Analytics/)  
- [ ] 🏷️ Brand Deep Dive - Nike Focus (Collection: Brand Analytics/)
- [ ] 🏪 StockX Performance (Collection: Platform Analytics/)
- [ ] 🌍 Sales by Location (Collection: Geographic Analytics/)
- [ ] ⏰ Daily & Weekly Trends (Collection: Time Analytics/)

### Automatisierung:
- [ ] Email Subscriptions konfiguriert
- [ ] Performance Alerts eingerichtet
- [ ] Dashboard Auto-Refresh aktiviert

**Ready to build your analytics empire! 🚀📊**