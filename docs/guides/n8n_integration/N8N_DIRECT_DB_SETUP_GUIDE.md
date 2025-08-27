# n8n Direct Database Setup Guide

## 🔧 PostgreSQL Credentials in n8n

### 1. **Database Credentials erstellen:**
```
Name: SoleFlipper Database  
Host: 192.168.2.45
Port: 2665
Database: soleflip
User: metabaseuser
Password: metabasepass
SSL: disabled (internal network)
```

### 2. **Wichtige Schema-Namen:**
- `core.*` - Brands, Categories, Sizes, Suppliers, Platforms
- `products.*` - Products, Inventory  
- `sales.*` - Transactions
- `integration.*` - Import Batches, Records

---

## 📁 **Erstellte Workflows:**

### **1. Supplier Updates** (`n8n_direct_db_supplier_update.json`)
**Trigger:** Notion Webhook `/notion-supplier-update`
**Funktion:** 
- Aktualisiert Supplier-Info in Transactions & Inventory
- Basiert auf Order Number Matching
- Fügt Tracking-Notes hinzu

**Notion Properties erwartet:**
- `Supplier` (Select oder Text)
- `Order Number` (Text)

### **2. Inventory Status** (`n8n_direct_db_inventory_status.json`)  
**Trigger:** Notion Webhook `/notion-inventory-status`
**Funktion:**
- Ändert Inventory Status (available, sold, reserved)
- Erstellt automatisch Transaction bei "sold"
- Flexible Product/Size-Matching

**Notion Properties erwartet:**
- `Status` (Select: Available, Sold, Reserved)
- `Product` (Title)
- `SKU` (Text, optional)
- `Size` (Text, optional)

### **3. Transaction Updates** (`n8n_direct_db_transaction_updates.json`)
**Trigger:** Notion Webhook `/notion-transaction-update`  
**Funktion:**
- Aktualisiert Sale Price, Platform Fee, Shipping Cost
- Berechnet automatisch Net Profit
- Multiple Matching-Strategien

**Notion Properties erwartet:**
- `Sale Price` (Number)
- `Platform Fee` (Number, optional)
- `Shipping Cost` (Number, optional)
- `Order Number` (Text) ODER `External ID` (Text)

---

## 🚀 **Setup-Schritte:**

### **1. n8n Credentials:**
1. Settings → Credentials → Add Credential
2. PostgreSQL auswählen
3. Obige Daten eingeben
4. Test Connection ✅

### **2. Workflows importieren:**
1. n8n → Workflows → Import from file
2. Jeweils eine der JSON-Dateien auswählen
3. Credentials "SoleFlipper Database" zuweisen

### **3. Notion Webhooks einrichten:**
1. Notion Database → Add Integration → Webhook
2. URL: `http://your-n8n-url/webhook/notion-supplier-update`
3. Events: Database Item Updated
4. Test mit Dummy-Eintrag

### **4. Webhook URLs:**
- Supplier: `http://n8n-url/webhook/notion-supplier-update`
- Inventory: `http://n8n-url/webhook/notion-inventory-status`  
- Transactions: `http://n8n-url/webhook/notion-transaction-update`

---

## ⚠️ **Sicherheitshinweise:**

1. **Backup vor Tests** - Direkte DB-Änderungen sind irreversibel
2. **Test Environment** - Erst an Test-DB testen
3. **Limited User** - DB-User nur mit nötigen Permissions
4. **Error Handling** - Webhooks können fehlschlagen
5. **Logging** - n8n Execution Logs überwachen

---

## 🔍 **Debugging:**

### **SQL Queries testen:**
```sql
-- Test Transaction Matching
SELECT t.id, t.external_id, p.name 
FROM sales.transactions t
JOIN products.inventory i ON t.inventory_id = i.id
JOIN products.products p ON i.product_id = p.id  
WHERE t.external_id ILIKE '%ORDER123%'
LIMIT 5;

-- Test Inventory Updates
SELECT i.id, p.name, s.value, i.status
FROM products.inventory i
JOIN products.products p ON i.product_id = p.id
JOIN core.sizes s ON i.size_id = s.id
WHERE p.name ILIKE '%Jordan%';
```

### **Notion Webhook Payload debuggen:**
1. n8n Execution → View Details
2. Webhook Node → Output Data
3. Properties-Struktur prüfen

---

## 📊 **Monitoring Queries:**

```sql  
-- Recent Updates (last 24h)
SELECT 
    'transactions' as table_name,
    COUNT(*) as updated_count
FROM sales.transactions 
WHERE updated_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
UNION ALL
SELECT 
    'inventory' as table_name,
    COUNT(*) as updated_count  
FROM products.inventory
WHERE updated_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours';

-- Failed Executions Log
SELECT execution_id, created_at, finished_at, data
FROM n8n.execution_entity
WHERE finished_at IS NULL 
   OR (finished_at - created_at) > INTERVAL '5 minutes'
ORDER BY created_at DESC;
```

Diese Workflows ermöglichen vollständige Datenbankoperationen direkt aus Notion heraus ohne API-Umwege! 🎯