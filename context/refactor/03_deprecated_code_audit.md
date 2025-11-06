# Deprecated Code and Technical Debt Audit

**Date**: 2025-11-06
**Scope**: Full codebase scan for deprecated patterns, TODOs, and technical debt

## Summary

- **Deprecated Domains**: 1 (sales domain)
- **TODO Comments**: 11 across 4 domains
- **Deprecated Imports**: 0 (all imports are current)
- **Unused Code**: 1 file identified (transaction_processor.py)

## Deprecated Domain: Sales

**Status**: Active but marked for deprecation
**Action Required**: See `01_sales_domain_deprecation_analysis.md`

```python
# domains/__init__.py:23
- sales: Legacy sales domain (deprecated - use orders instead)
```

**Migration Plan**: Move OrderProcessor to orders domain, remove sales domain after 1-2 release cycles.

## TODO Comments by Domain

### Auth Domain (2 TODOs)
**File**: `domains/auth/api/router.py`

```python
# Line 161
# TODO: Implement with API key authentication

# Line 179
# TODO: Implement with API key authentication
```

**Assessment**: Future feature - API key authentication endpoints
**Priority**: Low (JWT auth is fully functional)
**Action**: Keep as planned enhancement

---

### Orders Domain (1 TODO)
**File**: `domains/orders/services/order_import_service.py`

```python
# Line 199
# TODO: Implement inventory matching logic
```

**Assessment**: Orders should link to inventory items
**Priority**: Medium (functionality works without, but linking would improve tracking)
**Action**: Create ticket for inventory-order linking feature

---

### Inventory Domain (4 TODOs)
**File**: `domains/inventory/api/router.py`

```python
# Line 580
# TODO: Query database for existing product by name or stockx_id

# Line 603
# TODO: Actually create product in database

# Line 630
# TODO: Actually create inventory item in database
```

**Assessment**: Incomplete endpoint implementation (likely stub/placeholder)
**Priority**: High if endpoint is used, Low if it's unused
**Action**: Verify if endpoint is in use, complete or remove

**File**: `domains/inventory/services/inventory_service.py`

```python
# Line 466
# TODO: Fix boolean clause issues in duplicate detection
```

**Assessment**: Known bug in duplicate detection logic
**Priority**: High (data quality issue)
**Action**: Create bug ticket for duplicate detection fix

---

### Integration Domain (4 TODOs)
**File**: `domains/integration/services/quickflip_detection_service.py`

```python
# Line 204
stockx_listing_id=None,  # TODO: Add StockX listing ID when available

# Line 208-209
days_since_last_sale=None,  # TODO: Calculate from transaction history
stockx_demand_score=None   # TODO: Calculate demand score

# Line 300
# TODO: Implement tracking table for acted opportunities
```

**Assessment**: QuickFlip feature enhancements for better opportunity detection
**Priority**: Medium (core feature works, these are enhancements)
**Action**: Enhancement tickets for QuickFlip v2

---

## Deprecated Feature Tracking (Budibase)

**Files**:
- `domains/integration/budibase/services/config_generator.py`
- `domains/integration/budibase/schemas/budibase_models.py`

**Purpose**: Budibase integration tracks deprecated features to warn users

```python
deprecated_features = []
if "selling" in datasource_refs:
    deprecated_features.append("Selling domain references (removed in v2.2.1)")
```

**Assessment**: This is GOOD - proactive deprecation tracking ✅
**Action**: None required (working as intended)

---

## Unused Code Identified

### TransactionProcessor (SAFE TO DELETE)
**File**: `domains/sales/services/transaction_processor.py`
**Size**: 19,168 bytes
**Status**: Not imported anywhere in active code
**Used By**: Only documentation files

**Verification**:
```bash
# No active usage found
grep -r "TransactionProcessor" --include="*.py" domains/ shared/ scripts/
# Only matches: documentation files
```

**Action**: ✅ Safe to delete immediately

```bash
rm domains/sales/services/transaction_processor.py
```

**Rationale**: Superseded by OrderProcessor which uses unified Order model (Gibson Schema v2.4)

---

## Import Analysis

### No Deprecated Imports Found ✅

Scanned for common deprecated patterns:
- ❌ Old SQLAlchemy 1.x patterns (all using 2.0 style)
- ❌ Deprecated FastAPI imports
- ❌ Old Pydantic v1 syntax (using v2)
- ❌ Legacy async patterns

**All imports are current and using modern patterns.**

---

## Code Quality Markers

### FIXME Comments: 0
No FIXME markers found in codebase.

### XXX Comments: 0
No XXX markers found in codebase.

### DEPRECATED Comments: 2
Both are legitimate deprecation tracking (Budibase feature detection).

---

## Structural Improvements Completed

### ✅ Added Missing `__init__.py` Files (30+ files)
- domains/ (root)
- shared/ (root)
- 13 shared subdirectories
- 15+ domain subdirectories

### ✅ Enhanced Empty `__init__.py` Files
- Added docstrings and `__all__` exports
- Improved module discoverability
- Better IDE support and import hints

### ✅ Removed Backup Files
- Deleted `domains/inventory/api/router_backup.py.disabled`

---

## Recommendations

### Immediate Actions (This Sprint)
1. ✅ Delete `transaction_processor.py` (unused, safe)
2. ✅ Add deprecation warning to sales domain `__init__.py`
3. 🔲 Fix duplicate detection bug (inventory_service.py:466)
4. 🔲 Complete or remove stub endpoints (inventory/api/router.py:580, 603, 630)

### Short-term (Next 2 Sprints)
5. 🔲 Implement inventory-order linking (orders/order_import_service.py:199)
6. 🔲 Complete QuickFlip enhancements (4 TODOs)
7. 🔲 Migrate OrderProcessor to orders domain
8. 🔲 Add API key authentication (auth/router.py:161, 179)

### Long-term (Backlog)
9. 🔲 Remove sales domain entirely (after migration complete)
10. 🔲 Expand test coverage (currently ~30%, target 80%+)

---

## Technical Debt Score

| Category | Status | Debt Level |
|----------|--------|------------|
| Deprecated Imports | ✅ Clean | None |
| Unused Code | ⚠️ Minor | Low |
| TODO Comments | ⚠️ Tracked | Medium |
| Code Duplication | ⚠️ Sales/Orders | Medium |
| Test Coverage | 🔴 Low (~30%) | High |
| Documentation | ✅ Good | Low |

**Overall Technical Debt**: **Medium** (improving with refactoring)

---

## Next Steps

1. Run code quality checks (format, lint, type-check)
2. Run comprehensive test suite
3. Delete transaction_processor.py
4. Add deprecation warnings
5. Create enhancement tickets for TODO items

See `04_code_quality_report.md` for quality validation results.
