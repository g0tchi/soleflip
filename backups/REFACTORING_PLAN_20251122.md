# 🔧 REFACTORING PLAN - SoleFlipper Modularization
**Generated**: 2025-11-22 19:35:00 UTC
**Target**: Transform monolithic codebase into maintainable, scalable architecture
**Backup ID**: backup-20251122-190822
**Estimated Effort**: 120-160 hours over 6-8 sprints

---

## 🎯 REFACTORING GOALS

### Primary Objectives:
1. **Modularity**: Break monolithic structures into focused, testable modules
2. **Maintainability**: Reduce cognitive load, improve code navigability
3. **Scalability**: Enable parallel development, easier onboarding
4. **Type Safety**: Achieve 100% MyPy compliance
5. **Test Coverage**: Maintain 80%+ coverage through refactoring

### Success Metrics:
- ✅ All tests passing (80%+ coverage maintained)
- ✅ Zero MyPy errors (strict mode)
- ✅ Zero Ruff linting errors
- ✅ CI/CD pipeline green
- ✅ <10% performance regression
- ✅ Documentation complete (README, API docs, ER diagrams)

---

## 📐 PROPOSED PROJECT STRUCTURE

### Current Structure (Monolithic):
```
soleflip/
├── domains/              # 116 Python files
│   ├── analytics/
│   ├── integration/
│   ├── inventory/
│   ├── pricing/
│   ├── products/
│   └── ...
├── shared/               # 74 Python files
│   ├── database/
│   │   └── models.py     # ❌ 1,093 lines, 23 models
│   ├── auth/
│   ├── monitoring/
│   └── ...
├── tests/                # Test files
├── migrations/           # 44 Alembic migrations ⚠️
└── main.py               # ❌ Imports all routers
```

### Target Structure (Modular):
```
soleflip/
├── src/                  # 🆕 Source root
│   ├── core/             # 🆕 Core domain models and utilities
│   │   ├── __init__.py
│   │   ├── config.py     # Centralized configuration
│   │   ├── constants.py  # Global constants
│   │   └── types.py      # Custom type definitions
│   │
│   ├── database/         # 🔧 Refactored database layer
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── base.py       # Base classes (TimestampMixin, EncryptedFieldMixin)
│   │   ├── session.py    # Session management
│   │   ├── models/       # 🆕 Split models by domain
│   │   │   ├── __init__.py
│   │   │   ├── catalog.py      # Brand, Category, Size, Product
│   │   │   ├── inventory.py    # InventoryItem, StockXPresaleMarking
│   │   │   ├── transactions.py # Transaction, Order, Listing
│   │   │   ├── integration.py  # ImportBatch, ImportRecord
│   │   │   ├── pricing.py      # SourcePrice, PricingHistory
│   │   │   ├── suppliers.py    # Supplier, SupplierAccount
│   │   │   └── system.py       # Platform, SystemConfig, SystemLog
│   │   └── repositories/  # 🆕 Base repository abstractions
│   │       ├── __init__.py
│   │       └── base.py
│   │
│   ├── domains/          # Domain logic (existing, cleaned up)
│   │   ├── catalog/      # 🆕 Renamed from products/
│   │   │   ├── api/
│   │   │   ├── services/
│   │   │   ├── repositories/
│   │   │   ├── schemas/
│   │   │   └── events/
│   │   ├── inventory/
│   │   ├── pricing/
│   │   ├── analytics/
│   │   ├── integration/
│   │   ├── orders/       # 🆕 Unified multi-platform
│   │   └── suppliers/
│   │
│   ├── shared/           # Cross-cutting concerns
│   │   ├── auth/
│   │   ├── caching/
│   │   ├── monitoring/
│   │   ├── logging/
│   │   ├── exceptions/
│   │   └── utils/
│   │
│   └── api/              # 🆕 API layer (extracted from main.py)
│       ├── __init__.py
│       ├── app.py        # FastAPI app factory
│       ├── dependencies.py
│       ├── middleware.py
│       └── routes.py     # Route aggregation
│
├── migrations/           # 🔧 Squashed and cleaned
│   ├── versions/
│   │   ├── 001_baseline_schema.py  # 🆕 Consolidated
│   │   └── 002_...py               # Future migrations
│   └── archive/          # 🆕 Old migrations (reference only)
│
├── tests/                # 🔧 Restructured to mirror src/
│   ├── unit/
│   │   ├── database/
│   │   ├── domains/
│   │   └── shared/
│   ├── integration/
│   │   ├── api/
│   │   └── database/
│   ├── e2e/              # 🆕 End-to-end tests
│   └── fixtures/         # 🆕 Centralized test fixtures
│
├── scripts/              # Utility scripts
│   ├── db/               # 🆕 Database utilities
│   │   ├── seed.py
│   │   ├── backup.py
│   │   └── migrate.py
│   └── dev/              # 🆕 Development utilities
│
├── docs/                 # 🔧 Enhanced documentation
│   ├── api/              # API documentation
│   ├── architecture/     # 🆕 ER diagrams, architecture docs
│   │   ├── database_schema.md
│   │   ├── domain_model.md
│   │   └── er_diagram.svg
│   ├── guides/
│   └── deployment/
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml     # 🔧 Enhanced CI with strict checks
│
├── main.py               # 🔧 Thin wrapper (calls src/api/app.py)
├── pyproject.toml        # 🔧 Updated paths
├── CLAUDE.md
└── README.md             # 🔧 Updated with new structure

```

---

## 🗺️ MIGRATION ROADMAP

### Phase 1: Foundation & Critical Fixes (Sprint 1-2, ~40 hours)

**Goal**: Fix blocking issues, establish refactoring foundation

#### Sprint 1 (Week 1-2):
**PR #1: Fix Critical Test Blocker** [BLOCKER]
- [ ] Fix cryptography library issue (see Debugging Report Critical #1)
- [ ] Verify all tests can run
- [ ] Document test execution environment requirements
- **Estimated**: 4 hours
- **Branch**: `bugfix/fix-cryptography-test-blocker-018AffTcysMopgPbc7cpoEU6`

**PR #2: Auto-fix Linting Issues**
- [ ] Run `ruff check . --fix`
- [ ] Run `ruff check . --unsafe-fixes --fix`
- [ ] Manually fix E712 comparison style
- [ ] Remove unused imports from migrations
- **Estimated**: 2 hours
- **Branch**: `chore/auto-fix-ruff-linting-018AffTcysMopgPbc7cpoEU6`

**PR #3: Install Type Stubs & Basic MyPy Fixes**
- [ ] Add `types-passlib`, `types-redis` to dev dependencies
- [ ] Fix `import-not-found` errors (4 errors)
- [ ] Add type ignores for unavoidable third-party issues
- **Estimated**: 3 hours
- **Branch**: `chore/install-type-stubs-018AffTcysMopgPbc7cpoEU6`

#### Sprint 2 (Week 3-4):
**PR #4: Split models.py into Domain Models**
- [ ] Create `shared/database/models/` directory
- [ ] Create `base.py` (Base, TimestampMixin, EncryptedFieldMixin)
- [ ] Split models:
  - [ ] `catalog.py` (Brand, BrandPattern, Category, Size, Product)
  - [ ] `inventory.py` (InventoryItem, StockXPresaleMarking)
  - [ ] `transactions.py` (Transaction, Order, Listing)
  - [ ] `integration.py` (ImportBatch, ImportRecord, MarketplaceData)
  - [ ] `pricing.py` (SourcePrice, PricingHistory)
  - [ ] `suppliers.py` (Supplier, SupplierAccount, SupplierPerformance, AccountPurchaseHistory)
  - [ ] `system.py` (Platform, SystemConfig, SystemLog, EventStore)
- [ ] Update `shared/database/models/__init__.py` to re-export all
- [ ] Find-replace imports across codebase
- [ ] Run full test suite to verify
- [ ] Deprecate old `models.py` with warning
- **Estimated**: 12 hours
- **Branch**: `refactor/split-models-by-domain-018AffTcysMopgPbc7cpoEU6`

**PR #5: Fix MyPy Type Errors (Phase 1)**
- [ ] Fix `shared/validation/financial_validators.py` (15 errors)
- [ ] Fix `shared/auth/password_hasher.py` (3 errors)
- [ ] Fix `shared/exceptions/domain_exceptions.py` (1 error)
- [ ] Add proper return type annotations
- [ ] Replace `Any` with specific types
- **Estimated**: 8 hours
- **Branch**: `fix/mypy-type-errors-phase1-018AffTcysMopgPbc7cpoEU6`

**PR #6: Document Current Database Schema**
- [ ] Generate ER diagram from SQLAlchemy models (using ERAlchemy or similar)
- [ ] Create `docs/architecture/database_schema.md`
- [ ] Document all schemas (catalog, inventory, transactions, etc.)
- [ ] List all foreign key relationships
- [ ] Document indexes and constraints
- **Estimated**: 6 hours
- **Branch**: `docs/database-schema-documentation-018AffTcysMopgPbc7cpoEU6`

**Phase 1 Deliverables**:
- ✅ All tests passing
- ✅ Zero Ruff errors
- ✅ <15 MyPy errors (down from 24)
- ✅ models.py split into 8 domain files
- ✅ Database schema documented

---

### Phase 2: Core Refactoring (Sprint 3-4, ~50 hours)

**Goal**: Establish `src/` structure, refactor main.py

#### Sprint 3 (Week 5-6):
**PR #7: Create src/ Directory Structure**
- [ ] Create `src/core/` with config, constants, types
- [ ] Move `shared/database/` → `src/database/`
- [ ] Create `src/api/` directory
- [ ] Update pyproject.toml paths
- [ ] Update import paths incrementally
- **Estimated**: 8 hours
- **Branch**: `refactor/create-src-structure-018AffTcysMopgPbc7cpoEU6`

**PR #8: Refactor main.py into API Factory**
- [ ] Create `src/api/app.py` with FastAPI app factory
- [ ] Extract middleware setup to `src/api/middleware.py`
- [ ] Extract route registration to `src/api/routes.py`
- [ ] Extract dependencies to `src/api/dependencies.py`
- [ ] Update `main.py` to thin wrapper calling app factory
- **Estimated**: 10 hours
- **Branch**: `refactor/extract-api-factory-018AffTcysMopgPbc7cpoEU6`

**PR #9: Squash Old Migrations (Risky)**
- [ ] **BACKUP DATABASE FIRST** (critical!)
- [ ] Create new baseline migration with current schema
- [ ] Archive old migrations to `migrations/archive/`
- [ ] Test migration on staging environment
- [ ] Update migration documentation
- **Estimated**: 12 hours + extensive testing
- **Branch**: `refactor/squash-old-migrations-018AffTcysMopgPbc7cpoEU6`
- **Note**: Requires staging environment and careful coordination

#### Sprint 4 (Week 7-8):
**PR #10: Restructure Tests to Mirror src/**
- [ ] Create `tests/unit/database/`
- [ ] Create `tests/unit/domains/`
- [ ] Create `tests/integration/api/`
- [ ] Move existing tests to new structure
- [ ] Create centralized `tests/fixtures/` directory
- [ ] Consolidate factory-boy factories
- **Estimated**: 10 hours
- **Branch**: `refactor/restructure-tests-018AffTcysMopgPbc7cpoEU6`

**PR #11: Fix Remaining MyPy Errors (Phase 2)**
- [ ] Fix remaining 7 `no-untyped-def` errors
- [ ] Fix 3 `operator` type errors
- [ ] Achieve strict mypy compliance
- [ ] Enable `disallow_any_unimported` in mypy config
- **Estimated**: 6 hours
- **Branch**: `fix/mypy-type-errors-phase2-018AffTcysMopgPbc7cpoEU6`

**PR #12: Create ER Diagrams and Architecture Docs**
- [ ] Generate ER diagram (ERAlchemy, dbdiagram.io, or draw.io)
- [ ] Create `docs/architecture/domain_model.md`
- [ ] Document DDD patterns in use
- [ ] Create sequence diagrams for key workflows
- [ ] Update README with architecture overview
- **Estimated**: 8 hours
- **Branch**: `docs/architecture-diagrams-018AffTcysMopgPbc7cpoEU6`

**Phase 2 Deliverables**:
- ✅ src/ structure established
- ✅ main.py refactored to <50 lines
- ✅ Zero MyPy errors (strict mode)
- ✅ Tests restructured and passing
- ✅ Migrations squashed (optional, risky)
- ✅ Architecture documentation complete

---

### Phase 3: Domain Optimization (Sprint 5-6, ~40 hours)

**Goal**: Optimize domain boundaries, improve modularity

#### Sprint 5 (Week 9-10):
**PR #13: Rename products/ → catalog/**
- [ ] Rename `domains/products/` to `domains/catalog/`
- [ ] Update all imports
- [ ] Update database schema references
- [ ] Update API routes (/api/v1/catalog/)
- [ ] Deprecate old routes with warnings
- **Estimated**: 6 hours
- **Branch**: `refactor/rename-products-to-catalog-018AffTcysMopgPbc7cpoEU6`

**PR #14: Consolidate Orders Domain**
- [ ] Verify multi-platform Order model works for StockX, eBay, GOAT
- [ ] Create unified OrderService
- [ ] Abstract platform-specific logic into strategies
- [ ] Update documentation
- **Estimated**: 10 hours
- **Branch**: `refactor/consolidate-orders-domain-018AffTcysMopgPbc7cpoEU6`

**PR #15: Create Base Repository Abstractions**
- [ ] Create `src/database/repositories/base.py`
- [ ] Extract common CRUD operations
- [ ] Add pagination helpers
- [ ] Add filtering/sorting helpers
- [ ] Update domain repositories to inherit
- **Estimated**: 8 hours
- **Branch**: `refactor/create-base-repositories-018AffTcysMopgPbc7cpoEU6`

#### Sprint 6 (Week 11-12):
**PR #16: Add Comprehensive Docstrings**
- [ ] Document all public API endpoints (Google-style)
- [ ] Document all service classes
- [ ] Document all repository methods
- [ ] Generate API documentation (mkdocs or Sphinx)
- **Estimated**: 10 hours
- **Branch**: `docs/add-comprehensive-docstrings-018AffTcysMopgPbc7cpoEU6`

**PR #17: Performance Optimization Pass**
- [ ] Profile critical endpoints (cProfile, py-spy)
- [ ] Optimize N+1 queries (use selectinload)
- [ ] Add database query logging
- [ ] Benchmark before/after
- **Estimated**: 8 hours
- **Branch**: `perf/optimize-critical-endpoints-018AffTcysMopgPbc7cpoEU6`

**PR #18: CI/CD Enhancement**
- [ ] Add strict mypy check to CI
- [ ] Add ruff check to CI (zero tolerance)
- [ ] Add test coverage enforcement (80% minimum)
- [ ] Add dependency vulnerability scanning (pip-audit)
- [ ] Add performance regression tests
- **Estimated**: 6 hours
- **Branch**: `ci/enhance-quality-checks-018AffTcysMopgPbc7cpoEU6`

**Phase 3 Deliverables**:
- ✅ Domain boundaries optimized
- ✅ Base repository pattern implemented
- ✅ Comprehensive documentation
- ✅ CI/CD enforcing quality gates
- ✅ Performance baseline established

---

## 🏗️ DETAILED REFACTORING STEPS

### Step-by-Step: Split models.py (PR #4)

**Preparation**:
```bash
git checkout -b refactor/split-models-by-domain-018AffTcysMopgPbc7cpoEU6
mkdir -p shared/database/models
```

**1. Create base.py** (~30 min):
```python
# shared/database/models/base.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, func

Base = declarative_base()

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class EncryptedFieldMixin:
    """Mixin for models that need encrypted field support"""
    # ... (copy from original models.py)
```

**2. Create catalog.py** (~1 hour):
```python
# shared/database/models/catalog.py
import uuid
from sqlalchemy import Column, String, ForeignKey, UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin
from shared.database.utils import IS_POSTGRES, get_schema_ref

class Brand(Base, TimestampMixin):
    __tablename__ = "brand"
    __table_args__ = {"schema": "catalog"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    # ... rest of model

# BrandPattern, Category, Size, Product...
```

**3. Repeat for other domain models** (~4 hours):
- inventory.py
- transactions.py
- integration.py
- pricing.py
- suppliers.py
- system.py

**4. Create __init__.py** (~30 min):
```python
# shared/database/models/__init__.py
from .base import Base, TimestampMixin, EncryptedFieldMixin
from .catalog import Brand, BrandPattern, Category, Size, Product
from .inventory import InventoryItem, StockXPresaleMarking
from .transactions import Transaction, Order, Listing
from .integration import ImportBatch, ImportRecord, MarketplaceData
from .pricing import SourcePrice, PricingHistory
from .suppliers import Supplier, SupplierAccount, SupplierPerformance, AccountPurchaseHistory
from .system import Platform, SystemConfig, SystemLog, EventStore

__all__ = [
    # Base
    "Base", "TimestampMixin", "EncryptedFieldMixin",
    # Catalog
    "Brand", "BrandPattern", "Category", "Size", "Product",
    # Inventory
    "InventoryItem", "StockXPresaleMarking",
    # Transactions
    "Transaction", "Order", "Listing",
    # Integration
    "ImportBatch", "ImportRecord", "MarketplaceData",
    # Pricing
    "SourcePrice", "PricingHistory",
    # Suppliers
    "Supplier", "SupplierAccount", "SupplierPerformance", "AccountPurchaseHistory",
    # System
    "Platform", "SystemConfig", "SystemLog", "EventStore",
]
```

**5. Update imports** (~3 hours):
```bash
# Find all imports of models
grep -r "from shared.database.models import" --include="*.py"

# Replace imports (be careful, review each file)
find . -name "*.py" -type f -exec sed -i 's/from shared\.database\.models import/from shared.database.models import/g' {} +

# Verify no broken imports
python -c "from shared.database.models import *; print('OK')"
```

**6. Run tests** (~1 hour):
```bash
pytest -xvs
# Fix any import errors
# Ensure all tests pass
```

**7. Add deprecation warning to old models.py** (~15 min):
```python
# shared/database/models_DEPRECATED.py (rename old file)
import warnings
warnings.warn(
    "shared/database/models.py is deprecated. Import from shared.database.models/ instead.",
    DeprecationWarning,
    stacklevel=2
)
# ... keep old code for backwards compatibility temporarily
```

**8. Commit and PR**:
```bash
git add shared/database/models/
git commit -m "refactor: Split models.py into domain-specific model files

BREAKING CHANGE: shared/database/models.py split into modular files
- Created shared/database/models/ directory
- Split 23 models across 8 domain files
- Maintained backwards compatibility via __init__.py
- Added deprecation warning to old models.py

Files:
- base.py (Base, mixins)
- catalog.py (Brand, Category, Product, Size)
- inventory.py (InventoryItem, StockXPresaleMarking)
- transactions.py (Transaction, Order, Listing)
- integration.py (ImportBatch, ImportRecord, MarketplaceData)
- pricing.py (SourcePrice, PricingHistory)
- suppliers.py (Supplier, SupplierAccount, SupplierPerformance)
- system.py (Platform, SystemConfig, SystemLog, EventStore)

Closes #XXX"

git push -u origin refactor/split-models-by-domain-018AffTcysMopgPbc7cpoEU6
```

---

### Step-by-Step: Squash Migrations (PR #9) **[HIGH RISK]**

**⚠️ CRITICAL**: This is a destructive operation. Requires careful planning and testing.

**Prerequisites**:
- [ ] Full database backup created and verified
- [ ] Staging environment available for testing
- [ ] Team coordination (no parallel migration work)
- [ ] Downtime window scheduled (if needed)

**Process**:

**1. Analyze current state**:
```bash
# Check migration history
alembic history

# Identify last "consolidated" migration (if any)
# Target: Squash all migrations before 2025-10-13 (consolidated_fresh_start)

# Count migrations to squash
ls migrations/versions/ | grep -E "2025_(08|09|10)" | wc -l
# Result: ~30 migrations
```

**2. Export current schema**:
```bash
# Connect to database
PGPASSWORD=changeme_secure_password psql -h localhost -U soleflip -d soleflip

# Export schema
pg_dump -h localhost -U soleflip -d soleflip --schema-only -f /tmp/current_schema.sql

# Review schema
cat /tmp/current_schema.sql | grep "CREATE TABLE" | wc -l
# Verify table count matches expectations
```

**3. Create baseline migration**:
```bash
# Create new migration
alembic revision -m "baseline_schema_v2_consolidated"

# Edit migration file
nano migrations/versions/YYYY_MM_DD_HHMM_baseline_schema_v2_consolidated.py
```

**Migration Content**:
```python
"""baseline_schema_v2_consolidated

Revision ID: baseline_v2
Revises: None
Create Date: 2025-11-22 20:00:00.000000

This migration consolidates all previous migrations into a single baseline.
All tables, indexes, constraints, and data from previous migrations are
represented here.

Previous migrations archived in migrations/archive/pre-2025-10/
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'baseline_v2'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Catalog schema
    op.execute("CREATE SCHEMA IF NOT EXISTS catalog")

    # Brand table
    op.create_table(
        'brand',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        schema='catalog'
    )

    # ... (continue for all 23 tables)
    # ... (copy from current_schema.sql)

def downgrade():
    # Drop all tables in reverse order
    op.drop_table('brand', schema='catalog')
    # ...
    op.execute("DROP SCHEMA IF EXISTS catalog CASCADE")
    # ...
```

**4. Test on staging**:
```bash
# Staging database setup
export DATABASE_URL=postgresql://soleflip:password@staging:5432/soleflip_test

# Create fresh database
dropdb soleflip_test
createdb soleflip_test

# Run new baseline migration
alembic upgrade baseline_v2

# Verify schema
psql $DATABASE_URL -c "\dt catalog.*"
psql $DATABASE_URL -c "\d+ catalog.brand"

# Run application
python main.py --check-db

# Run tests
pytest -xvs
```

**5. Archive old migrations**:
```bash
mkdir -p migrations/archive/pre-2025-10/
mv migrations/versions/2025_08_*.py migrations/archive/pre-2025-10/
mv migrations/versions/2025_09_*.py migrations/archive/pre-2025-10/
mv migrations/versions/2025_10_0[1-9]_*.py migrations/archive/pre-2025-10/
```

**6. Update alembic_version** (for existing databases):
```sql
-- Run on production AFTER successful staging test
-- This tells Alembic the current DB state matches the new baseline

-- Backup first!
-- pg_dump -h localhost -U soleflip soleflip > backup_before_squash.sql

-- Update version
UPDATE alembic_version SET version_num = 'baseline_v2';
```

**7. Document and deploy**:
```markdown
# Migration Squash Deployment Plan

## Pre-deployment
1. ✅ Full database backup created
2. ✅ Staging tested successfully
3. ✅ Team notified
4. ✅ Rollback plan ready

## Deployment
1. Schedule maintenance window (5-10 min)
2. Stop application (to prevent writes)
3. Take final backup
4. Update alembic_version table
5. Archive old migrations
6. Deploy new code
7. Run `alembic history` to verify
8. Start application
9. Verify health checks

## Rollback (if needed)
1. Restore from backup
2. Revert code changes
3. Restart application
```

**Estimated effort**: 12 hours + 4 hours testing + 2 hours deployment = **18 hours total**

**Risk Level**: **HIGH** - Requires extensive testing and coordination

---

## 🧪 TESTING STRATEGY

### Test Coverage Requirements

**Maintain 80%+ coverage** through all refactoring:

```bash
# Before any PR
pytest --cov=domains --cov=shared --cov-report=html --cov-report=term-missing

# Verify coverage meets minimum
# Current target: 80% (enforced by CI)

# Generate coverage badge
coverage-badge -o docs/coverage.svg -f
```

### Regression Testing Checklist

For each PR, verify:

- [ ] All unit tests pass (`pytest -m unit`)
- [ ] All integration tests pass (`pytest -m integration`)
- [ ] All API tests pass (`pytest -m api`)
- [ ] MyPy passes with zero errors (`mypy domains/ shared/`)
- [ ] Ruff passes with zero errors (`ruff check .`)
- [ ] Black formatting passes (`black --check .`)
- [ ] Isort passes (`isort --check-only .`)
- [ ] No performance regression (benchmark critical endpoints)
- [ ] Documentation updated (if public API changed)
- [ ] CHANGELOG.md updated (if breaking change)

### Performance Benchmarking

**Baseline metrics** (establish before refactoring):

```bash
# Install locust for load testing
pip install locust

# Create locustfile.py
cat > tests/performance/locustfile.py << 'EOF'
from locust import HttpUser, task, between

class SoleflipUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_products(self):
        self.client.get("/api/v1/products/")

    @task(2)
    def get_inventory(self):
        self.client.get("/api/v1/inventory/")

    @task(1)
    def get_prices(self):
        self.client.get("/api/v1/prices/")
EOF

# Run baseline benchmark
locust -f tests/performance/locustfile.py --headless -u 100 -r 10 -t 60s --host=http://localhost:8000
# Save results to baseline.txt

# After refactoring, compare
locust -f tests/performance/locustfile.py --headless -u 100 -r 10 -t 60s --host=http://localhost:8000
# Compare to baseline - ensure <10% regression
```

---

## 🚀 DEPLOYMENT STRATEGY

### GitFlow-Light Workflow

**Branch Naming**:
```
feature/short-description-018AffTcysMopgPbc7cpoEU6
bugfix/short-description-018AffTcysMopgPbc7cpoEU6
refactor/short-description-018AffTcysMopgPbc7cpoEU6
docs/short-description-018AffTcysMopgPbc7cpoEU6
chore/short-description-018AffTcysMopgPbc7cpoEU6
```

**PR Size Guidelines**:
- **Ideal**: <500 lines changed
- **Maximum**: <1000 lines changed
- **Rationale**: Easier to review, lower risk, faster merges

**Commit Message Format** (Conventional Commits):
```
<type>(<scope>): <subject>

<body>

<footer>
```

Example:
```
refactor(database): Split models.py into domain-specific files

BREAKING CHANGE: Models must now be imported from
shared.database.models.catalog, .inventory, etc. instead of
shared.database.models directly.

Backwards compatibility maintained via __init__.py re-exports.

- Created 8 domain model files
- Reduced models.py from 1,093 to 0 lines
- Improved code navigability and maintainability

Closes #42
```

**Types**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

### CI/CD Pipeline (Enhanced)

**`.github/workflows/ci-cd.yml`** (excerpt):
```yaml
name: CI/CD Pipeline

on:
  pull_request:
    branches: [claude/*]
  push:
    branches: [claude/*]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run Ruff
        run: ruff check . --output-format=github
      - name: Run Black
        run: black --check .
      - name: Run Isort
        run: isort --check-only .
      - name: Run MyPy (Strict)
        run: mypy domains/ shared/ --strict --show-error-codes

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17-alpine
        env:
          POSTGRES_USER: soleflip
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: soleflip_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run migrations
        run: alembic upgrade head
        env:
          DATABASE_URL: postgresql://soleflip:test_password@localhost:5432/soleflip_test
          FIELD_ENCRYPTION_KEY: test_key_32_bytes_long_padding_here
      - name: Run tests with coverage
        run: |
          pytest --cov=domains --cov=shared --cov-report=xml --cov-report=term-missing --cov-fail-under=80
        env:
          DATABASE_URL: postgresql://soleflip:test_password@localhost:5432/soleflip_test
          REDIS_URL: redis://localhost:6379/0
          FIELD_ENCRYPTION_KEY: test_key_32_bytes_long_padding_here
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Run pip-audit
        run: |
          pip install pip-audit
          pip-audit --require-hashes --desc
      - name: Run Bandit
        run: |
          pip install bandit
          bandit -r domains/ shared/ -f json -o bandit-report.json
```

---

## 📋 REFACTORING CHECKLIST (MASTER)

### Phase 1 Checklist
- [ ] Fix cryptography test blocker
- [ ] Auto-fix ruff linting issues
- [ ] Install type stubs for MyPy
- [ ] Split models.py into 8 domain files
- [ ] Fix MyPy errors in financial_validators.py
- [ ] Fix MyPy errors in password_hasher.py
- [ ] Fix MyPy errors in domain_exceptions.py
- [ ] Document current database schema
- [ ] Generate ER diagram
- [ ] All tests passing (80%+ coverage)

### Phase 2 Checklist
- [ ] Create src/ directory structure
- [ ] Create src/core/ with config, constants, types
- [ ] Move shared/database/ to src/database/
- [ ] Create src/api/ directory
- [ ] Refactor main.py into API factory
- [ ] Create src/api/app.py
- [ ] Create src/api/middleware.py
- [ ] Create src/api/routes.py
- [ ] Squash old migrations (optional, high-risk)
- [ ] Restructure tests to mirror src/
- [ ] Fix remaining MyPy errors
- [ ] Create architecture documentation
- [ ] Zero MyPy errors (strict mode)

### Phase 3 Checklist
- [ ] Rename domains/products/ to domains/catalog/
- [ ] Consolidate multi-platform orders
- [ ] Create base repository abstractions
- [ ] Add comprehensive docstrings
- [ ] Profile and optimize critical endpoints
- [ ] Enhance CI/CD with strict checks
- [ ] Generate API documentation
- [ ] Update README with new structure
- [ ] Final performance benchmarking
- [ ] Celebrate! 🎉

---

## 🎓 LESSONS LEARNED & BEST PRACTICES

### Do's ✅
- **Small, incremental PRs** (<500 lines)
- **Test coverage maintained** throughout (80%+)
- **Backwards compatibility** via re-exports during transitions
- **Comprehensive documentation** updated with each change
- **Stakeholder communication** before breaking changes
- **Staging testing** before production deployment

### Don'ts ❌
- **No "big bang" refactors** (too risky)
- **No skipping tests** ("I'll add them later" = never)
- **No undocumented breaking changes**
- **No migrations without backups**
- **No force-pushing to shared branches**
- **No committing secrets** (use .env, never commit .env)

### Tips 💡
- **Use git worktrees** for parallel work
- **Automate repetitive tasks** (scripts, Make targets)
- **Pair program for complex refactors** (reduces errors)
- **Take breaks** (fresh eyes catch bugs)
- **Celebrate wins** (morale matters!)

---

## 📞 SUPPORT & ESCALATION

### If You Get Stuck:

1. **Review documentation**:
   - This refactoring plan
   - Debugging report
   - CLAUDE.md (project-specific)

2. **Check existing code**:
   - Look for similar patterns in codebase
   - Read tests for expected behavior

3. **Run diagnostics**:
   ```bash
   make check        # Run all quality checks
   make test         # Run test suite
   make env-check    # Verify environment
   ```

4. **Seek help**:
   - Ask team members
   - Create GitHub discussion
   - Consult Claude Code documentation

---

## 📊 SUCCESS METRICS (KPIs)

Track these metrics before, during, and after refactoring:

| Metric | Baseline | Target | Post-Refactor |
|--------|----------|--------|---------------|
| **Lines of Code** | 92,759 | <90,000 | TBD |
| **MyPy Errors** | 24 | 0 | TBD |
| **Ruff Errors** | 10 | 0 | TBD |
| **Test Coverage** | 80%+ | 80%+ | TBD |
| **# of Model Files** | 1 (1,093 lines) | 8 (~150 lines each) | TBD |
| **# of Migrations** | 44 | <20 (post-squash) | TBD |
| **API Response Time (p95)** | TBD | <200ms | TBD |
| **CI/CD Duration** | TBD | <10 min | TBD |
| **Onboarding Time (New Dev)** | TBD | <2 days | TBD |

---

## 🗓️ TIMELINE SUMMARY

| Phase | Duration | Effort | Deliverables |
|-------|----------|--------|--------------|
| **Phase 1** | 4 weeks | 40 hours | Tests passing, models split, MyPy <15 errors |
| **Phase 2** | 4 weeks | 50 hours | src/ structure, main.py refactored, MyPy 0 errors |
| **Phase 3** | 4 weeks | 40 hours | Domains optimized, docs complete, CI enhanced |
| **Total** | **12 weeks** | **130 hours** | Production-ready modular codebase |

**Note**: Timeline assumes part-time work (10-15 hours/week). Full-time dedication would complete in 3-4 weeks.

---

## 🎯 FINAL CHECKLIST

Before marking refactoring as **COMPLETE**:

- [ ] All tests passing (80%+ coverage)
- [ ] Zero MyPy errors (strict mode)
- [ ] Zero Ruff errors
- [ ] Zero Black/Isort errors
- [ ] CI/CD pipeline green
- [ ] Documentation complete and up-to-date
- [ ] ER diagrams generated
- [ ] Architecture docs written
- [ ] Performance benchmarks show <10% regression
- [ ] All PRs merged and closed
- [ ] CHANGELOG.md updated
- [ ] README.md updated with new structure
- [ ] Team trained on new structure
- [ ] Stakeholders notified of completion

---

**Plan End** | Generated by Claude Code Refactoring Planner v1.0
**Next Steps**: Begin Phase 1, Sprint 1, PR #1 (Fix Cryptography Test Blocker)
