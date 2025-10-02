# Product Review Before Bulk Sync

## Purpose
Before running `bulk_sync_notion_sales.py` which will create **238 new products** in the database, this tool allows you to review all products first.

## Why Review First?

1. **Data Quality:** Verify SKUs are correct and match StockX catalog
2. **Brand Validation:** Check for brand name mismatches (Notion vs StockX)
3. **Missing Products:** Identify products not found on StockX
4. **Duplicates:** Spot potential duplicate SKUs with different names

## How to Use

### Step 1: Generate Product List

```bash
# Ensure API server is running
uvicorn main:app --reload

# In separate terminal, generate product list
python list_products_from_notion.py
```

**Expected Output:**
```
Starting product discovery...
Found 347 sales in Notion
Checking StockX for: HQ4276
Checking StockX for: DZ5485-612
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
```

### Step 2: Review CSV File

Open `products_to_create.csv` in Excel or Google Sheets.

**CSV Columns:**
| Column | Description | Action |
|--------|-------------|--------|
| `sku` | Product SKU | Verify correct format |
| `notion_brand` | Brand from Notion | Check spelling |
| `notion_sale_id` | Reference to Notion sale | For tracking |
| `stockx_found` | Yes/No | **Review all "No" entries** |
| `stockx_product_id` | StockX Product ID | Will be used in DB |
| `stockx_official_name` | Full product name | Verify accuracy |
| `stockx_brand` | Brand from StockX | Compare with Notion |
| `stockx_colorway` | Product colorway | Additional info |
| `stockx_retail_price` | Original retail price | Verify reasonable |
| `stockx_release_date` | Release date | Check for errors |
| `stockx_url` | Direct StockX link | Click to verify |
| `brand_mismatch` | Yes/No | **Review all "Yes" entries** |

### Step 3: Focus Areas for Review

#### A) Products NOT Found on StockX (`stockx_found = No`)

**These need manual investigation:**

**Possible Reasons:**
1. **SKU Typo in Notion** - e.g., "HQ427**6**" instead of "HQ427**7**"
2. **Regional SKU Variation** - EU vs US model numbers differ
3. **Custom/Limited Edition** - Not sold on StockX
4. **Very New Release** - Not yet in StockX catalog
5. **Non-Sneaker Product** - Apparel, accessories (StockX API focuses on sneakers)

**Action Required:**
- [ ] Manually search SKU on StockX.com
- [ ] If found, note correct SKU/Product ID
- [ ] If not found, decide: Skip or create with placeholder?

**Example Review:**
```csv
sku,notion_brand,stockx_found,stockx_product_id
HQ4276,Adidas,Yes,fa671f11-b94d-4596-a4fe-d91e0bd995a0  ✓ OK
CUSTOM-001,Nike,No,  ⚠️ INVESTIGATE
DZ5485,Nike,No,  ⚠️ Could be typo (missing suffix?)
```

#### B) Brand Mismatches (`brand_mismatch = Yes`)

**These might indicate data quality issues:**

**Common Mismatches:**
- Notion: "Adidas" vs StockX: "adidas" (capitalization - OK)
- Notion: "Nike" vs StockX: "Jordan" (different but valid - OK)
- Notion: "New Balance" vs StockX: "NewBalance" (spacing - OK)
- Notion: "Yeezy" vs StockX: "Adidas" (⚠️ Should be Adidas Yeezy)

**Action Required:**
- [ ] Check if mismatch is cosmetic (OK) or semantic (needs fix)
- [ ] Update Notion brand if incorrect
- [ ] Document intentional differences

**Example Review:**
```csv
sku,notion_brand,stockx_brand,brand_mismatch
HQ4276,Adidas,adidas,Yes  ✓ Capitalization only - OK
FB9922,Yeezy,Adidas,Yes  ⚠️ Should be "Adidas" in Notion
DZ5485,Nike,Jordan,Yes  ✓ Valid (Jordan is Nike subsidiary)
```

#### C) Suspicious Patterns

**Look for:**
1. **Duplicate SKUs** - Same SKU appears multiple times (shouldn't happen)
2. **Missing Colorways** - All products should have colorway
3. **Retail Price $0** - Likely missing data
4. **Release Date in Future** - Check for data entry errors
5. **Very Old Release Dates** - e.g., 1990 (likely error)

### Step 4: Document Findings

Create a summary of issues found:

**Template:**
```markdown
# Product Review Findings - 2025-09-30

## Summary
- Total Products: 238
- StockX Found: 215 (90.3%)
- Needs Investigation: 23

## Issues Found

### 1. Products Not Found on StockX (23)
| SKU | Notion Brand | Reason | Action |
|-----|--------------|--------|--------|
| CUSTOM-001 | Nike | Custom product | Skip - not on StockX |
| DZ5485 | Nike | Missing suffix? | Check if DZ5485-612 |
| ... | ... | ... | ... |

### 2. Brand Mismatches (5)
| SKU | Notion | StockX | Resolution |
|-----|--------|--------|------------|
| FB9922 | Yeezy | Adidas | Update Notion to "Adidas" |
| ... | ... | ... | ... |

### 3. Data Quality Issues
- [ ] 3 products missing colorway
- [ ] 1 product has retail price $0
- [ ] 2 products have future release dates

## Recommendations
1. Fix 5 brand names in Notion
2. Skip 8 custom products not on StockX
3. Investigate 15 potentially typo'd SKUs
4. After fixes, re-run list_products_from_notion.py
5. Proceed with bulk_sync_notion_sales.py
```

### Step 5: Fix Issues in Notion

**Before running bulk sync:**
1. Correct any SKU typos in Notion
2. Update incorrect brand names
3. Add missing data (colorway, prices)
4. Remove or flag invalid sales

### Step 6: Re-Generate Product List

After fixes:
```bash
python list_products_from_notion.py
```

**Verify:**
- `stockx_found = No` count decreased
- `brand_mismatch = Yes` count decreased
- All critical issues resolved

### Step 7: Proceed with Bulk Sync

Once product list is validated:
```bash
python bulk_sync_notion_sales.py
```

This will create all 238 products in PostgreSQL with confidence that data is accurate.

## Expected Timeline

| Task | Time | Status |
|------|------|--------|
| Generate product list | 10-15 min | ⏳ |
| Review CSV in Excel | 30-45 min | ⏳ |
| Fix issues in Notion | 15-30 min | ⏳ |
| Re-generate & verify | 5 min | ⏳ |
| Run bulk sync | 10-15 min | ⏳ |
| **Total** | **1.5-2 hours** | ⏳ |

## Quality Gates

**Do NOT proceed with bulk sync if:**
- [ ] More than 15% products not found on StockX
- [ ] More than 10 brand mismatches
- [ ] Critical SKU typos detected
- [ ] Missing essential data (prices, dates)

**Proceed with bulk sync if:**
- [x] Less than 10% products not found (expected for custom items)
- [x] Brand mismatches are cosmetic only
- [x] All SKUs verified or investigated
- [x] Data quality issues documented and acceptable

## Files Generated

1. **`products_to_create.csv`** - Full product list for review
2. **`products_review_findings.md`** - Your documented findings (create manually)
3. **`products_to_skip.txt`** - List of SKUs to skip during bulk sync (optional)

## Next Steps After Review

1. ✅ Product list reviewed and validated
2. ✅ Issues documented and fixed in Notion
3. ✅ CSV re-generated and verified
4. ➡️ **Ready to run:** `python bulk_sync_notion_sales.py`
5. ➡️ Monitor sync progress and verify results

---

**Questions?** Check the script comments or ask for clarification before proceeding.