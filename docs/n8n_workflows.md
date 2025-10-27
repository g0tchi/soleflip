# SoleFlipper n8n Workflows

Sinnvolle Automatisierungs-Workflows für das SoleFlipper-System.

## 📋 Übersicht

Diese Workflows automatisieren kritische Geschäftsprozesse:
1. **Multi-Platform Order Sync** - Synchronisiert Orders alle 15 Minuten
2. **Daily Dead Stock Alert** - Warnt täglich vor toter Ware
3. **Low Stock Notifications** - Benachrichtigt bei niedrigen Beständen
4. **Daily Analytics Report** - Täglicher KPI-Report um 8 Uhr
5. **Price Alert System** - Überwacht Preisänderungen in Echtzeit
6. **StockX Webhook Handler** - Verarbeitet StockX Events sofort

---

## 🔄 Workflow 1: Multi-Platform Order Synchronization

**Zweck:** Synchronisiert automatisch Orders von StockX, eBay und GOAT alle 15 Minuten.

**Trigger:** Schedule (alle 15 Minuten)

**Ablauf:**
1. Schedule Trigger startet alle 15 Minuten
2. Parallele API-Calls zu StockX und eBay Sync-Endpoints
3. Check auf neue Orders in der Datenbank
4. Slack-Benachrichtigung bei neuen Orders

### Workflow JSON

```json
{
  "name": "Multi-Platform Order Sync",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "minutes",
              "minutesInterval": 15
            }
          ]
        }
      },
      "id": "schedule-1",
      "name": "Every 15 Minutes",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [250, 300]
    },
    {
      "parameters": {
        "url": "http://localhost:8000/api/integration/stockx/orders/sync",
        "method": "POST",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Content-Type",
              "value": "application/json"
            }
          ]
        },
        "options": {
          "timeout": 30000,
          "retry": {
            "retry": {
              "maxRetries": 3,
              "retryInterval": 5000
            }
          }
        }
      },
      "id": "stockx-sync",
      "name": "Sync StockX Orders",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.3,
      "position": [450, 200],
      "onError": "continueRegularOutput"
    },
    {
      "parameters": {
        "url": "http://localhost:8000/api/integration/ebay/orders/sync",
        "method": "POST",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Content-Type",
              "value": "application/json"
            }
          ]
        },
        "options": {
          "timeout": 30000,
          "retry": {
            "retry": {
              "maxRetries": 3,
              "retryInterval": 5000
            }
          }
        }
      },
      "id": "ebay-sync",
      "name": "Sync eBay Orders",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.3,
      "position": [450, 400],
      "onError": "continueRegularOutput"
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT \n  COUNT(*) as new_orders,\n  SUM(CASE WHEN source = 'stockx' THEN 1 ELSE 0 END) as stockx_orders,\n  SUM(CASE WHEN source = 'ebay' THEN 1 ELSE 0 END) as ebay_orders\nFROM transactions.orders \nWHERE created_at > NOW() - INTERVAL '15 minutes'",
        "options": {}
      },
      "id": "check-orders",
      "name": "Check New Orders",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.6,
      "position": [650, 300],
      "retryOnFail": true,
      "maxTries": 2
    },
    {
      "parameters": {
        "conditions": {
          "number": [
            {
              "value1": "={{ $json.new_orders }}",
              "operation": "larger",
              "value2": 0
            }
          ]
        }
      },
      "id": "if-orders",
      "name": "Has New Orders?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2.2,
      "position": [850, 300]
    },
    {
      "parameters": {
        "resource": "message",
        "operation": "post",
        "select": "channel",
        "channelId": {
          "__rl": true,
          "value": "#orders",
          "mode": "name"
        },
        "text": "=✅ **Order Sync Complete!**\n\n📦 *New Orders:* {{ $json.new_orders }}\n🛍️ *StockX:* {{ $json.stockx_orders }}\n🛒 *eBay:* {{ $json.ebay_orders }}\n⏰ *Synced:* {{ $now.format('DD.MM.YYYY HH:mm:ss') }}"
      },
      "id": "slack-notify",
      "name": "Notify Slack",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2.3,
      "position": [1050, 200],
      "onError": "continueRegularOutput"
    }
  ],
  "connections": {
    "Every 15 Minutes": {
      "main": [
        [
          {
            "node": "Sync StockX Orders",
            "type": "main",
            "index": 0
          },
          {
            "node": "Sync eBay Orders",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Sync StockX Orders": {
      "main": [
        [
          {
            "node": "Check New Orders",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Sync eBay Orders": {
      "main": [
        [
          {
            "node": "Check New Orders",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Check New Orders": {
      "main": [
        [
          {
            "node": "Has New Orders?",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Has New Orders?": {
      "main": [
        [
          {
            "node": "Notify Slack",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1",
    "saveDataErrorExecution": "all",
    "saveDataSuccessExecution": "all",
    "saveExecutionProgress": true,
    "saveManualExecutions": true
  }
}
```

---

## 📊 Workflow 2: Daily Dead Stock Alert

**Zweck:** Identifiziert täglich Dead Stock (Produkte älter als 90 Tage) und sendet Benachrichtigungen.

**Trigger:** Schedule (täglich um 8:00 Uhr)

**Ablauf:**
1. Trigger um 8:00 Uhr morgens
2. Query findet alle Dead Stock Items (>90 Tage im Lager)
3. Berechnet Gesamtwert des Dead Stocks
4. Sendet detaillierten Slack-Report

### Workflow JSON

```json
{
  "name": "Daily Dead Stock Alert",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "hours",
              "hoursInterval": 24,
              "triggerAtHour": 8
            }
          ]
        }
      },
      "id": "schedule-daily",
      "name": "Daily at 8 AM",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [250, 300]
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT \n  p.name as product_name,\n  p.brand,\n  i.size,\n  i.condition,\n  i.purchase_cost,\n  i.created_at,\n  EXTRACT(DAY FROM NOW() - i.created_at) as days_in_stock,\n  i.location\nFROM inventory.inventory_items i\nJOIN products.products p ON i.product_id = p.id\nWHERE i.status = 'available'\n  AND i.created_at < NOW() - INTERVAL '90 days'\nORDER BY i.created_at ASC\nLIMIT 50",
        "options": {}
      },
      "id": "find-dead-stock",
      "name": "Find Dead Stock",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.6,
      "position": [450, 300],
      "retryOnFail": true
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT \n  COUNT(*) as total_items,\n  SUM(purchase_cost) as total_value,\n  AVG(EXTRACT(DAY FROM NOW() - created_at)) as avg_days\nFROM inventory.inventory_items\nWHERE status = 'available'\n  AND created_at < NOW() - INTERVAL '90 days'",
        "options": {}
      },
      "id": "dead-stock-stats",
      "name": "Calculate Stats",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.6,
      "position": [450, 450],
      "retryOnFail": true
    },
    {
      "parameters": {
        "jsCode": "// Verarbeite Dead Stock Daten\nconst items = $input.first().json;\nconst stats = $input.last().json;\n\n// Formatiere Items für Slack\nconst topItems = items.slice(0, 10).map(item => {\n  return `• *${item.product_name}* (${item.brand}) - Size ${item.size}\\n  💰 €${item.purchase_cost} | 📅 ${item.days_in_stock} days | 📍 ${item.location}`;\n}).join('\\n\\n');\n\nreturn {\n  json: {\n    total_items: stats.total_items,\n    total_value: parseFloat(stats.total_value).toFixed(2),\n    avg_days: parseInt(stats.avg_days),\n    top_items: topItems,\n    has_dead_stock: stats.total_items > 0\n  }\n};"
      },
      "id": "format-report",
      "name": "Format Report",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [650, 375]
    },
    {
      "parameters": {
        "conditions": {
          "boolean": [
            {
              "value1": "={{ $json.has_dead_stock }}",
              "value2": true
            }
          ]
        }
      },
      "id": "check-stock",
      "name": "Has Dead Stock?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2.2,
      "position": [850, 375]
    },
    {
      "parameters": {
        "resource": "message",
        "operation": "post",
        "select": "channel",
        "channelId": {
          "__rl": true,
          "value": "#inventory-alerts",
          "mode": "name"
        },
        "text": "=🚨 **Dead Stock Alert!**\n\n📊 *Summary:*\n• Total Items: {{ $json.total_items }}\n• Total Value: €{{ $json.total_value }}\n• Average Age: {{ $json.avg_days }} days\n\n🔝 *Top 10 Items:*\n{{ $json.top_items }}\n\n💡 _Consider price reductions or promotions for these items_"
      },
      "id": "slack-alert",
      "name": "Send Slack Alert",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2.3,
      "position": [1050, 300],
      "onError": "continueRegularOutput"
    }
  ],
  "connections": {
    "Daily at 8 AM": {
      "main": [
        [
          {
            "node": "Find Dead Stock",
            "type": "main",
            "index": 0
          },
          {
            "node": "Calculate Stats",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Find Dead Stock": {
      "main": [
        [
          {
            "node": "Format Report",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Calculate Stats": {
      "main": [
        [
          {
            "node": "Format Report",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Format Report": {
      "main": [
        [
          {
            "node": "Has Dead Stock?",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Has Dead Stock?": {
      "main": [
        [
          {
            "node": "Send Slack Alert",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1",
    "saveDataErrorExecution": "all",
    "saveDataSuccessExecution": "all"
  }
}
```

---

## 📉 Workflow 3: Low Stock Notifications

**Zweck:** Überwacht Lagerbestände und warnt bei niedrigem Bestand beliebter Produkte.

**Trigger:** Schedule (alle 6 Stunden)

**Ablauf:**
1. Trigger alle 6 Stunden
2. Findet Produkte mit weniger als 3 Einheiten auf Lager
3. Prüft historische Verkaufsgeschwindigkeit
4. Benachrichtigt bei kritischen Beständen

### Workflow JSON

```json
{
  "name": "Low Stock Notifications",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "hours",
              "hoursInterval": 6
            }
          ]
        }
      },
      "id": "schedule-6h",
      "name": "Every 6 Hours",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [250, 300]
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "WITH product_stock AS (\n  SELECT \n    p.id,\n    p.name,\n    p.brand,\n    COUNT(i.id) as stock_count,\n    AVG(i.purchase_cost) as avg_cost\n  FROM products.products p\n  LEFT JOIN inventory.inventory_items i ON p.id = i.product_id AND i.status = 'available'\n  GROUP BY p.id, p.name, p.brand\n  HAVING COUNT(i.id) > 0 AND COUNT(i.id) < 3\n),\nrecent_sales AS (\n  SELECT \n    product_id,\n    COUNT(*) as sales_last_30_days\n  FROM transactions.orders\n  WHERE created_at > NOW() - INTERVAL '30 days'\n    AND status IN ('completed', 'shipped')\n  GROUP BY product_id\n)\nSELECT \n  ps.*,\n  COALESCE(rs.sales_last_30_days, 0) as recent_sales\nFROM product_stock ps\nLEFT JOIN recent_sales rs ON ps.id = rs.product_id\nWHERE COALESCE(rs.sales_last_30_days, 0) > 2\nORDER BY recent_sales DESC, stock_count ASC\nLIMIT 20",
        "options": {}
      },
      "id": "find-low-stock",
      "name": "Find Low Stock Items",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.6,
      "position": [450, 300],
      "retryOnFail": true
    },
    {
      "parameters": {
        "conditions": {
          "number": [
            {
              "value1": "={{ $json.length }}",
              "operation": "larger",
              "value2": 0
            }
          ]
        }
      },
      "id": "has-items",
      "name": "Has Low Stock?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2.2,
      "position": [650, 300]
    },
    {
      "parameters": {
        "jsCode": "// Format low stock items\nconst items = $input.all().map(item => item.json);\n\nconst formattedItems = items.slice(0, 10).map(item => {\n  const urgency = item.stock_count === 1 ? '🔴 CRITICAL' : '🟡 LOW';\n  return `${urgency} *${item.name}* (${item.brand})\\n  📦 Stock: ${item.stock_count} | 📈 Sales (30d): ${item.recent_sales} | 💰 Avg Cost: €${parseFloat(item.avg_cost).toFixed(2)}`;\n}).join('\\n\\n');\n\nreturn {\n  json: {\n    total_products: items.length,\n    critical_items: items.filter(i => i.stock_count === 1).length,\n    items_list: formattedItems\n  }\n};"
      },
      "id": "format-alert",
      "name": "Format Alert",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [850, 200]
    },
    {
      "parameters": {
        "resource": "message",
        "operation": "post",
        "select": "channel",
        "channelId": {
          "__rl": true,
          "value": "#inventory-alerts",
          "mode": "name"
        },
        "text": "=⚠️ **Low Stock Alert!**\n\n📊 *Summary:*\n• Total Products: {{ $json.total_products }}\n• Critical (1 item): {{ $json.critical_items }}\n\n📦 *Top Items:*\n{{ $json.items_list }}\n\n💡 _Consider restocking these popular items_"
      },
      "id": "slack-low-stock",
      "name": "Send Alert",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2.3,
      "position": [1050, 200],
      "onError": "continueRegularOutput"
    }
  ],
  "connections": {
    "Every 6 Hours": {
      "main": [
        [
          {
            "node": "Find Low Stock Items",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Find Low Stock Items": {
      "main": [
        [
          {
            "node": "Has Low Stock?",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Has Low Stock?": {
      "main": [
        [
          {
            "node": "Format Alert",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Format Alert": {
      "main": [
        [
          {
            "node": "Send Alert",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1",
    "saveDataErrorExecution": "all"
  }
}
```

---

## 📈 Workflow 4: Daily Analytics Report

**Zweck:** Generiert täglich einen umfassenden KPI-Report mit Verkaufszahlen, Umsatz und Top-Produkten.

**Trigger:** Schedule (täglich um 8:30 Uhr)

**Ablauf:**
1. Trigger um 8:30 Uhr
2. Sammelt KPIs der letzten 24 Stunden
3. Vergleicht mit Vorwoche
4. Sendet formatierten Report

### Workflow JSON

```json
{
  "name": "Daily Analytics Report",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "hours",
              "hoursInterval": 24,
              "triggerAtHour": 8,
              "triggerAtMinute": 30
            }
          ]
        }
      },
      "id": "schedule-morning",
      "name": "Daily at 8:30 AM",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [250, 400]
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "-- Daily Sales KPIs\nSELECT \n  COUNT(*) as orders_today,\n  SUM(final_price) as revenue_today,\n  AVG(final_price) as avg_order_value,\n  COUNT(DISTINCT customer_id) as unique_customers\nFROM transactions.orders\nWHERE created_at >= CURRENT_DATE\n  AND created_at < CURRENT_DATE + INTERVAL '1 day'\n  AND status IN ('completed', 'shipped')",
        "options": {}
      },
      "id": "today-kpis",
      "name": "Today KPIs",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.6,
      "position": [450, 300],
      "retryOnFail": true
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "-- Yesterday KPIs for comparison\nSELECT \n  COUNT(*) as orders_yesterday,\n  SUM(final_price) as revenue_yesterday\nFROM transactions.orders\nWHERE created_at >= CURRENT_DATE - INTERVAL '1 day'\n  AND created_at < CURRENT_DATE\n  AND status IN ('completed', 'shipped')",
        "options": {}
      },
      "id": "yesterday-kpis",
      "name": "Yesterday KPIs",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.6,
      "position": [450, 500],
      "retryOnFail": true
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "-- Top Products Today\nSELECT \n  p.name,\n  p.brand,\n  COUNT(*) as units_sold,\n  SUM(o.final_price) as total_revenue\nFROM transactions.orders o\nJOIN products.products p ON o.product_id = p.id\nWHERE o.created_at >= CURRENT_DATE\n  AND o.created_at < CURRENT_DATE + INTERVAL '1 day'\n  AND o.status IN ('completed', 'shipped')\nGROUP BY p.id, p.name, p.brand\nORDER BY units_sold DESC\nLIMIT 5",
        "options": {}
      },
      "id": "top-products",
      "name": "Top Products",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.6,
      "position": [450, 700],
      "retryOnFail": true
    },
    {
      "parameters": {
        "jsCode": "// Combine all analytics data\nconst today = $('Today KPIs').first().json;\nconst yesterday = $('Yesterday KPIs').first().json;\nconst topProducts = $('Top Products').all().map(p => p.json);\n\n// Calculate changes\nconst orderChange = ((today.orders_today - yesterday.orders_yesterday) / yesterday.orders_yesterday * 100).toFixed(1);\nconst revenueChange = ((today.revenue_today - yesterday.revenue_yesterday) / yesterday.revenue_yesterday * 100).toFixed(1);\n\n// Format top products\nconst topProductsList = topProducts.map((p, i) => \n  `${i+1}. *${p.name}* (${p.brand}) - ${p.units_sold} units | €${parseFloat(p.total_revenue).toFixed(2)}`\n).join('\\n');\n\nconst orderEmoji = orderChange >= 0 ? '📈' : '📉';\nconst revenueEmoji = revenueChange >= 0 ? '💰' : '💸';\n\nreturn {\n  json: {\n    orders_today: today.orders_today || 0,\n    revenue_today: parseFloat(today.revenue_today || 0).toFixed(2),\n    avg_order: parseFloat(today.avg_order_value || 0).toFixed(2),\n    unique_customers: today.unique_customers || 0,\n    order_change: orderChange,\n    revenue_change: revenueChange,\n    order_emoji: orderEmoji,\n    revenue_emoji: revenueEmoji,\n    top_products: topProductsList\n  }\n};"
      },
      "id": "combine-data",
      "name": "Combine Analytics",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [650, 500]
    },
    {
      "parameters": {
        "resource": "message",
        "operation": "post",
        "select": "channel",
        "channelId": {
          "__rl": true,
          "value": "#daily-reports",
          "mode": "name"
        },
        "text": "=📊 **Daily Analytics Report**\n_{{ $now.format('dddd, DD MMMM YYYY') }}_\n\n*Yesterday's Performance:*\n{{ $json.order_emoji }} Orders: {{ $json.orders_today }} ({{ $json.order_change }}% vs day before)\n{{ $json.revenue_emoji }} Revenue: €{{ $json.revenue_today }} ({{ $json.revenue_change }}% vs day before)\n👥 Unique Customers: {{ $json.unique_customers }}\n💳 Avg Order Value: €{{ $json.avg_order }}\n\n*🏆 Top 5 Products:*\n{{ $json.top_products }}\n\n_Have a great day!_ ☕"
      },
      "id": "slack-report",
      "name": "Send Daily Report",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2.3,
      "position": [850, 500],
      "onError": "continueRegularOutput"
    }
  ],
  "connections": {
    "Daily at 8:30 AM": {
      "main": [
        [
          {
            "node": "Today KPIs",
            "type": "main",
            "index": 0
          },
          {
            "node": "Yesterday KPIs",
            "type": "main",
            "index": 0
          },
          {
            "node": "Top Products",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Today KPIs": {
      "main": [
        [
          {
            "node": "Combine Analytics",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Yesterday KPIs": {
      "main": [
        [
          {
            "node": "Combine Analytics",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Top Products": {
      "main": [
        [
          {
            "node": "Combine Analytics",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Combine Analytics": {
      "main": [
        [
          {
            "node": "Send Daily Report",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1",
    "saveDataErrorExecution": "all",
    "saveDataSuccessExecution": "all",
    "timezone": "Europe/Berlin"
  }
}
```

---

## 💰 Workflow 6: Smart Price Monitoring & Alerts

**Zweck:** Überwacht Preisänderungen bei Produkten und sendet Alerts bei signifikanten Änderungen.

**Trigger:** Schedule (alle 2 Stunden)

**Ablauf:**
1. Trigger alle 2 Stunden
2. Ruft aktuelle Marktpreise ab (via API)
3. Vergleicht mit aktuellen Listenpreisen
4. Benachrichtigt bei Abweichungen >10%

### Workflow JSON

```json
{
  "name": "Smart Price Monitoring",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "hours",
              "hoursInterval": 2
            }
          ]
        }
      },
      "id": "schedule-2h",
      "name": "Every 2 Hours",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [250, 400]
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "-- Get products with active listings\nSELECT \n  p.id,\n  p.name,\n  p.brand,\n  p.style_code,\n  i.size,\n  i.condition,\n  i.purchase_cost,\n  COALESCE(i.listed_price, 0) as current_price,\n  i.id as inventory_id\nFROM inventory.inventory_items i\nJOIN products.products p ON i.product_id = p.id\nWHERE i.status = 'listed'\n  AND i.listed_price > 0\nORDER BY RANDOM()\nLIMIT 50",
        "options": {}
      },
      "id": "get-listed-products",
      "name": "Get Listed Products",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.6,
      "position": [450, 400],
      "retryOnFail": true
    },
    {
      "parameters": {
        "url": "=http://localhost:8000/api/pricing/market-price",
        "method": "POST",
        "sendBody": true,
        "contentType": "json",
        "jsonBody": "={\n  \"product_id\": \"{{ $json.id }}\",\n  \"size\": \"{{ $json.size }}\",\n  \"condition\": \"{{ $json.condition }}\"\n}",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "options": {
          "timeout": 10000,
          "retry": {
            "retry": {
              "maxRetries": 2
            }
          }
        }
      },
      "id": "get-market-price",
      "name": "Get Market Price",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.3,
      "position": [650, 400],
      "onError": "continueRegularOutput"
    },
    {
      "parameters": {
        "jsCode": "// Calculate price differences\nconst items = $input.all();\nconst alerts = [];\n\nfor (const item of items) {\n  const data = item.json;\n  \n  // Skip if no market price returned\n  if (!data.market_price || data.market_price === 0) continue;\n  \n  const currentPrice = parseFloat(data.current_price);\n  const marketPrice = parseFloat(data.market_price);\n  const purchaseCost = parseFloat(data.purchase_cost);\n  \n  // Calculate differences\n  const priceDiff = ((currentPrice - marketPrice) / marketPrice * 100).toFixed(1);\n  const profitMargin = ((currentPrice - purchaseCost) / currentPrice * 100).toFixed(1);\n  \n  // Alert if price is >10% above market or <5% profit margin\n  if (Math.abs(priceDiff) > 10 || profitMargin < 5) {\n    alerts.push({\n      product_name: data.name,\n      brand: data.brand,\n      size: data.size,\n      condition: data.condition,\n      current_price: currentPrice.toFixed(2),\n      market_price: marketPrice.toFixed(2),\n      purchase_cost: purchaseCost.toFixed(2),\n      price_diff: priceDiff,\n      profit_margin: profitMargin,\n      inventory_id: data.inventory_id,\n      alert_type: Math.abs(priceDiff) > 10 ? 'price_mismatch' : 'low_margin'\n    });\n  }\n}\n\nreturn alerts.map(alert => ({ json: alert }));"
      },
      "id": "analyze-prices",
      "name": "Analyze Prices",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [850, 400]
    },
    {
      "parameters": {
        "conditions": {
          "number": [
            {
              "value1": "={{ $input.all().length }}",
              "operation": "larger",
              "value2": 0
            }
          ]
        }
      },
      "id": "has-alerts",
      "name": "Has Alerts?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2.2,
      "position": [1050, 400]
    },
    {
      "parameters": {
        "jsCode": "// Format price alerts for Slack\nconst alerts = $input.all().map(a => a.json);\n\n// Group by alert type\nconst priceMismatches = alerts.filter(a => a.alert_type === 'price_mismatch');\nconst lowMargins = alerts.filter(a => a.alert_type === 'low_margin');\n\nconst formatAlert = (alert) => {\n  const emoji = alert.price_diff > 0 ? '📈' : '📉';\n  return `${emoji} *${alert.product_name}* (${alert.brand}) - Size ${alert.size}\\n  💰 Listed: €${alert.current_price} | 📊 Market: €${alert.market_price}\\n  📉 Diff: ${alert.price_diff}% | 💵 Margin: ${alert.profit_margin}%`;\n};\n\nlet message = '🔔 **Price Alerts!**\\n\\n';\n\nif (priceMismatches.length > 0) {\n  message += `⚠️ *Price Mismatches (${priceMismatches.length}):*\\n`;\n  message += priceMismatches.slice(0, 5).map(formatAlert).join('\\n\\n');\n  message += '\\n\\n';\n}\n\nif (lowMargins.length > 0) {\n  message += `💸 *Low Profit Margins (${lowMargins.length}):*\\n`;\n  message += lowMargins.slice(0, 5).map(formatAlert).join('\\n\\n');\n}\n\nmessage += '\\n\\n💡 _Review pricing strategy for these items_';\n\nreturn {\n  json: {\n    message: message,\n    total_alerts: alerts.length,\n    price_mismatches: priceMismatches.length,\n    low_margins: lowMargins.length\n  }\n};"
      },
      "id": "format-alerts",
      "name": "Format Alerts",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [1250, 300]
    },
    {
      "parameters": {
        "resource": "message",
        "operation": "post",
        "select": "channel",
        "channelId": {
          "__rl": true,
          "value": "#pricing-alerts",
          "mode": "name"
        },
        "text": "={{ $json.message }}"
      },
      "id": "slack-price-alert",
      "name": "Send Price Alert",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2.3,
      "position": [1450, 300],
      "onError": "continueRegularOutput"
    }
  ],
  "connections": {
    "Every 2 Hours": {
      "main": [
        [
          {
            "node": "Get Listed Products",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Get Listed Products": {
      "main": [
        [
          {
            "node": "Get Market Price",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Get Market Price": {
      "main": [
        [
          {
            "node": "Analyze Prices",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Analyze Prices": {
      "main": [
        [
          {
            "node": "Has Alerts?",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Has Alerts?": {
      "main": [
        [
          {
            "node": "Format Alerts",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Format Alerts": {
      "main": [
        [
          {
            "node": "Send Price Alert",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1",
    "saveDataErrorExecution": "all",
    "saveDataSuccessExecution": "none"
  }
}
```

---

## 🎯 Workflow 5: StockX Webhook Handler

**Zweck:** Verarbeitet eingehende StockX Webhooks für Echtzeit-Orderupdates.

**Trigger:** Webhook (bei StockX Events)

**Ablauf:**
1. Webhook empfängt StockX Event
2. Validiert Event-Daten
3. Aktualisiert Order in Datenbank
4. Sendet Benachrichtigung bei wichtigen Events

### Workflow JSON

```json
{
  "name": "StockX Webhook Handler",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "stockx-webhook",
        "responseMode": "responseNode",
        "options": {
          "noResponseBody": false
        }
      },
      "id": "webhook-trigger",
      "name": "StockX Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2.1,
      "position": [250, 400],
      "webhookId": "stockx-events"
    },
    {
      "parameters": {
        "jsCode": "// Validate and extract StockX webhook data\nconst body = $input.first().json.body;\n\n// StockX webhook structure\nconst eventType = body.event_type || 'unknown';\nconst orderId = body.data?.order_id || body.order_id;\nconst status = body.data?.status || body.status;\nconst trackingNumber = body.data?.tracking_number;\n\nif (!orderId) {\n  throw new Error('Missing order_id in webhook payload');\n}\n\nreturn {\n  json: {\n    event_type: eventType,\n    order_id: orderId,\n    status: status,\n    tracking_number: trackingNumber,\n    raw_data: body,\n    received_at: new Date().toISOString()\n  }\n};"
      },
      "id": "validate-webhook",
      "name": "Validate Webhook",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [450, 400]
    },
    {
      "parameters": {
        "url": "=http://localhost:8000/api/integration/stockx/webhook",
        "method": "POST",
        "sendBody": true,
        "contentType": "json",
        "jsonBody": "={{ JSON.stringify($json) }}",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "options": {
          "timeout": 15000
        }
      },
      "id": "process-event",
      "name": "Process Event in API",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.3,
      "position": [650, 400],
      "onError": "continueErrorOutput"
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.event_type }}",
              "operation": "equals",
              "value2": "order.shipped"
            }
          ]
        }
      },
      "id": "is-shipped",
      "name": "Is Shipped?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2.2,
      "position": [850, 300]
    },
    {
      "parameters": {
        "resource": "message",
        "operation": "post",
        "select": "channel",
        "channelId": {
          "__rl": true,
          "value": "#orders",
          "mode": "name"
        },
        "text": "=📦 **Order Shipped!**\n\n*Order ID:* {{ $json.order_id }}\n*Tracking:* {{ $json.tracking_number }}\n*Status:* {{ $json.status }}\n\n_Order is on its way!_ 🚚"
      },
      "id": "notify-shipped",
      "name": "Notify Shipped",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2.3,
      "position": [1050, 200],
      "onError": "continueRegularOutput"
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ JSON.stringify({ status: 'success', message: 'Webhook processed', order_id: $json.order_id }) }}",
        "options": {
          "responseCode": 200
        }
      },
      "id": "respond-success",
      "name": "Respond to Webhook",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [850, 500]
    }
  ],
  "connections": {
    "StockX Webhook": {
      "main": [
        [
          {
            "node": "Validate Webhook",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Validate Webhook": {
      "main": [
        [
          {
            "node": "Process Event in API",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Process Event in API": {
      "main": [
        [
          {
            "node": "Is Shipped?",
            "type": "main",
            "index": 0
          },
          {
            "node": "Respond to Webhook",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Is Shipped?": {
      "main": [
        [
          {
            "node": "Notify Shipped",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1",
    "saveDataErrorExecution": "all",
    "saveDataSuccessExecution": "none"
  }
}
```

---

## 🚀 Deployment Guide

### 1. n8n Setup

```bash
# Starten Sie n8n (bereits in docker-compose.yml)
docker-compose up -d n8n

# Zugriff auf n8n UI
# URL: http://localhost:5678
```

### 2. Credentials einrichten

**PostgreSQL Connection:**
- Host: `postgres` (Docker) oder `localhost`
- Port: `5432`
- Database: `soleflip`
- User: Ihr DB-User
- Password: Ihr DB-Password

**Slack Integration:**
1. Erstellen Sie einen Slack App in Ihrem Workspace
2. Fügen Sie Bot Token Scopes hinzu: `chat:write`, `channels:read`
3. Installieren Sie die App im Workspace
4. Kopieren Sie Bot User OAuth Token in n8n Credentials

**HTTP Header Auth (für API Calls):**
- Header Name: `Authorization`
- Header Value: `Bearer YOUR_API_KEY`

### 3. Workflows importieren

1. Öffnen Sie n8n UI: `http://localhost:5678`
2. Klicken Sie auf "+" → "Import from File" oder "Import from URL"
3. Fügen Sie das Workflow-JSON ein
4. Passen Sie Credentials an
5. Aktivieren Sie den Workflow

### 4. Testen

**Order Sync Workflow:**
```bash
# Manuell triggern in n8n UI oder warten auf Schedule
```

**Webhook Workflow:**
```bash
# Test webhook
curl -X POST http://localhost:5678/webhook/stockx-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "order.shipped",
    "data": {
      "order_id": "test-123",
      "status": "shipped",
      "tracking_number": "1Z999AA10123456784"
    }
  }'
```

---

## 📊 Monitoring & Best Practices

### Monitoring

1. **n8n Execution History:**
   - Überprüfen Sie regelmäßig die Workflow-Ausführungen
   - Aktivieren Sie Execution Data Saving für Debugging

2. **Slack Notifications:**
   - Alle Workflows senden Status-Updates
   - Error-Notifications bei kritischen Failures

3. **Database Queries:**
   - Optimieren Sie langsame Queries
   - Fügen Sie Indizes hinzu falls nötig

### Best Practices

1. **Error Handling:**
   - Alle HTTP Requests haben `onError: "continueRegularOutput"`
   - Database nodes haben `retryOnFail: true`

2. **Performance:**
   - Limit SQL queries (z.B. `LIMIT 50`)
   - Use appropriate intervals (nicht zu häufig)

3. **Security:**
   - Nutzen Sie n8n Credentials, keine hardcoded Secrets
   - Webhook Paths sollten komplex sein
   - Validieren Sie alle Webhook Inputs

4. **Maintenance:**
   - Regelmäßige Backup der n8n Workflows
   - Update n8n und Dependencies
   - Monitor disk space für execution data

---

## 🔧 Troubleshooting

### Workflow läuft nicht

1. **Check Credentials:**
   ```bash
   # Test DB Connection
   psql -h localhost -U your_user -d soleflip -c "SELECT 1;"
   ```

2. **Check n8n Logs:**
   ```bash
   docker-compose logs -f n8n
   ```

3. **Validate Workflow:**
   - Öffnen Sie Workflow in n8n
   - Klicken Sie "Execute Workflow"
   - Prüfen Sie jeden Node einzeln

### Slack Notifications funktionieren nicht

1. **Check Slack Credentials:**
   - Bot Token ist korrekt
   - App ist im Workspace installiert
   - Bot ist in Channels invited

2. **Test Slack API:**
   ```bash
   curl -X POST https://slack.com/api/chat.postMessage \
     -H "Authorization: Bearer YOUR_BOT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"channel":"#test","text":"Test message"}'
   ```

### Database Queries sind langsam

1. **Add Indexes:**
   ```sql
   -- Orders table
   CREATE INDEX IF NOT EXISTS idx_orders_created_at ON transactions.orders(created_at);
   CREATE INDEX IF NOT EXISTS idx_orders_status ON transactions.orders(status);

   -- Inventory table
   CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory.inventory_items(status);
   CREATE INDEX IF NOT EXISTS idx_inventory_created_at ON inventory.inventory_items(created_at);
   ```

2. **Optimize Queries:**
   - Use `EXPLAIN ANALYZE` für Query Plans
   - Limit result sets
   - Use appropriate WHERE clauses

---

## 📈 Erweiterungsmöglichkeiten

### Zukünftige Workflows

1. **Auto-Pricing Workflow:**
   - Überwacht Marktpreise
   - Passt Preise automatisch an
   - Trigger: Hourly oder Event-based

2. **Supplier Order Workflow:**
   - Erstellt automatisch Bestellungen bei Suppliers
   - Basiert auf Low Stock Alerts
   - Integration mit Supplier APIs

3. **Customer Communication:**
   - Automatische Order-Status Updates
   - Email/SMS Notifications
   - Versandbenachrichtigungen

4. **eBay Integration:**
   - Auto-Listing für neue Products
   - Order Sync
   - Price Updates

5. **GOAT/Alias Integration:**
   - Order Sync
   - Inventory Updates
   - Price Monitoring

---

## 📞 Support

Bei Fragen oder Problemen:
1. Prüfen Sie n8n Documentation: https://docs.n8n.io
2. Check SoleFlipper API Docs: http://localhost:8000/docs
3. Review n8n Community Forum: https://community.n8n.io

**Happy Automating!** 🚀
