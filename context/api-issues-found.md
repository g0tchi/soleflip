# API Issues Found - Functional Testing Report

**Date:** 2025-10-09
**Version:** 2.2.5
**Test Session:** Post JWT-Auth Removal

## Critical Issues Found

### 1. Dashboard Metrics Endpoint - Database Schema Mismatch

**Endpoint:** `GET /api/v1/dashboard/metrics`
**Status:** ❌ HTTP 500 Error
**Error:** `relation "sales.transactions" does not exist`

**Root Cause:**
The dashboard query references `sales.transactions`, but the actual table is `transactions.transactions` (in the `transactions` schema, not `sales`).

**Location:** `domains/dashboard/api/router.py:170`

**SQL Query Problem:**
```sql
SELECT ... FROM sales.transactions t  -- ❌ Wrong schema
```

**Should be:**
```sql
SELECT ... FROM transactions.transactions t  -- ✅ Correct schema
```

**Impact:** Dashboard metrics completely broken

**Fix Priority:** 🔴 HIGH - Dashboard is a core feature

**Affected Code:**
- `domains/dashboard/api/router.py` - Dashboard metrics query
- Multiple CTEs (Common Table Expressions) reference wrong schema

---

### 2. Inventory Items Endpoint - Missing Column

**Endpoint:** `GET /api/v1/inventory/items`
**Status:** ❌ HTTP 500 Error
**Error:** `column inventory.sale_overview does not exist`

**Root Cause:**
SQLAlchemy model `InventoryItem` in `shared/database/models.py` defines a `sale_overview` column that doesn't exist in the database.

**Location:** `shared/database/models.py:347`

**Model Definition:**
```python
class InventoryItem(Base, TimestampMixin):
    # ...
    sale_overview = Column(Text, nullable=True)  # ❌ Column doesn't exist in DB
```

**Impact:** Cannot list inventory items - critical business function

**Fix Priority:** 🔴 HIGH - Inventory management is core functionality

**Options:**
1. Create migration to add `sale_overview` column
2. Remove `sale_overview` from model if not needed
3. Make column optional in queries

---

### 3. StockX Listings Connection Error

**Endpoint:** `GET /api/v1/inventory/stockx-listings`
**Status:** ⚠️ Connection Failed (Graceful Handling)
**Error:** `[Errno 10060] Connect call failed ('192.168.2.45', 2665)`

**Root Cause:**
Attempting to connect to internal IP `192.168.2.45:2665` - likely a proxy or SSH tunnel that's not running.

**Impact:** StockX listings cannot be fetched from API, but error is handled gracefully with empty results.

**Response:**
```json
{
    "success": true,
    "message": "StockX API unavailable, showing empty results",
    "data": {
        "listings": [],
        "count": 0,
        "error": "[Errno 10060] Connect call failed ('192.168.2.45', 2665)"
    }
}
```

**Fix Priority:** 🟡 MEDIUM - Graceful degradation works, but feature unavailable

**Action Required:**
- Verify proxy/tunnel configuration
- Check if `192.168.2.45:2665` is correct IP:port
- Ensure SSH tunnel or proxy is running

---

### 4. StockX Order History - Required Parameters

**Endpoint:** `GET /api/v1/orders/stockx-history`
**Status:** ⚠️ Validation Error (Expected)
**Error:** `Field required: fromDate, toDate`

**Root Cause:**
Endpoint requires date range parameters but none were provided in initial test.

**Working Test:**
```bash
curl "http://localhost:8000/api/v1/orders/stockx-history?fromDate=2025-10-01&toDate=2025-10-09"
```

**Result:** ✅ Returns empty array `[]` (no historical data in date range)

**Impact:** None - working as designed

**Fix Priority:** ✅ No action needed - proper validation

---

## Performance Alerts

### 1. High Memory Usage

**Alert:** `Memory usage exceeded 85%`
**Current:** 89.0%
**Threshold:** 85%
**Severity:** 🔴 CRITICAL

**Monitoring Data:**
```json
{
    "cpu_percent": 46.7,
    "memory_percent": 89.0,
    "disk_percent": 72.9
}
```

**Impact:** System close to memory limit, may cause performance degradation

**Recommendations:**
1. Monitor memory leaks
2. Check for unclosed database connections
3. Review caching strategies
4. Consider increasing available RAM

---

### 2. High Error Rate

**Alert:** `Error rate exceeded 10%`
**Cause:** Multiple 500 errors from dashboard and inventory endpoints

**Impact:** Overall API health score affected (93.4)

**Fix:** Resolve database schema issues above

---

### 3. Slow Request Times

**Alerts Generated:**
- `/api/v1/inventory/stockx-listings` - 40,194ms (40 seconds!)
- `/api/v1/orders/stockx-history` - 18,078ms (18 seconds)

**Cause:** Connection timeouts to StockX API proxy (192.168.2.45:2665)

**Impact:** Poor user experience, potential timeouts

**Fix Priority:** 🔴 HIGH - 40 second response time unacceptable

---

## Working Endpoints ✅

### Fully Operational

1. **Health Check**
   - `GET /health` ✅
   - Health Score: 93.4
   - All components healthy

2. **StockX Active Orders**
   - `GET /api/v1/orders/active` ✅
   - Successfully returns 2 active orders
   - OAuth2 refresh token working

3. **StockX Credentials Management**
   - `GET /api/v1/integration/stockx/credentials/status` ✅
   - All 4 credentials encrypted and accessible
   - `POST /api/v1/integration/stockx/credentials/update-timestamps` ✅

4. **Supplier Intelligence**
   - `GET /api/suppliers/intelligence/health` ✅
   - All features operational

5. **Budibase Integration**
   - `GET /api/v1/budibase/health` ✅
   - Module version 2.2.1 active

---

## Database Schema Analysis Required

Created diagnostic script: `scripts/database/check_schema_issues.sql`

**Script will check:**
1. Existence of `sales.transactions` vs `transactions.transactions`
2. All columns in `products.inventory` table
3. Whether `sale_overview` column exists
4. All available schemas

---

## Recommended Fixes

### Priority 1 - Database Schema Issues

#### Fix 1: Dashboard Metrics Schema
**File:** `domains/dashboard/api/router.py`

**Change all occurrences:**
```python
# OLD
FROM sales.transactions t

# NEW
FROM transactions.transactions t
```

**Affected Queries:**
- Line ~150-250 (main dashboard metrics query)
- All CTEs: `sales_summary`, `top_brands`, `recent_activity`

---

#### Fix 2: Inventory sale_overview Column

**Option A: Add Migration** (if column is needed)
```python
# alembic/versions/XXXX_add_sale_overview.py
def upgrade():
    op.add_column('inventory',
        sa.Column('sale_overview', sa.Text(), nullable=True),
        schema='products'
    )
```

**Option B: Remove from Model** (if column not needed)
```python
# shared/database/models.py:347
# Remove this line:
# sale_overview = Column(Text, nullable=True)
```

**Recommendation:** Check Notion sync requirements first - `sale_overview` was added for Notion feature parity.

---

### Priority 2 - StockX Proxy Configuration

**File:** Check StockX service configuration

**Action Items:**
1. Verify proxy IP: `192.168.2.45:2665`
2. Ensure SSH tunnel or proxy is running
3. Update connection timeout settings
4. Add retry logic with exponential backoff

---

### Priority 3 - Performance Optimization

1. **Memory:**
   - Review database connection pooling
   - Check for memory leaks in long-running requests
   - Monitor Redis cache usage

2. **Request Timeouts:**
   - Reduce StockX API timeout from 40s to 10s max
   - Implement async request patterns
   - Add request queueing for high-volume calls

---

## Testing Summary

**Total Endpoints Tested:** 15
**Working:** 8 ✅
**Schema Errors:** 2 ❌
**Connection Errors:** 3 ⚠️
**Validation Errors:** 2 (expected)

**Success Rate:** 53% (8/15)

**Critical Path Working:**
- ✅ Health monitoring
- ✅ StockX OAuth2 authentication
- ✅ Active orders retrieval
- ❌ Dashboard metrics
- ❌ Inventory management

---

## Next Steps

1. **Immediate (Today):**
   - Run `scripts/database/check_schema_issues.sql`
   - Fix dashboard schema references (15 min)
   - Decide on `sale_overview` column (5 min)

2. **Short Term (This Week):**
   - Create database migration if needed
   - Fix StockX proxy configuration
   - Add request timeout optimizations

3. **Medium Term (Next Sprint):**
   - Comprehensive endpoint testing
   - Load testing with realistic data
   - Memory profiling and optimization

---

## Conclusion

The API is partially functional after JWT removal:
- ✅ Core authentication and health checks work
- ✅ StockX integration operational for active orders
- ❌ Dashboard and inventory endpoints broken due to database schema mismatches
- ⚠️ Performance concerns (memory, slow requests)

**Estimated Fix Time:** 2-4 hours for critical issues

**Risk Level:** 🟡 MEDIUM
- Core business function (active orders) works
- Dashboard and inventory need immediate attention
- No data loss risk, only feature unavailability

---

**Report Generated:** 2025-10-09T05:00:00Z
**Tested By:** Claude Code
**Environment:** Development (localhost:8000)
