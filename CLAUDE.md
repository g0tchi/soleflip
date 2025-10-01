# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m api           # API endpoint tests only

# Run tests with coverage
pytest --cov=domains --cov=shared --cov-report=html --cov-report=term-missing

# Single test file
pytest tests/test_specific.py
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

# Production server
make run                        # Production settings
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Docker Operations
```bash
# Docker workflow
docker-compose up --build -d    # Start all services (API, DB, Metabase, n8n)
docker-compose down             # Stop services
docker-compose logs -f          # View logs

# Individual services access
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Metabase: http://localhost:6400
# n8n: http://localhost:5678
# Adminer: http://localhost:8220
```

## Architecture Overview

### Domain-Driven Design Structure
This codebase follows Domain-Driven Design (DDD) principles with clean separation of concerns (**v2.2.1 OPTIMIZED**):

- **domains/**: Business logic organized by domain
  - `integration/`: StockX API integration, CSV imports, data processing
  - `inventory/`: Product inventory management, dead stock analysis
  - `pricing/`: Smart pricing engine, auto-listing service
  - `products/`: Product catalog, brand intelligence system
  - `analytics/`: Forecasting, KPI calculations
  - `orders/`: Order management and tracking (replaces legacy selling domain)
  - `dashboard/`: Dashboard data aggregation
  - `auth/`: Authentication and authorization
  - `suppliers/`: Supplier account management

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
- **PostgreSQL** with multi-schema architecture for data organization
- **Alembic** for schema migrations with detailed timestamps
- **SQLAlchemy 2.0** with async support and proper type hints
- **Field encryption** for sensitive data using Fernet keys
- **Multi-Platform Orders** (**v2.2.2 NEW**) - Unified `transactions.orders` table supports all marketplace platforms (StockX, eBay, GOAT, etc.) - see `context/orders-multi-platform-migration.md`

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
2. Run `make quick-start` for complete development setup
3. Use `make dev` to start development server

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
- Connection pooling optimized for async workloads
- Query optimization utilities in `shared/performance/`
- Bulk operations for large datasets
- Streaming responses to prevent memory issues