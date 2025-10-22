# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Quick Start
```bash
make quick-start        # Complete development setup (install deps + DB setup)
make dev                # Start development server with hot reload
make check              # Run all quality checks (lint + type + test)
```

### Testing
```bash
# Run all tests
pytest                  # Direct command
make test               # Via Makefile

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m api           # API endpoint tests only
pytest -m slow          # Slow/performance tests only
pytest -m database      # Database-dependent tests

# Alternative: use Makefile shortcuts
make test-unit          # Unit tests
make test-integration   # Integration tests
make test-api          # API tests

# Coverage reports
pytest --cov=domains --cov=shared --cov-report=html --cov-report=term-missing
make test-cov           # Same via Makefile (generates htmlcov/ directory)

# Single test file or function
pytest tests/test_specific.py
pytest tests/test_specific.py::test_function_name

# Watch mode (re-run on file changes)
make test-watch
```

### Code Quality & Linting
```bash
# Format and lint code (recommended workflow)
make format              # Auto-format with black, isort, ruff
make lint               # Check formatting and linting
make type-check         # Run mypy type checking
make check              # Run all quality checks (lint + type-check + test)

# Individual tools (PRODUCTION READY - Zero violations)
black .                 # Format code (✅ Applied across codebase)
isort .                 # Sort imports (✅ PEP 8 compliant)
ruff check .            # Lint with ruff (✅ Zero violations achieved)
mypy domains/ shared/   # Type checking (✅ Enhanced validation)

# Quick quality validation
python -m ruff check main.py    # Main application file (✅ Clean)
python -m black --check main.py # Code formatting check
python -m isort --check-only main.py # Import ordering check
```

### Database Operations
```bash
# Setup database
make db-setup                    # Create database and run migrations
alembic upgrade head            # Apply all pending migrations

# Migration workflow
make db-migrate                 # Create new migration (will prompt for name)
alembic revision --autogenerate -m "description"  # Alternative syntax

# Database management
make db-downgrade               # Rollback one migration
make db-reset                   # Reset database (destroys all data)
```

### Development Server
```bash
# Start development server (recommended)
make dev                        # With hot reload and debug logging
uvicorn main:app --reload --host 127.0.0.1 --port 8000 --log-level debug

# Development with file watcher (auto-restart on changes)
make dev-watch                  # Watches domains/, shared/, and root directory

# Production server
make run                        # Production settings
uvicorn main:app --host 127.0.0.1 --port 8000

# View API documentation
make serve-docs                 # Starts server and displays doc URLs
# Then visit: http://localhost:8000/docs (Swagger) or http://localhost:8000/redoc (ReDoc)
```

### Docker Operations
```bash
# Docker workflow
docker-compose up --build -d    # Start all services (API, DB, Metabase, n8n)
make docker-up                  # Alternative via Makefile
docker-compose down             # Stop services
make docker-down                # Alternative via Makefile
docker-compose logs -f          # View logs
make docker-logs                # Alternative via Makefile

# Build only the API image
make docker-build

# Individual services access
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Metabase: http://localhost:6400
# n8n: http://localhost:5678
# Adminer (DB GUI): http://localhost:8220
```

### Utilities & Monitoring
```bash
# System monitoring
make health                     # Check application health (/health endpoint)
make status                     # Check import status
make monitor                    # Monitor system resources (CPU, memory, DB connections)
make logs                       # Show application logs (tail -f)

# Maintenance
make clean                      # Remove temp files (.pyc, __pycache__, caches)
make backup                     # Create timestamped database backup
make restore BACKUP_FILE=file   # Restore database from backup file

# Security & performance
make security-check             # Run pip-audit and bandit security scans
make benchmark                  # Run performance benchmarks
make env-check                  # Verify environment variables and dependencies

# Complete checks
make full-check                 # Clean + install-dev + check + test
make deploy-check               # Pre-deployment validation (clean + test + security)
```

## Architecture Overview

### Domain-Driven Design Structure
This codebase follows Domain-Driven Design (DDD) principles with clean separation of concerns (**v2.3.1 CURRENT**):

- **domains/**: Business logic organized by domain (each has `api/`, `services/`, `repositories/`, `events/`)
  - `integration/`: StockX API integration, CSV imports, data processing (webhooks, Budibase, Metabase)
  - `inventory/`: Product inventory management, dead stock analysis, predictive insights
  - `pricing/`: Smart pricing engine, auto-listing service, condition-based pricing
  - `products/`: Product catalog, brand intelligence system, brand extraction
  - `analytics/`: Forecasting (ARIMA), KPI calculations, seasonal adjustments
  - `orders/`: **Multi-platform order management** (StockX, eBay, GOAT/Alias unified table)
  - `dashboard/`: Dashboard data aggregation and metrics
  - `auth/`: Authentication and authorization (JWT, token blacklist)
  - `suppliers/`: Supplier account management
  - `admin/`: Admin operations (security-restricted, not in production coverage)
  - `sales/`: Legacy sales domain (mostly replaced by orders/)

- **shared/**: Cross-cutting concerns and utilities
  - `database/`: Connection management, models, sessions
  - `auth/`: JWT handling, password hashing, token blacklist
  - `monitoring/`: Health checks, metrics, APM integration
  - `logging/`: Structured logging with request correlation
  - `caching/`: Redis-based caching strategies
  - `performance/`: Database optimizations, query improvements
  - `streaming/`: Large dataset streaming responses
  - `error_handling/`: Centralized exception handling

### Key Architectural Patterns

#### Repository Pattern
Each domain has repositories for data access (e.g., `domains/inventory/repositories/inventory_repository.py`). These handle database interactions and are injected into services.

#### Event-Driven Architecture
The system uses an event bus (`shared/events/event_bus.py`) for decoupled communication between domains. Event handlers are in `domains/*/events/handlers.py`.

#### Service Layer Pattern
Business logic resides in service classes (e.g., `domains/pricing/services/smart_pricing_service.py`) which orchestrate repositories and handle domain logic.

#### Dependency Injection
FastAPI's dependency injection is used extensively. Common dependencies are in `shared/api/dependencies.py`.

### Database Schema
- **PostgreSQL** with multi-schema architecture for data organization (schemas: `transactions`, `inventory`, `products`, `analytics`)
- **Alembic** for schema migrations with detailed timestamps (auto-applied on startup)
- **SQLAlchemy 2.0** with async support and proper type hints (`async with` pattern)
- **Field encryption** for sensitive data using Fernet keys (`EncryptedFieldMixin`)
- **Multi-Platform Orders** (**v2.3.1**) - Unified `transactions.orders` table supports all marketplace platforms (StockX, eBay, GOAT, etc.)
- **Connection pooling** optimized for NAS/network environments (pool_size=15, max_overflow=20, pool_pre_ping=True)

### Key Database Models (shared/database/models.py)
- `Product` - Product catalog with brand, category, size information
- `InventoryItem` - Stock/inventory tracking with location and condition
- `Transaction` (orders table) - **Multi-platform unified orders** from StockX, eBay, GOAT, etc.
- `Brand` - Brand intelligence data (founders, sustainability, collaborations)
- `User` - User accounts with encrypted credentials
- `Supplier` - Supplier information and account management
- `Price` - Historical pricing data for analytics
- All models use UUID primary keys and include `created_at`/`updated_at` timestamps

### Performance Considerations (**v2.2.1 ENHANCED**)
- **Optimized Connection Pooling** - Enhanced async SQLAlchemy engine with 15% faster startup
- **Streaming Responses** - Large datasets (`shared/streaming/`) with improved efficiency
- **Redis Caching** - Multi-tier caching with blacklist support and performance monitoring
- **Database Optimizations** - Strategic indexing, bulk operations, query performance tracking
- **Background Task Processing** - Enhanced task monitoring and error handling
- **APM Integration** - Real-time performance monitoring and alerting system

## Environment Configuration

### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/soleflip

# Security (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
FIELD_ENCRYPTION_KEY=your_fernet_key_here

# Environment
ENVIRONMENT=development  # or production

# StockX Integration (optional)
STOCKX_CLIENT_ID=your_client_id
STOCKX_CLIENT_SECRET=your_client_secret
```

### Development Setup
1. Copy `.env.example` to `.env` and configure variables
2. Generate encryption key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
3. Run `make quick-start` for complete development setup (installs deps + creates DB)
4. Use `make dev` to start development server
5. Visit http://localhost:8000/docs for interactive API documentation

### Optional ML/Analytics Dependencies
For forecasting and advanced analytics features, install ML dependencies:
```bash
pip install -e ".[ml]"  # Installs scikit-learn, statsmodels, scipy
```
These enable ARIMA forecasting, gradient boosting, and seasonal adjustment features in the analytics domain.

## Code Style Guidelines

### Python Standards
- **Line length**: 100 characters (configured in pyproject.toml)
- **Type hints**: Required for all function signatures
- **Import sorting**: isort with black profile
- **Docstrings**: Google-style for public APIs

### FastAPI Patterns
- Use dependency injection for database sessions, authentication
- Implement proper HTTP status codes and response models
- Use Pydantic models for request/response validation
- Follow RESTful API conventions

### Database Patterns
- Use SQLAlchemy 2.0 async syntax
- Implement proper connection lifecycle management
- Use repository pattern for data access
- Handle transactions explicitly in service layer

### Error Handling
- Use custom exception classes in `shared/error_handling/exceptions.py`
- Implement proper HTTP exception handlers
- Log errors with structured context using structlog

## Testing Strategy

### Test Organization
- **Unit tests**: Test individual functions/classes in isolation
- **Integration tests**: Test database interactions and external services
- **API tests**: Test HTTP endpoints end-to-end
- **Performance tests**: Marked with `@pytest.mark.slow`

### Test Data Management
- Use factories (`factory-boy`) for test data generation
- Sample data available in `tests/data/`
- Database fixtures use transactions for isolation

### Coverage Requirements
- Minimum 80% coverage (enforced in CI)
- Focus on business logic in `domains/` and `shared/`
- Exclude migrations, tests, and main.py from coverage

## StockX Integration

### Authentication Flow
1. Follow setup guide: `docs/guides/stockx_auth_setup.md`
2. OAuth2 credentials stored encrypted in database
3. Automatic token refresh handled by `domains/integration/services/stockx_service.py`

### Data Sync Process
- Orders synced via scheduled background jobs
- CSV import fallback for bulk historical data
- Data validation and transformation in `domains/integration/services/`

## Security Considerations

### Data Protection
- Sensitive fields encrypted using Fernet (API keys, tokens)
- Database credentials via environment variables only
- No secrets committed to repository

### API Security
- JWT authentication with token blacklist
- Rate limiting and request validation
- CORS properly configured for frontend

### Pre-commit Hooks
- Security scanning with bandit
- Dependency vulnerability checks
- Private key detection
- Code quality enforcement

## Performance Monitoring

### Metrics and Observability
- Health check endpoint: `/health`
- Metrics collection in `shared/monitoring/`
- Structured logging with request correlation IDs
- APM integration ready (`shared/monitoring/apm.py`)

### Database Performance
- Connection pooling optimized for async workloads (NAS-aware settings)
- Query optimization utilities in `shared/performance/`
- Bulk operations for large datasets
- Streaming responses to prevent memory issues (`shared/streaming/`)

## Important Development Patterns

### Adding a New Feature to a Domain
1. **Create/update API endpoint** in `domains/{domain}/api/router.py`
   - Define route with proper HTTP method and path
   - Use Pydantic models for request/response validation
   - Inject dependencies (DB session, services)

2. **Implement service logic** in `domains/{domain}/services/{service_name}_service.py`
   - Keep business logic in service layer, not in routes
   - Use repository pattern for data access
   - Handle errors with custom exceptions from `shared/error_handling/exceptions.py`

3. **Create repository methods** in `domains/{domain}/repositories/{repository_name}_repository.py` if needed
   - Inherit from `BaseRepository` for common CRUD operations
   - Use async/await for all database operations
   - Example: `async def get_by_id(self, id: UUID) -> Optional[Model]`

4. **Write tests** in `tests/unit/` and `tests/integration/`
   - Unit tests for services and repositories (isolated, mocked dependencies)
   - Integration tests for API endpoints (full request/response cycle)
   - Mark tests with appropriate markers: `@pytest.mark.unit`, `@pytest.mark.integration`

5. **Run quality checks** before committing
   ```bash
   make format      # Auto-format code
   make check       # Lint, type-check, and test
   ```

### Working with Database Migrations
```bash
# After modifying models in shared/database/models.py:
make db-migrate  # Creates migration (will prompt for description)

# Review the generated migration in migrations/versions/
# Edit if needed (Alembic auto-generate isn't always perfect)

# Test the migration
make db-upgrade  # Apply migration
make db-downgrade  # Rollback if needed

# Run tests to verify
make test
```

### Using Structured Logging
```python
import structlog

logger = structlog.get_logger(__name__)

# Log with context
logger.info(
    "event_description",
    user_id=user.id,
    product_id=product.id,
    duration_ms=45.2
)

# Error logging with exception
try:
    await risky_operation()
except Exception as e:
    logger.error("operation_failed", error=str(e), exc_info=True)
```

### Repository Pattern Example
```python
from shared.repositories.base_repository import BaseRepository
from shared.database.models import Product

class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession):
        super().__init__(Product, session)

    async def find_by_brand(self, brand: str) -> list[Product]:
        stmt = select(Product).where(Product.brand == brand)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

### Error Handling Pattern
```python
from shared.error_handling.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    BusinessRuleViolation
)
from shared.error_handling.error_codes import ErrorCode

# In service layer
async def get_product(self, product_id: UUID) -> Product:
    product = await self.repository.get_by_id(product_id)
    if not product:
        raise ResourceNotFoundException(
            message=f"Product {product_id} not found",
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            details={"product_id": str(product_id)}
        )
    return product
```

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
pg_isready

# Verify database exists
psql -l | grep soleflip

# Test connection with environment
make env-check

# Reset database if corrupted (WARNING: destroys data)
make db-reset
```

### Import Errors or Module Not Found
```bash
# Reinstall dependencies
make install-dev

# Clear Python caches
make clean

# Verify Python version (requires 3.11+)
python --version
```

### Tests Failing After DB Schema Changes
```bash
# Ensure migrations are applied
make db-upgrade

# Reset test database
ENVIRONMENT=testing make db-reset

# Run tests with verbose output
pytest -vv
```

### Linting/Formatting Errors
```bash
# Auto-fix most issues
make format

# Check what would be changed (without modifying)
black --check .
isort --check-only .
ruff check .

# View specific mypy errors
mypy domains/ shared/ --show-error-codes
```

### Docker Services Not Starting
```bash
# View container logs
make docker-logs

# Restart services
make docker-down
make docker-up

# Rebuild from scratch
docker-compose down -v  # Remove volumes
docker-compose up --build -d
```

Always use IDE diagnostics to validate code after implementation

