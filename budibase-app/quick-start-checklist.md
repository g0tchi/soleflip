# ✅ Budibase StockX API App - Quick Start Checklist

## 🎯 **15-Minuten Setup für erfahrene Budibase-User**

### **Phase 1: App & Datenquellen (5 Min)**

**✅ 1. App erstellen**
```
Create App → "SoleFlipper StockX API" → Theme: Midnight
```

**✅ 2. PostgreSQL verbinden**
```
Data → PostgreSQL → localhost:5432/soleflip
Tabellen: products.products, integration.market_prices
```

**✅ 3. REST APIs hinzufügen**
```
StockX API: https://gateway.stockx.com/api
SoleFlipper: http://127.0.0.1:8000/api/v1
```

### **Phase 2: Screens erstellen (8 Min)**

**✅ 4. Dashboard Screen**
```
/ → Container (Column)
├── Stats Row: 3 Cards (Opportunities, Margin, Products)
├── Table: Top 10 QuickFlip Opportunities
└── Buttons: Navigation Links
```

**✅ 5. QuickFlip Screen**
```
/quickflip → Container (Column)
├── Filter Form (margin, profit, limit)
└── Table: All Opportunities mit Actions
```

**✅ 6. StockX Search**
```
/stockx-search → Container (Column)
├── Search Form (product name, limit)
└── Results Table
```

**✅ 7. Price Monitor**
```
/price-monitor → Container (Column)
├── Source Filter
└── Market Prices Table
```

### **Phase 3: Navigation & Testing (2 Min)**

**✅ 8. Navigation Menu**
```
Design → Navigation → Add Links:
Home, QuickFlip, StockX Search, Price Monitor
```

**✅ 9. Quick Test**
```
Preview → Test alle Screens → Daten laden korrekt?
```

**✅ 10. Publish**
```
Publish App → Live schalten
```

---

## 🚀 **Express Setup - Copy & Paste Configs**

### **Environment Variables**
```bash
STOCKX_API_TOKEN=your_token_here
DB_USER=soleflip_user
DB_PASSWORD=your_password
ALERT_EMAIL=your@email.com
```

### **PostgreSQL Custom Queries**

**QuickFlip Opportunities:**
```sql
SELECT DISTINCT ON (mp.product_id, mp.source)
    mp.product_id,
    p.name as product_name,
    p.brand as brand_name,
    mp.buy_price,
    COALESCE(p.current_market_price, p.retail_price * 1.2) as sell_price,
    (COALESCE(p.current_market_price, p.retail_price * 1.2) - mp.buy_price) as gross_profit,
    ROUND(((COALESCE(p.current_market_price, p.retail_price * 1.2) - mp.buy_price) / mp.buy_price * 100), 2) as profit_margin,
    mp.source as buy_source
FROM integration.market_prices mp
JOIN products.products p ON mp.product_id = p.id
WHERE mp.availability = true
AND ((COALESCE(p.current_market_price, p.retail_price * 1.2) - mp.buy_price) / mp.buy_price * 100) >= {{ min_margin }}
ORDER BY mp.product_id, mp.source, profit_margin DESC
LIMIT {{ limit }};
```

**Dashboard Summary:**
```sql
SELECT
    COUNT(*) as total_opportunities,
    ROUND(AVG(profit_margin), 2) as avg_profit_margin,
    COUNT(DISTINCT source) as active_sources
FROM (
    SELECT DISTINCT ON (mp.product_id, mp.source)
        mp.product_id,
        mp.source,
        ROUND(((COALESCE(p.current_market_price, p.retail_price * 1.2) - mp.buy_price) / mp.buy_price * 100), 2) as profit_margin
    FROM integration.market_prices mp
    JOIN products.products p ON mp.product_id = p.id
    WHERE mp.availability = true
    AND ((COALESCE(p.current_market_price, p.retail_price * 1.2) - mp.buy_price) / mp.buy_price * 100) >= 10
) opportunities;
```

**Recent Price Updates:**
```sql
SELECT
    p.name as product_name,
    mp.source,
    mp.buy_price,
    mp.availability,
    mp.last_updated
FROM integration.market_prices mp
JOIN products.products p ON mp.product_id = p.id
WHERE mp.last_updated >= NOW() - INTERVAL '24 hours'
ORDER BY mp.last_updated DESC
LIMIT 20;
```

### **StockX API Queries**

**Search Products:**
```
GET /catalog/search?query={{ query }}&limit={{ limit }}
```

**Product Details:**
```
GET /catalog/products/{{ product_id }}
```

### **SoleFlipper API Queries**

**QuickFlip Opportunities:**
```
GET /quickflip/opportunities?min_profit_margin={{ min_margin }}&limit={{ limit }}
```

**Summary Stats:**
```
GET /quickflip/opportunities/summary
```

---

## 🎨 **One-Click Styling**

**Custom CSS:**
```css
/* Profit Colors */
.profit-high { color: #10b981; font-weight: bold; }
.profit-medium { color: #f59e0b; }
.profit-low { color: #ef4444; }

/* Cards */
.bb-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

/* Status Badges */
.status-available {
    background: #10b981;
    color: white;
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 12px;
}
```

---

## 🔍 **Troubleshooting Schnell-Check**

**❌ Keine Daten?**
```sql
-- Test PostgreSQL
SELECT COUNT(*) FROM products.products;
SELECT COUNT(*) FROM integration.market_prices;
```

**❌ API Fehler?**
```bash
# Test StockX API
curl -H "Authorization: Bearer $STOCKX_API_TOKEN" https://gateway.stockx.com/api/health

# Test SoleFlipper API
curl http://127.0.0.1:8000/health
```

**❌ Queries leer?**
- Environment Variables gesetzt?
- Query Parameters richtig mapped?
- Table Columns korrekt?

---

## ⚡ **Pro Tips**

1. **Bulk Setup**: Importiere alle SQL Views aus `budibase-table-configs.sql`
2. **Auto-Refresh**: Dashboard alle 5 Minuten
3. **Mobile First**: Teste auf Handy
4. **Performance**: Max 100 Rows pro Table
5. **Caching**: 5 Min für API Calls

---

**🎉 Nach 15 Minuten: Vollständige SoleFlipper StockX API App ready!**

**Nächste Schritte:**
- [ ] User-Management konfigurieren
- [ ] Automationen für Alerts einrichten
- [ ] Performance monitoring
- [ ] Mobile App testen