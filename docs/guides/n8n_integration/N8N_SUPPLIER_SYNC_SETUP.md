# n8n Notion Supplier Sync - Setup Guide

## 📋 Übersicht
Dieser Workflow synchronisiert Supplier-Änderungen von Notion zurück zur SoleFlipper-Datenbank.

## 🔧 Setup-Schritte

### 1. **n8n Workflow importieren**
```bash
# Workflow-Datei: n8n_notion_supplier_sync_workflow.json
# In n8n: Settings → Import → Workflow auswählen
```

### 2. **Credentials konfigurieren**

#### **Notion API**
- **Credential Name:** `Notion API`
- **Integration Token:** [Dein Notion Integration Token]
- **Database ID:** [Deine Transaction Database ID]

#### **SoleFlipper API Auth**
- **Credential Name:** `SoleFlipper API Auth`
- **Header Name:** `Authorization`
- **Header Value:** `Bearer [dein-api-key]` (falls auth benötigt)

#### **Slack Notifications** (optional)
- **Credential Name:** `Slack Notifications`
- **Bot Token:** [Dein Slack Bot Token]

### 3. **Workflow-Konfiguration anpassen**

#### **Notion Trigger Node**
```json
{
  "databaseId": "DEINE-NOTION-DATABASE-ID",
  "properties": ["property_supplier"]
}
```

#### **SoleFlipper API URL**
```javascript
// In "SoleFlipper API Call" Node
"url": "http://localhost:8000/api/v1/integration/n8n/notion/sync"
// Oder deine Production URL
```

### 4. **Notion Database Properties**
Stelle sicher, dass deine Notion Transaction Database diese Properties hat:
- `property_supplier` (Select oder Text)
- `property_sale_id` (Text) - zur Identifikation
- `property_order_no` (Text) - alternative ID

## 🔄 Workflow-Ablauf

### **Trigger**
- **Typ:** Notion Database Webhook
- **Event:** Property Change (property_supplier)
- **Filter:** Nur bei Supplier-Änderungen

### **Datenverarbeitung**
1. **Filter:** Prüft ob `property_supplier` geändert wurde
2. **Transform:** Erstellt API-Payload mit sale_id und supplier_name
3. **API Call:** Sendet Update an SoleFlipper
4. **Response Check:** Prüft ob Update erfolgreich war
5. **Notifications:** Slack-Benachrichtigung (Erfolg/Fehler)

### **API Payload Format**
```json
{
  "action": "update_supplier",
  "transaction_data": {
    "sale_id": "72160496-72060255",
    "supplier_name": "Solebox",
    "notion_page_id": "abc123...",
    "updated_at": "2025-08-05T10:00:00.000Z"
  }
}
```

## 🛠️ SoleFlipper API Endpoint

Der Workflow erwartet einen API-Endpoint: `/api/v1/integration/n8n/notion/sync`

### **Expected Handler Logic:**
```python
@webhook_router.post("/notion/sync")
async def notion_sync_webhook(payload: dict):
    if payload["action"] == "update_supplier":
        # 1. Transaction finden via sale_id
        transaction = db.query(Transaction).filter(
            Transaction.external_id == payload["transaction_data"]["sale_id"]
        ).first()
        
        if not transaction:
            raise HTTPException(404, "Transaction not found")
        
        # 2. Supplier finden/erstellen
        supplier_name = payload["transaction_data"]["supplier_name"]
        supplier = db.query(Supplier).filter(
            Supplier.name == supplier_name
        ).first()
        
        if not supplier:
            # Neuen Supplier erstellen
            supplier = Supplier(
                name=supplier_name,
                slug=supplier_name.lower().replace(" ", "-"),
                supplier_type="reseller"
            )
            db.add(supplier)
            db.flush()
        
        # 3. InventoryItem.supplier_id updaten
        inventory_item = transaction.inventory_item
        inventory_item.supplier_id = supplier.id
        
        db.commit()
        
        return {"success": True, "message": f"Supplier updated to {supplier_name}"}
```

## 🧪 Testing

### **Test-Schritte:**
1. Notion öffnen → Transaction Database
2. Bei einer Transaction das `property_supplier` Feld ändern
3. n8n Workflow sollte triggern
4. SoleFlipper API sollte InventoryItem.supplier_id updaten
5. Slack-Notification sollte Success melden

### **Debug:**
- n8n Execution Log checken
- SoleFlipper API Logs prüfen
- Database: `SELECT * FROM products.inventory WHERE supplier_id IS NOT NULL`

## 📊 Monitoring

- **n8n:** Execution History für Success/Failure Rate
- **Slack:** Automatische Notifications bei Erfolg/Fehler
- **SoleFlipper:** API Logs für Debugging

## ⚡ Performance

- **Trigger:** Nur bei property_supplier Änderungen
- **Batch Processing:** Einzelne Updates (real-time)
- **Error Handling:** Retry bei API-Fehlern
- **Rate Limiting:** Notion API Limits beachten

---

**🎯 Ergebnis:** Notion wird zur zentralen Eingabemaske für Supplier-Informationen, die automatisch in der SoleFlipper-Datenbank persistiert werden.