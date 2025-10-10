# Transaction Architecture Analysis
**Datum:** 2025-10-09
**Version:** v2.2.5
**Autor:** Claude Code Analysis

## Problem: Datenredundanz zwischen `transactions.transactions` und `products.inventory`

### Hintergrund
Bei der Implementierung eines StockX-Verkaufs wurde festgestellt, dass Daten sowohl in `transactions.transactions` als auch in `products.inventory` gespeichert werden, obwohl viele dieser Daten bereits in `products.inventory` vorhanden sind.

## Tabellenstruktur Vergleich

### `products.inventory` (Zeilen 315-380 in models.py)
**Zweck:** Bestandsverwaltung mit Einkaufsdaten

```python
class InventoryItem(Base, TimestampMixin):
    # Einkaufsdaten (bereits vorhanden)
    purchase_price = Column(Numeric(10, 2))          # ✅ Einkaufspreis netto
    purchase_date = Column(DateTime(timezone=True))  # ✅ Einkaufsdatum
    supplier_id = Column(UUID, ForeignKey)           # ✅ Lieferant (Beziehung)
    supplier = Column(String(100))                   # ✅ Lieferant (String)

    # Verkaufsdaten
    status = Column(String(50))                      # Status: in_stock, sold, etc.
    roi_percentage = Column(Numeric(5, 2))           # ROI in Prozent

    # Notion Sync Fields
    gross_purchase_price = Column(Numeric(10, 2))   # ✅ Brutto-Einkaufspreis
    vat_amount = Column(Numeric(10, 2))             # ✅ MwSt-Betrag
    vat_rate = Column(Numeric(5, 2))                # ✅ MwSt-Satz
    delivery_date = Column(DateTime(timezone=True))  # ✅ Lieferdatum

    # Business Intelligence
    shelf_life_days = Column(Integer)                # Lagerdauer
    profit_per_shelf_day = Column(Numeric(10, 2))   # Gewinn pro Tag
```

### `transactions.transactions` (Zeilen 388-410 in models.py)
**Zweck:** Verkaufstransaktionen (für zukünftige Multi-Platform Unterstützung)

```python
class Transaction(Base, TimestampMixin):
    inventory_id = Column(UUID, ForeignKey)          # ✅ Verknüpfung zu Inventory
    platform_id = Column(UUID, ForeignKey)           # ✅ Verkaufsplattform

    # Verkaufsdaten
    transaction_date = Column(DateTime(timezone=True)) # Verkaufsdatum
    sale_price = Column(Numeric(10, 2))               # Verkaufspreis
    platform_fee = Column(Numeric(10, 2))             # Plattform-Gebühr
    shipping_cost = Column(Numeric(10, 2))            # Versandkosten
    net_profit = Column(Numeric(10, 2))               # Nettogewinn
    status = Column(String(50))                       # Status
    external_id = Column(String(100))                 # Externe ID (z.B. StockX Order Nr.)

    # Käuferdaten
    buyer_destination_country = Column(String(100))
    buyer_destination_city = Column(String(100))
    notes = Column(Text)
```

### `transactions.orders` (Zeilen 436-475 in models.py)
**Zweck:** StockX-spezifische Orders mit erweiterten Metriken

```python
class Order(Base, TimestampMixin):
    inventory_item_id = Column(UUID, ForeignKey)
    platform_id = Column(UUID, ForeignKey)           # ✅ REQUIRED

    stockx_order_number = Column(String(100))        # StockX Order ID
    status = Column(String(50))
    amount = Column(Numeric(10, 2))

    # StockX-spezifische Felder
    shipping_label_url = Column(String(512))
    shipping_document_path = Column(String(512))
    stockx_created_at = Column(DateTime(timezone=True))
    last_stockx_updated_at = Column(DateTime(timezone=True))

    # Notion Sync Fields (Profit-Metriken)
    sold_at = Column(DateTime(timezone=True))
    gross_sale = Column(Numeric(10, 2))
    net_proceeds = Column(Numeric(10, 2))
    gross_profit = Column(Numeric(10, 2))
    net_profit = Column(Numeric(10, 2))
    roi = Column(Numeric(5, 2))
    payout_received = Column(Boolean)
    payout_date = Column(DateTime(timezone=True))
    shelf_life_days = Column(Integer)
```

## Datenredundanz Analyse

### ❌ REDUNDANTE Daten zwischen `inventory` und `transactions`

| Daten | products.inventory | transactions.transactions | Notwendig? |
|-------|-------------------|---------------------------|------------|
| Einkaufspreis | ✅ purchase_price | ⚠️ (über JOIN) | ❌ Nein |
| Einkaufsdatum | ✅ purchase_date | ⚠️ (über JOIN) | ❌ Nein |
| Lieferant | ✅ supplier_id | ⚠️ (über JOIN) | ❌ Nein |

### ❌ REDUNDANTE Daten zwischen `orders` und `transactions`

| Daten | transactions.orders | transactions.transactions | Notwendig? |
|-------|---------------------|---------------------------|------------|
| Verkaufspreis | ✅ gross_sale | ✅ sale_price | ❌ Duplikat |
| Nettogewinn | ✅ net_profit | ✅ net_profit | ❌ Duplikat |
| Datum | ✅ sold_at | ✅ transaction_date | ❌ Duplikat |
| Status | ✅ status | ✅ status | ❌ Duplikat |
| Platform | ✅ platform_id | ✅ platform_id | ❌ Duplikat |

## ✅ Architektur-Empfehlung

### Option 1: **NUR `transactions.orders` verwenden (EMPFOHLEN)**

**Begründung:**
- `transactions.orders` ist StockX-spezifisch und enthält ALLE notwendigen Daten
- `platform_id` ermöglicht zukünftige Multi-Platform-Unterstützung
- Vermeidet Datenredundanz zwischen `orders` und `transactions`
- Einkaufsdaten kommen via JOIN von `products.inventory`

**Implementierung:**
```python
# Verkauf erfassen - NUR in transactions.orders
INSERT INTO transactions.orders (
    inventory_item_id,      # Verknüpfung zu Inventory (enthält purchase data)
    platform_id,            # StockX, eBay, GOAT, etc.
    stockx_order_number,    # Plattform-spezifische Order-Nr.
    sold_at,                # Verkaufsdatum
    gross_sale,             # Verkaufspreis
    net_proceeds,           # Nach Gebühren
    net_profit,             # Endgewinn
    roi,                    # ROI
    status                  # completed, pending, etc.
)

# Inventory aktualisieren
UPDATE products.inventory
SET status = 'sold',
    roi_percentage = :roi
WHERE id = :inventory_id
```

### Option 2: `transactions.transactions` für Multi-Platform erweitern

**NUR sinnvoll wenn:**
- Andere Plattformen (eBay, GOAT) KEINE eigenen Order-Tabellen bekommen
- Aber: StockX hat bereits `transactions.orders` - inkonsistent!

### Option 3: **Hybrid-Ansatz (NICHT EMPFOHLEN)**
- StockX → `transactions.orders`
- Andere Platforms → `transactions.transactions`
- **Problem:** Inkonsistente Datenarchitektur, schwer zu warten

## 🎯 Konkrete Handlungsempfehlung

### Sofortmaßnahme für v2.2.6:

1. **Transaction-Record LÖSCHEN:**
   ```sql
   DELETE FROM transactions.transactions
   WHERE external_id = '04-UW2Q0ZAQT8';
   ```

2. **Verkäufe NUR in `transactions.orders` speichern**
   - Order-Record ist bereits vollständig ✅
   - Inventory-Status ist aktualisiert ✅
   - Kein Transaction-Record notwendig ❌

3. **Zukünftige Entwicklung:**
   - Für **eBay, GOAT, etc.**: Eigene Order-Tabellen erstellen analog zu `stockx_orders`
   - ODER: `transactions.orders` umbenennen zu `multi_platform_orders` und `stockx_*` Felder optional machen
   - `transactions.transactions` sollte DEPRECATED werden

### Langfristige Strategie:

**Vorschlag: Multi-Platform Orders in EINER Tabelle**

```python
class Order(Base, TimestampMixin):
    """Multi-Platform Order Management"""
    inventory_item_id = Column(UUID, ForeignKey)
    platform_id = Column(UUID, ForeignKey)           # StockX, eBay, GOAT, etc.

    # Universelle Felder (alle Plattformen)
    external_order_id = Column(String(100))          # Plattform-spezifische ID
    sold_at = Column(DateTime(timezone=True))
    gross_sale = Column(Numeric(10, 2))
    net_proceeds = Column(Numeric(10, 2))
    platform_fee = Column(Numeric(10, 2))
    shipping_cost = Column(Numeric(10, 2))
    net_profit = Column(Numeric(10, 2))
    roi = Column(Numeric(5, 2))
    status = Column(String(50))

    # Plattform-spezifische Daten als JSON
    platform_metadata = Column(JSONB)                # StockX: {shipping_label_url, ...}
                                                     # eBay: {listing_id, ...}
                                                     # GOAT: {...}
```

## 📊 Aktueller Zustand (v2.2.5)

**Timex Verkauf - Datenverteilung:**

| Tabelle | Datensatz | Status |
|---------|-----------|--------|
| `products.inventory` | ✅ id: c7e227a4-... | Status: sold, ROI: 26.90% |
| `transactions.orders` | ✅ Order: 04-UW2Q0ZAQT8 | Vollständige Verkaufsdaten |
| `transactions.transactions` | ⚠️ id: ... | **REDUNDANT - sollte gelöscht werden** |

## 🔍 Migration Plan für v2.2.6

```sql
-- 1. Prüfen ob transactions.transactions verwendet wird
SELECT COUNT(*) FROM transactions.transactions;

-- 2. Falls nur Test-Daten: Tabelle leeren
TRUNCATE transactions.transactions;

-- 3. Zukünftig: Nur transactions.orders verwenden
-- Alle Verkäufe (StockX, eBay, etc.) in dieser Tabelle

-- 4. Optional: transactions.transactions deprecaten
ALTER TABLE transactions.transactions
ADD COLUMN deprecated BOOLEAN DEFAULT TRUE;

-- 5. Code-Änderung: record_timex_sale.py sollte
-- NUR Order-Record erstellen, KEIN Transaction-Record
```

## Zusammenfassung

**Problem:**
- `transactions.transactions` speichert redundante Daten
- Einkaufsdaten sind bereits in `products.inventory`
- Verkaufsdaten sind bereits in `transactions.orders`

**Lösung:**
- ✅ Verkäufe NUR in `transactions.orders` speichern
- ✅ `platform_id` ermöglicht Multi-Platform-Support
- ✅ Einkaufsdaten via JOIN von `products.inventory` holen
- ❌ `transactions.transactions` sollte deprecatet werden

**Vorteil:**
- Keine Datenredundanz
- Konsistente Architektur
- Einfachere Wartung
- Skalierbar für alle Plattformen
