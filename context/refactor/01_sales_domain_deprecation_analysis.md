# Sales Domain Deprecation Analysis

**Date**: 2025-11-06
**Status**: ACTIVE - Sales domain still in use
**Migration Status**: In Progress

## Executive Summary

The sales domain (`domains/sales/`) is marked as legacy in CLAUDE.md with the note "_mostly replaced by orders/_". However, active usage analysis reveals that the domain is still integrated into critical import processing workflows and **cannot be safely removed** without breaking functionality.

## Current State

### Sales Domain Structure
```
domains/sales/
├── __init__.py (minimal)
└── services/
    ├── __init__.py
    ├── transaction_processor.py (19,168 bytes) - DEPRECATED, creates Transaction records
    └── order_processor.py (19,293 bytes) - ACTIVE, creates Order records
```

### Active Dependencies

**OrderProcessor is imported and used by:**
1. `domains/integration/services/import_processor.py` (Line 20)
   - Core integration service for processing CSV/Excel/JSON imports
   - Creates orders from validated ImportRecord batches

2. `scripts/transactions/create_alias_transactions.py` (Line 12)
   - Script for creating Alias platform transactions
   - Used for data migration and batch processing

### Functional Distinction: Sales vs Orders

| Aspect | Sales Domain (OrderProcessor) | Orders Domain (OrderImportService) |
|--------|------------------------------|-----------------------------------|
| **Purpose** | Batch processing from import system | Direct API imports |
| **Source** | ImportBatch → ImportRecord → Orders | StockX/eBay/GOAT APIs → Orders |
| **Usage** | CSV/Excel import workflows | Real-time platform syncs |
| **Status** | Active but legacy | Current and expanding |
| **Model** | Uses unified `Order` model | Uses unified `Order` model |

Both services write to the same `transactions.orders` table (Gibson Schema v2.4).

## Migration Strategy

### Phase 1: Consolidation (Recommended)
**Goal**: Move OrderProcessor to orders domain where it belongs conceptually

**Steps**:
1. Move `domains/sales/services/order_processor.py` → `domains/orders/services/order_processor.py`
2. Update imports:
   - `domains/integration/services/import_processor.py`
   - `scripts/transactions/create_alias_transactions.py`
3. Add deprecation warning to `domains/sales/__init__.py`
4. Run full test suite to ensure no breakage

**Benefits**:
- Centralizes all order-related logic in orders domain
- Maintains backward compatibility via import path updates
- Clear separation: orders domain owns all order creation logic

### Phase 2: Deprecation Notice
Add deprecation warnings to sales domain:

```python
# domains/sales/__init__.py
"""
Sales Domain (DEPRECATED)
=========================

⚠️ DEPRECATION NOTICE: This domain is deprecated and will be removed in a future version.

The sales domain has been replaced by the orders domain (domains/orders/).

Migration Guide:
- OrderProcessor has moved to domains.orders.services.order_processor
- TransactionProcessor is deprecated (use OrderProcessor instead)

All new development should use the orders domain.
"""

import warnings

warnings.warn(
    "The sales domain is deprecated. Use domains.orders instead.",
    DeprecationWarning,
    stacklevel=2
)
```

### Phase 3: Removal (Future)
**Prerequisites**:
- All import paths updated to use orders domain
- No references to `domains.sales` remain in:
  - Application code (`domains/`, `shared/`)
  - Scripts (`scripts/`)
  - Tests (`tests/`)
- Full test coverage passing

**Timeline**: After 1-2 release cycles with deprecation warnings

## Transaction Processor Status

### transaction_processor.py
- **Size**: 19,168 bytes (similar to order_processor.py)
- **Status**: DEPRECATED (superseded by OrderProcessor)
- **Model**: Used old `Transaction` model (now unified with Order)
- **Action**: Can be removed immediately if not used

**Verification needed**: Check for any references to `TransactionProcessor`

```bash
# Search for TransactionProcessor usage
grep -r "TransactionProcessor" --include="*.py" domains/ shared/ scripts/
```

If no matches, delete `transaction_processor.py` immediately.

## Recommendations

### Immediate Actions (Low Risk)
1. ✅ Add deprecation warning to `domains/sales/__init__.py`
2. ✅ Document migration path in CLAUDE.md
3. ✅ Verify TransactionProcessor is unused and delete if safe

### Short-term (Next Sprint)
4. Move OrderProcessor to orders domain
5. Update all imports to point to new location
6. Add integration tests for OrderProcessor in orders domain
7. Update API documentation

### Long-term (2-3 sprints)
8. Monitor deprecation warnings in logs
9. Confirm zero usage of legacy import paths
10. Remove sales domain entirely
11. Update git history documentation

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking imports during move | HIGH | Thorough grep search, comprehensive testing |
| Import processor failure | CRITICAL | Staged rollout, maintain backward compatibility |
| Script breakage | MEDIUM | Update scripts first, test batch processing |
| Hidden dependencies | MEDIUM | Search entire codebase including tests |

## Testing Checklist

Before removing sales domain:
- [ ] All unit tests pass
- [ ] Integration tests for order import pass
- [ ] CSV/Excel import workflow tested end-to-end
- [ ] StockX API import tested
- [ ] eBay import tested
- [ ] GOAT import tested
- [ ] Alias batch processing tested
- [ ] No references to `domains.sales` in codebase
- [ ] Deprecation warnings monitored for 2 release cycles

## Conclusion

The sales domain **cannot be removed immediately**. It contains active, critical functionality (OrderProcessor) that must be migrated to the orders domain first. The recommended approach is:

1. **Now**: Add deprecation warnings and documentation
2. **Next sprint**: Move OrderProcessor to orders domain
3. **Future**: Remove sales domain after confirmation of zero usage

TransactionProcessor can likely be removed immediately after verification check.

---

**Next Steps**: See `02_orders_domain_enhancement_plan.md` for detailed migration steps.
