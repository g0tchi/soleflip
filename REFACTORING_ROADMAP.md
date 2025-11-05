# SoleFlipper Refactoring Roadmap

## Critical Issues (Immediate Action Required)

### 1. Inventory Service - CRITICAL (1,711 lines)
**File**: `domains/inventory/services/inventory_service.py`

**Issues**:
- Monolithic service with 50+ methods
- Multiple responsibilities: stats, search, CRUD, predictions
- Difficult to test individual features
- High cognitive complexity

**Recommended Split**:
```
inventory_service.py (core CRUD)
├── stats_service.py (inventory aggregations)
├── search_service.py (filtering/pagination)
├── duplicate_detection_service.py (duplicate logic)
└── product_service.py (product-related ops)
```

**Effort**: 4-5 days
**Tests to update**: 12 test files
**Risk**: Medium (high test coverage helps)

---

### 2. CLI Main Module (1,275 lines)
**File**: `cli/cli.py`

**Issues**:
- All CLI commands in single file
- Import side effects
- Difficult to maintain
- Hard to test individual commands

**Recommended Split**:
```
cli/
├── cli.py (entry point, dispatcher only)
├── integration_cli.py (import, sync commands)
├── inventory_cli.py (inventory commands)
├── pricing_cli.py (pricing commands)
├── products_cli.py (product commands)
└── database_cli.py (database commands)
```

**Effort**: 3-4 days
**Tests to create**: 5-6 new test files
**Risk**: Low (CLI changes rarely break production)

---

### 3. Integration API Router (983 lines)
**File**: `domains/integration/api/router.py`

**Issues**:
- 35+ endpoints in single router
- Mixed concerns: webhooks, uploads, imports
- Hard to maintain endpoint consistency
- Response format inconsistency

**Recommended Split**:
```
integration/api/
├── router.py (dispatcher, main endpoints)
├── stockx_router.py (StockX sync endpoints)
├── import_router.py (import operations)
├── webhooks_router.py (webhook handlers)
└── upload_router.py (file upload endpoints)
```

**Effort**: 2-3 days
**Tests to update**: 8 integration test files
**Risk**: Medium (API changes need careful testing)

---

### 4. Database Models (967 lines)
**File**: `shared/database/models.py`

**Issues**:
- 15+ model definitions in single file
- Models from 6 different schemas
- Relationships getting complex
- Hard to find specific models

**Recommended Split Option A (by schema)**:
```
shared/database/
├── catalog_models.py (Brand, Product, Category, Size)
├── transactions_models.py (Transaction, Order)
├── supplier_models.py (Supplier, Account)
├── analytics_models.py (Forecast, Demand)
└── core_models.py (User, Settings)
```

**Or Option B (by domain)**:
```
shared/database/
├── product_models.py (Brand, Product, Category)
├── inventory_models.py (InventoryItem)
├── transaction_models.py (Transaction, Order)
├── supplier_models.py (Supplier)
└── analytics_models.py (Forecast, Demand)
```

**Effort**: 2-3 days
**Tests to update**: All tests importing models (significant)
**Risk**: High (widespread imports require careful refactoring)

---

## High Priority Issues (Week 2-3)

### 5. Predictive Insights Service (940 lines)
**File**: `domains/inventory/services/predictive_insights_service.py`

**Issues**:
- Complex ML/analytics logic
- Multiple algorithms mixed
- Hard to test individual predictions
- Tight coupling with inventory service

**Recommended Split**:
```
domains/inventory/services/
├── predictive_insights_service.py (coordinator)
├── demand_predictor.py (demand forecasting)
├── trend_analyzer.py (trend analysis)
└── anomaly_detector.py (outlier detection)
```

**Effort**: 3-4 days
**Tests to update**: 5 test files
**Risk**: Medium (need to validate prediction accuracy)

---

### 6. StockX Catalog Service (811 lines)
**File**: `domains/integration/services/stockx_catalog_service.py`

**Issues**:
- External API integration logic
- Data transformation logic mixed
- Error handling scattered
- Cache invalidation logic embedded

**Recommended Split**:
```
domains/integration/services/
├── stockx_catalog_service.py (coordinator)
├── stockx_client_wrapper.py (API calls)
├── catalog_transformer.py (data mapping)
└── catalog_cache.py (caching logic)
```

**Effort**: 2-3 days
**Tests to update**: 4 test files
**Risk**: Medium (external service dependency)

---

### 7. Transformers Module (738 lines)
**File**: `domains/integration/services/transformers.py`

**Issues**:
- Generic transformation functions
- Hard to test individual transformations
- No clear responsibility separation
- Duplication with other transform logic

**Recommended Split**:
```
domains/integration/services/transformers/
├── __init__.py (exports)
├── product_transformer.py
├── inventory_transformer.py
├── order_transformer.py
├── marketplace_transformer.py
└── data_mapper.py (utilities)
```

**Effort**: 2-3 days
**Tests to update**: 6 test files
**Risk**: Low (transformers are generally isolated)

---

## Medium Priority Issues (Month 2)

### 8. Consolidate Repository Pattern
**Files**: 
- `domains/pricing/repositories/pricing_repository.py`
- `domains/analytics/repositories/forecast_repository.py`

**Issues**:
- Some repositories don't follow BaseRepository[T] pattern
- Custom implementations instead of generic
- Inconsistent query patterns

**Solution**:
```python
# Convert to generic pattern
class PricingRepository(BaseRepository[Price]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(Price, db_session)
    
    # Add domain-specific methods only

class ForecastRepository(BaseRepository[SalesForecast]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(SalesForecast, db_session)
```

**Effort**: 1-2 days
**Tests to update**: 3-4 test files
**Risk**: Low

---

### 9. Extract Common Response Patterns
**Files**: All routers (33 files)

**Issues**:
- Response formatting repeated
- ErrorContext usage inconsistent
- Exception handling patterns vary
- StatusCode handling scattered

**Solution**:
```python
# Create decorators for common patterns
@response_handler
@error_context("create", "inventory_item")
async def create_item(...):
    pass

@response_handler
@paginate_response
async def list_items(...):
    pass
```

**Effort**: 2-3 days
**Tests to update**: 10+ test files
**Risk**: Low

---

### 10. Event System Activation
**Current Status**: "Not actively used" in coverage exclusions

**Issues**:
- Implemented but not utilized
- Loose coupling opportunity missed
- Event handlers exist but not triggered
- Test coverage excluded

**Solution**:
1. Identify business events to emit
2. Connect event publishers to services
3. Ensure event handlers are called
4. Add test coverage
5. Document event schema

**Effort**: 4-5 days
**Risk**: Medium (behavior changes)

---

## Code Duplication Issues (Ongoing)

### 11. Service-Level Validation Logic
**Problem**: Validation repeated across services

**Solution**:
```python
# Create shared validators
from shared.validation.service_validators import validate_inventory_item_creation

# Use in all services
async def create_item(self, request: CreateItemRequest):
    await validate_inventory_item_creation(request)
    # Create item
```

**Files to Review**: 15+ service files
**Effort**: 2-3 days

---

### 12. Database Query Patterns
**Problem**: Complex queries duplicated in multiple repositories

**Solution**:
```python
# Create query builders
from shared.database.query_builders import InventoryQueryBuilder

builder = InventoryQueryBuilder()
query = builder.with_product_details().with_status("in_stock").build()
```

**Files to Review**: 8+ repository files
**Effort**: 2-3 days

---

### 13. Data Transformation Logic
**Problem**: Transform functions scattered across transformers.py, services, and utilities

**Solution**:
- Consolidate to `domains/integration/services/transformers/`
- Create domain-specific transformer classes
- Remove duplicate transforms from services

**Effort**: 1-2 days

---

## Testing Improvements

### 14. Increase Coverage for Event System
**Current**: Excluded from coverage
**Target**: 80%+
**Files**: 3 handler modules

**Effort**: 1-2 days
**Risk**: Low

---

### 15. Add Integration Tests for Large Services
**Services Needing Tests**:
- `inventory_service.py` (esp. after split)
- `stockx_catalog_service.py`
- `forecast_engine.py`

**Target**: +5-10% overall coverage
**Effort**: 3-4 days

---

## Documentation Tasks

### 16. Create Architectural Diagrams
**Missing**:
- Domain interaction diagram
- Data flow diagram
- Event flow diagram
- API architecture diagram

**Effort**: 1-2 days

---

### 17. Document Event Schema
**Missing**:
- Event type definitions
- Event payload examples
- Event subscriber guide

**Effort**: 1 day

---

### 18. Create Refactoring Guide
**Contents**:
- How to split files
- Testing strategy during refactoring
- Checklist for completion
- Common pitfalls

**Effort**: 1-2 days

---

## Cleanup Tasks

### 19. Resolve TODO Comments
**Found**: 8 TODO items

**Examples**:
- "Fix boolean clause issues in duplicate detection" (inventory_service.py)
- "Implement API key authentication" (auth/router.py, 2x)
- "Implement inventory matching logic" (order_import_service.py)

**Action**: 
1. Create GitHub issues for each
2. Prioritize by impact
3. Schedule implementation

**Effort**: 1 day (to create issues)

---

### 20. Remove Legacy Code
**Legacy Components**:
- Sales domain (mostly replaced by orders)
- Admin router (disabled for security)
- Business Intelligence router (disabled)

**Action**:
1. Verify all functionality moved
2. Migrate tests if applicable
3. Remove old code
4. Update documentation

**Effort**: 1-2 days

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- **Priority**: Blocks other refactoring
- **Files**: inventory_service, models
- **Effort**: 6-8 days
- **Deliverable**: Split services working with all tests passing

### Phase 2: API Layer (Week 3)
- **Priority**: Improves maintainability
- **Files**: routers, CLI
- **Effort**: 5-7 days
- **Deliverable**: Modular routers with consistent response formats

### Phase 3: Services & Repositories (Week 4)
- **Priority**: Consistency
- **Files**: services, repositories
- **Effort**: 4-5 days
- **Deliverable**: Generic repository pattern throughout

### Phase 4: Event System & Testing (Week 5-6)
- **Priority**: Features & Coverage
- **Effort**: 5-6 days
- **Deliverable**: Active event system with 85%+ coverage

### Phase 5: Documentation & Cleanup (Ongoing)
- **Priority**: Maintenance
- **Effort**: 3-4 days
- **Deliverable**: Complete documentation, resolved TODO items

---

## Success Metrics

### Code Quality
- [ ] All files < 500 lines (except models.py split)
- [ ] Largest file: 500-600 lines max
- [ ] Cyclomatic complexity < 10 per function
- [ ] Test coverage: 85%+

### Architecture
- [ ] Single responsibility per class/module
- [ ] Clear domain boundaries
- [ ] No circular dependencies
- [ ] Consistent patterns across domains

### Maintainability
- [ ] No TODO comments
- [ ] All code documented
- [ ] Clear refactoring guide
- [ ] Event system active

---

## Risk Mitigation

### Testing Strategy
1. Run full test suite before each major change
2. Create feature branch per refactoring
3. Keep commits small and focused
4. Review each PR with 2+ team members

### Rollback Plan
1. Tag stable version before refactoring
2. Keep main branch green always
3. Quick rollback procedures documented
4. Staging environment testing before merge

### Validation
1. Compare behavior before/after with integration tests
2. Performance benchmarking for large services
3. Monitor production metrics post-deployment
4. Gradual rollout (canary deployment)

