# SoleFlipper - Professional Sneaker Reselling Management System

## 🚀 Overview

SoleFlipper is a comprehensive sneaker reselling management system built with modern Python technologies. It provides automated data import, inventory tracking, sales analytics, and seamless integration with platforms like StockX and Notion.

## 🏗️ Architecture

- **FastAPI**: Modern async Python web framework
- **PostgreSQL**: Primary database with schema separation
- **SQLAlchemy 2.0**: Async ORM with declarative models
- **Domain-Driven Design**: Clean architecture with separated concerns
- **Alembic**: Database migration management
- **pytest**: Comprehensive testing framework
- **Metabase**: Analytics and reporting dashboards

## 📁 Project Structure

```
soleflip/
├── main.py                     # FastAPI application entry point
├── alembic.ini                 # Database migration configuration
├── pyproject.toml              # Python dependencies and project config
│
├── shared/                     # Shared utilities and infrastructure
│   ├── database/
│   │   ├── connection.py       # Database connection management
│   │   └── models.py           # SQLAlchemy models and schemas
│   ├── error_handling/
│   │   └── exceptions.py       # Custom exception classes
│   └── logging/
│       └── logger.py           # Structured logging configuration
│
├── domains/                    # Domain-specific business logic
│   ├── integration/            # Data import and processing
│   │   ├── api/
│   │   │   └── webhooks.py     # Webhook endpoints for n8n/external systems
│   │   └── services/
│   │       ├── import_processor.py    # Main import processing engine
│   │       └── validators.py          # Data validation and normalization
│   └── inventory/              # Inventory management
│       ├── repositories/
│       │   ├── base_repository.py     # Base repository pattern
│       │   └── product_repository.py  # Product-specific data access
│       └── services/
│           └── inventory_service.py   # Inventory business logic
│
├── migrations/                 # Alembic database migrations
│   ├── env.py                  # Migration environment configuration
│   └── versions/               # Individual migration files
│
├── tests/                      # Comprehensive test suite
│   ├── conftest.py             # Test configuration and fixtures
│   ├── unit/                   # Unit tests for isolated components
│   ├── integration/            # End-to-end integration tests
│   └── api/                    # API endpoint tests
│
└── docs/                       # Documentation and setup guides
    ├── openapi.json            # Complete API specification
    ├── postman_collection.json # API testing collection
    ├── metabase_annotations.sql # Analytics view definitions
    └── metabase_setup_guide.md # Dashboard setup instructions
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 13+
- (Optional) Docker and Docker Compose

### 2. Installation

```bash
# Clone and enter directory
cd soleflip

# Install dependencies
pip install -e .

# Or using poetry
poetry install
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb soleflip

# Configure environment variables
export DATABASE_URL="postgresql://user:password@localhost/soleflip"
export ENVIRONMENT="development"

# Run database migrations
alembic upgrade head
```

### 4. Start the Application

```bash
# Development server with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production server
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/soleflip
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
API_VERSION=v1

# External Services (optional)
N8N_WEBHOOK_URL=http://localhost:5678/webhook
METABASE_URL=http://localhost:3000

# Security (production)
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Database Configuration

The application uses a multi-schema PostgreSQL setup:

- `core`: Master data (brands, categories, sizes, platforms)
- `products`: Product catalog and inventory
- `sales`: Transaction and sales data
- `integration`: Import tracking and logging
- `logging`: Application logs and audit trails

## 📊 Data Import

### Supported Sources

1. **StockX**: Sales reports and transaction data
2. **Notion**: Inventory management database
3. **Manual**: CSV/Excel files with auto-detection
4. **Sales**: Custom sales tracking data

### Import Methods

#### Via API Endpoints

```bash
# StockX CSV upload
curl -X POST "http://localhost:8000/api/v1/integration/webhooks/stockx/upload" \
  -F "file=@stockx_sales_report.csv" \
  -F "batch_size=1000" \
  -F "validate_only=false"

# Notion database import
curl -X POST "http://localhost:8000/api/v1/integration/webhooks/notion/import" \
  -H "Content-Type: application/json" \
  -d @notion_export.json

# Manual file upload with auto-detection
curl -X POST "http://localhost:8000/api/v1/integration/webhooks/manual/upload" \
  -F "file=@data.csv" \
  -F "source_type=auto"
```

#### Via Python API

```python
from domains.integration.services.import_processor import ImportProcessor
from domains.integration.services.validators import SourceType

# Initialize processor
processor = ImportProcessor()

# Process a file
result = await processor.process_file(
    file_path="stockx_sales_report.csv",
    source_type=SourceType.STOCKX,
    batch_size=1000
)

print(f"Processed {result.processed_records} records")
```

### Data Validation

All imports include comprehensive validation:

- **Field validation**: Required fields, data types, formats
- **Business rules**: Profit calculations, status transitions
- **Data normalization**: Standardized sizes, currencies, dates
- **Duplicate detection**: SKU and transaction ID checking

## 🧪 Testing

### Run All Tests

```bash
# Full test suite
pytest

# With coverage report
pytest --cov=. --cov-report=html

# Specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m api          # API endpoint tests only
```

### Test Categories

- **Unit Tests**: Fast, isolated component testing
- **Integration Tests**: End-to-end data flow testing
- **API Tests**: HTTP endpoint and webhook testing
- **Performance Tests**: Load and concurrent processing testing

### Writing Tests

```python
# Unit test example
@pytest.mark.unit
async def test_stockx_validator():
    validator = StockXValidator()
    result = await validator.validate_record(sample_data, 0)
    assert result['source'] == 'stockx'

# Integration test example
@pytest.mark.integration
async def test_import_pipeline(db_session):
    processor = ImportProcessor()
    result = await processor.process_file("test.csv", SourceType.STOCKX)
    assert result.status == ImportStatus.COMPLETED
```

## 📈 Analytics & Reporting

### Metabase Setup

1. **Install Metabase** (Docker recommended):
```bash
docker run -d -p 3000:3000 --name metabase metabase/metabase
```

2. **Configure Database Connection**:
   - Host: Your PostgreSQL host
   - Database: soleflip
   - User: Create dedicated read-only user (see docs/metabase_setup_guide.md)

3. **Import Analytics Views**:
```bash
psql -d soleflip -f docs/metabase_annotations.sql
```

4. **Create Dashboards**:
   - Business Overview: KPIs, trends, top performers
   - Inventory Management: Stock levels, size distribution
   - Import Monitoring: Pipeline health, success rates
   - Profitability Analysis: Margins, platform performance

### Key Metrics

- **Inventory Value**: Total value of current stock
- **Profit Margins**: By product, brand, platform
- **Sell-Through Rate**: Inventory turnover analytics
- **Import Success Rate**: Data pipeline health
- **Processing Time**: Performance monitoring

## 🔌 API Reference

### Core Endpoints

#### Import Webhooks
- `POST /api/v1/integration/webhooks/stockx/upload` - StockX file upload
- `POST /api/v1/integration/webhooks/notion/import` - Notion data import
- `POST /api/v1/integration/webhooks/manual/upload` - Manual file upload
- `GET /api/v1/integration/webhooks/import-status` - Import status overview
- `GET /api/v1/integration/webhooks/import-status/{batch_id}` - Specific batch status

#### System
- `GET /health` - System health check
- `GET /docs` - Interactive API documentation
- `GET /redoc` - Alternative API documentation

### API Documentation

- **OpenAPI Schema**: Available at `/docs` or `docs/openapi.json`
- **Postman Collection**: Import `docs/postman_collection.json`
- **Examples**: Comprehensive request/response examples included

## 🔧 Development

### Code Style

```bash
# Format code
black .
isort .

# Type checking
mypy .

# Linting
ruff check .
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Check current version
alembic current

# Migration history
alembic history
```

### Adding New Features

1. **Create Domain Service**:
```python
# domains/new_feature/services/feature_service.py
class FeatureService:
    async def process(self, data):
        # Business logic here
        pass
```

2. **Add API Endpoints**:
```python
# domains/new_feature/api/routes.py
@router.post("/process")
async def process_feature(data: FeatureRequest):
    service = FeatureService()
    result = await service.process(data)
    return result
```

3. **Write Tests**:
```python
# tests/unit/test_feature_service.py
async def test_feature_processing():
    service = FeatureService()
    result = await service.process(test_data)
    assert result.success
```

### Performance Optimization

- **Database Indexes**: Monitor query performance, add indexes as needed
- **Connection Pooling**: Configured for 20 base connections, 30 overflow
- **Async Processing**: All I/O operations use async/await
- **Batch Processing**: Large imports processed in configurable batches
- **Caching**: Consider Redis for frequently accessed data

## 🐳 Docker Deployment

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/soleflip
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=soleflip
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  metabase:
    image: metabase/metabase
    ports:
      - "3000:3000"
    depends_on:
      - db

volumes:
  postgres_data:
```

### Production Deployment

```bash
# Build and start services
docker-compose up -d

# Run migrations
docker-compose exec app alembic upgrade head

# View logs
docker-compose logs -f app
```

## 🔧 Troubleshooting

### Common Issues

**Database Connection Errors**:
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Verify database exists
psql -h localhost -U postgres -l | grep soleflip

# Test connection
psql "postgresql://user:password@localhost/soleflip" -c "SELECT 1;"
```

**Import Processing Failures**:
```bash
# Check import status
curl http://localhost:8000/api/v1/integration/webhooks/import-status

# View application logs
tail -f logs/application.log

# Database query for failed imports
psql -d soleflip -c "SELECT * FROM integration.import_batches WHERE status = 'failed';"
```

**Performance Issues**:
```bash
# Monitor database performance
psql -d soleflip -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check connection pool status
curl http://localhost:8000/health
```

### Monitoring

```bash
# Application health
curl http://localhost:8000/health

# Database size
psql -d soleflip -c "SELECT pg_size_pretty(pg_database_size('soleflip'));"

# Import statistics
psql -d soleflip -c "SELECT source_type, COUNT(*), AVG(processing_time_ms) FROM integration.import_batches GROUP BY source_type;"
```

## 📝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Write tests**: Ensure all new code is tested
4. **Follow code style**: Use black, isort, and type hints
5. **Update documentation**: Add docstrings and update README if needed
6. **Submit pull request**: With clear description of changes

### Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run full development check
make check  # Runs tests, linting, type checking
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

- **Documentation**: Check `/docs` directory for detailed guides
- **API Reference**: Visit `/docs` endpoint when server is running
- **Issues**: Create GitHub issues for bugs or feature requests
- **Discussions**: Use GitHub discussions for questions and ideas

---

Built with ❤️ for sneaker resellers worldwide