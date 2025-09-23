# 🛠️ Budibase StockX API App - Manuelle Einrichtung

Da Budibase den JSON-Import nicht unterstützt, hier die Schritt-für-Schritt-Anleitung zur manuellen Erstellung:

## 🚀 **Schritt 1: Neue App erstellen**

1. **Budibase Builder öffnen**
   - Navigiere zu deiner Budibase-Instanz
   - Klicke auf "Create new app"
   - Name: `SoleFlipper StockX API`
   - URL: `/soleflip-stockx`

2. **Theme konfigurieren**
   - Settings → Design → Theme: `Midnight`
   - Primary Color: `#4285f4`
   - Navigation: `Top`

## 📊 **Schritt 2: Datenquellen einrichten**

### A) PostgreSQL Datenbank
```
Data → Add data source → PostgreSQL
```
**Konfiguration:**
- Name: `SoleFlipper Database`
- Host: `localhost`
- Port: `5432`
- Database: `soleflip`
- User: `{{ env.DB_USER }}`
- Password: `{{ env.DB_PASSWORD }}`
- SSL: `Disabled`

**Tabellen hinzufügen:**
- ✅ `products.products`
- ✅ `integration.market_prices`
- ✅ `sales.transactions`
- ✅ `inventory.stock_levels`

### B) StockX REST API
```
Data → Add data source → REST API
```
**Konfiguration:**
- Name: `StockX API`
- Base URL: `https://gateway.stockx.com/api`
- Headers:
  ```json
  {
    "Authorization": "Bearer {{ env.STOCKX_API_TOKEN }}",
    "Content-Type": "application/json",
    "Accept": "application/json"
  }
  ```

**Queries erstellen:**

**1. Search Products**
```
Method: GET
URL: /catalog/search?query={{ query }}&limit={{ limit }}
Parameters:
- query (string, required)
- limit (number, default: 20)
```

**2. Get Product Details**
```
Method: GET
URL: /catalog/products/{{ product_id }}
Parameters:
- product_id (string, required)
```

**3. Get Market Data**
```
Method: GET
URL: /catalog/products/{{ product_id }}/market
Parameters:
- product_id (string, required)
- currency (string, default: EUR)
```

### C) SoleFlipper Backend API
```
Data → Add data source → REST API
```
**Konfiguration:**
- Name: `SoleFlipper Backend`
- Base URL: `http://127.0.0.1:8000/api/v1`
- Headers:
  ```json
  {
    "Content-Type": "application/json"
  }
  ```

**Queries erstellen:**

**1. QuickFlip Opportunities**
```
Method: GET
URL: /quickflip/opportunities?min_profit_margin={{ min_margin }}&limit={{ limit }}
Parameters:
- min_margin (number, default: 10)
- limit (number, default: 100)
```

**2. Opportunities Summary**
```
Method: GET
URL: /quickflip/opportunities/summary
```

**3. Inventory Summary**
```
Method: GET
URL: /inventory/summary
```

## 🖥️ **Schritt 3: Screens erstellen**

### Screen 1: Dashboard (`/`)

**Layout:**
```
Container (Column)
├── Heading: "SoleFlipper StockX Dashboard"
├── Container (Row) - Stats Cards
│   ├── Card: "Active Opportunities"
│   │   └── Data Provider (SoleFlipper Backend → Opportunities Summary)
│   │       └── Text: "{{ data.total_opportunities }} Opportunities"
│   ├── Card: "Average Margin"
│   │   └── Text: "{{ data.avg_profit_margin }}%"
│   └── Card: "Total Products"
│       └── Data Provider (PostgreSQL → COUNT products)
│           └── Text: "{{ data.count }} Products"
├── Container (Row) - Content
│   ├── Card: "Top Opportunities" (60%)
│   │   └── Data Provider (SoleFlipper Backend → QuickFlip Opportunities)
│   │       └── Table:
│   │           - Columns: product_name, buy_price, sell_price, profit_margin
│   │           - Limit: 10
│   │           - Sort: profit_margin DESC
│   └── Card: "Recent Updates" (40%)
│       └── Data Provider (PostgreSQL → market_prices)
│           └── Table:
│               - Filter: last_updated >= NOW() - INTERVAL '24 hours'
│               - Columns: product_name, buy_price, source, last_updated
│               - Limit: 8
└── Button Row
    ├── Button: "Search StockX" → Navigate /stockx-search
    ├── Button: "View Opportunities" → Navigate /quickflip
    └── Button: "Price Monitor" → Navigate /price-monitor
```

### Screen 2: StockX Search (`/stockx-search`)

**Layout:**
```
Container (Column)
├── Heading: "StockX Product Search"
├── Form: "Search Form"
│   ├── Text Input: "search_term" (placeholder: "Enter product name...")
│   ├── Number Input: "limit" (default: 20)
│   └── Button: "Search" → Trigger StockX API query
└── Data Provider (StockX API → Search Products)
    └── Table:
        - Columns: title, brand, retail_price, market_price
        - Actions: [View Details]
        - Pagination: true
```

### Screen 3: QuickFlip Opportunities (`/quickflip`)

**Layout:**
```
Container (Column)
├── Heading: "QuickFlip Opportunities"
├── Form: "Filter Options"
│   ├── Number Input: "min_profit_margin" (default: 15)
│   ├── Number Input: "min_gross_profit" (default: 25)
│   ├── Number Input: "limit" (default: 50)
│   └── Button: "Update Results" → Refresh data
└── Data Provider (SoleFlipper Backend → QuickFlip Opportunities)
    └── Table:
        - Columns: product_name, brand_name, buy_price, sell_price, gross_profit, profit_margin, buy_source
        - Sort: profit_margin DESC
        - Actions: [Mark as Acted]
        - Export: CSV
```

### Screen 4: Price Monitor (`/price-monitor`)

**Layout:**
```
Container (Column)
├── Heading: "Price Monitor"
├── Form: "Filter"
│   ├── Select: "source" (options: awin, webgains, all)
│   └── Button: "Filter" → Apply filter
└── Data Provider (PostgreSQL → market_prices)
    └── Table:
        - Columns: product_name, source, supplier_name, buy_price, availability, last_updated
        - Sort: last_updated DESC
        - Filter: Dynamic based on form
        - Pagination: true
```

### Screen 5: Inventory (`/inventory`)

**Layout:**
```
Container (Column)
├── Heading: "Inventory Management"
├── Button: "Add Product" → Open modal
└── Data Provider (PostgreSQL → products)
    └── Table:
        - Columns: name, sku, brand, category, stockx_product_id, created_at
        - Sort: created_at DESC
        - Actions: [Edit, Delete]
        - Search: Global search
```

## 🔄 **Schritt 4: Navigation einrichten**

**Navigation Menu:**
```
Design → Navigation → Links:
1. Home → / (Icon: Home)
2. StockX Search → /stockx-search (Icon: Search)
3. QuickFlip → /quickflip (Icon: TrendingUp)
4. Price Monitor → /price-monitor (Icon: BarChart)
5. Inventory → /inventory (Icon: Package)
```

## 🤖 **Schritt 5: Automationen (Optional)**

### Price Alert Automation
```
Automate → Create Automation
```
**Trigger:** `Cron` - `*/15 * * * *` (every 15 minutes)

**Steps:**
1. **Query Data** → SoleFlipper Backend → QuickFlip Opportunities
   - Parameters: min_profit_margin: 40, limit: 50

2. **Filter Data** → JavaScript
   ```javascript
   return steps.trigger.data.filter(item => item.gross_profit > 50);
   ```

3. **Conditional** → `{{ steps.filter.data.length > 0 }}`
   - **True:** Send Email
     - To: `{{ env.ALERT_EMAIL }}`
     - Subject: `🚀 High-Profit Opportunities Found!`
     - Body: Dynamic message with opportunity details

## 🔐 **Schritt 6: Environment Variables**

**Settings → Environment Variables:**
```bash
# StockX API
STOCKX_API_TOKEN=your_stockx_token_here
STOCKX_CLIENT_ID=your_client_id
STOCKX_CLIENT_SECRET=your_client_secret

# Database
DB_USER=soleflip_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=soleflip

# Alerts
ALERT_EMAIL=your-email@domain.com
```

## 🎨 **Schritt 7: Styling & Theming**

**Custom CSS:** (Design → Theme → Custom CSS)
```css
/* QuickFlip Cards */
.bb-card {
  transition: transform 0.2s ease;
}

.bb-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

/* Profit Indicators */
.profit-high {
  color: #10b981;
  font-weight: bold;
}

.profit-medium {
  color: #f59e0b;
}

.profit-low {
  color: #ef4444;
}

/* Status Badges */
.status-available {
  background: #10b981;
  color: white;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.status-unavailable {
  background: #ef4444;
  color: white;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
}
```

## ✅ **Schritt 8: Testing & Go-Live**

### Testing Checklist:
- [ ] PostgreSQL Verbindung funktioniert
- [ ] StockX API liefert Suchergebnisse
- [ ] QuickFlip Opportunities werden angezeigt
- [ ] Navigation zwischen Screens funktioniert
- [ ] Automationen laufen korrekt
- [ ] Mobile Responsive Design

### Go-Live:
1. **Preview** → Test all functionality
2. **Publish** → Make app available
3. **User Access** → Configure roles and permissions
4. **Monitoring** → Set up performance monitoring

## 🔧 **Troubleshooting**

**Häufige Probleme:**

1. **API Connection Failed**
   - Environment Variables prüfen
   - API Token validieren
   - Network/Firewall prüfen

2. **Database Connection Error**
   - PostgreSQL läuft?
   - Credentials korrekt?
   - Tabellen existieren?

3. **No Data Showing**
   - Data Provider konfiguriert?
   - Query Parameters korrekt?
   - Table Columns mapped?

## 📊 **Performance Optimization**

- **Caching:** 5 Minuten für API Responses
- **Pagination:** Max 100 Rows per Table
- **Lazy Loading:** Für Charts und große Tabellen
- **Refresh Interval:** Auto-refresh alle 5 Minuten

---

**🎉 Nach diesen Schritten hast du eine vollständige SoleFlipper StockX API App in Budibase!**

**Geschätzte Setup-Zeit:** 2-3 Stunden
**Schwierigkeit:** Mittel
**Wartungsaufwand:** Niedrig