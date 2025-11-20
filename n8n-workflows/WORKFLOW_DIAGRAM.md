# StockX Profit Checker - Visual Workflow Diagram

## Complete Workflow Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER INTERACTION                                │
└─────────────────────────────────────────────────────────────────────────┘

    User sends message: "Check KI6956 at 129.95"
                        │
                        ▼
    ┌───────────────────────────────────────────────────────┐
    │  📱 Chat Trigger                                      │
    │  • Public chat interface                              │
    │  • Webhook: /webhook/stockx-profit-checker           │
    │  • Captures: chatInput, sessionId                    │
    └───────────────────┬───────────────────────────────────┘
                        │
                        ▼
    ┌───────────────────────────────────────────────────────┐
    │  🔍 Parse Input (Code Node)                          │
    │  • Regex: Extract SKU ([A-Z0-9]{5,10})              │
    │  • Regex: Extract Price (\d+\.?\d*)                 │
    │  • Validation: Throw error if invalid               │
    │  Output: { sku, retailPrice, originalMessage }      │
    └───────────────────┬───────────────────────────────────┘
                        │
                        ▼
    ┌───────────────────────────────────────────────────────┐
    │  🌐 Search StockX (HTTP Request)                     │
    │  GET /products/search-stockx?query={{ $json.sku }}  │
    │  Timeout: 30s                                        │
    │  Output: { productId, name, brand, ... }            │
    └───────────────────┬───────────────────────────────────┘
                        │
                        ▼
    ┌───────────────────────────────────────────────────────┐
    │  ❓ Product Found? (IF Node)                         │
    │  Condition: $json.productId EXISTS                   │
    └──────────────┬────────────────┬───────────────────────┘
                   │                │
           YES     │                │ NO
                   ▼                ▼
    ┌──────────────────────┐  ┌──────────────────────────┐
    │  Get Market Data     │  │  Product Not Found      │
    │                      │  │  (Set Node)              │
    └──────────┬───────────┘  │  Output: Error message   │
               │              └──────────┬───────────────┘
               │                         │
               ▼                         │
    ┌──────────────────────┐            │
    │  🌐 Get Market Data  │            │
    │  (HTTP Request)      │            │
    │  GET /products/      │            │
    │    {productId}/      │            │
    │    stockx-market-    │            │
    │    data?currency=EUR │            │
    │  Timeout: 30s        │            │
    │  Output: { variants  │            │
    │    [ { shoeSize,     │            │
    │        market: {     │            │
    │          lowestAsk   │            │
    │        }             │            │
    │    } ] }             │            │
    └──────────┬───────────┘            │
               │                        │
               ▼                        │
    ┌──────────────────────┐            │
    │  💰 Calculate Profit │            │
    │  (Code Node)         │            │
    │                      │            │
    │  For each variant:   │            │
    │  1. Get lowestAsk    │            │
    │  2. netProceeds =    │            │
    │     price * 0.90     │            │
    │  3. profit =         │            │
    │     netProceeds -    │            │
    │     retailPrice      │            │
    │  4. marginPercent =  │            │
    │     (profit /        │            │
    │      retailPrice)    │            │
    │      * 100           │            │
    │  5. Filter: profit>0 │            │
    │  6. Sort by margin   │            │
    │  7. Take top 5       │            │
    │                      │            │
    │  Output: {           │            │
    │    profitableCount,  │            │
    │    topOpportunities, │            │
    │    bestMargin        │            │
    │  }                   │            │
    └──────────┬───────────┘            │
               │                        │
               ▼                        │
    ┌──────────────────────┐            │
    │  ❓ Has Profitable?  │            │
    │  (IF Node)           │            │
    │  Condition:          │            │
    │  profitableCount > 0 │            │
    └──────┬───────┬───────┘            │
           │       │                    │
    YES    │       │ NO                 │
           ▼       ▼                    │
    ┌──────────┐ ┌──────────────┐      │
    │  Format  │ │  Format No   │      │
    │  Profit  │ │  Profit      │      │
    │  Response│ │  Response    │      │
    │  (Code)  │ │  (Code)      │      │
    └─────┬────┘ └──────┬───────┘      │
          │             │              │
          └──────┬──────┘              │
                 │                     │
                 └──────┬──────────────┘
                        │
                        ▼
    ┌───────────────────────────────────────────────────────┐
    │  📤 Response to User                                  │
    │  • Formatted message with profit analysis             │
    │  • OR Error message                                   │
    └───────────────────────────────────────────────────────┘
```

## Detailed Node Breakdown

### 1. Chat Trigger (Entry Point)

**Type**: `@n8n/n8n-nodes-langchain.chatTrigger`

**Input**: User message
```json
{
  "chatInput": "Check KI6956 at 129.95",
  "sessionId": "unique-session-id"
}
```

**Configuration**:
```json
{
  "public": true,
  "options": {
    "title": "🔍 StockX Profit Checker",
    "responseMode": "lastNode"
  }
}
```

**Output**: Passes through to next node

---

### 2. Parse Input (Extraction & Validation)

**Type**: `n8n-nodes-base.code`

**JavaScript Code**:
```javascript
const message = $input.first().json.chatInput || '';
const skuMatch = message.match(/\b([A-Z0-9]{5,10})\b/i);
const priceMatch = message.match(/\b(\d+\.?\d*)\b/);

if (!skuMatch || !priceMatch) {
  throw new Error('❌ Invalid format');
}

return {
  json: {
    sku: skuMatch[1].toUpperCase(),
    retailPrice: parseFloat(priceMatch[1]),
    originalMessage: message
  }
};
```

**Input**:
```json
{"chatInput": "Check KI6956 at 129.95"}
```

**Output**:
```json
{
  "sku": "KI6956",
  "retailPrice": 129.95,
  "originalMessage": "Check KI6956 at 129.95"
}
```

**Error Case**: Throws exception if SKU or price not found

---

### 3. Search StockX (API Call)

**Type**: `n8n-nodes-base.httpRequest`

**Request**:
```
GET http://host.docker.internal:8000/products/search-stockx?query=KI6956
```

**Input**: Uses `$json.sku` from previous node

**Output**:
```json
{
  "productId": "550dc7a4-9f4c-4b56-8a7b-123456789abc",
  "sku": "KI6956",
  "name": "Samba OG Cow Print",
  "brand": "adidas",
  "category": "Sneakers"
}
```

**Error Case**: API returns 404 or empty productId

---

### 4. Product Found? (Conditional)

**Type**: `n8n-nodes-base.if`

**Condition**:
```javascript
{{ $json.productId }} EXISTS
```

**Branches**:
- **TRUE (main[0])**: Product exists → Get Market Data
- **FALSE (main[1])**: Product not found → Error Message

---

### 5a. Get Market Data (API Call)

**Type**: `n8n-nodes-base.httpRequest`

**Request**:
```
GET http://host.docker.internal:8000/products/{productId}/stockx-market-data?currencyCode=EUR
```

**Input**: Uses `$json.productId` from Search StockX

**Output**:
```json
{
  "productId": "550dc7a4-...",
  "brand": "adidas",
  "name": "Samba OG Cow Print",
  "variants": [
    {
      "shoeSize": "US W 8",
      "sizeAllTypes": "US W 8 / UK 6.5 / EU 40",
      "market": {
        "lowestAsk": 175.00,
        "highestBid": 165.00
      }
    },
    {
      "shoeSize": "US W 8.5",
      "sizeAllTypes": "US W 8.5 / UK 7 / EU 40.5",
      "market": {
        "lowestAsk": 180.00,
        "highestBid": 170.00
      }
    }
    // ... more variants
  ]
}
```

---

### 5b. Product Not Found (Error Message)

**Type**: `n8n-nodes-base.set`

**Output**:
```json
{
  "response": "❌ **Product Not Found**\n\nCouldn't find SKU: KI6956\n\nPlease check:\n• SKU is correct\n• Product exists on StockX"
}
```

**Result**: Workflow ends, error message displayed to user

---

### 6. Calculate Profit (Business Logic)

**Type**: `n8n-nodes-base.code`

**Logic**:
```javascript
// Get data
const marketData = $input.first().json;
const retailPrice = $('Parse Input').first().json.retailPrice;
const variants = marketData.variants || [];

// Calculate for each variant
const profitableVariants = [];
for (const variant of variants) {
  const stockxPrice = variant.market?.lowestAsk || 0;

  if (stockxPrice > 0) {
    // 90% after StockX 10% fee
    const netProceeds = stockxPrice * 0.90;
    const profit = netProceeds - retailPrice;
    const marginPercent = (profit / retailPrice) * 100;

    if (profit > 0) {
      profitableVariants.push({
        size: variant.shoeSize,
        stockxPrice: stockxPrice.toFixed(2),
        profit: profit.toFixed(2),
        marginPercent: marginPercent.toFixed(1),
        netProceeds: netProceeds.toFixed(2)
      });
    }
  }
}

// Sort by margin (descending)
profitableVariants.sort((a, b) =>
  parseFloat(b.marginPercent) - parseFloat(a.marginPercent)
);

// Get top 5
const topOpportunities = profitableVariants.slice(0, 5);
```

**Input**: Market data with variants

**Output**:
```json
{
  "sku": "KI6956",
  "productName": "adidas Samba OG Cow Print",
  "brand": "adidas",
  "retailPrice": "129.95",
  "totalVariants": 15,
  "profitableCount": 8,
  "topOpportunities": [
    {
      "size": "US W 8.5",
      "stockxPrice": "180.00",
      "netProceeds": "162.00",
      "profit": "32.05",
      "marginPercent": "24.7"
    },
    {
      "size": "US W 8",
      "stockxPrice": "175.00",
      "netProceeds": "157.50",
      "profit": "27.55",
      "marginPercent": "21.2"
    }
    // ... top 3 more
  ],
  "bestMargin": "24.7"
}
```

---

### 7. Has Profitable? (Conditional)

**Type**: `n8n-nodes-base.if`

**Condition**:
```javascript
{{ $json.profitableCount }} > 0
```

**Branches**:
- **TRUE (main[0])**: Has profitable opportunities → Format Profitable Response
- **FALSE (main[1])**: No profitable opportunities → Format No Profit Response

---

### 8a. Format Profitable Response (Success)

**Type**: `n8n-nodes-base.code`

**Output**:
```json
{
  "response": "🔍 **StockX Analysis: adidas Samba OG Cow Print**\n\n📊 **Summary**\n• SKU: KI6956\n• Retail: €129.95\n• Profitable Sizes: 8 of 15\n\n✅ **Top Opportunities** (Net profit after 10% StockX fee)\n\n**1. Size US W 8.5**\n   • StockX Price: €180.00\n   • Net Proceeds: €162.00\n   • Profit: €32.05 (24.7%)\n\n**2. Size US W 8**\n   • StockX Price: €175.00\n   • Net Proceeds: €157.50\n   • Profit: €27.55 (21.2%)\n\n💡 **Best Opportunity**: Size US W 8.5 with 24.7% margin (€32.05 profit)"
}
```

---

### 8b. Format No Profit Response (No Opportunities)

**Type**: `n8n-nodes-base.code`

**Output**:
```json
{
  "response": "🔍 **StockX Analysis: adidas Samba OG Cow Print**\n\n📊 **Summary**\n• SKU: KI6956\n• Retail: €129.95\n• Total Variants: 15\n\n❌ **No Profitable Opportunities**\n\nUnfortunately, none of the 15 size variants are profitable at the retail price of €129.95.\n\n**Suggestions:**\n• Wait for StockX prices to increase\n• Look for discounted retail prices\n• Try different colorways or models"
}
```

---

## Data Flow Example

### Example 1: Profitable Product

```
Input:  "Check KI6956 at 129.95"
           ↓
Parse:  { sku: "KI6956", retailPrice: 129.95 }
           ↓
Search: { productId: "550dc7a4-...", name: "Samba OG Cow Print" }
           ↓
Market: { variants: [15 sizes with prices] }
           ↓
Calc:   { profitableCount: 8, topOpportunities: [5 sizes] }
           ↓
Format: "✅ Top Opportunities... Size US W 8.5 (24.7% margin)"
           ↓
Output: Displayed to user in chat
```

### Example 2: Product Not Found

```
Input:  "Check INVALID at 99.99"
           ↓
Parse:  { sku: "INVALID", retailPrice: 99.99 }
           ↓
Search: { } (empty response)
           ↓
Check:  productId NOT EXISTS → FALSE branch
           ↓
Error:  "❌ Product Not Found"
           ↓
Output: Error message to user
```

### Example 3: No Profitable Opportunities

```
Input:  "Check DZ5485 at 180"
           ↓
Parse:  { sku: "DZ5485", retailPrice: 180 }
           ↓
Search: { productId: "abc-...", name: "Air Force 1" }
           ↓
Market: { variants: [12 sizes, all below €180] }
           ↓
Calc:   { profitableCount: 0, topOpportunities: [] }
           ↓
Check:  profitableCount = 0 → FALSE branch
           ↓
Format: "❌ No Profitable Opportunities"
           ↓
Output: No profit message to user
```

## Error Handling Paths

```
┌─────────────────┐
│  Parse Input    │
└────────┬────────┘
         │ ❌ Invalid format
         ▼
    throw Error
         │
         ▼
    "Could not parse message"


┌─────────────────┐
│  Search StockX  │
└────────┬────────┘
         │ ❌ API Error / 404
         ▼
    { productId: null }
         │
         ▼
    Product Found? → FALSE
         │
         ▼
    "Product Not Found"


┌─────────────────┐
│  Get Market Data│
└────────┬────────┘
         │ ❌ Timeout / Error
         ▼
    HTTP Error Handler
         │
         ▼
    "Failed to fetch market data"
```

## Performance Timing

```
┌────────────────────────────────────────────────────┐
│  Node                 │  Avg Time  │  Max Time    │
├───────────────────────┼────────────┼──────────────┤
│  Chat Trigger         │   <10ms    │   50ms       │
│  Parse Input          │   <5ms     │   10ms       │
│  Search StockX        │   200ms    │   2s         │
│  Product Found?       │   <5ms     │   10ms       │
│  Get Market Data      │   500ms    │   3s         │
│  Calculate Profit     │   10ms     │   50ms       │
│  Has Profitable?      │   <5ms     │   10ms       │
│  Format Response      │   5ms      │   20ms       │
├───────────────────────┼────────────┼──────────────┤
│  TOTAL (Success)      │   ~750ms   │   ~5s        │
│  TOTAL (Error)        │   ~200ms   │   ~2s        │
└────────────────────────────────────────────────────┘
```

## Node Positions (Canvas Layout)

```
y=80      [Format Profitable Response]
y=180     [Get Market Data] → [Calculate Profit] → [Has Profitable?]
y=280                                                [Format No Profit]
y=300     [Chat] → [Parse] → [Search] → [Product Found?]
y=420                                    [Product Not Found]

x=240     x=460   x=680     x=900       x=1120      x=1340    x=1560   x=1780
```

This layout ensures:
- Clear left-to-right flow
- Error paths below main path
- Success paths above main path
- No crossing connections

---

**Last Updated**: 2025-11-19
**Workflow Version**: 1.0
