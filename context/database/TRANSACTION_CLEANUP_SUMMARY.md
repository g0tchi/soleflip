# Transaction Cleanup Summary - v2.2.5
**Datum:** 2025-10-09
**Issue:** Datenredundanz zwischen `transactions.transactions` und `transactions.orders`

## ✅ Durchgeführte Maßnahmen

### 1. Redundanter Eintrag entfernt
```sql
DELETE FROM transactions.transactions
WHERE external_id = '04-UW2Q0ZAQT8';
```

**Ergebnis:**
- ✅ Redundanter Transaction-Record gelöscht
- ✅ `transactions.transactions` ist jetzt leer (0 Einträge)
- ✅ Alle Verkaufsdaten bleiben in `transactions.orders` erhalten

### 2. Aktueller Zustand - Timex Verkauf

| Tabelle | Status | Daten |
|---------|--------|-------|
| `products.inventory` | ✅ AKTIV | status: sold, roi_percentage: 26.90% |
| `transactions.orders` | ✅ AKTIV | Order: 04-UW2Q0ZAQT8, vollständige Verkaufsdaten |
| `transactions.transactions` | ✅ LEER | Redundanter Eintrag entfernt |

## 📋 Architektur-Entscheidung

### ❌ NICHT verwenden: `transactions.transactions`

**Gründe:**
1. **Redundanz:** Einkaufsdaten sind bereits in `products.inventory`
2. **Duplikate:** Verkaufsdaten sind bereits in `transactions.orders`
3. **Inkonsistenz:** Zwei Tabellen für dieselben Verkaufsdaten

### ✅ EMPFOHLEN: `transactions.orders`

**Vorteile:**
1. **Vollständig:** Enthält alle Verkaufsdaten
2. **Multi-Platform Ready:** `platform_id` ermöglicht eBay, GOAT, etc.
3. **Keine Redundanz:** Einkaufsdaten via JOIN von `products.inventory`
4. **Plattform-spezifisch:** Separate Felder für StockX-Daten (shipping_label_url, etc.)

## 🎯 Konkrete Empfehlungen für zukünftige Entwicklung

### Option A: `transactions.orders` umbenennen (EMPFOHLEN)

```sql
-- Tabelle umbenennen für Klarheit
ALTER TABLE transactions.orders RENAME TO multi_platform_orders;

-- Oder: Neue universelle Order-Tabelle erstellen
CREATE TABLE transactions.platform_orders (
    id UUID PRIMARY KEY,
    inventory_item_id UUID REFERENCES products.inventory(id),
    platform_id UUID REFERENCES core.platforms(id) NOT NULL,

    -- Universelle Felder (alle Plattformen)
    external_order_id VARCHAR(100) NOT NULL,
    sold_at TIMESTAMP WITH TIME ZONE,
    gross_sale NUMERIC(10,2),
    net_proceeds NUMERIC(10,2),
    platform_fee NUMERIC(10,2),
    net_profit NUMERIC(10,2),
    roi NUMERIC(5,2),
    status VARCHAR(50),

    -- Plattform-spezifische Daten
    platform_metadata JSONB,  -- StockX: {shipping_label_url, ...}
                              -- eBay: {listing_id, ...}
                              -- GOAT: {...}

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Option B: Separate Tabellen pro Plattform

```python
# domains/orders/models.py

class StockXOrder(Base, TimestampMixin):
    """StockX-spezifische Orders"""
    __tablename__ = "stockx_orders"
    __table_args__ = {"schema": "platforms"} if IS_POSTGRES else None

    # ... StockX-spezifische Felder

class eBayOrder(Base, TimestampMixin):
    """eBay-spezifische Orders"""
    __tablename__ = "ebay_orders"
    __table_args__ = {"schema": "platforms"} if IS_POSTGRES else None

    # ... eBay-spezifische Felder

class GOATOrder(Base, TimestampMixin):
    """GOAT-spezifische Orders"""
    __tablename__ = "goat_orders"
    __table_args__ = {"schema": "platforms"} if IS_POSTGRES else None

    # ... GOAT-spezifische Felder
```

**Vorteil:** Jede Plattform hat eigene Felder
**Nachteil:** Mehr Tabellen, komplexere Queries für Gesamt-Analysen

## 📝 Code-Änderungen für v2.2.6

### 1. `scripts/record_timex_sale.py` korrigieren

**VORHER (v2.2.5):**
```python
# Erstellt ZWEI Records (redundant!)
await session.execute(text("INSERT INTO transactions.orders ..."))
await session.execute(text("INSERT INTO transactions.transactions ..."))  # ❌ REDUNDANT
```

**NACHHER (v2.2.6):**
```python
# Nur EINEN Order-Record erstellen
await session.execute(
    text("""
        INSERT INTO transactions.orders (
            inventory_item_id, platform_id, stockx_order_number,
            sold_at, gross_sale, net_proceeds, net_profit, roi, status
        ) VALUES (...)
    """)
)

# Inventory aktualisieren
await session.execute(
    text("""
        UPDATE products.inventory
        SET status = :status, roi_percentage = :roi
        WHERE id = :inventory_id
    """)
)
```

### 2. Verkaufs-Service vereinfachen

```python
# domains/orders/services/order_service.py

async def create_sale_from_stockx(
    inventory_id: UUID,
    stockx_order_data: dict
) -> Order:
    """Erstellt Order-Record von StockX-Daten"""

    # 1. Order-Record erstellen (nur transactions.orders!)
    order = Order(
        inventory_item_id=inventory_id,
        platform_id=get_platform_id("stockx"),
        stockx_order_number=stockx_order_data["order_number"],
        sold_at=stockx_order_data["created_at"],
        gross_sale=stockx_order_data["amount"],
        net_proceeds=calculate_net_proceeds(...),
        net_profit=calculate_net_profit(...),
        roi=calculate_roi(...),
        status="completed"
    )

    # 2. Inventory aktualisieren
    inventory = await get_inventory_item(inventory_id)
    inventory.status = "sold"
    inventory.roi_percentage = order.roi

    await session.commit()
    return order
```

## 🚫 Tabellen-Deprecation Plan

### Phase 1: Warnung hinzufügen (v2.2.6)
```python
# shared/database/models.py

class Transaction(Base, TimestampMixin):
    """
    ⚠️ DEPRECATED: Diese Tabelle wird in v2.3.0 entfernt
    Verwende stattdessen transactions.orders für alle Verkäufe
    """
    __tablename__ = "transactions"
    __table_args__ = {"schema": "transactions"} if IS_POSTGRES else None

    # ... existing fields
```

### Phase 2: Migration Script (v2.3.0)
```python
# migrations/versions/xxx_deprecate_transactions.py

def upgrade():
    # Prüfe ob Daten vorhanden
    op.execute("""
        SELECT COUNT(*) FROM transactions.transactions
    """)

    # Falls leer: Tabelle droppen
    op.drop_table('transactions', schema='transactions')
```

## 📊 Datenfluss-Diagramm

```
┌─────────────────┐
│  StockX Order   │
│   (API Call)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  transactions.orders            │
│  ─────────────────────────────  │
│  • stockx_order_number          │
│  • platform_id (StockX)         │
│  • sold_at                      │
│  • gross_sale, net_proceeds     │
│  • net_profit, roi              │
│  • shipping_label_url (StockX)  │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  products.inventory             │
│  ─────────────────────────────  │
│  • status = 'sold'              │
│  • roi_percentage               │
└─────────────────────────────────┘

[products.inventory enthält bereits:]
• purchase_price ✅
• purchase_date ✅
• supplier_id ✅
• gross_purchase_price ✅
• vat_amount ✅

[Keine transactions.transactions nötig! ❌]
```

## 🎯 Zusammenfassung

### Was haben wir gelernt?

1. **`transactions.transactions` ist redundant**
   - Einkaufsdaten sind bereits in `products.inventory`
   - Verkaufsdaten sind bereits in `transactions.orders`

2. **`transactions.orders` ist ausreichend**
   - Enthält alle Verkaufsdaten
   - `platform_id` ermöglicht Multi-Platform
   - Plattform-spezifische Felder via JSONB oder eigene Spalten

3. **Einkaufsdaten via JOIN holen**
   ```sql
   SELECT
       o.*,
       i.purchase_price,
       i.purchase_date,
       s.name as supplier_name
   FROM transactions.orders o
   JOIN products.inventory i ON o.inventory_item_id = i.id
   LEFT JOIN core.suppliers s ON i.supplier_id = s.id
   WHERE o.stockx_order_number = '04-UW2Q0ZAQT8'
   ```

### Nächste Schritte für v2.2.6

1. ✅ `transactions.transactions` Tabelle ist leer
2. ⏭️ Script `record_timex_sale.py` anpassen (nur Order-Record)
3. ⏭️ Deprecation-Warnung in models.py hinzufügen
4. ⏭️ Dokumentation für andere Entwickler aktualisieren
5. ⏭️ In v2.3.0: `transactions.transactions` komplett entfernen

### Wichtigste Regel:

**Für ALLE Verkäufe (StockX, eBay, GOAT, etc.):**
- ✅ NUR `transactions.orders` verwenden
- ✅ `platform_id` zur Unterscheidung nutzen
- ✅ Einkaufsdaten via JOIN von `products.inventory` holen
- ❌ KEINE Einträge in `transactions.transactions` erstellen
