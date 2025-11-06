# Integration Domain Guide

**Domain**: `domains/integration/`
**Purpose**: External platform integrations, data imports, webhooks, and synchronization
**Last Updated**: 2025-11-06

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Services](#core-services)
4. [API Endpoints](#api-endpoints)
5. [Data Import System](#data-import-system)
6. [Webhooks & n8n Integration](#webhooks--n8n-integration)
7. [Business Intelligence](#business-intelligence)
8. [Usage Examples](#usage-examples)
9. [Error Handling](#error-handling)
10. [Testing](#testing)

---

## Overview

The Integration domain handles all external data exchange and platform integrations. It acts as the bridge between SoleFlipper and external marketplaces, analytics tools, and data sources.

### Key Responsibilities

- **StockX API Integration**: OAuth2 authentication, order fetching, product catalog search, listing management
- **CSV Import System**: Multi-source data imports (StockX, Awin, eBay, GOAT, Alias)
- **Webhook Processing**: n8n-compatible endpoints for automation workflows
- **Business Intelligence**: Metabase and Budibase integrations for analytics and admin dashboards
- **QuickFlip Detection**: Arbitrage opportunity identification across platforms
- **Market Data Sync**: Real-time price data from multiple sources

### Domain Structure

```
domains/integration/
├── api/                          # REST API endpoints
│   ├── router.py                 # Main integration endpoints
│   ├── upload_router.py          # CSV upload and validation
│   ├── webhooks.py              # n8n-compatible webhooks
│   ├── quickflip_router.py      # Arbitrage opportunities
│   ├── price_sources_router.py  # Multi-source pricing
│   └── commerce_intelligence_router.py
├── services/                     # Business logic
│   ├── stockx_service.py        # StockX API integration ⭐ CORE
│   ├── import_processor.py      # Import engine ⭐ CORE
│   ├── awin_connector.py        # Awin CSV imports
│   ├── stockx_catalog_service.py # Product enrichment
│   ├── market_price_import_service.py
│   ├── unified_price_import_service.py
│   ├── quickflip_detection_service.py
│   ├── parsers.py               # CSV/JSON/Excel parsing
│   ├── validators.py            # Data validation
│   └── transformers.py          # Data transformation
├── repositories/                 # Data access
│   └── import_repository.py
├── events/                       # Event handlers
│   └── handlers.py
├── metabase/                     # Metabase BI integration
│   ├── services/
│   ├── config/
│   └── schemas/
└── budibase/                     # Budibase admin dashboards
    ├── services/
    ├── config/
    └── schemas/
```

---

## Architecture

### Service Interaction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Integration Domain                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │ StockX API   │────▶│ Import       │────▶│ Product      │   │
│  │ Service      │     │ Processor    │     │ Processor    │   │
│  └──────────────┘     └──────────────┘     └──────────────┘   │
│         │                    │                     │           │
│         │                    ▼                     ▼           │
│         │             ┌──────────────┐     ┌──────────────┐   │
│         │             │ Validators   │     │ Transformers │   │
│         │             └──────────────┘     └──────────────┘   │
│         │                                          │           │
│         ▼                                          ▼           │
│  ┌──────────────────────────────────────────────────────┐     │
│  │          Database (Orders, Products, Inventory)       │     │
│  └──────────────────────────────────────────────────────┘     │
│                            │                                   │
└────────────────────────────┼───────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
         ┌──────────────┐         ┌──────────────┐
         │  Metabase    │         │  Budibase    │
         │  Analytics   │         │  Admin UI    │
         └──────────────┘         └──────────────┘
```

### Data Flow Patterns

1. **Real-Time API Integration** (StockX)
   - OAuth2 authentication → Token management → API requests → Response parsing → Database update

2. **Batch Import Processing**
   - File upload → Validation → Batch creation → Background processing → Status monitoring

3. **Webhook-Driven Automation** (n8n)
   - External trigger → Webhook endpoint → Background task → Database update → Response

---

## Core Services

### 1. StockXService (`stockx_service.py`)

**Purpose**: Comprehensive StockX Public API integration with OAuth2, rate limiting, and connection pooling.

**Location**: `domains/integration/services/stockx_service.py`

#### Key Features

- **OAuth2 Authentication**: Automatic token refresh with refresh token grant
- **Rate Limiting**: 10 requests/second limit (prevents 429 errors)
- **Connection Pooling**: HTTP/2 persistent connections (30-40% performance improvement)
- **429 Error Handling**: Automatic retry with `Retry-After` header support
- **Comprehensive Logging**: Structured logs with context

#### Supported Operations

| Operation Category | Methods | Description |
|-------------------|---------|-------------|
| **Order Management** | `get_active_orders()` | Fetch current active StockX orders |
| | `get_historical_orders()` | Fetch orders within date range |
| | `get_order_details()` | Get single order by order number |
| | `get_shipping_documents()` | Download PDF shipping labels |
| **Product Catalog** | `search_stockx_catalog()` | Search by SKU, GTIN, or text |
| | `get_product_details()` | Get product by ID |
| | `get_product_variants()` | Fetch available sizes |
| | `get_market_data_from_stockx()` | Get current bids/asks |
| **Listing Management** | `get_active_listings()` | Fetch all seller listings |
| | `create_listing()` | Create new ask (listing) |
| **Sales History** | `get_completed_orders()` | Historical sales data |

#### Configuration Requirements

Stored in database (`system_config` table):
- `stockx_client_id` - OAuth2 client ID
- `stockx_client_secret` - OAuth2 client secret
- `stockx_refresh_token` - Long-lived refresh token
- `stockx_api_key` - API key for authentication header

#### Usage Example

```python
from domains.integration.services.stockx_service import StockXService
from shared.database.connection import db_manager

async def fetch_orders_example():
    async with db_manager.get_session() as session:
        service = StockXService(session)

        # Fetch active orders
        orders = await service.get_active_orders()
        print(f"Found {len(orders)} active orders")

        # Search catalog
        results = await service.search_stockx_catalog("Jordan 1 Chicago")
        for product in results:
            print(f"- {product['name']} (SKU: {product['sku']})")

        # Get market data
        market_data = await service.get_market_data_from_stockx(product_id)
        print(f"Lowest Ask: €{market_data['lowest_ask']}")
        print(f"Highest Bid: €{market_data['highest_bid']}")
```

#### Performance Characteristics

- **Connection Pooling**: Reuses up to 20 persistent TCP connections
- **Rate Limiting**: Enforces 10 req/sec limit (shared across all instances)
- **Retry Strategy**: Automatic retry on 429 errors with exponential backoff
- **HTTP/2 Multiplexing**: Multiple requests over single connection
- **Latency**: ~100-300ms per request (after initial connection)

#### Error Handling

```python
from shared.exceptions.domain_exceptions import AuthenticationException

try:
    orders = await service.get_active_orders()
except AuthenticationException as e:
    logger.error("StockX authentication failed", error=str(e))
    # Refresh credentials or alert admin
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:
        # Rate limit exceeded (should be handled automatically)
        logger.warning("Rate limit exceeded", retry_after=e.response.headers.get("Retry-After"))
    elif e.response.status_code == 401:
        # Invalid credentials
        logger.error("Invalid StockX credentials")
except Exception as e:
    logger.error("Unexpected error in StockX service", error=str(e), exc_info=True)
```

---

### 2. ImportProcessor (`import_processor.py`)

**Purpose**: Clean, testable data import engine replacing legacy SQL-based system.

**Location**: `domains/integration/services/import_processor.py`

#### Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Import Processor                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────┐    ┌───────────┐    ┌──────────────┐       │
│  │ Parsers  │───▶│ Validators│───▶│ Transformers │       │
│  └──────────┘    └───────────┘    └──────────────┘       │
│       │                │                    │             │
│       ▼                ▼                    ▼             │
│  ┌────────────────────────────────────────────────┐       │
│  │        Product/Order Processors                │       │
│  └────────────────────────────────────────────────┘       │
│                          │                                 │
│                          ▼                                 │
│  ┌────────────────────────────────────────────────┐       │
│  │  Database (ImportBatch, ImportRecord, Orders)  │       │
│  └────────────────────────────────────────────────┘       │
└────────────────────────────────────────────────────────────┘
```

#### Supported Source Types

```python
class SourceType(Enum):
    STOCKX = "stockx"      # StockX transaction exports
    NOTION = "notion"      # Notion database exports
    SALES = "sales"        # Generic sales data
    ALIAS = "alias"        # Alias marketplace exports
    MANUAL = "manual"      # Manual data entry
```

#### Import Workflow

**Phase 1: Validation** (Pre-Import)
```python
# 1. Parse file
parser = CSVParser()  # or JSONParser, ExcelParser
data = await parser.parse(file_path)

# 2. Validate data
validator = StockXValidator(db_session)  # or AliasValidator, etc.
validation_result = await validator.validate(data)

if not validation_result.is_valid:
    return {"errors": validation_result.errors}
```

**Phase 2: Import** (Background Processing)
```python
# 3. Create batch
batch = await processor.create_initial_batch(
    source_type=SourceType.STOCKX,
    filename="stockx_export.csv"
)

# 4. Process rows
for row in validation_result.normalized_data:
    # Transform data
    transformed = transformer.transform(row, source_type)

    # Create records
    await product_processor.process(transformed)
    await order_processor.process(transformed)

    # Track progress
    batch.processed_records += 1

# 5. Complete batch
batch.status = ImportStatus.COMPLETED
await db_session.commit()
```

**Phase 3: Monitoring**
```python
# Poll batch status
status = await processor.get_batch_status(batch_id)
print(f"Progress: {status.processed_records}/{status.total_records}")
print(f"Status: {status.status}")
```

#### Usage Example

```python
from domains.integration.services.import_processor import ImportProcessor, SourceType

async def import_stockx_orders():
    async with db_manager.get_session() as session:
        processor = ImportProcessor(session)

        # Create batch
        batch = await processor.create_initial_batch(
            source_type=SourceType.STOCKX,
            filename="stockx_orders_2025.csv"
        )

        # Process in background
        import_result = await processor.process_import(
            batch_id=batch.id,
            file_path="/path/to/stockx_orders_2025.csv",
            source_type=SourceType.STOCKX
        )

        print(f"Import completed: {import_result.successful_records} records")
        print(f"Failed: {import_result.failed_records} records")
```

#### Validation Rules

Each source type has specific validation rules:

**StockX Validator**:
- Required fields: `order_number`, `product_name`, `order_date`, `price`
- Date format: ISO 8601 (YYYY-MM-DD)
- Price: Positive decimal, 2 decimal places
- Status: Valid order status from enum

**Awin Validator**:
- Required fields: `product_id`, `product_name`, `price`, `commission`
- URL validation for product links
- Currency code validation

---

### 3. AwinConnector (`awin_connector.py`)

**Purpose**: CSV import connector for Awin affiliate network data with memory-optimized chunked reading.

**Location**: `domains/integration/services/awin_connector.py`

#### Chunking Strategy

| File Size | Chunk Size | Memory Usage |
|-----------|-----------|--------------|
| < 10 MB | Full file | ~10-20 MB |
| 10-50 MB | 1000 rows | ~20-50 MB |
| > 50 MB | 500 rows | ~30-70 MB |

#### Import Process (7 Steps)

1. **Validate File**: Check existence, readability, CSV format
2. **Create Batch**: Initialize `ImportBatch` record with status "pending"
3. **Read CSV in Chunks**: Memory-optimized streaming reader
4. **Validate Rows**: Apply Awin-specific validation rules
5. **Transform Data**: Convert to internal format
6. **Create Records**: Insert products, orders, inventory
7. **Update Batch**: Mark as "completed" or "failed"

#### CSV Format Example

```csv
Product ID,Product Name,Brand,Price,Commission,Product URL,Image URL
12345,Nike Air Max 97,Nike,159.99,15.99,https://...,https://...
67890,Adidas Yeezy Boost 350,Adidas,220.00,22.00,https://...,https://...
```

#### Usage Example

```python
from domains.integration.services.awin_connector import AwinConnector

async def import_awin_products():
    async with db_manager.get_session() as session:
        connector = AwinConnector(session)

        # Import from Awin CSV
        batch_id = await connector.import_from_csv(
            file_path="/path/to/awin_export.csv",
            batch_size=1000
        )

        # Monitor progress
        status = await connector.get_batch_status(batch_id)
        print(f"Status: {status.status}")
        print(f"Progress: {status.processed_records}/{status.total_records}")
```

---

## API Endpoints

### Upload & Import Endpoints

**Base Path**: `/api/integration/upload`

#### POST `/upload/validate`
Validate CSV file without importing.

```bash
curl -X POST "http://localhost:8000/api/integration/upload/validate" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@stockx_orders.csv" \
  -F "source_type=STOCKX_CSV"
```

**Response**:
```json
{
  "status": "valid",
  "total_rows": 150,
  "valid_rows": 148,
  "errors": [
    {"row": 45, "field": "order_date", "error": "Invalid date format"},
    {"row": 89, "field": "price", "error": "Negative price not allowed"}
  ]
}
```

#### POST `/upload/import`
Upload and import CSV file.

```bash
curl -X POST "http://localhost:8000/api/integration/upload/import" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@stockx_orders.csv" \
  -F "source_type=STOCKX_CSV" \
  -F "batch_size=1000"
```

**Response**:
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Import started successfully"
}
```

#### GET `/upload/batch/{batch_id}/status`
Poll import batch status.

```bash
curl "http://localhost:8000/api/integration/upload/batch/{batch_id}/status" \
  -H "Authorization: Bearer $TOKEN"
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "source_type": "STOCKX_CSV",
  "source_file": "stockx_orders.csv",
  "total_records": 150,
  "processed_records": 148,
  "error_records": 2,
  "status": "completed",
  "progress_percent": 100.0,
  "created_at": "2025-11-06T10:00:00Z",
  "completed_at": "2025-11-06T10:02:34Z"
}
```

### Webhook Endpoints

**Base Path**: `/api/integration/webhooks`

#### POST `/webhooks/stockx/import-orders-background`
Trigger StockX order import (n8n-compatible).

```bash
curl -X POST "http://localhost:8000/api/integration/webhooks/stockx/import-orders-background" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from_date": "2025-01-01",
    "to_date": "2025-11-06"
  }'
```

**Response**:
```json
{
  "status": "processing_started",
  "message": "Import has been successfully queued.",
  "batch_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Data Import System

### Supported File Formats

- **CSV**: Standard comma-separated values
- **JSON**: Structured JSON arrays
- **Excel**: `.xlsx` and `.xls` formats

### Parsers

**Location**: `domains/integration/services/parsers.py`

```python
# CSV Parser
parser = CSVParser()
data = await parser.parse("/path/to/file.csv")

# JSON Parser
parser = JSONParser()
data = await parser.parse("/path/to/file.json")

# Excel Parser
parser = ExcelParser()
data = await parser.parse("/path/to/file.xlsx")
```

### Validators

**Location**: `domains/integration/services/validators.py`

```python
# StockX Validator
validator = StockXValidator(db_session)
result = await validator.validate(data)

# Awin Validator
validator = AwinValidator(db_session)
result = await validator.validate(data)

# Alias Validator
validator = AliasValidator(db_session)
result = await validator.validate(data)
```

### Transformers

**Location**: `domains/integration/services/transformers.py`

```python
# Transform data to internal format
transformer = DataTransformer()
transformed = transformer.transform(row, source_type=SourceType.STOCKX)

# Transformed output:
# {
#   "product_name": "Nike Air Jordan 1 Retro High OG",
#   "brand": "Nike",
#   "price": Decimal("159.99"),
#   "order_date": datetime(2025, 11, 6),
#   "status": "completed"
# }
```

---

## Webhooks & n8n Integration

### Purpose

Provide n8n-compatible webhook endpoints for automation workflows, replacing direct SQL queries with proper API endpoints.

**Location**: `domains/integration/api/webhooks.py`

### Available Webhooks

| Endpoint | Method | Purpose | n8n Node Type |
|----------|--------|---------|---------------|
| `/webhooks/stockx/import-orders-background` | POST | Import StockX orders | HTTP Request |
| `/webhooks/import/{batch_id}/status` | GET | Poll import status | HTTP Request |

### n8n Workflow Example

**Workflow**: Daily StockX Order Import

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Schedule    │────▶│ HTTP Request │────▶│  Wait Until  │
│  (Daily 6am) │     │ (Import)     │     │  Complete    │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │ Send Slack   │
                                          │ Notification │
                                          └──────────────┘
```

**n8n Configuration**:

1. **Schedule Trigger Node**
   - Trigger: Cron Expression `0 6 * * *` (6am daily)

2. **HTTP Request Node (Import)**
   - Method: POST
   - URL: `http://api:8000/api/integration/webhooks/stockx/import-orders-background`
   - Headers: `Authorization: Bearer {{$env.API_TOKEN}}`
   - Body JSON:
     ```json
     {
       "from_date": "{{$today.minus(7, 'days').format('YYYY-MM-DD')}}",
       "to_date": "{{$today.format('YYYY-MM-DD')}}"
     }
     ```

3. **Wait Node**
   - Poll endpoint: `/webhooks/import/{{$json.batch_id}}/status`
   - Wait until: `status === "completed"`
   - Max wait: 10 minutes

4. **Slack Notification Node**
   - Message: `StockX import completed: {{$json.processed_records}} orders imported`

---

## Business Intelligence

### Metabase Integration

**Purpose**: Analytics dashboards and SQL-based reporting.

**Location**: `domains/integration/metabase/`

#### Features

- **Materialized Views**: Pre-aggregated analytics tables for fast queries
- **Dashboard Service**: Programmatic dashboard creation and updates
- **Sync Service**: Automatic schema synchronization
- **View Manager**: Materialized view refresh management

#### Usage

```python
from domains.integration.metabase.services.dashboard_service import DashboardService

async def create_sales_dashboard():
    service = DashboardService()

    # Create dashboard
    dashboard = await service.create_dashboard(
        name="Sales Analytics",
        description="Daily sales metrics and trends"
    )

    # Add charts
    await service.add_chart(
        dashboard_id=dashboard.id,
        chart_type="line",
        title="Daily Revenue",
        sql_query="SELECT date, SUM(revenue) FROM sales_mv GROUP BY date"
    )
```

### Budibase Integration

**Purpose**: Low-code admin dashboards and internal tools.

**Location**: `domains/integration/budibase/`

#### Features

- **Config Generator**: Auto-generate Budibase datasource configuration
- **Deployment Service**: Automated dashboard deployment
- **Sync Service**: Two-way data synchronization

---

## Usage Examples

### Complete Import Workflow Example

```python
from domains.integration.services.import_processor import ImportProcessor, SourceType
from domains.integration.services.stockx_service import StockXService

async def complete_import_workflow():
    """Complete example: Import StockX orders from CSV"""

    async with db_manager.get_session() as session:
        # Step 1: Validate file before importing
        processor = ImportProcessor(session)

        validation_result = await processor.validate_file(
            file_path="/uploads/stockx_orders.csv",
            source_type=SourceType.STOCKX
        )

        if not validation_result.is_valid:
            print(f"Validation failed: {validation_result.errors}")
            return

        print(f"Validation passed: {len(validation_result.normalized_data)} valid rows")

        # Step 2: Create import batch
        batch = await processor.create_initial_batch(
            source_type=SourceType.STOCKX,
            filename="stockx_orders.csv"
        )

        print(f"Created batch: {batch.id}")

        # Step 3: Process import in background
        import_result = await processor.process_import(
            batch_id=batch.id,
            file_path="/uploads/stockx_orders.csv",
            source_type=SourceType.STOCKX,
            batch_size=1000
        )

        # Step 4: Monitor progress
        while batch.status not in ["completed", "failed"]:
            await asyncio.sleep(5)  # Poll every 5 seconds

            status = await processor.get_batch_status(batch.id)
            progress = (status.processed_records / status.total_records) * 100
            print(f"Progress: {progress:.1f}% ({status.processed_records}/{status.total_records})")

        # Step 5: Report results
        print(f"Import completed!")
        print(f"- Successful: {import_result.successful_records}")
        print(f"- Failed: {import_result.failed_records}")
        print(f"- Processing time: {import_result.processing_time_ms}ms")
```

### StockX Real-Time Integration Example

```python
async def sync_stockx_orders_and_prices():
    """Sync StockX orders and update market prices"""

    async with db_manager.get_session() as session:
        stockx = StockXService(session)

        # Fetch active orders
        orders = await stockx.get_active_orders()
        print(f"Found {len(orders)} active orders")

        # Process each order
        for order in orders:
            print(f"Processing order {order['order_number']}")

            # Get product details
            product_id = order['product_id']
            product = await stockx.get_product_details(product_id)

            # Get current market data
            market_data = await stockx.get_market_data_from_stockx(product_id)

            # Update pricing
            print(f"- {product['name']}")
            print(f"- Lowest Ask: €{market_data['lowest_ask']}")
            print(f"- Highest Bid: €{market_data['highest_bid']}")

            # Save to database
            await save_market_price(session, product_id, market_data)
```

---

## Error Handling

### Common Errors and Solutions

#### 1. Authentication Errors

**Error**: `AuthenticationException: Invalid StockX credentials`

**Solution**:
```python
# Check credentials in database
from shared.database.models import SystemConfig

async def verify_stockx_credentials():
    config = await session.execute(
        select(SystemConfig).where(SystemConfig.key == "stockx_client_id")
    )
    client_id = config.scalar_one_or_none()

    if not client_id:
        print("StockX credentials not configured")
        print("Run: python scripts/setup_stockx_credentials.py")
```

#### 2. Rate Limit Errors

**Error**: `429 Too Many Requests`

**Solution**: Rate limiting is automatic, but if errors persist:
```python
# Adjust rate limiter in stockx_service.py
StockXService._rate_limiter = AsyncLimiter(5, 1)  # Reduce to 5 req/sec
```

#### 3. Import Validation Errors

**Error**: `ValidationException: Invalid date format in row 45`

**Solution**:
```python
# View detailed validation errors
validation_result = await processor.validate_file(file_path, source_type)

for error in validation_result.errors:
    print(f"Row {error['row']}: {error['field']} - {error['message']}")
```

#### 4. Connection Pool Exhaustion

**Error**: `Connection pool exhausted`

**Solution**:
```python
# Increase connection pool size in stockx_service.py
_http_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=50,  # Increase from 20
        max_connections=200,            # Increase from 100
    )
)
```

---

## Testing

### Unit Tests

**Location**: `tests/unit/domains/integration/`

```python
# Test StockX service
pytest tests/unit/domains/integration/test_stockx_service.py -v

# Test import processor
pytest tests/unit/domains/integration/test_import_processor.py -v

# Test validators
pytest tests/unit/domains/integration/test_validators.py -v
```

### Integration Tests

**Location**: `tests/integration/domains/integration/`

```python
# Test complete import workflow
pytest tests/integration/domains/integration/test_import_workflow.py -v

# Test webhook endpoints
pytest tests/integration/domains/integration/test_webhooks.py -v
```

### Testing Checklist

- [ ] Mock StockX API responses in unit tests
- [ ] Test all validation rules with edge cases
- [ ] Test import error handling (network failures, invalid data)
- [ ] Test rate limiting behavior
- [ ] Test connection pool reuse
- [ ] Test webhook endpoints with n8n-compatible payloads
- [ ] Test batch status monitoring
- [ ] Load test with large CSV files (>10,000 rows)

---

## See Also

- [API Endpoints Reference](../API_ENDPOINTS.md) - Complete API documentation
- [StockX Auth Setup Guide](../../docs/guides/stockx_auth_setup.md) - OAuth2 configuration
- [Pricing Domain Guide](./PRICING_DOMAIN.md) - Pricing integration
- [Repository Pattern Guide](../patterns/REPOSITORY_PATTERN.md) - Data access patterns
- [CLAUDE.md](../../CLAUDE.md) - Architecture overview

---

**Last Updated**: 2025-11-06
**Maintainer**: SoleFlipper Development Team
**Status**: ✅ Production Ready
