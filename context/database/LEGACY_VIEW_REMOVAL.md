# Legacy View Removal - v2.2.6
**Datum:** 2025-10-10
**Issue:** analytics.legacy_supplier_analysis verwendet veraltetes String-Feld

## ❌ Entfernte View

### `analytics.legacy_supplier_analysis`

**Problem:**
- Verwendete `inventory.supplier` (String-Feld) statt `supplier_id` (Relation)
- Zeigte falsche Daten:
  - "g0tchi" als Supplier (190 Items) ❌
  - "StockX" als Supplier (60 Items) ❌
  - Nur "allike" war korrekt (über supplier_id) ✅

**View Definition (veraltet):**
```sql
SELECT
    supplier AS supplier_name,  -- ❌ String-Feld statt Relation
    count(*) AS total_items,
    count(CASE WHEN status = 'available' THEN 1 END) AS available_items,
    count(CASE WHEN status = 'sold' THEN 1 END) AS sold_items,
    round((count(*) * 100.0 / sum(count(*)) OVER ()), 2) AS supplier_share_percent,
    round(avg(purchase_price), 2) AS avg_purchase_price,
    -- ... weitere Felder
FROM products.inventory
WHERE supplier IS NOT NULL AND supplier <> ''
GROUP BY supplier
ORDER BY count(*) DESC;
```

## ✅ Ersatz: `analytics.supplier_profitability`

**Vorteile:**
- ✅ Verwendet korrekte `supplier_id` Relation
- ✅ Zeigt nur echte Supplier aus `core.suppliers`
- ✅ VAT-aware Berechnungen (net vs gross)
- ✅ Sell-Through-Rate Tracking
- ✅ ROI pro Supplier
- ✅ Verkaufsmetriken aus `transactions.orders`

**View Definition (neu):**
```sql
CREATE VIEW analytics.supplier_profitability AS
SELECT
    COALESCE(s.name, 'Unknown Supplier') as supplier_name,
    s.slug as supplier_slug,
    COUNT(DISTINCT i.id) as total_items_purchased,
    COUNT(DISTINCT o.id) as total_items_sold,

    -- VAT-aware calculations
    SUM(i.purchase_price) as total_purchase_net,
    SUM(i.gross_purchase_price) as total_purchase_gross,
    SUM(i.vat_amount) as total_vat_paid,

    -- Sales metrics
    SUM(o.gross_sale) as total_sale_revenue,
    SUM(o.net_proceeds) as total_net_proceeds,
    SUM(o.net_profit) as total_net_profit,
    AVG(o.roi) as avg_roi_percent,

    -- Sell-through rate
    ROUND((COUNT(DISTINCT o.id)::numeric / NULLIF(COUNT(DISTINCT i.id), 0) * 100), 2)
        as sell_through_rate_percent

FROM products.inventory i
LEFT JOIN core.suppliers s ON i.supplier_id = s.id  -- ✅ Proper relation
LEFT JOIN transactions.orders o ON o.inventory_item_id = i.id AND o.sold_at IS NOT NULL
WHERE i.purchase_date IS NOT NULL
GROUP BY s.id, s.name, s.slug
ORDER BY total_net_profit DESC NULLS LAST;
```

## 📊 Migration für Metabase Dashboards

Falls Metabase-Dashboards die alte View verwenden:

### Option 1: View-Name austauschen
```sql
-- In Metabase Query Builder
-- ALT:
SELECT * FROM analytics.legacy_supplier_analysis

-- NEU:
SELECT * FROM analytics.supplier_profitability
```

### Option 2: Spalten-Mapping

| Legacy View | Neue View | Änderung |
|-------------|-----------|----------|
| `supplier_name` | `supplier_name` | ✅ Gleich |
| `total_items` | `total_items_purchased` | ⚠️ Name geändert |
| `sold_items` | `total_items_sold` | ⚠️ Name geändert |
| `avg_purchase_price` | - | ❌ Entfernt (nutze `total_purchase_net / total_items_purchased`) |
| `total_value` | `total_purchase_gross` | ⚠️ Name geändert |
| - | `sell_through_rate_percent` | ✨ NEU |
| - | `avg_roi_percent` | ✨ NEU |
| - | `total_net_profit` | ✨ NEU |

## 🔧 Durchgeführte Maßnahmen

```sql
-- View entfernt (2025-10-10)
DROP VIEW IF EXISTS analytics.legacy_supplier_analysis CASCADE;
```

## 📝 Hinweise für zukünftige Entwicklung

1. **String-Feld `inventory.supplier` sollte deprecatet werden**
   - Aktuell gibt es noch 250+ Items mit String-Wert statt Relation
   - Migration-Script erstellen für Daten-Cleanup

2. **Alle Views sollten `supplier_id` Relation nutzen**
   - Nicht mehr `inventory.supplier` String-Feld
   - Bessere Datenintegrität durch Foreign Key

3. **Metabase Dashboards prüfen**
   - Falls `legacy_supplier_analysis` verwendet wird
   - Auf `supplier_profitability` umstellen
