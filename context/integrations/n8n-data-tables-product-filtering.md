# n8n Data Tables - Product Feed Filtering Strategy

## Overview

This document describes the strategy for using n8n Data Tables as a pre-filtering layer for product catalog data from affiliate networks (Webgains, Awin) before importing into the SoleFlip product catalog.

**Last Updated:** 2025-12-02
**Status:** Planning Phase
**Related Files:**
- `context/integrations/awin_feed_sample.csv` - Sample Awin feed data
- `domains/products/` - Product domain implementation

---

## Problem Statement

### Challenges with Affiliate Product Feeds

1. **Volume**: Feeds contain 50,000+ products per merchant
2. **Irrelevance**: 95%+ products don't match SoleFlip's focus (sneakers/streetwear)
3. **Duplicates**: Same product across multiple merchants (different IDs, same EAN/GTIN)
4. **Data Quality**: Inconsistent brand names, missing attributes, poor categorization
5. **Performance**: Direct import overwhelms database and API

### Solution: Pre-filtering with n8n Data Tables

Use n8n Data Tables as an intelligent staging/filtering layer to:
- Filter products by brand whitelist
- Filter by product categories
- Deduplicate using EAN/GTIN codes
- Track import history and errors
- Reduce import volume by 95%+

---

## n8n Data Tables Capabilities

### Technical Specifications

- **Storage Limit**: 50 MB per table (default)
  - Self-hosted: Configurable via `N8N_DATA_TABLES_MAX_SIZE_BYTES`
  - Warnings at 80% capacity, errors at 100%
- **Supported Data Types**: String, Number, Datetime
  - JSON support: Coming soon (store as string currently)
- **Operations**: Get, Insert, Update, Upsert, Delete
- **Scope**: Per-project (accessible across workflows in same project)

### Ideal Use Cases

✅ **Excellent for:**
- Reference data (brand/category whitelists)
- Deduplication tracking (EAN fingerprints)
- Import logging and error tracking
- Small-to-medium metadata storage

❌ **Not suitable for:**
- Large raw product data (>50MB)
- Complex queries/joins (use PostgreSQL instead)
- Real-time high-frequency updates

---

## Architecture Design

### Data Flow

```
┌─────────────────────┐
│  Webgains/Awin API  │
│   (Product Feeds)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  n8n Workflow       │
│  - Fetch feed       │
│  - Parse CSV/XML    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────┐
│        Filter Layer (Data Tables)   │
│  ┌─────────────────────────────┐   │
│  │ 1. Brand Whitelist Check    │   │
│  │    → Only Nike, Adidas, etc.│   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ 2. Category Filter          │   │
│  │    → Only sneakers/footwear │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ 3. EAN Deduplication        │   │
│  │    → Check fingerprints     │   │
│  └─────────────────────────────┘   │
└──────────┬──────────────────────────┘
           │
           ▼ (Only ~5% of products pass)
┌─────────────────────┐
│  Data Enrichment    │
│  - Normalize brand  │
│  - Extract size     │
│  - Map category     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  SoleFlip API       │
│  POST /products     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  PostgreSQL         │
│  catalog.product    │
└─────────────────────┘
```

---

## Data Tables Schema

### Table 1: `brand_whitelist`

**Purpose:** Define allowed brands and their variations

```sql
Columns:
- id (auto-generated)
- brand_name (string) - Canonical brand name (e.g., "Nike")
- variations (string) - JSON string: ["NIKE", "nike", "Nike Inc"]
- active (number) - 1 = active, 0 = inactive
- priority (number) - Higher = more important brands
- created_at (datetime)
- updated_at (datetime)
```

**Sample Data:**
```json
[
  {
    "brand_name": "Nike",
    "variations": "[\"NIKE\", \"nike\", \"Nike Inc\", \"Nike Sportswear\"]",
    "active": 1,
    "priority": 100
  },
  {
    "brand_name": "Adidas",
    "variations": "[\"ADIDAS\", \"adidas\", \"Adidas Originals\"]",
    "active": 1,
    "priority": 95
  },
  {
    "brand_name": "Jordan",
    "variations": "[\"Air Jordan\", \"JORDAN\", \"Jordan Brand\"]",
    "active": 1,
    "priority": 90
  },
  {
    "brand_name": "New Balance",
    "variations": "[\"NB\", \"NewBalance\", \"NEW BALANCE\"]",
    "active": 1,
    "priority": 85
  },
  {
    "brand_name": "Asics",
    "variations": "[\"ASICS\", \"asics\"]",
    "active": 1,
    "priority": 80
  }
]
```

### Table 2: `category_filters`

**Purpose:** Define allowed/blocked product categories

```sql
Columns:
- id (auto-generated)
- category_keyword (string) - Keyword to match
- include (number) - 1 = include, 0 = exclude
- category_type (string) - "footwear", "apparel", "accessories"
- match_type (string) - "exact", "contains", "starts_with"
- created_at (datetime)
```

**Sample Data:**
```json
[
  {"category_keyword": "sneaker", "include": 1, "category_type": "footwear", "match_type": "contains"},
  {"category_keyword": "trainer", "include": 1, "category_type": "footwear", "match_type": "contains"},
  {"category_keyword": "shoe", "include": 1, "category_type": "footwear", "match_type": "contains"},
  {"category_keyword": "boot", "include": 1, "category_type": "footwear", "match_type": "contains"},
  {"category_keyword": "sandal", "include": 0, "category_type": "footwear", "match_type": "contains"},
  {"category_keyword": "flip flop", "include": 0, "category_type": "footwear", "match_type": "contains"},
  {"category_keyword": "slipper", "include": 0, "category_type": "footwear", "match_type": "contains"}
]
```

### Table 3: `product_fingerprints`

**Purpose:** Track unique products and prevent duplicates

```sql
Columns:
- id (auto-generated)
- ean_code (string) - EAN/GTIN/UPC code (primary dedup key)
- brand (string) - Normalized brand name
- model (string) - Product model/name
- color (string) - Colorway
- size (string) - Size (if available)
- source (string) - "webgains", "awin", "manual"
- merchant_id (string) - Original merchant identifier
- soleflip_product_id (string) - UUID from catalog.product table
- first_imported (datetime) - When first seen
- last_seen (datetime) - Last time seen in feed
- status (string) - "active", "archived", "error"
```

**Sample Data:**
```json
[
  {
    "ean_code": "0194953025890",
    "brand": "Nike",
    "model": "Air Max 90",
    "color": "White/Black",
    "size": "US 10",
    "source": "webgains",
    "merchant_id": "webgains_merchant_42",
    "soleflip_product_id": "550e8400-e29b-41d4-a716-446655440000",
    "first_imported": "2025-12-01T10:00:00Z",
    "last_seen": "2025-12-02T02:00:00Z",
    "status": "active"
  }
]
```

**Deduplication Logic:**
1. New product arrives with EAN
2. Query `product_fingerprints` by EAN
3. **Not found**: Insert new fingerprint + import to SoleFlip
4. **Found**: Update `last_seen` timestamp, optionally check price changes

### Table 4: `import_log`

**Purpose:** Track import runs and statistics

```sql
Columns:
- id (auto-generated)
- import_id (string) - Unique run identifier (UUID)
- source (string) - "webgains", "awin"
- run_date (datetime)
- total_products (number) - Products in feed
- brand_filtered (number) - Filtered by brand whitelist
- category_filtered (number) - Filtered by category
- duplicates_found (number) - Already in fingerprints
- new_products (number) - Newly imported
- errors (number) - Failed imports
- duration_seconds (number)
- status (string) - "success", "partial", "failed"
- error_details (string) - JSON string with error messages
```

**Sample Data:**
```json
[
  {
    "import_id": "550e8400-e29b-41d4-a716-446655440001",
    "source": "webgains",
    "run_date": "2025-12-02T02:00:00Z",
    "total_products": 52000,
    "brand_filtered": 48000,
    "category_filtered": 3500,
    "duplicates_found": 350,
    "new_products": 150,
    "errors": 0,
    "duration_seconds": 240,
    "status": "success",
    "error_details": null
  }
]
```

### Table 5: `price_tracking` (Optional)

**Purpose:** Track best prices across merchants

```sql
Columns:
- id (auto-generated)
- ean_code (string)
- merchant_id (string)
- price (number)
- currency (string) - "EUR", "USD"
- last_updated (datetime)
- in_stock (number) - 1 = yes, 0 = no
```

**Use Case:** Find lowest price for each product across all merchants

---

## n8n Workflow Implementation

### Workflow 1: Initial Data Tables Setup

**Trigger:** Manual (one-time setup)

**Nodes:**
1. **Manual Trigger**
2. **Create Brand Whitelist Table** (Data Table node)
3. **Insert Brand Data** (Loop through brands)
4. **Create Category Filters Table**
5. **Insert Category Data**
6. **Create Product Fingerprints Table**
7. **Create Import Log Table**

### Workflow 2: Webgains Product Import

**Trigger:** Schedule (Daily at 02:00 UTC)

**Flow:**
```
1. Schedule Trigger (Cron: 0 2 * * *)
   ↓
2. HTTP Request - Fetch Webgains Product Feed
   Settings:
   - Method: GET
   - URL: {{ $env.WEBGAINS_FEED_URL }}
   - Authentication: API Key
   ↓
3. Parse CSV/XML
   - Split into individual products
   - Extract fields: ean, brand, name, category, price, image_url
   ↓
4. Generate Import ID
   - Code: const importId = $now.toString() + '_webgains'
   ↓
5. Split In Batches (1000 products per batch)
   ↓
6. Data Table: Get Brand Whitelist
   - Operation: Get
   - Table: brand_whitelist
   - Filter: active = 1
   ↓
7. Filter Node - Brand Check
   - Keep only if product.brand IN whitelist.variations
   ↓
8. Data Table: Get Category Filters
   - Operation: Get
   - Table: category_filters
   - Filter: include = 1
   ↓
9. Filter Node - Category Check
   - Keep only if product.category CONTAINS allowed keywords
   ↓
10. Code Node - Normalize Data
    - Normalize brand name (use canonical from whitelist)
    - Extract size from product name
    - Clean/validate EAN code
   ↓
11. Data Table: Check Fingerprints
    - Operation: Get
    - Table: product_fingerprints
    - Filter: ean_code = {{ $json.ean }}
   ↓
12. Switch Node - Duplicate Check
    Case 1: EAN not found (new product)
      → Continue to import
    Case 2: EAN exists
      → Update last_seen timestamp
      → Skip import (or optionally check price changes)
   ↓
13. HTTP Request - POST to SoleFlip API
    - URL: http://localhost:8000/products
    - Method: POST
    - Body: {
        "brand": "{{ $json.brand }}",
        "name": "{{ $json.name }}",
        "ean": "{{ $json.ean }}",
        "category": "{{ $json.category }}",
        "price": {{ $json.price }},
        "image_url": "{{ $json.image_url }}"
      }
   ↓
14. Data Table: Insert Fingerprint
    - Operation: Insert
    - Table: product_fingerprints
    - Data: {
        ean_code, brand, model, source, soleflip_product_id,
        first_imported: $now, last_seen: $now, status: "active"
      }
   ↓
15. Aggregate Node - Count Statistics
    - Total processed
    - Filtered (brands)
    - Filtered (categories)
    - Duplicates
    - Imported
    - Errors
   ↓
16. Data Table: Insert Import Log
    - Operation: Insert
    - Table: import_log
    - Data: {import_id, source, run_date, statistics...}
   ↓
17. Send Notification (optional)
    - Email/Slack with import summary
```

### Workflow 3: Awin Product Import

**Same structure as Webgains, adjusted for Awin API/CSV format**

---

## Data Size Estimation

### Brand Whitelist Table
```
Assumptions:
- 50 brands
- 5 variations per brand (avg)
- 100 bytes per row

Calculation: 50 brands × 100 bytes = 5 KB
✅ Well within 50 MB limit
```

### Category Filters Table
```
Assumptions:
- 100 category keywords
- 50 bytes per row

Calculation: 100 × 50 bytes = 5 KB
✅ Well within 50 MB limit
```

### Product Fingerprints Table
```
Assumptions:
- 10,000 unique products in catalog
- 200 bytes per row (EAN + metadata)

Calculation: 10,000 × 200 bytes = 2 MB
✅ Comfortable within 50 MB limit

Growth projection:
- At 50,000 products: ~10 MB (still safe)
- At 100,000 products: ~20 MB (40% capacity)
- At 250,000 products: ~50 MB (at limit)

Mitigation:
- Archive old/inactive products
- Move to PostgreSQL if >100k products
```

### Import Log Table
```
Assumptions:
- 1 import per day
- 365 days = 365 rows
- 150 bytes per row

Calculation: 365 × 150 bytes = 55 KB
✅ Minimal storage impact

Cleanup strategy:
- Keep last 90 days in Data Table
- Archive older logs to PostgreSQL
```

**Total Estimated Usage: ~2.5 MB / 50 MB (5% capacity)**

---

## Benefits Analysis

### Performance Gains

**Before (Direct Import):**
```
Feed size: 50,000 products
↓ (no filtering)
API calls: 50,000
Database inserts: 50,000
Processing time: ~2 hours
Relevant products: ~2,500 (5%)
Duplicates: ~500
```

**After (With Data Tables Filtering):**
```
Feed size: 50,000 products
↓ Brand filter (96% reduction)
2,000 products remain
↓ Category filter (50% reduction)
1,000 products remain
↓ Deduplication (70% reduction)
300 NEW products remain
↓
API calls: 300
Database inserts: 300
Processing time: ~5 minutes
Success rate: 100%
```

**Improvement:**
- **166x fewer API calls** (50,000 → 300)
- **24x faster** (2 hours → 5 minutes)
- **99.4% reduction** in database writes
- **Zero duplicates** in catalog

### Cost Savings

**API/Database Load:**
- 99.4% reduction in writes → Less database I/O
- Fewer API calls → Less CPU/memory usage
- Faster processing → Lower infrastructure costs

**Storage Savings:**
- Only relevant products stored
- No duplicate products
- Cleaner catalog = better user experience

**Operational Benefits:**
- Auditable import logs
- Easy brand/category management (just edit Data Tables)
- No code changes for filter rules
- Centralized deduplication logic

---

## Alternative Architectures Considered

### Option A: Direct PostgreSQL Staging Schema

**Approach:** Create `staging` schema in PostgreSQL with `webgains_raw`, `awin_raw` tables

**Pros:**
- More storage capacity
- Complex SQL queries possible
- Integrated with main database

**Cons:**
- Pollutes production database
- Requires database migrations
- Harder to maintain/clean up
- Slower than n8n Data Tables for simple filters

**Verdict:** ❌ Overkill for this use case

### Option B: Redis Cache

**Approach:** Use Redis for temporary storage and deduplication

**Pros:**
- Very fast (in-memory)
- Simple key-value lookups

**Cons:**
- Requires separate Redis instance
- Data not persistent by default
- No built-in UI for data management
- Additional infrastructure complexity

**Verdict:** ❌ Too complex, Data Tables better fit

### Option C: Google Sheets API

**Approach:** Use Google Sheets as external database

**Pros:**
- Easy to visualize data
- Non-technical users can edit

**Cons:**
- API rate limits
- Slow for large datasets
- Requires OAuth setup
- External dependency

**Verdict:** ❌ Performance concerns, external dependency

### **Selected: n8n Data Tables ✅**

**Why:**
- Built-in, no external dependencies
- Fast for filtering operations
- Easy to manage via n8n UI
- Sufficient storage for our needs
- Zero infrastructure overhead
- Perfect for <50MB reference data

---

## Migration Strategy

### Phase 1: Setup (Week 1)
- [ ] Create Data Tables (brand_whitelist, category_filters, etc.)
- [ ] Populate initial brand/category data
- [ ] Test table operations (CRUD)

### Phase 2: Workflow Development (Week 2)
- [ ] Build Webgains import workflow
- [ ] Implement filtering logic
- [ ] Add deduplication
- [ ] Test with sample feed data

### Phase 3: Integration (Week 3)
- [ ] Connect to SoleFlip products API
- [ ] Test end-to-end flow
- [ ] Add error handling
- [ ] Implement logging

### Phase 4: Production (Week 4)
- [ ] Deploy to production n8n instance
- [ ] Schedule daily imports
- [ ] Monitor for 1 week
- [ ] Adjust filters based on results

### Phase 5: Expansion
- [ ] Add Awin workflow (same pattern)
- [ ] Add price tracking table
- [ ] Implement best-price logic
- [ ] Add more affiliate networks

---

## Monitoring & Maintenance

### Daily Checks
- Review import_log for errors
- Check product_fingerprints growth rate
- Validate new products in SoleFlip catalog

### Weekly Tasks
- Review brand_whitelist (add new brands?)
- Update category_filters (new keywords?)
- Clean up old fingerprints (>90 days inactive)

### Monthly Tasks
- Analyze import statistics
- Optimize filters (too restrictive? too loose?)
- Archive old import logs (keep last 90 days)

### Alerts
- Import fails → Email/Slack notification
- Fingerprints table >80% capacity → Warning
- More than 50% products filtered → Review filters

---

## Code Integration Points

### SoleFlip API Endpoint

**Required endpoint:** `POST /products`

**Location:** `domains/products/api/router.py`

**Expected Request Body:**
```json
{
  "brand": "Nike",
  "name": "Air Max 90 Essential",
  "ean": "0194953025890",
  "category": "Sneakers",
  "price": 129.99,
  "currency": "EUR",
  "image_url": "https://...",
  "source": "webgains",
  "merchant_id": "webgains_merchant_42"
}
```

**Expected Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "brand": "Nike",
  "name": "Air Max 90 Essential",
  "ean": "0194953025890",
  "created_at": "2025-12-02T10:30:00Z"
}
```

### Database Model

**Table:** `catalog.product`

**Fields:**
- `id` (UUID, primary key)
- `brand` (string)
- `name` (string)
- `ean` (string, unique index)
- `category` (string)
- `price` (decimal)
- `image_url` (string)
- `source` (string) - "webgains", "awin", "manual"
- `merchant_id` (string, nullable)
- `created_at` (timestamp)
- `updated_at` (timestamp)

---

## Testing Strategy

### Unit Tests (Data Tables Logic)
```python
# Test brand matching
def test_brand_in_whitelist():
    product = {"brand": "NIKE"}
    whitelist = [{"brand_name": "Nike", "variations": '["NIKE", "nike"]'}]
    assert is_brand_allowed(product, whitelist) == True

# Test category filtering
def test_category_filter():
    product = {"category": "Running Sneakers"}
    filters = [{"keyword": "sneaker", "include": 1}]
    assert is_category_allowed(product, filters) == True

# Test EAN deduplication
def test_ean_deduplication():
    ean = "0194953025890"
    fingerprints = [{"ean_code": "0194953025890"}]
    assert is_duplicate(ean, fingerprints) == True
```

### Integration Tests (n8n Workflow)
1. Mock Webgains API response
2. Run workflow with test data
3. Verify filtering results
4. Check fingerprints table updates
5. Validate API calls to SoleFlip

### End-to-End Tests
1. Use real Awin sample data (`awin_feed_sample.csv`)
2. Process through workflow
3. Verify products in PostgreSQL
4. Check import logs
5. Validate no duplicates

---

## Troubleshooting

### Issue: Too many products filtered out

**Symptom:** Import log shows 99.9% filtered

**Causes:**
1. Brand whitelist too restrictive
2. Category filters too strict
3. Feed format changed

**Solutions:**
1. Review `brand_whitelist` - add missing variations
2. Check `category_filters` - adjust keywords
3. Inspect raw feed data - update parsing logic

### Issue: Duplicates still appearing

**Symptom:** Same product multiple times in catalog

**Causes:**
1. EAN missing in feed
2. EAN format inconsistent
3. Fingerprint table not queried

**Solutions:**
1. Add fallback deduplication (brand+model+size)
2. Normalize EAN codes (remove dashes, spaces)
3. Check workflow Switch node logic

### Issue: Data Tables at capacity

**Symptom:** Warnings at 80%, errors at 100%

**Causes:**
1. Too many fingerprints (>250k products)
2. Import logs not cleaned up

**Solutions:**
1. Archive inactive products (last_seen >90 days)
2. Move fingerprints to PostgreSQL
3. Increase limit (self-hosted: `N8N_DATA_TABLES_MAX_SIZE_BYTES`)

---

## Future Enhancements

### Short-term (Q1 2025)
- [ ] Add price tracking table
- [ ] Implement best-price logic across merchants
- [ ] Add Awin workflow
- [ ] Email notifications for import summaries

### Medium-term (Q2 2025)
- [ ] Machine learning for category classification
- [ ] Automatic brand extraction from product names
- [ ] Price history tracking and alerts
- [ ] Multi-language support

### Long-term (Q3+ 2025)
- [ ] Real-time webhook processing (instead of daily batch)
- [ ] Product image analysis (AI-based categorization)
- [ ] Predictive inventory recommendations
- [ ] Integration with more affiliate networks

---

## References

- **n8n Data Tables Documentation**: https://docs.n8n.io/data/data-tables
- **n8n MCP Server Tools**: See `integrations/memori-mcp/README.md`
- **Awin Sample Feed**: `context/integrations/awin_feed_sample.csv`
- **SoleFlip Products Domain**: `domains/products/`
- **Database Schema**: `context/current_database_schema.md`

---

## Questions & Answers

**Q: Why not use Google Sheets?**
A: Data Tables are faster, no external dependencies, no OAuth, no rate limits.

**Q: What if we exceed 50 MB?**
A: Self-hosted can increase limit via env var. Or migrate to PostgreSQL staging schema.

**Q: Can we edit Data Tables manually?**
A: Yes! n8n has built-in UI for viewing/editing tables (like a mini database GUI).

**Q: How do we handle feed format changes?**
A: n8n workflows are easy to modify. Update CSV parsing node, test, deploy.

**Q: What about real-time processing?**
A: Current design is batch (daily). For real-time, use webhooks + same filtering logic.

---

**Document Status:** ✅ Complete
**Next Steps:** Review with team → Implement Phase 1 (Setup Data Tables)
