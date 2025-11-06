# StockX API Quick Reference

**Version**: v2
**Base URL**: `https://api.stockx.com/v2`
**Authentication**: OAuth 2.0 (Refresh Token Flow)

---

## Authentication

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `https://accounts.stockx.com/oauth/token` | POST | Get/refresh access token |

### Headers Required

```http
Authorization: Bearer <access_token>
x-api-key: <api_key>
Content-Type: application/json
```

---

## Catalog Endpoints

### Product Search

```http
GET /catalog/search
```

**Parameters**:
- `query` (string, required): SKU, GTIN, keyword
- `pageNumber` (integer, optional): Page number (default: 1)
- `pageSize` (integer, optional): Results per page (default: 10, max: 50)

**Response**:
```json
{
  "products": [
    {
      "id": "uuid",
      "brand": "string",
      "name": "string",
      "model": "string",
      "colorway": "string",
      "releaseDate": "YYYY-MM-DD",
      "retailPrice": number,
      "urlKey": "string",
      "media": {
        "imageUrl": "string",
        "thumbUrl": "string"
      }
    }
  ],
  "pagination": {
    "total": number,
    "page": number,
    "pageSize": number
  }
}
```

**Implementation**: `StockXService.search_stockx_catalog()`

---

### Product Details

```http
GET /catalog/products/{productId}
```

**Path Parameters**:
- `productId` (UUID, required): StockX product ID

**Response**:
```json
{
  "id": "uuid",
  "brand": "string",
  "name": "string",
  "description": "string",
  "category": "string",
  "releaseDate": "YYYY-MM-DD",
  "retailPrice": number,
  "colorway": "string",
  "primaryCategory": "string",
  "secondaryCategory": "string",
  "media": {
    "imageUrl": "string",
    "thumbUrl": "string",
    "360": ["string"],
    "all": ["string"]
  }
}
```

**Implementation**: `StockXService.get_product_details()`

---

### Product Variants (Sizes)

```http
GET /catalog/products/{productId}/variants
```

**Path Parameters**:
- `productId` (UUID, required): StockX product ID

**Query Parameters**:
- `page` (integer, optional): Page number
- `limit` (integer, optional): Results per page

**Response**:
```json
{
  "variants": [
    {
      "variantId": "uuid",
      "variantValue": "string",
      "gtins": ["string"],
      "hidden": boolean
    }
  ],
  "pagination": {
    "page": number,
    "limit": number,
    "total": number
  }
}
```

**Implementation**: `StockXService.get_all_product_variants()`

---

### Market Data

```http
GET /catalog/products/{productId}/market-data
```

**Path Parameters**:
- `productId` (UUID, required): StockX product ID

**Query Parameters**:
- `currencyCode` (string, optional): EUR, USD, GBP (default: EUR)

**Response**:
```json
{
  "productId": "uuid",
  "lowestAsk": number,
  "highestBid": number,
  "lastSale": number,
  "salesLast72Hours": number,
  "averageDeadstockPrice": number,
  "volatility": number,
  "deadstockSold": number,
  "pricePremium": number,
  "changeValue": number,
  "changePercentage": number,
  "lastSaleDate": "ISO-8601"
}
```

**Implementation**: `StockXService.get_market_data_from_stockx()`

---

### Sales History

```http
GET /catalog/products/{productId}/sales
```

**Path Parameters**:
- `productId` (UUID, required): StockX product ID

**Query Parameters**:
- `from` (date, optional): Start date (YYYY-MM-DD)
- `to` (date, optional): End date (YYYY-MM-DD)

**Response**:
```json
{
  "sales": [
    {
      "saleDate": "ISO-8601",
      "salePrice": number,
      "shoeSize": "string"
    }
  ]
}
```

**Implementation**: `StockXService.get_sales_history()`

---

## Selling Endpoints

### Get Orders

```http
GET /selling/orders
```

**Query Parameters**:
- `status` (string, optional): `active`, `completed`, `cancelled`
- `from` (date, optional): Start date (YYYY-MM-DD)
- `to` (date, optional): End date (YYYY-MM-DD)
- `page` (integer, optional): Page number
- `limit` (integer, optional): Results per page

**Response**:
```json
{
  "orders": [
    {
      "orderNumber": "string",
      "status": "string",
      "createdAt": "ISO-8601",
      "product": {
        "productId": "uuid",
        "productName": "string"
      },
      "variant": {
        "variantId": "uuid",
        "variantValue": "string"
      },
      "amount": number,
      "currencyCode": "string"
    }
  ],
  "pagination": {
    "page": number,
    "limit": number,
    "total": number
  }
}
```

**Implementations**:
- `StockXService.get_historical_orders()`
- `StockXService.get_active_orders()`

---

### Get Order Details

```http
GET /selling/orders/{orderNumber}
```

**Path Parameters**:
- `orderNumber` (string, required): Order number

**Response**:
```json
{
  "orderNumber": "string",
  "status": "string",
  "createdAt": "ISO-8601",
  "product": {
    "productId": "uuid",
    "productName": "string",
    "productCondition": "string"
  },
  "variant": {
    "variantId": "uuid",
    "variantValue": "string"
  },
  "pricing": {
    "amount": number,
    "currencyCode": "string",
    "processingFee": number,
    "shippingCost": number,
    "payoutAmount": number
  },
  "shipping": {
    "addressId": "uuid",
    "shippingId": "uuid",
    "carrier": "string",
    "trackingNumber": "string"
  },
  "buyer": {
    "buyerId": "uuid",
    "username": "string"
  }
}
```

**Implementation**: `StockXService.get_order_details()`

---

### Get Listings

```http
GET /selling/listings
```

**Query Parameters**:
- `status` (string, optional): `active`, `pending`, `expired`
- `page` (integer, optional): Page number
- `limit` (integer, optional): Results per page

**Response**:
```json
{
  "listings": [
    {
      "listingId": "uuid",
      "status": "string",
      "product": {
        "productId": "uuid",
        "productName": "string"
      },
      "variant": {
        "variantId": "uuid",
        "variantValue": "string"
      },
      "amount": number,
      "currencyCode": "string",
      "createdAt": "ISO-8601"
    }
  ],
  "pagination": {
    "page": number,
    "limit": number,
    "total": number
  }
}
```

**Implementation**: `StockXService.get_all_listings()`

---

### Create Listing

```http
POST /selling/listings
```

**Request Body**:
```json
{
  "productId": "uuid",
  "variantId": "uuid",
  "amount": number,
  "currencyCode": "string",
  "condition": "new" | "used",
  "shipsFrom": {
    "countryCode": "string"
  }
}
```

**Response**:
```json
{
  "listingId": "uuid",
  "status": "active",
  "createdAt": "ISO-8601",
  "expiresAt": "ISO-8601"
}
```

**Implementation**: `StockXService.create_listing()`

---

### Get Shipping Document

```http
GET /selling/orders/{orderNumber}/shipping/{shippingId}
```

**Path Parameters**:
- `orderNumber` (string, required): Order number
- `shippingId` (UUID, required): Shipping ID

**Response**: Binary PDF file

**Implementation**: `StockXService.get_shipping_document()`

---

## Rate Limits

### Official Limits

⚠️ **Not publicly documented**

### Observed Limits (Conservative)

- **Requests per second**: 10
- **Requests per minute**: 600
- **Daily quota**: Unknown (likely 50,000+)

### Rate Limit Response

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please retry after 60 seconds."
}
```

---

## Error Codes

| Status Code | Meaning | Action |
|-------------|---------|--------|
| 200 OK | Success | Process response |
| 201 Created | Resource created | Return new resource |
| 400 Bad Request | Invalid parameters | Check request format |
| 401 Unauthorized | Invalid/expired token | Refresh token |
| 404 Not Found | Resource doesn't exist | Return None/empty |
| 429 Too Many Requests | Rate limit exceeded | Wait and retry |
| 500 Internal Server Error | StockX API error | Retry with backoff |
| 502 Bad Gateway | Service unavailable | Retry with backoff |
| 503 Service Unavailable | Maintenance | Wait and retry |

---

## Request/Response Examples

### Example: Search for Product by SKU

**Request**:
```http
GET /catalog/search?query=HQ4276&pageSize=1
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6...
x-api-key: your-api-key-here
```

**Response** (200 OK):
```json
{
  "products": [
    {
      "id": "fa671f11-b94d-4596-a4fe-d91e0bd995a0",
      "brand": "adidas",
      "name": "adidas Reptossage Hook-And-Loop Slides Yu-Gi-Oh! Blue Eyes White Dragon",
      "model": "HQ4276",
      "colorway": "Focus Blue/Cloud White/Glow Blue",
      "releaseDate": "2023-04-01",
      "retailPrice": 55.0,
      "urlKey": "adidas-reptossage-hook-and-loop-slides-yu-gi-oh-blue-eyes-white-dragon",
      "media": {
        "imageUrl": "https://images.stockx.com/images/adidas-Reptossage-Hook-And-Loop-Slides-Yu-Gi-Oh-Blue-Eyes-White-Dragon-Product.jpg",
        "thumbUrl": "https://images.stockx.com/images/adidas-Reptossage-Hook-And-Loop-Slides-Yu-Gi-Oh-Blue-Eyes-White-Dragon-Product.jpg?fit=fill&bg=FFFFFF&w=140&h=100&auto=format,compress&trim=color&q=90&dpr=2&updated_at=1680307200"
      }
    }
  ],
  "pagination": {
    "total": 10,
    "page": 1,
    "pageSize": 1
  }
}
```

---

### Example: Get Market Data

**Request**:
```http
GET /catalog/products/fa671f11-b94d-4596-a4fe-d91e0bd995a0/market-data?currencyCode=EUR
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6...
x-api-key: your-api-key-here
```

**Response** (200 OK):
```json
{
  "productId": "fa671f11-b94d-4596-a4fe-d91e0bd995a0",
  "lowestAsk": 67.00,
  "highestBid": 62.00,
  "lastSale": 65.00,
  "salesLast72Hours": 12,
  "averageDeadstockPrice": 66.50,
  "volatility": 0.05,
  "deadstockSold": 324,
  "pricePremium": 0.22,
  "changeValue": 2.00,
  "changePercentage": 0.031,
  "lastSaleDate": "2025-11-05T14:32:00Z"
}
```

---

### Example: Create Listing

**Request**:
```http
POST /selling/listings
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6...
x-api-key: your-api-key-here
Content-Type: application/json

{
  "productId": "fa671f11-b94d-4596-a4fe-d91e0bd995a0",
  "variantId": "variant-uuid-for-size-8",
  "amount": 70.00,
  "currencyCode": "EUR",
  "condition": "new",
  "shipsFrom": {
    "countryCode": "DE"
  }
}
```

**Response** (201 Created):
```json
{
  "listingId": "new-listing-uuid",
  "status": "active",
  "createdAt": "2025-11-06T10:15:00Z",
  "expiresAt": "2025-12-06T10:15:00Z"
}
```

---

## Python Client Usage Examples

### Initialize Service

```python
from domains.integration.services.stockx_service import StockXService
from shared.database.connection import db_manager

async with db_manager.get_session() as session:
    stockx = StockXService(session)
```

---

### Search Products

```python
# Search by SKU
results = await stockx.search_stockx_catalog(
    query="HQ4276",
    page=1,
    page_size=10
)

if results and results["products"]:
    product = results["products"][0]
    print(f"Found: {product['name']}")
    print(f"StockX ID: {product['id']}")
```

---

### Get Market Data

```python
# Get pricing for a product
market_data = await stockx.get_market_data_from_stockx(
    product_id="fa671f11-b94d-4596-a4fe-d91e0bd995a0",
    currency_code="EUR"
)

if market_data:
    print(f"Lowest Ask: €{market_data['lowestAsk']}")
    print(f"Highest Bid: €{market_data['highestBid']}")
    print(f"Last Sale: €{market_data['lastSale']}")
```

---

### Get Orders

```python
# Get historical orders
orders = await stockx.get_historical_orders(
    from_date=datetime(2025, 1, 1),
    to_date=datetime(2025, 11, 6),
    limit=100
)

print(f"Found {len(orders)} orders")
for order in orders:
    print(f"Order {order['orderNumber']}: €{order['amount']}")
```

---

### Create Listing

```python
# Create new listing
listing = await stockx.create_listing({
    "productId": "fa671f11-b94d-4596-a4fe-d91e0bd995a0",
    "variantId": "variant-uuid",
    "amount": 70.00,
    "currencyCode": "EUR",
    "condition": "new"
})

if listing:
    print(f"Listing created: {listing['listingId']}")
```

---

## Implementation Files

| File | Purpose | Lines |
|------|---------|-------|
| `domains/integration/services/stockx_service.py` | Core API client | 637 |
| `domains/integration/services/stockx_catalog_service.py` | Product enrichment | 809 |
| `docs/guides/stockx_auth_setup.md` | Authentication setup | N/A |
| `context/integrations/stockx-product-search-api-discovery.md` | API discovery docs | N/A |

---

## Related Resources

- **Official Docs**: (Not publicly available)
- **Authentication Guide**: `docs/guides/stockx_auth_setup.md`
- **API Discovery**: `context/integrations/stockx-product-search-api-discovery.md`
- **SKU Strategy**: `context/integrations/stockx-sku-strategy.md`
- **Audit Report**: `context/api_audit/01_stockx_api_audit_report.md`

---

**Last Updated**: 2025-11-06
**API Version**: v2
**Implementation Status**: ✅ Production Ready
