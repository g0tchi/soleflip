# SoleFlipper API Endpoints Reference
**Version**: 2.2.1
**Base URL**: `http://localhost:8000` (development)
**Authentication**: JWT Bearer Token (except `/auth` endpoints)

## Table of Contents
- [Authentication](#authentication)
- [Orders](#orders)
- [Integration & Import](#integration--import)
- [Products](#products)
- [Inventory](#inventory)
- [Pricing](#pricing)
- [Analytics](#analytics)
- [Dashboard](#dashboard)
- [QuickFlip](#quickflip)
- [Suppliers](#suppliers)
- [Health & Monitoring](#health--monitoring)

---

## Authentication

### POST `/auth/login`
Authenticate user and receive JWT access token.

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `401 Unauthorized`: Invalid credentials

---

## Orders

**Base Path**: `/api/v1/orders`

### GET `/active`
Fetch active orders from StockX marketplace.

**Query Parameters**:
- `orderStatus` (optional): Filter by status (e.g., "PENDING", "SHIPPED")
- `productId` (optional): Filter by product ID
- `variantId` (optional): Filter by variant/size ID
- `sortOrder` (optional): Sort order (default: "CREATEDAT")
- `inventoryTypes` (optional): Comma-separated list ("STANDARD", "DIRECT")
- `initiatedShipmentDisplayIds` (optional): Filter by shipment IDs

**Response** (200 OK):
```json
[
  {
    "orderId": "order-uuid",
    "orderNumber": "SO-123456",
    "status": "COMPLETED",
    "productId": "product-uuid",
    "variantId": "variant-uuid",
    "price": {
      "amount": "150.00",
      "currencyCode": "USD"
    },
    "createdAt": "2025-01-15T10:30:00Z",
    "sku": "NKE-AM90-001",
    "size": "US 10"
  }
]
```

**Errors**:
- `401 Unauthorized`: Missing or invalid JWT token
- `500 Internal Server Error`: StockX API error

---

### GET `/stockx-history`
Fetch historical orders within a date range.

**Query Parameters** (required):
- `fromDate`: Start date (format: `YYYY-MM-DD`)
- `toDate`: End date (format: `YYYY-MM-DD`)
- `orderStatus` (optional): Filter by status (e.g., "COMPLETED", "CANCELED")

**Example Request**:
```
GET /api/v1/orders/stockx-history?fromDate=2025-01-01&toDate=2025-01-31&orderStatus=COMPLETED
```

**Response**: Same structure as `/active`

---

## Integration & Import

**Base Path**: `/api/v1/integration`

### POST `/upload`
Upload CSV file for validation and import.

**Request** (multipart/form-data):
- `file`: CSV file
- `source_type`: Source type enum (e.g., "STOCKX_CSV", "AWIN_CSV", "EBAY_CSV")

**Response** (200 OK):
```json
{
  "filename": "stockx_export.csv",
  "total_records": 150,
  "validation_errors": [],
  "status": "validated",
  "message": "File validated successfully",
  "batch_id": "batch-uuid"
}
```

**Response** (422 Unprocessable Entity - Validation Errors):
```json
{
  "filename": "invalid_file.csv",
  "total_records": 50,
  "validation_errors": [
    "Row 5: Missing required field 'sku'",
    "Row 12: Invalid price format",
    "Row 23: Unknown product_name"
  ],
  "status": "validation_failed",
  "message": "Validation failed with 3 errors"
}
```

**Errors**:
- `400 Bad Request`: Invalid file format
- `422 Unprocessable Entity`: Validation errors

---

### POST `/import/stockx-orders`
Import orders directly from StockX API by date range.

**Request Body**:
```json
{
  "from_date": "2025-01-01",
  "to_date": "2025-01-31"
}
```

**Response** (200 OK):
```json
{
  "status": "started",
  "message": "Import job started successfully",
  "batch_id": "batch-uuid"
}
```

**Errors**:
- `400 Bad Request`: Invalid date format
- `500 Internal Server Error`: StockX API unavailable

---

### GET `/batch/{batch_id}/status`
Check import batch status and progress.

**Path Parameters**:
- `batch_id`: UUID of the import batch

**Response** (200 OK):
```json
{
  "id": "batch-uuid",
  "source_type": "STOCKX_API",
  "status": "in_progress",
  "progress": 67.5,
  "records_processed": 135,
  "records_failed": 5,
  "created_at": "2025-01-15T10:00:00Z",
  "completed_at": null
}
```

**Status Values**:
- `pending`: Waiting to start
- `in_progress`: Currently processing
- `completed`: Finished successfully
- `failed`: Encountered critical error
- `partially_completed`: Finished with some errors

**Errors**:
- `404 Not Found`: Batch ID not found

---

### POST `/webhooks/stockx`
Webhook endpoint for StockX order notifications.

**Request Body** (from StockX):
```json
{
  "event_type": "order.created",
  "order_id": "order-123",
  "timestamp": "2025-01-15T10:30:00Z",
  ...
}
```

**Response** (200 OK):
```json
{
  "status": "received",
  "message": "Webhook processed successfully"
}
```

---

## Products

**Base Path**: `/api/v1/products`

### GET `/`
List all products with pagination.

**Query Parameters**:
- `page` (default: 1): Page number
- `page_size` (default: 50): Items per page
- `brand` (optional): Filter by brand name
- `category` (optional): Filter by category
- `search` (optional): Search by product name

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "product-uuid",
      "name": "Nike Air Max 90",
      "sku": "NKE-AM90-001",
      "brand": "Nike",
      "category": "Footwear",
      "description": "Classic sneaker design",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 1250,
  "page": 1,
  "page_size": 50,
  "total_pages": 25
}
```

---

### GET `/{product_id}`
Get detailed product information.

**Path Parameters**:
- `product_id`: UUID of the product

**Response** (200 OK):
```json
{
  "id": "product-uuid",
  "name": "Nike Air Max 90",
  "sku": "NKE-AM90-001",
  "brand": {
    "id": "brand-uuid",
    "name": "Nike",
    "slug": "nike"
  },
  "category": "Footwear",
  "sizes": ["US 8", "US 9", "US 10", "US 11"],
  "market_data": {
    "lowest_ask": 150.00,
    "highest_bid": 145.00,
    "last_sale": 148.00
  },
  "stockx_product_id": "stockx-12345",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

**Errors**:
- `404 Not Found`: Product not found

---

### POST `/`
Create a new product.

**Request Body**:
```json
{
  "name": "Adidas Ultra Boost",
  "sku": "ADS-UB-001",
  "brand_name": "Adidas",
  "category": "Footwear",
  "description": "Premium running shoe"
}
```

**Response** (201 Created):
```json
{
  "id": "new-product-uuid",
  "name": "Adidas Ultra Boost",
  ...
}
```

**Errors**:
- `400 Bad Request`: Missing required fields
- `409 Conflict`: Duplicate SKU

---

## Inventory

**Base Path**: `/api/v1/inventory`

### GET `/`
List all inventory items with filters.

**Query Parameters**:
- `location` (optional): Filter by storage location
- `condition` (optional): Filter by condition ("new", "used")
- `in_stock` (optional): Filter by stock status (boolean)
- `page`, `page_size`: Pagination

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "inventory-uuid",
      "product_id": "product-uuid",
      "product_name": "Nike Air Max 90",
      "sku": "NKE-AM90-001",
      "size": "US 10",
      "condition": "new",
      "quantity": 3,
      "location": "Warehouse A",
      "cost_price": 120.00,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 450,
  "page": 1,
  "page_size": 50
}
```

---

### POST `/sync-from-stockx`
Sync inventory from StockX active listings.

**Request Body**: None required

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Inventory sync completed. Created 45 items, updated 23 items.",
  "data": {
    "created": 45,
    "updated": 23,
    "matched": 12,
    "skipped": 5,
    "total_processed": 85
  }
}
```

---

## Pricing

**Base Path**: `/api/v1/pricing`

### POST `/calculate`
Calculate optimal price for a product using pricing engine.

**Request Body**:
```json
{
  "product_id": "product-uuid",
  "inventory_item_id": "inventory-uuid",
  "condition": "new",
  "strategy": "DYNAMIC"
}
```

**Strategy Options**:
- `COST_PLUS`: Cost + markup percentage
- `MARKET_BASED`: Based on StockX market data
- `COMPETITIVE`: Undercut competitors
- `VALUE_BASED`: Premium pricing for high-demand items
- `DYNAMIC`: Weighted combination of strategies

**Response** (200 OK):
```json
{
  "suggested_price": 155.00,
  "min_price": 145.00,
  "max_price": 170.00,
  "strategy_used": "DYNAMIC",
  "confidence_score": 0.85,
  "market_data": {
    "lowest_ask": 158.00,
    "highest_bid": 150.00,
    "last_sale": 154.00
  },
  "breakdown": {
    "cost_plus_price": 150.00,
    "market_based_price": 157.00,
    "competitive_price": 156.00,
    "final_price": 155.00
  }
}
```

---

## Analytics

**Base Path**: `/api/v1/analytics`

### GET `/forecast`
Generate sales forecast using ARIMA model.

**Query Parameters**:
- `product_id` (optional): Forecast for specific product
- `days` (default: 30): Number of days to forecast
- `model` (default: "ARIMA"): Forecasting model

**Response** (200 OK):
```json
{
  "product_id": "product-uuid",
  "forecast_period": {
    "start_date": "2025-01-16",
    "end_date": "2025-02-15",
    "days": 30
  },
  "predictions": [
    {"date": "2025-01-16", "predicted_sales": 15, "confidence_low": 12, "confidence_high": 18},
    {"date": "2025-01-17", "predicted_sales": 16, "confidence_low": 13, "confidence_high": 19}
  ],
  "model_metadata": {
    "model_type": "ARIMA",
    "accuracy": 0.87,
    "mae": 2.3,
    "rmse": 3.1
  }
}
```

---

### GET `/kpis`
Get key performance indicators dashboard.

**Query Parameters**:
- `from_date`: Start date (YYYY-MM-DD)
- `to_date`: End date (YYYY-MM-DD)

**Response** (200 OK):
```json
{
  "period": {
    "from": "2025-01-01",
    "to": "2025-01-31"
  },
  "revenue": {
    "total": 45600.00,
    "growth_percentage": 12.5,
    "average_order_value": 152.00
  },
  "orders": {
    "total": 300,
    "completed": 285,
    "canceled": 15,
    "completion_rate": 0.95
  },
  "inventory": {
    "total_items": 1250,
    "in_stock": 980,
    "low_stock_alerts": 15
  },
  "top_products": [
    {"name": "Nike Air Max 90", "sales": 45, "revenue": 6750.00}
  ]
}
```

---

## Dashboard

**Base Path**: `/api/v1/dashboard`

### GET `/metrics`
Get comprehensive dashboard metrics.

**Response** (200 OK):
```json
{
  "overview": {
    "total_revenue": 125000.00,
    "total_orders": 850,
    "total_products": 320,
    "active_inventory": 1450
  },
  "recent_orders": [...],
  "low_stock_alerts": [...],
  "trending_products": [...]
}
```

---

## QuickFlip

**Base Path**: `/api/v1/quickflip`

### GET `/opportunities`
Get quick-flip arbitrage opportunities.

**Query Parameters**:
- `min_profit_margin` (default: 15): Minimum profit margin percentage
- `max_holding_days` (default: 7): Maximum inventory holding period
- `limit` (default: 50): Number of results

**Response** (200 OK):
```json
[
  {
    "product_id": "product-uuid",
    "product_name": "Nike Dunk Low",
    "buy_price": 120.00,
    "sell_price": 155.00,
    "profit": 35.00,
    "profit_margin": 29.2,
    "demand_score": 85,
    "days_to_flip": 3,
    "confidence": "HIGH"
  }
]
```

---

## Suppliers

**Base Path**: `/api/v1/suppliers`

### GET `/`
List all suppliers.

**Response** (200 OK):
```json
[
  {
    "id": "supplier-uuid",
    "name": "Sneaker Wholesale Co.",
    "contact_email": "contact@supplier.com",
    "phone": "+1-555-0123",
    "reliability_score": 4.5,
    "total_orders": 120
  }
]
```

---

## Health & Monitoring

### GET `/health`
Comprehensive health check with performance metrics.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "version": "2.2.1",
  "environment": "production",
  "uptime_seconds": 3600,
  "checks_summary": {
    "database": "healthy",
    "redis": "healthy",
    "stockx_api": "healthy"
  },
  "performance": {
    "health_score": 95,
    "requests": {
      "total": 15000,
      "success_rate": 0.99
    },
    "database": {
      "avg_query_time_ms": 12.5,
      "active_connections": 8
    }
  }
}
```

---

### GET `/health/ready`
Kubernetes readiness probe.

**Response** (200 OK or 503 Service Unavailable):
```json
{
  "status": "ready",
  "timestamp": "2025-01-15T10:30:00Z",
  "checks": {
    "database": "healthy",
    "migrations": "healthy"
  }
}
```

---

### GET `/health/live`
Kubernetes liveness probe.

**Response** (200 OK or 503 Service Unavailable):
```json
{
  "status": "alive",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

### GET `/metrics`
Prometheus metrics endpoint.

**Response** (200 OK, `text/plain`):
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/orders/active",status="200"} 1523

# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1"} 12450
```

---

## Error Response Format

All error responses follow this structure:

```json
{
  "detail": "Human-readable error message",
  "error_code": "RESOURCE_NOT_FOUND",
  "timestamp": "2025-01-15T10:30:00Z",
  "path": "/api/v1/products/invalid-uuid"
}
```

**Common HTTP Status Codes**:
- `200 OK`: Success
- `201 Created`: Resource created
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (duplicate)
- `422 Unprocessable Entity`: Validation errors
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

---

## Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

To obtain a token, use the `/auth/login` endpoint.

---

## Rate Limiting

API rate limits (subject to change):
- **Authenticated requests**: 1000 requests/hour
- **Unauthenticated requests**: 100 requests/hour
- **Webhook endpoints**: No limit

Rate limit headers included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1642261200
```

---

## Pagination

List endpoints support pagination with these parameters:
- `page` (default: 1): Page number (1-indexed)
- `page_size` (default: 50, max: 100): Items per page

Paginated responses include metadata:
```json
{
  "items": [...],
  "total": 1250,
  "page": 1,
  "page_size": 50,
  "total_pages": 25,
  "has_next": true,
  "has_previous": false
}
```

---

## Interactive Documentation

For interactive API documentation with request/response examples:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

Note: API documentation endpoints are disabled in production for security.

---

## Changelog

### v2.2.1 (Current)
- Added rate limiting to StockX API integration
- Implemented HTTP/2 connection pooling
- Enhanced error handling for 429 responses
- Improved performance monitoring

### v2.2.0
- Multi-platform order management (StockX, eBay, GOAT)
- Enhanced pricing engine with 5 strategies
- ARIMA forecasting for analytics
- QuickFlip arbitrage detection

---

## Support

For API support:
- Documentation: See `docs/` directory
- Issues: Report at GitHub repository
- Development: See `CLAUDE.md` for development guidelines
