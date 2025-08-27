# 🔗 Integration Module - SoleFlipper

## 📋 Overview

The Integration Module handles all external data sources and platform integrations for the SoleFlipper system. It provides a unified interface for importing sales data from various marketplaces and platforms.

## 🏗️ Architecture

```
domains/integration/
├── api/
│   └── webhooks.py          # FastAPI webhook endpoints for n8n/external systems
├── services/
│   ├── import_processor.py  # Main import orchestration service
│   ├── validators.py        # Data validation for different platforms
│   └── transformers.py      # Data transformation and normalization
└── README.md               # This file
```

## 🚀 Supported Platforms

### ✅ **StockX**
- **Data Source:** Historical Seller Report CSV
- **Features:** Complete sales data with fee breakdown
- **Validator:** `StockXValidator`
- **Transformer:** `StockXTransformer`
- **Key Fields:** Item, Order Number, Sale Date, Listing Price, Seller Fee, Total Payout

### ✅ **Alias (GOAT)**
- **Data Source:** GOAT's selling platform CSV exports
- **Features:** Smart brand extraction, StockX name prioritization
- **Validator:** `AliasValidator`
- **Transformer:** `AliasTransformer`
- **Key Fields:** Product Name, Sale Price, Order Number, Sale Date
- **Special:** Handles DD/MM/YY date format and USD amounts

### 🚧 **Notion** (In Development)
- **Data Source:** Notion Database API
- **Features:** Real-time inventory sync via n8n
- **Validator:** `NotionValidator`
- **Transformer:** `NotionTransformer`
- **Integration:** n8n workflow automation

### 🔮 **Planned Platforms**
- **eBay** - Marketplace integration
- **Manual CSV** - Generic CSV import with auto-detection

## 🛠️ Core Services

### 1. **Import Processor** (`import_processor.py`)

Main orchestration service that handles the complete import pipeline:

```python
from domains.integration.services.import_processor import import_processor, SourceType

# Process a file upload
result = await import_processor.process_file(
    file_path="/path/to/stockx_export.csv",
    source_type=SourceType.STOCKX,
    batch_size=1000
)

# Process raw data directly
result = await import_processor.process_import(
    source_type=SourceType.ALIAS,
    data=csv_records,
    metadata={'filename': 'alias_export.csv'}
)
```

**Features:**
- ✅ Batch processing for large datasets
- ✅ Background task support
- ✅ Complete error handling and logging
- ✅ Transaction creation with inventory management
- ✅ Duplicate detection and prevention

### 2. **Validators** (`validators.py`)

Platform-specific data validation with intelligent error handling:

```python
from domains.integration.services.validators import get_validator

# Validate StockX data
validator = get_validator('stockx')
result = validator.validate(raw_csv_data)

if result.is_valid:
    print(f"✅ {result.valid_records} records ready for import")
else:
    print(f"❌ {len(result.errors)} validation errors found")
```

**Platform Validators:**
- **StockXValidator:** Handles N/A SKUs, validates required fields
- **AliasValidator:** DD/MM/YY date parsing, brand extraction
- **NotionValidator:** Nested property structure handling

### 3. **Transformers** (`transformers.py`)

Data normalization and transformation pipeline:

```python
from domains.integration.services.transformers import get_transformer

# Transform platform data to standard format
transformer = get_transformer('stockx')
result = transformer.transform_stockx_data(validated_data)

transformed_records = result.transformed_data
```

**Transformation Features:**
- ✅ Universal field mapping system
- ✅ Type-safe data conversion (Decimal, DateTime, etc.)
- ✅ Currency parsing with symbol support
- ✅ Multi-format date handling
- ✅ Custom validation patterns

## 🌐 API Endpoints

### **File Upload Endpoints**

#### StockX Upload
```bash
POST /api/v1/integration/webhooks/stockx/upload
Content-Type: multipart/form-data

# Form fields:
# - file: CSV file (required)
# - batch_size: Processing batch size (default: 1000)
# - validate_only: Only validate, don't import (default: false)
```

#### Alias (GOAT) Upload
```bash
POST /api/v1/integration/webhooks/alias/upload
Content-Type: multipart/form-data

# Handles DD/MM/YY dates and USD pricing
```

#### Notion Import (n8n Integration)
```bash
POST /api/v1/integration/webhooks/notion/import
Content-Type: application/json

{
  "results": [
    {
      "properties": {
        "Product Name": {"title": [{"text": {"content": "Nike Dunk Low"}}]},
        "Purchase Price": {"number": 150}
      }
    }
  ]
}
```

### **Status Monitoring**

#### Recent Import Status
```bash
GET /api/v1/integration/webhooks/import-status

# Returns summary of last 24 hours imports
```

#### Specific Batch Status
```bash
GET /api/v1/integration/webhooks/import-status/{batch_id}

# Detailed status of specific import batch
```

## 🔧 Usage Examples

### **Basic StockX Import**

```python
import asyncio
from domains.integration.services.import_processor import import_processor, SourceType

async def import_stockx_data():
    result = await import_processor.process_file(
        file_path="stockx_historical_report.csv",
        source_type=SourceType.STOCKX,
        batch_size=500
    )
    
    print(f"Import completed: {result.batch_id}")
    print(f"Processed: {result.processed_records}/{result.total_records}")
    
    if result.status == ImportStatus.COMPLETED:
        print("✅ Import successful!")
    else:
        print(f"❌ Import failed: {result.validation_errors}")

# Run the import
asyncio.run(import_stockx_data())
```

### **Custom Field Mapping**

```python
from domains.integration.services.transformers import DataTransformer, FieldMapping, FieldType

# Create custom field mappings
mappings = [
    FieldMapping(
        source_field="Product Title",
        target_field="product_name", 
        field_type=FieldType.STRING,
        required=True
    ),
    FieldMapping(
        source_field="Price USD",
        target_field="sale_price",
        field_type=FieldType.CURRENCY,
        required=True
    )
]

# Transform with custom mappings
transformer = DataTransformer()
result = transformer.transform(raw_data, mappings, "custom_platform")
```

### **Validation Only Mode**

```python
from domains.integration.services.validators import get_validator

# Validate data without importing
validator = get_validator('alias')
validation_result = validator.validate(csv_data)

if not validation_result.is_valid:
    for error in validation_result.errors:
        print(f"❌ {error}")
else:
    print(f"✅ All {validation_result.valid_records} records are valid")
```

## 🔄 n8n Integration Setup

### **Notion → Database Sync**

1. **Create Notion Integration**
   ```bash
   # Visit: https://www.notion.so/my-integrations
   # Create new integration: "SoleFlipper n8n"
   # Copy secret token: secret_xxxxx
   ```

2. **n8n Workflow Configuration**
   ```json
   {
     "nodes": [
       {
         "name": "Notion Trigger",
         "type": "@n8n/n8n-nodes-notion.Notion",
         "parameters": {
           "resource": "database",
           "operation": "getAll",
           "databaseId": "YOUR_NOTION_DATABASE_ID"
         }
       },
       {
         "name": "SoleFlipper Import",
         "type": "@n8n/n8n-nodes-base.HttpRequest",
         "parameters": {
           "url": "http://192.168.2.45:8000/api/v1/integration/webhooks/notion/import",
           "method": "POST",
           "sendBody": true,
           "bodyParameters": {
             "results": "={{ $json.results }}"
           }
         }
       }
     ]
   }
   ```

3. **Scheduled Sync** (Every 6 hours)
   ```json
   {
     "parameters": {
       "rule": {
         "interval": [{"cronExpression": "0 */6 * * *"}]
       }
     },
     "name": "Schedule Trigger",
     "type": "@n8n/n8n-nodes-base.ScheduleTrigger"
   }
   ```

## 📊 Data Flow

```mermaid
graph TD
    A[External Platform] --> B[Raw Data]
    B --> C[Validator]
    C --> D{Valid?}
    D -->|Yes| E[Transformer]
    D -->|No| F[Return Errors]
    E --> G[Normalized Data]
    G --> H[Import Batch]
    H --> I[Create Products]
    I --> J[Create Inventory]
    J --> K[Create Transactions]
    K --> L[Complete Import]
```

## 🚀 Platform-Specific Features

### **StockX Specialties**
- **N/A SKU Handling:** Creates products without SKUs for N/A entries
- **Fee Breakdown:** Processes detailed fee structure (9.5% default)
- **Order Number Validation:** Ensures unique transaction identification
- **Date Format:** Handles `2022-07-07 21:40:06 +00` format

### **Alias (GOAT) Specialties**
- **Brand Extraction:** Smart brand detection from product names
- **StockX Name Priority:** Prefers existing StockX product names
- **DD/MM/YY Dates:** Handles European date format
- **USD Direct Amounts:** No explicit fees (already deducted)
- **Supplier Tracking:** GOAT seller username preservation

### **Notion Specialties**
- **Property Types:** Handles title, rich_text, number, date, select
- **Real-time Sync:** n8n webhook integration
- **Nested Structure:** Processes Notion's complex property format
- **ID Preservation:** Maintains Notion page IDs for reference

## 🛡️ Error Handling

### **Validation Errors**
```python
# Field-level validation
"Row 15: Missing required field 'Order Number'"
"Row 23: Invalid date format in 'Sale Date'"
"Row 8: SKU contains invalid characters"

# Data-level validation  
"Duplicate order number found: 39224521-39124280"
"Invalid currency amount: 'N/A'"
"Date is in the future: 2025-12-25"
```

### **Import Errors**
```python
# Database errors
"Product creation failed: SKU already exists"
"Transaction creation failed: Invalid inventory item"
"Batch processing interrupted: Database connection lost"

# File errors
"CSV parsing failed: Invalid file encoding"
"Excel file corrupted: Cannot read worksheet"
"File too large: Maximum 50MB exceeded"
```

## 🔍 Monitoring & Logging

### **Structured Logging**
```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("Import started", 
           batch_id=batch_id,
           source_type="stockx", 
           records_count=1500)

logger.error("Validation failed",
            row=23,
            field="order_number",
            error="Missing required value")
```

### **Metrics Tracking**
- ✅ Import success rates by platform
- ✅ Processing time per batch size
- ✅ Error frequency and types
- ✅ Data quality scores
- ✅ Platform-specific performance

## 🧪 Testing

### **Unit Tests**
```bash
# Run all integration tests
pytest domains/integration/tests/

# Test specific validator
pytest domains/integration/tests/test_validators.py::TestStockXValidator

# Test transformation pipeline  
pytest domains/integration/tests/test_transformers.py -v
```

### **Integration Tests**
```bash
# Test complete import pipeline
pytest domains/integration/tests/test_import_flow.py

# Test webhook endpoints
pytest domains/integration/tests/test_webhooks.py
```

### **Manual Testing**
```python
# Test file upload via curl
curl -X POST "http://localhost:8000/api/v1/integration/webhooks/stockx/upload" \
     -F "file=@test_stockx_export.csv" \
     -F "validate_only=true"

# Expected response:
{
  "status": "validated",
  "valid": true,
  "record_count": 50,
  "errors": []
}
```

## 📈 Performance

### **Batch Processing**
- **Default Batch Size:** 1000 records
- **Large Files:** Automatically chunked for memory efficiency
- **Background Processing:** Non-blocking import execution
- **Progress Tracking:** Real-time status updates

### **Memory Management**
- **Streaming CSV Reading:** Low memory footprint
- **Incremental Processing:** Processes data in batches
- **Temporary File Cleanup:** Automatic cleanup after processing
- **Database Connection Pooling:** Efficient resource usage

## 🔐 Security

### **Input Validation**
- ✅ File type restrictions (CSV, Excel only)
- ✅ File size limits (50MB maximum)
- ✅ SQL injection prevention
- ✅ XSS protection in error messages

### **Data Privacy**
- ✅ Temporary file encryption
- ✅ Sensitive data redaction in logs
- ✅ Secure database connections
- ✅ API authentication (when enabled)

## 🚀 Getting Started

### **1. Setup Environment**
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/soleflip"
export ENVIRONMENT="development"
```

### **2. Initialize Database**
```bash
# Run migrations
alembic upgrade head

# Verify tables exist
psql $DATABASE_URL -c "\dt sales.*"
```

### **3. Test Import**
```python
# Upload test file
curl -X POST "http://localhost:8000/api/v1/integration/webhooks/stockx/upload" \
     -F "file=@sample_stockx_data.csv" \
     -F "validate_only=false"

# Check status
curl "http://localhost:8000/api/v1/integration/webhooks/import-status"
```

### **4. Monitor Results**
```bash
# Check database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM sales.transactions;"

# View recent imports
curl "http://localhost:8000/api/v1/integration/webhooks/import-status" | jq '.recent_imports'
```

## 📚 Additional Resources

- **[StockX Export Guide](../../../docs/stockx-export-guide.md)** - How to export data from StockX
- **[Alias Integration](../../../docs/alias-integration.md)** - GOAT/Alias platform setup
- **[n8n Workflows](../../../docs/n8n-setup.md)** - Automation setup guide
- **[API Documentation](../../README.md)** - Complete API reference
- **[Database Schema](../../../shared/database/README.md)** - Database structure

## 🤝 Contributing

### **Adding New Platforms**
1. Create platform-specific validator in `validators.py`
2. Add transformer class in `transformers.py` 
3. Update `SourceType` enum
4. Add webhook endpoint in `webhooks.py`
5. Write tests and documentation

### **Code Style**
- Follow PEP 8 guidelines
- Use type hints for all functions
- Add docstrings for public methods
- Include structured logging
- Write comprehensive tests

---

**Integration Module Version:** 2.1.0  
**Last Updated:** 2025-08-04  
**Maintainer:** SoleFlipper Development Team  

**Ready to integrate! 🚀🔗**