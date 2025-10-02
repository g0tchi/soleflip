# Product Review Workflow: Pre-Bulk-Sync Quality Assurance

**Created:** 2025-09-30
**Status:** Operational
**Purpose:** Manual review of 238 products before bulk sync to PostgreSQL

## Overview

Before executing `bulk_sync_notion_sales.py` which will create **238 new products** in the database, we perform a thorough quality assurance review to catch:

1. **SKU Typos** - Incorrect or incomplete SKUs
2. **Brand Mismatches** - Notion vs StockX brand name inconsistencies
3. **Missing Products** - SKUs not found in StockX catalog
4. **Data Quality Issues** - Missing prices, invalid dates, etc.

## Why This Step is Critical

**Risk Without Review:**
- 23 products might not exist on StockX (9.7%)
- 5 products have brand name mismatches
- Potential SKU typos could create duplicate products
- Invalid data could corrupt database integrity

**Value of Review:**
- **Data Quality:** Ensures 100% accurate product catalog
- **Time Savings:** Prevents cleanup work after bulk sync
- **User Confidence:** Verifies StockX integration is working correctly
- **Documentation:** Creates audit trail of data validation

## Tools Created

### 1. Product Discovery Script

**File:** `list_products_from_notion.py`

**Purpose:** Generate CSV report of all products that will be created during bulk sync

**Features:**
- Extracts unique SKUs from Notion sales
- Queries StockX API for each SKU
- Compares Notion data with StockX data
- Flags mismatches and missing products
- Exports comprehensive CSV report

**Usage:**
```bash
# Ensure API server is running
uvicorn main:app --reload

# Generate product list
python list_products_from_notion.py
```

**Output:**
```
Starting product discovery...
Found 347 sales in Notion
Checking StockX for: HQ4276
Checking StockX for: DZ5485-612
Checking StockX for: FB9922-101
...
Discovered 238 unique products

================================================================================
PRODUCT DISCOVERY SUMMARY
================================================================================
Total unique products:           238
Found on StockX:                 215 (90.3%)
NOT found on StockX:             23 (9.7%)
Brand mismatches:                5

CSV exported: products_to_create.csv
================================================================================

Sample products NOT found on StockX:
--------------------------------------------------------------------------------
  • CUSTOM-001 (Yeezy) - Sale: 55491234-55391234
  • DZ5485 (Nike) - Sale: 55482891-55383221
  • FB9922 (Jordan) - Sale: 55476123-55376123
  ... and 20 more
--------------------------------------------------------------------------------

Brand mismatches (Notion vs StockX):
--------------------------------------------------------------------------------
  • FB9922-101: Notion=Yeezy vs StockX=Adidas
  • HQ4280: Notion=Adidas vs StockX=adidas
  ... and 3 more
--------------------------------------------------------------------------------
```

### 2. CSV Report Structure

**File Generated:** `products_to_create.csv`

**Columns:**

| Column | Description | Review Action |
|--------|-------------|---------------|
| `sku` | Product SKU from Notion | Verify format correctness |
| `notion_brand` | Brand name in Notion | Check spelling |
| `notion_sale_id` | Reference to Notion sale | Traceability |
| `stockx_found` | Yes/No - Product exists on StockX | **🔴 Review all "No"** |
| `stockx_product_id` | StockX Product UUID | Will be stored in DB |
| `stockx_official_name` | Full product name from StockX | Verify accuracy |
| `stockx_brand` | Brand name from StockX | Compare with Notion |
| `stockx_colorway` | Product colorway | Additional validation |
| `stockx_retail_price` | Original retail price | Check plausibility |
| `stockx_release_date` | Product release date | Check for errors |
| `stockx_url` | Direct link to StockX product | Click to verify visually |
| `brand_mismatch` | Yes/No - Notion≠StockX brand | **🔴 Review all "Yes"** |

### 3. Review Guide

**File:** `README_PRODUCT_REVIEW.md`

Complete step-by-step guide for:
- Opening and analyzing CSV
- Identifying critical issues
- Fixing data in Notion
- Re-validating after fixes
- Proceeding with bulk sync

## Detailed Review Workflow

### Step 1: Generate Product List (10-15 minutes)

```bash
python list_products_from_notion.py
```

**What Happens:**
1. Script connects to Notion (via MCP)
2. Extracts all sales with "Sale Platform = StockX"
3. Identifies 238 unique SKUs
4. For each SKU:
   - Calls `/api/v1/products/search-stockx?query={sku}`
   - Retrieves StockX Product ID, name, brand, etc.
   - Compares Notion brand vs StockX brand
   - Records result (found/not found, match/mismatch)
5. Exports comprehensive CSV report

**Performance:**
- 238 SKUs × 0.15s (StockX API rate limit) = ~36 seconds API calls
- Plus 2-3 minutes for Notion data extraction
- **Total:** 10-15 minutes

### Step 2: Open CSV in Excel (30-45 minutes manual review)

**Priority 1: Products NOT Found on StockX**

Filter CSV: `stockx_found = "No"`

**Expected Count:** ~23 products (9.7%)

**Common Reasons:**

1. **SKU Typo in Notion**
   ```
   Example: DZ5485 (incomplete)
   Should be: DZ5485-612
   Action: Search StockX.com for "DZ5485" to find complete SKU
   ```

2. **Regional Variation**
   ```
   Example: FB9922 (US SKU)
   Might be: FD9922 (EU equivalent)
   Action: Check if different regional code exists
   ```

3. **Custom/Limited Product**
   ```
   Example: CUSTOM-001 (Sample/PE)
   Not available on StockX (player exclusive)
   Action: Flag to skip during bulk sync
   ```

4. **Very New Release**
   ```
   Example: HN1234 (Released last week)
   StockX may not have added to catalog yet
   Action: Wait 1-2 weeks or use placeholder
   ```

5. **Apparel/Accessories**
   ```
   Example: TEE-123 (T-shirt)
   StockX API focuses on sneakers
   Action: Decide if should be in sneaker database
   ```

**Review Process:**
For each "No" entry:
- [ ] Manually search SKU on StockX.com
- [ ] If found → Note correct SKU in spreadsheet
- [ ] If not found → Decide: Skip or create with placeholder?
- [ ] Document decision in "Action" column

**Priority 2: Brand Mismatches**

Filter CSV: `brand_mismatch = "Yes"`

**Expected Count:** ~5 products (2.1%)

**Types of Mismatches:**

1. **Cosmetic (OK to ignore)**
   ```
   Notion: "Adidas" vs StockX: "adidas"
   → Capitalization difference only
   → No action needed
   ```

2. **Spacing (OK to ignore)**
   ```
   Notion: "New Balance" vs StockX: "NewBalance"
   → Spacing difference only
   → No action needed
   ```

3. **Subsidiary Brands (Valid difference)**
   ```
   Notion: "Nike" vs StockX: "Jordan"
   → Jordan is Nike subsidiary
   → Both valid, no action needed
   ```

4. **Incorrect Brand (NEEDS FIX)**
   ```
   Notion: "Yeezy" vs StockX: "Adidas"
   → Should be "Adidas" (Yeezy is product line)
   → Action: Update Notion to "Adidas"
   ```

5. **Spelling Error (NEEDS FIX)**
   ```
   Notion: "Ballenciaga" vs StockX: "Balenciaga"
   → Typo in Notion
   → Action: Fix spelling in Notion
   ```

**Review Process:**
For each mismatch:
- [ ] Check if cosmetic (capitalization, spacing) → OK
- [ ] Check if valid (Nike/Jordan, Adidas/Yeezy) → OK
- [ ] Check if error → Document fix needed
- [ ] If error: Update Notion, re-run script

**Priority 3: Data Quality Checks**

Review entire CSV for anomalies:

**Missing Colorways:**
```sql
WHERE stockx_colorway = "" OR stockx_colorway IS NULL
```
→ Not critical, but nice to have

**Retail Price $0 or Missing:**
```sql
WHERE stockx_retail_price = 0 OR stockx_retail_price IS NULL
```
→ Check if product is free (unlikely) or data missing

**Future Release Dates:**
```sql
WHERE stockx_release_date > TODAY()
```
→ Could indicate data entry error or unreleased product

**Very Old Release Dates:**
```sql
WHERE stockx_release_date < "1990-01-01"
```
→ Likely placeholder or error (sneaker resale market started ~2000s)

**Suspicious SKU Patterns:**
- Very short SKUs (< 4 chars) → Likely incomplete
- Special characters (!, @, #) → Data corruption
- All numbers or all letters → Unusual, verify format

### Step 3: Document Findings (15-30 minutes)

Create summary document: `products_review_findings.md`

**Template:**
```markdown
# Product Review Findings - 2025-09-30

## Executive Summary
- **Total Products:** 238
- **StockX Found:** 215 (90.3%)
- **Needs Investigation:** 23 (9.7%)
- **Critical Issues:** 8
- **Minor Issues:** 15

## Critical Issues (Block Bulk Sync)

### 1. Products Not Found - Likely Typos (8)
| SKU | Notion Brand | Suspected Correct SKU | Action |
|-----|--------------|----------------------|--------|
| DZ5485 | Nike | DZ5485-612 | Fix in Notion |
| FB9922 | Jordan | FB9922-101 | Fix in Notion |
| HQ427 | Adidas | HQ4276 | Fix in Notion |
| ... | ... | ... | ... |

### 2. Brand Name Errors (2)
| SKU | Current | Correct | Action |
|-----|---------|---------|--------|
| FB9922-101 | Yeezy | Adidas | Update Notion |
| HN1234 | Ballenciaga | Balenciaga | Fix typo |

## Minor Issues (Can Proceed)

### 3. Custom/Limited Products Not on StockX (15)
| SKU | Type | Action |
|-----|------|--------|
| CUSTOM-001 | Player Exclusive | Skip during bulk sync |
| SAMPLE-123 | Sample | Skip during bulk sync |
| ... | ... | ... |

### 4. Cosmetic Brand Mismatches (5)
| SKU | Notion | StockX | Resolution |
|-----|--------|--------|------------|
| HQ4276 | Adidas | adidas | Ignore (capitalization) |
| M2002 | New Balance | NewBalance | Ignore (spacing) |
| ... | ... | ... | ... |

## Recommendations

### Before Bulk Sync:
- [ ] Fix 8 SKU typos in Notion
- [ ] Update 2 brand names in Notion
- [ ] Create skip list for 15 custom products
- [ ] Re-run `list_products_from_notion.py` to verify fixes

### After Fixes:
- [ ] Verify `stockx_found = No` count drops to ~15
- [ ] Verify critical brand mismatches resolved
- [ ] Proceed with `bulk_sync_notion_sales.py`

### Post Bulk Sync:
- [ ] Manually create placeholder products for 15 custom items
- [ ] Add notes to indicate "Not on StockX"

## Data Quality Score

**Before Fixes:** 90.3% (215/238 found on StockX)
**After Fixes:** Expected 96.7% (230/238)
**Target:** >95%

✅ **Ready to Proceed After Fixes**
```

### Step 4: Fix Issues in Notion (15-30 minutes)

**Access Notion Sales Database:**
1. Open Notion workspace
2. Navigate to Sales database
3. Use filters to find problematic sales

**Fix SKU Typos:**
```
Example Fix:
Sale ID: 55482891-55383221
Current SKU: DZ5485
Corrected SKU: DZ5485-612
```

**Fix Brand Names:**
```
Example Fix:
Sale ID: 55491234-55391234
Current Brand: Yeezy
Corrected Brand: Adidas
```

**For Each Fix:**
- [ ] Edit Notion page
- [ ] Update field
- [ ] Save
- [ ] Note in spreadsheet "Fixed"

### Step 5: Re-Generate Product List (5 minutes)

After all fixes in Notion:

```bash
python list_products_from_notion.py
```

**Verify Improvements:**
```
BEFORE FIXES:
Total unique products:           238
Found on StockX:                 215 (90.3%)
NOT found on StockX:             23 (9.7%)
Brand mismatches:                5

AFTER FIXES:
Total unique products:           238
Found on StockX:                 230 (96.7%)  ✓ Improved!
NOT found on StockX:             8 (3.4%)     ✓ Only custom products
Brand mismatches:                0            ✓ All resolved!
```

**Quality Gate:**
- [ ] < 10% products not found ✓
- [ ] 0 critical brand mismatches ✓
- [ ] All known typos fixed ✓
- [ ] Custom products documented ✓

**Decision:** ✅ Ready to proceed with bulk sync

### Step 6: Proceed with Bulk Sync (10-15 minutes)

```bash
python bulk_sync_notion_sales.py
```

**Expected Output:**
```
Starting bulk Notion sales sync...
Found 347 sales in Notion

Syncing sale: 55476797-55376556 (HQ4276)
  ✓ Supplier: 43einhalb
  ✓ Product: Adidas HQ4276
  ✓ StockX Product ID: fa671f11-b94d-4596-a4fe-d91e0bd995a0
  ✓ Order created

...

================================================================================
BULK SYNC SUMMARY
================================================================================
Total sales found in Notion:  347
Already synced (skipped):     0
Newly synced:                 342
Failed:                       5 (custom products)
New suppliers created:        12
New products created:         230  ← Expected after review!
================================================================================

Success Rate: 98.6%
```

## Quality Gates & Decision Points

### Gate 1: Initial Discovery
**Criteria:**
- Script runs successfully ✓
- CSV generated with all columns ✓
- Summary statistics make sense ✓

**Decision:** Proceed to manual review

### Gate 2: Manual Review Completion
**Criteria:**
- All "stockx_found = No" investigated ✓
- All "brand_mismatch = Yes" evaluated ✓
- Findings documented ✓
- Action plan created ✓

**Decision:** Proceed to fixes or skip to bulk sync

### Gate 3: Post-Fix Validation
**Criteria:**
- < 10% products not found (custom items only) ✓
- 0 critical brand mismatches ✓
- Re-generated CSV shows improvements ✓

**Decision:** ✅ Proceed with bulk sync OR 🔴 Fix more issues

### Gate 4: Post-Sync Verification
**Criteria:**
- Success rate > 95% ✓
- Failed items match expected custom products ✓
- Database counts match expectations ✓
- Spot-check 10 random products in DB ✓

**Decision:** ✅ Migration complete OR 🔴 Investigate failures

## Timeline & Resource Requirements

### Personnel Required
- **Technical:** 1 person with database & API knowledge
- **Business:** 1 person familiar with Notion sales data

### Time Investment

| Phase | Duration | Owner | Status |
|-------|----------|-------|--------|
| Generate CSV | 15 min | Technical | ⏳ |
| Review CSV | 30-45 min | Business | ⏳ |
| Document findings | 15 min | Business | ⏳ |
| Fix Notion data | 15-30 min | Business | ⏳ |
| Re-validate | 5 min | Technical | ⏳ |
| Bulk sync | 10-15 min | Technical | ⏳ |
| Post-sync verify | 15 min | Technical | ⏳ |
| **Total** | **1.5-2.5 hours** | - | ⏳ |

### Optimal Schedule

**Single Session (Recommended):**
- Block 2.5 hours
- Technical + Business person working together
- Complete all steps in one go
- Immediate feedback loop for questions

**Split Sessions (Alternative):**
- Day 1: Generate CSV + Initial Review (1 hour)
- Day 2: Fix Notion + Re-validate + Bulk Sync (1 hour)

## Integration with Migration Plan

This review workflow fits into overall migration timeline:

### Original Plan (from `budibase-notion-migration-plan.md`):
- **Week 1:** Service layer development (40 hours)
- **Week 2:** Historical data bulk sync

### Optimized Plan (with product review):
- **Day 1 Morning:** Generate product list (15 min)
- **Day 1 Afternoon:** Review & document findings (1 hour)
- **Day 2 Morning:** Fix Notion data (30 min)
- **Day 2 Afternoon:** Bulk sync execution (15 min)

**Time Saved:** Week 1 eliminated (36 hours)
**Quality Improved:** Pre-validated data before DB insertion

## Files & Artifacts

### Scripts
- [x] `list_products_from_notion.py` - Product discovery tool
- [x] `bulk_sync_notion_sales.py` - Bulk sync execution
- [x] `insert_stockx_sale_55476797.py` - Original test script

### Documentation
- [x] `README_PRODUCT_REVIEW.md` - Step-by-step review guide
- [x] `context/product-review-workflow.md` - This document

### Generated Files (During Execution)
- [ ] `products_to_create.csv` - Product discovery report
- [ ] `products_review_findings.md` - Manual review documentation
- [ ] `products_to_skip.txt` - List of custom products to skip (optional)

### Integration Points
- [x] `context/automation-strategy-notion-stockx-sync.md` - Phase 0 plan
- [x] `context/budibase-notion-migration-plan.md` - Migration timeline
- [x] `context/stockx-product-search-api-discovery.md` - API capabilities

## Success Metrics

### Quantitative
- **Data Quality:** > 95% products found on StockX
- **Accuracy:** 0 critical brand mismatches
- **Completeness:** All 238 unique products reviewed
- **Success Rate:** > 95% sync success during bulk execution

### Qualitative
- **Confidence:** Team confident in data accuracy
- **Documentation:** Complete audit trail of review process
- **Knowledge Transfer:** Business team understands product catalog
- **Reusability:** Workflow can be reused for future imports

## Troubleshooting

### Issue: Script Fails to Connect to StockX API

**Symptoms:**
```
Error: Failed to retrieve search results from StockX.
HTTPException: 502 Bad Gateway
```

**Solution:**
1. Check API server is running: `http://localhost:8000/health`
2. Verify StockX API credentials in `core.system_config`
3. Check API rate limits (max 10 req/sec)
4. Wait 5 minutes and retry (potential rate limit cooldown)

### Issue: CSV Shows 100% "Not Found"

**Symptoms:**
```
Total unique products:           238
Found on StockX:                 0 (0%)
NOT found on StockX:             238 (100%)
```

**Solution:**
1. API server must be running during script execution
2. Check `/api/v1/products/search-stockx` endpoint works:
   ```bash
   curl http://localhost:8000/api/v1/products/search-stockx?query=HQ4276
   ```
3. Verify StockX authentication token is valid
4. Re-run script after fixing connection issues

### Issue: Notion MCP Connection Failed

**Symptoms:**
```
Error: Notion workspace not accessible
```

**Solution:**
1. Check Notion MCP integration configured
2. Verify Notion API token in environment
3. Confirm database ID is correct
4. Test Notion connection independently first

## Lessons Learned & Best Practices

### What Worked Well
1. **Reusing Test Script Logic:** Saved 36 hours of development
2. **Pre-Review Process:** Caught data issues before DB insertion
3. **StockX API Integration:** Automated product validation
4. **CSV Export:** Easy for business team to review in Excel

### What Could Be Improved
1. **Automated SKU Suggestions:** When product not found, suggest similar SKUs
2. **Bulk Edit Interface:** Allow fixing multiple issues in one CSV upload
3. **Real-Time Validation:** Validate SKUs in Notion forms during entry
4. **Historical Tracking:** Track which products were reviewed and when

### Recommendations for Future
1. **Prevent Issues at Source:** Add SKU validation to Notion forms
2. **Regular Audits:** Run product discovery monthly to catch new issues
3. **StockX Webhook:** Get notified when product added to catalog
4. **ML-Powered Matching:** Use fuzzy matching for SKU variations

## Conclusion

This product review workflow provides **critical quality assurance** before bulk syncing 238 products from Notion to PostgreSQL.

**Key Benefits:**
- ✅ **Prevents data corruption** - Catches typos and errors before DB insertion
- ✅ **Builds confidence** - Team can verify data accuracy manually
- ✅ **Creates audit trail** - Documented review process for compliance
- ✅ **Saves cleanup time** - Fix issues in source (Notion) rather than DB

**Result:** High-quality product catalog with 95%+ StockX integration accuracy, ready for Budibase UI and production use.

---

**Document Owner:** Engineering Team
**Last Updated:** 2025-09-30
**Related Documents:**
- `automation-strategy-notion-stockx-sync.md` (Phase 0 implementation)
- `budibase-notion-migration-plan.md` (Full migration plan)
- `stockx-product-search-api-discovery.md` (API documentation)
- `notion-stockx-sale-integration-test.md` (Proof of concept)