# Schema Enhancements - Gibson Features Integration

## Overview

PostgreSQL-Datenbank wurde um sinnvolle Features aus dem Gibson-Schema erweitert, während die bestehende PostgreSQL-Struktur beibehalten wurde.

## Datum
2025-10-25

## Migration
`migrations/versions/2025_10_25_2000_add_gibson_features.py`

---

## Hinzugefügte Features

### 1. **Compliance Schema** (3 Tabellen)

#### `compliance.business_rules`
Konfigurierbare Business Rules für automatisierte Geschäftslogik.

**Verwendung:**
```sql
INSERT INTO compliance.business_rules (rule_name, description, conditions, actions, active)
VALUES (
    'min_profit_threshold',
    'Reject listings below 15% profit margin',
    '{"min_profit_percent": 15}'::jsonb,
    '{"action": "reject", "notify": "admin@example.com"}'::jsonb,
    true
);
```

#### `compliance.data_retention_policies`
Definiert Datenaufbewahrungsfristen für GDPR/Compliance.

**Verwendung:**
```sql
INSERT INTO compliance.data_retention_policies (entity_name, retention_period_days, effective_date, description)
VALUES (
    'sales.order',
    2555,  -- 7 Jahre
    '2025-01-01',
    'Tax compliance requires 7 years retention'
);
```

#### `compliance.user_permissions`
Role-Based Access Control (RBAC) für granulare Berechtigungen.

**Verwendung:**
```sql
-- Grant permission
INSERT INTO compliance.user_permissions (user_id, permission_key, granted_by, expires_at)
VALUES (
    (SELECT id FROM auth.users WHERE email = 'user@example.com'),
    'pricing.update',
    'admin',
    now() + interval '1 year'
);

-- Check permissions
SELECT * FROM compliance.user_permissions
WHERE user_id = ?
  AND (expires_at IS NULL OR expires_at > now());
```

---

### 2. **Operations Schema** (3 Tabellen)

#### `operations.listing_history`
Tracking aller Listing-Status-Änderungen für Audit Trail.

**Verwendung:**
```sql
-- Automatisch via Trigger bei Listing-Updates, oder manuell:
INSERT INTO operations.listing_history (listing_id, status, previous_status, change_reason, changed_by)
VALUES (
    'listing-uuid',
    'sold',
    'active',
    'Order completed',
    'system'
);

-- Timeline anzeigen
SELECT changed_at, status, change_reason
FROM operations.listing_history
WHERE listing_id = 'listing-uuid'
ORDER BY changed_at DESC;
```

#### `operations.order_fulfillment`
Versand- und Fulfillment-Tracking.

**Verwendung:**
```sql
-- Fulfillment anlegen
INSERT INTO operations.order_fulfillment (
    order_id, shipping_provider, tracking_number, status, estimated_delivery
)
VALUES (
    'order-uuid',
    'DHL',
    'DHL123456789',
    'shipped',
    CURRENT_DATE + 3
);

-- Status Update
UPDATE operations.order_fulfillment
SET status = 'delivered', delivered_at = now()
WHERE order_id = 'order-uuid';

-- Pending Shipments
SELECT o.stockx_order_number, of.shipping_provider, of.estimated_delivery
FROM operations.order_fulfillment of
JOIN sales.order o ON of.order_id = o.id
WHERE of.status = 'shipped';
```

#### `operations.supplier_platform_integration`
Supplier-zu-Platform Integrationen (API-Sync Settings).

**Verwendung:**
```sql
-- Integration anlegen
INSERT INTO operations.supplier_platform_integration (
    supplier_id, platform_id, integration_active, sync_settings
)
VALUES (
    (SELECT id FROM supplier.profile WHERE name = 'FastKicks'),
    (SELECT id FROM platform.marketplace WHERE name = 'StockX'),
    true,
    '{"auto_sync": true, "sync_interval_hours": 6}'::jsonb
);

-- Active Integrations anzeigen
SELECT sp.name, pm.name, spi.last_sync_at, spi.sync_status
FROM operations.supplier_platform_integration spi
JOIN supplier.profile sp ON spi.supplier_id = sp.id
JOIN platform.marketplace pm ON spi.platform_id = pm.id
WHERE spi.integration_active = true;
```

---

### 3. **Realtime Schema** (1 Tabelle)

#### `realtime.event_log`
Logging für Real-Time Events/Notifications (WebSocket, SSE, etc.).

**Verwendung:**
```sql
-- Event loggen
INSERT INTO realtime.event_log (
    event_id, channel_name, event_type, event_payload, source_table, source_record_id
)
VALUES (
    gen_random_uuid()::text,
    'orders',
    'order.created',
    '{"order_id": "123", "amount": 250.00}'::jsonb,
    'sales.order',
    'order-uuid'
);

-- Recent Events für Channel
SELECT event_type, event_payload, sent_at
FROM realtime.event_log
WHERE channel_name = 'orders'
  AND sent_at > now() - interval '1 hour'
ORDER BY sent_at DESC;
```

---

### 4. **Inventory Split Tables** (4 Tabellen)

Detailliertes Inventory-Tracking mit Separation of Concerns.

#### `inventory.stock_financial`
Finanzielle Metriken pro Stock-Item.

**Verwendung:**
```sql
-- Beim Stock-Anlegen Financial Record erstellen
INSERT INTO inventory.stock_financial (
    stock_id, purchase_price, gross_purchase_price, vat_amount, profit_per_shelf_day, roi
)
VALUES (
    'stock-uuid',
    100.00,  -- Net price
    119.00,  -- Including VAT
    19.00,   -- VAT amount
    2.50,    -- Daily profit
    35.00    -- ROI %
);

-- Financial Summary
SELECT
    s.product_id,
    COUNT(*) as items,
    AVG(sf.purchase_price) as avg_price,
    SUM(sf.gross_purchase_price) as total_investment,
    AVG(sf.roi) as avg_roi
FROM inventory.stock s
JOIN inventory.stock_financial sf ON s.id = sf.stock_id
WHERE s.quantity > 0
GROUP BY s.product_id;
```

#### `inventory.stock_lifecycle`
Lifecycle-Tracking (Shelf-Life, Multi-Platform Status).

**Verwendung:**
```sql
-- Lifecycle anlegen
INSERT INTO inventory.stock_lifecycle (
    stock_id, shelf_life_days, listed_on_platforms, status_history
)
VALUES (
    'stock-uuid',
    45,
    '["stockx", "ebay"]'::jsonb,
    '[{"status": "received", "date": "2025-10-01"}, {"status": "listed", "date": "2025-10-02"}]'::jsonb
);

-- Items mit langer Shelf-Life
SELECT s.id, s.product_id, sl.shelf_life_days
FROM inventory.stock s
JOIN inventory.stock_lifecycle sl ON s.id = sl.stock_id
WHERE sl.shelf_life_days > 60
ORDER BY sl.shelf_life_days DESC;
```

#### `inventory.stock_reservation`
Stock-Reservierungen für Holds/Allocations.

**Verwendung:**
```sql
-- Stock reservieren
INSERT INTO inventory.stock_reservation (
    stock_id, reserved_quantity, reserved_until, reservation_reason, status, reserved_by
)
VALUES (
    'stock-uuid',
    1,
    now() + interval '48 hours',
    'Customer hold for order #12345',
    'active',
    'sales_team'
);

-- Available Quantity berechnen
SELECT
    s.id,
    s.quantity as total_quantity,
    COALESCE(SUM(sr.reserved_quantity) FILTER (WHERE sr.status = 'active'), 0) as reserved,
    s.quantity - COALESCE(SUM(sr.reserved_quantity) FILTER (WHERE sr.status = 'active'), 0) as available
FROM inventory.stock s
LEFT JOIN inventory.stock_reservation sr ON s.id = sr.stock_id
  AND (sr.reserved_until IS NULL OR sr.reserved_until > now())
WHERE s.id = 'stock-uuid'
GROUP BY s.id, s.quantity;
```

#### `inventory.stock_metrics`
Aggregierte Metriken pro Stock-Item (Performance-Cache).

**Verwendung:**
```sql
-- Metrics berechnen und speichern
INSERT INTO inventory.stock_metrics (
    stock_id, available_quantity, reserved_quantity, total_cost, expected_profit
)
SELECT
    s.id,
    s.quantity - COALESCE(SUM(sr.reserved_quantity), 0) as available,
    COALESCE(SUM(sr.reserved_quantity), 0) as reserved,
    sf.gross_purchase_price,
    sf.purchase_price * 0.35  -- Expected profit
FROM inventory.stock s
LEFT JOIN inventory.stock_reservation sr ON s.id = sr.stock_id AND sr.status = 'active'
LEFT JOIN inventory.stock_financial sf ON s.id = sf.stock_id
WHERE s.id = 'stock-uuid'
GROUP BY s.id, s.quantity, sf.gross_purchase_price, sf.purchase_price
ON CONFLICT (stock_id) DO UPDATE SET
    available_quantity = EXCLUDED.available_quantity,
    reserved_quantity = EXCLUDED.reserved_quantity,
    last_calculated_at = now();

-- Quick Metrics Lookup
SELECT * FROM inventory.stock_metrics WHERE stock_id = 'stock-uuid';
```

---

### 5. **Analytics Materialized Views** (3 Views)

Performance-optimierte Dashboards mit aggregierten Daten.

#### `analytics.inventory_status_summary`
Real-time Inventory Status pro Produkt.

**Verwendung:**
```sql
-- View abfragen (cached data)
SELECT
    product_id,
    total_items,
    total_quantity,
    available_quantity,
    supplier_count,
    avg_purchase_price,
    total_investment
FROM analytics.inventory_status_summary
ORDER BY total_investment DESC;

-- View refreshen (periodisch via Cron/Job)
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.inventory_status_summary;
```

#### `analytics.sales_summary_daily`
Tägliche Sales-Summary.

**Verwendung:**
```sql
-- Last 7 days performance
SELECT
    summary_date,
    total_orders,
    total_revenue,
    avg_order_value,
    gross_profit,
    avg_roi
FROM analytics.sales_summary_daily
WHERE summary_date > CURRENT_DATE - 7
ORDER BY summary_date DESC;

-- Refresh
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.sales_summary_daily;
```

#### `analytics.supplier_performance_summary`
Supplier Performance Metrics.

**Verwendung:**
```sql
-- Top Suppliers
SELECT
    sp.name,
    sps.total_stock_items,
    sps.total_spent,
    sps.avg_roi,
    sps.open_issues
FROM analytics.supplier_performance_summary sps
JOIN supplier.profile sp ON sps.supplier_id = sp.id
WHERE sps.avg_roi IS NOT NULL
ORDER BY sps.avg_roi DESC
LIMIT 10;

-- Refresh
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.supplier_performance_summary;
```

**View Refresh Strategy:**
```sql
-- Option 1: Manual Refresh
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.inventory_status_summary;

-- Option 2: Scheduled Refresh (via pg_cron extension)
SELECT cron.schedule(
    'refresh-analytics-views',
    '0 * * * *',  -- Every hour
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.inventory_status_summary$$
);

-- Option 3: Trigger-Based (on significant changes)
-- Implement via background job/worker
```

---

## Finale Statistik

```
Total Tables:           50 (+11 neue)
Neue Schemas:           3 (compliance, operations, realtime)
Neue Inventory Tables:  4 (stock_financial, stock_lifecycle, stock_reservation, stock_metrics)
Materialized Views:     3 (inventory_status_summary, sales_summary_daily, supplier_performance_summary)
Gibson-Aligned Schemas: 12
```

---

## PostgreSQL-Spezifische Features (Behalten)

Diese Tabellen bleiben PostgreSQL-spezifisch und werden **NICHT** nach Gibson synchronisiert:

1. **auth.users** - Lokale Authentifizierung
2. **catalog.brand_history** - Brand Timeline Tracking (NEU: 2025-10-25)
3. **catalog.brand_patterns** - Brand Intelligence Data
4. **supplier.supplier_history** - Supplier Timeline Tracking (NEU: 2025-10-25)
5. **analytics.forecast_accuracy** - ML Forecast Metrics
6. **core.sizes** - Legacy Size System
7. **core.size_validation_log** - StockX Size Validation

---

## Best Practices

### 1. Materialized Views Refreshen
```bash
# Via Cron Job (empfohlen für Produktion)
0 * * * * psql -U soleflip -d soleflip -c "REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.inventory_status_summary"
0 2 * * * psql -U soleflip -d soleflip -c "REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.sales_summary_daily"
0 3 * * * psql -U soleflip -d soleflip -c "REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.supplier_performance_summary"
```

### 2. Cleanup Old Realtime Events
```sql
-- Alte Events entfernen (älter als 7 Tage)
DELETE FROM realtime.event_log
WHERE sent_at < now() - interval '7 days';
```

### 3. Compliance Data Retention
```sql
-- Compliance-konforme Datenlöschung
DELETE FROM sales.order
WHERE created_at < now() - interval '1 year' * (
    SELECT retention_period_days / 365
    FROM compliance.data_retention_policies
    WHERE entity_name = 'sales.order'
);
```

---

## Rollback

Falls die neuen Features zurückgenommen werden müssen:

```bash
# Via Alembic
alembic downgrade -1

# Oder manuell via SQL:
DROP MATERIALIZED VIEW IF EXISTS analytics.supplier_performance_summary;
DROP MATERIALIZED VIEW IF EXISTS analytics.sales_summary_daily;
DROP MATERIALIZED VIEW IF EXISTS analytics.inventory_status_summary;

DROP TABLE inventory.stock_metrics;
DROP TABLE inventory.stock_reservation;
DROP TABLE inventory.stock_lifecycle;
DROP TABLE inventory.stock_financial;

DROP SCHEMA IF EXISTS realtime CASCADE;
DROP SCHEMA IF EXISTS operations CASCADE;
DROP SCHEMA IF EXISTS compliance CASCADE;
```

---

## Nächste Schritte

1. **Monitoring Setup** - Prometheus/Grafana Dashboards für Materialized Views
2. **Automated Refresh** - Cron Jobs oder pg_cron für View Refreshes
3. **API Integration** - FastAPI Endpoints für neue Features
4. **Documentation** - API Docs für Compliance/Operations Endpoints
5. **Testing** - Unit/Integration Tests für neue Features

---

## Migrationen Timeline

1. ✅ `2025_10_22_1722_add_gibson_size_system.py` - Gibson Size System
2. ✅ `2025_10_25_1800_move_size_tables_to_catalog.py` - Size Tables → Catalog
3. ✅ `2025_10_25_1900_add_brand_supplier_history.py` - Brand/Supplier History
4. ✅ `2025_10_25_2000_add_gibson_features.py` - Gibson Features Integration
