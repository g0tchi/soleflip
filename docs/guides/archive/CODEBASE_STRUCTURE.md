# SoleFlipper Codebase Structure

## 📁 Project Organization

```
soleflip/
├── 🎯 main.py                          # FastAPI application entry point
├── 📄 pyproject.toml                   # Project dependencies and configuration
├── 🐳 docker-compose.yml               # Docker development environment
├── 🔧 alembic.ini                      # Database migration configuration
│
├── 📁 domains/                         # Domain-driven design structure
│   ├── 📁 integration/                 # Data import and processing
│   │   ├── 📁 api/
│   │   │   └── webhooks.py            # REST API endpoints for file uploads
│   │   └── 📁 services/
│   │       ├── import_processor.py     # Core import pipeline engine
│   │       ├── validators.py          # Data validation (StockX, Alias, etc.)
│   │       ├── transformers.py        # Data transformation and cleaning
│   │       └── parsers.py             # File parsing (CSV, Excel, JSON)
│   │
│   ├── 📁 products/                    # Product management
│   │   └── 📁 services/
│   │       └── product_processor.py   # Product extraction from sales data
│   │
│   └── 📁 inventory/                   # Inventory management
│       ├── 📁 repositories/
│       │   ├── base_repository.py     # Base repository pattern
│       │   └── product_repository.py  # Product data access
│       └── 📁 services/
│           └── inventory_service.py   # Business logic for inventory
│
├── 📁 shared/                          # Shared utilities and infrastructure
│   ├── 📁 database/
│   │   ├── connection.py              # Database connection management
│   │   ├── models.py                  # SQLAlchemy data models
│   │   └── models_simple.py           # Simplified model definitions
│   ├── 📁 error_handling/
│   │   └── exceptions.py              # Custom exception classes
│   └── 📁 logging/
│       └── logger.py                  # Structured logging configuration
│
├── 📁 migrations/                      # Database schema migrations
│   ├── env.py                         # Alembic environment configuration
│   └── 📁 versions/
│       └── 2024_07_29_1200_001_initial_schema.py
│
├── 📁 tests/                          # Test suite
│   ├── conftest.py                    # Pytest configuration
│   ├── 📁 api/
│   │   └── test_webhook_endpoints.py
│   ├── 📁 integration/
│   │   └── test_import_pipeline.py
│   └── 📁 unit/
│       ├── test_inventory_service.py
│       └── test_validators.py
│
├── 📁 docs/                           # API documentation
│   ├── api_documentation.py          # Generated API docs
│   ├── metabase_setup_guide.md       # Metabase integration guide
│   ├── openapi.json                  # OpenAPI specification
│   └── postman_collection.json       # Postman API collection
│
├── 📁 temp_cleanup/                   # Temporarily moved files
│   ├── 📁 debug_scripts/             # Debug and testing scripts
│   ├── 📁 test_csvs/                 # Test data files
│   └── 📁 utility_scripts/           # Database utility scripts
│
└── 📄 sales report for total.csv     # Alias sample data (production data)
```

## 🏗️ Architecture Overview

### Domain-Driven Design
- **Integration Domain**: Handles data import from external platforms (StockX, Alias)
- **Products Domain**: Manages product catalog and extraction from sales data  
- **Inventory Domain**: Manages stock levels and product tracking

### Key Components

#### 1. Import Pipeline (`domains/integration/`)
- **Import Processor**: Orchestrates the complete import workflow
- **Validators**: Platform-specific data validation (StockX, Alias, Notion)
- **Transformers**: Clean and normalize data for database storage
- **Parsers**: Handle different file formats (CSV, Excel, JSON)

#### 2. Data Flow
```
Upload → Parse → Validate → Transform → Store → Extract Products
```

#### 3. Database Layer (`shared/database/`)
- **Async SQLAlchemy**: Modern async ORM for PostgreSQL
- **Connection Management**: Automatic connection pooling and lifecycle
- **Models**: Core data structures (ImportBatch, ImportRecord, Product, etc.)

#### 4. API Layer (`domains/integration/api/`)
- **Webhook Endpoints**: REST API for file uploads and status monitoring
- **Background Processing**: Async task processing for large files
- **Error Handling**: Comprehensive error responses and logging

## 🗄️ Database Schema Architecture

### Core Schema (`core.*`) - Master Data
- **`platforms`** ✅ - Sales platforms (StockX, Alias, GOAT, etc.)
- **`brands`** - Product brands (Nike, Adidas, etc.)
- **`categories`** - Product categories with hierarchy
- **`sizes`** - Size management with regional standards

### Products Schema (`products.*`) - Product Catalog
- **`products`** - Main product entities
- **`inventory`** - Individual inventory items with status

### Sales Schema (`sales.*`) - Transaction Data
- **`transactions`** - Sales transactions referencing `core.platforms`

### Integration Schema (`integration.*`) - Import Tracking
- **`import_batches`** - Import batch tracking
- **`import_records`** - Individual record processing

## 🔄 Import Process Flow

### StockX Integration
1. Upload CSV via `/api/v1/integration/stockx/upload`
2. Parse CSV with StockXValidator
3. Transform data with StockXTransformer  
4. Store in database with metadata
5. Extract unique products for catalog

### Alias Integration  
1. Upload CSV via `/api/v1/integration/alias/upload`
2. Parse CSV with AliasValidator (handles USD amounts, DD/MM/YY dates)
3. Extract brands from product names (no separate brand columns)
4. Transform with AliasTransformer (includes StockX name prioritization)
5. Store and extract products

### Key Features
- **Brand Extraction**: Intelligent brand detection from product names for Alias
- **StockX Name Prioritization**: Prefer StockX product names over Alias names when available
- **Comprehensive Validation**: Field-level validation with detailed error reporting
- **Background Processing**: Handle large files without blocking the API
- **Audit Trail**: Complete history of all imports with source data preservation

## 🧹 Cleanup Actions Performed

### Files Moved to `temp_cleanup/`
- ✅ All `debug_*.py` scripts → `debug_scripts/`
- ✅ All `test_*.py` files → `debug_scripts/`  
- ✅ All test CSV files → `test_csvs/`
- ✅ Utility scripts → `utility_scripts/`

### Code Improvements
- ✅ Removed unused imports from main.py
- ✅ Added proper webhook router integration
- ✅ All core files compile without errors
- ✅ Maintained clean domain separation

### Production Ready Structure
- ✅ Clean separation of concerns
- ✅ Proper error handling and logging
- ✅ Comprehensive test coverage structure
- ✅ Documentation and API specs included