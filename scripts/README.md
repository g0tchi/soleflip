# Scripts Directory

Utility scripts organized by purpose for maintenance, analysis, and data operations.

---

## 📁 Directory Structure

### `notion_sync/` - Notion Integration Scripts (12 files)
**Purpose:** Notion to PostgreSQL synchronization and data management

**Scripts:**
- `analyze_notion_schema.py` - Analyze Notion database schema
- `bulk_sync_all_notion_sales.py` - Bulk sync all Notion sales data
- `bulk_sync_notion_sales.py` - Bulk Notion sales synchronization
- `collect_all_notion_sales.py` - Collect Notion sales data
- `fetch_all_notion_sales_direct.py` - Direct Notion data fetch
- `fetch_and_sync_notion_sales.py` - Fetch and sync sales data
- `list_products_from_notion.py` - List products from Notion
- `notion_postgres_sync.py` - Core Notion-PostgreSQL sync
- `prepare_notion_sales_data.py` - Prepare sales data for import
- `run_bulk_sync_with_notion_data.py` - Execute bulk sync with Notion data
- `sync_notion_to_postgres.py` - Main Notion sync script
- `verify_synced_sales.py` - Verify synchronization results

**Usage:**
```bash
python scripts/notion_sync/sync_notion_to_postgres.py
python scripts/notion_sync/verify_synced_sales.py
```

---

### `database/` - Database Management Scripts (10 files)

#### Data Management (4 files)
- `compile_collected_sales.py` - Compile collected sales data
- `insert_sample_listings.py` - Insert sample product listings
- `remove_duplicate_orders.py` - Remove duplicate order entries
- `sync_stockx_listings.py` - Sync StockX product listings

#### Migrations Subfolder (6 files)
**Location:** `database/migrations/`

- `execute_view_migration.py` - Execute view migrations
- `list_analytics_views.py` - List all analytics views
- `migrate_legacy_transactions.py` - Migrate legacy transaction data
- `migrate_remaining_views.py` - Migrate remaining analytics views
- `migrate_views_batch.py` - Batch view migration utility
- `test_analytics_views.py` - Test analytics view functionality

**Usage:**
```bash
python scripts/database/migrations/migrate_remaining_views.py
python scripts/database/remove_duplicate_orders.py
```

---

### `analysis/` - Analysis & Testing Scripts (5 files)
**Purpose:** Data analysis, schema validation, and overlap detection

**Scripts:**
- `check_data_overlap.py` - Check for data overlaps between tables
- `check_inventory_orders_overlap.py` - Check inventory/orders overlap
- `check_transactions_schema.py` - Analyze transactions schema
- (2 additional analysis scripts)

**Usage:**
```bash
python scripts/analysis/check_data_overlap.py
python scripts/analysis/check_transactions_schema.py
```

---

### `brand_intelligence/` - Brand Analytics
**Purpose:** Brand analytics and deep dive analysis scripts

---

### `deployment/` - Deployment Utilities
**Purpose:** Deployment automation and configuration scripts

---

### `ci/` - Continuous Integration
**Purpose:** CI/CD pipeline scripts and quality checks

---

### `pricing/` - Pricing Scripts
**Purpose:** Pricing analysis and optimization scripts

---

### `setup/` - Setup & Installation
**Purpose:** Initial setup and configuration scripts

---

### `debug/` - Debug Utilities
**Purpose:** Debugging and troubleshooting tools

---

## 📊 Script Statistics

| Category | Count | Purpose |
|----------|-------|---------|
| **Notion Sync** | 12 | Notion integration |
| **Database Management** | 10 | Data operations & migrations |
| **Analysis** | 5 | Data analysis & validation |
| **Brand Intelligence** | Multiple | Brand analytics |
| **Other Categories** | Various | Specialized utilities |

**Total Scripts:** 33+ Python files (organized)

---

## 🚀 Common Workflows

### Notion Data Sync
```bash
# Full sync workflow
python scripts/notion_sync/fetch_and_sync_notion_sales.py
python scripts/notion_sync/verify_synced_sales.py
```

### Database Migrations
```bash
# View migration workflow
python scripts/database/migrations/list_analytics_views.py
python scripts/database/migrations/migrate_remaining_views.py
python scripts/database/migrations/test_analytics_views.py
```

### Data Analysis
```bash
# Check for data issues
python scripts/analysis/check_data_overlap.py
python scripts/analysis/check_inventory_orders_overlap.py
python scripts/analysis/check_transactions_schema.py
```

---

## 📝 Script Guidelines

### When to Add a New Script

**Add to scripts/** if the script is:
- A maintenance utility
- A one-time migration
- A data analysis tool
- A debugging helper
- An administrative task

**DO NOT add to scripts/** if it's:
- Part of the core application (use `domains/`)
- A test file (use `tests/`)
- A production service (use `shared/` or `domains/`)

### Naming Conventions

- Use descriptive snake_case names
- Include purpose in filename (e.g., `migrate_`, `check_`, `sync_`)
- Avoid generic names like `script.py` or `temp.py`

### Script Structure

```python
"""
Script Purpose: Brief description
Usage: python scripts/category/script_name.py
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def main():
    """Main script logic"""
    pass

if __name__ == "__main__":
    main()
```

---

## 🔧 Maintenance

### Recently Cleaned (v2.2.4 - 2025-10-02)

**Moved from root to scripts/:**
- 11 Notion sync scripts → `notion_sync/`
- 6 migration scripts → `database/migrations/`
- 3 analysis scripts → `analysis/`
- 4 data management scripts → `database/`

**Deleted obsolete scripts:**
- `execute_bulk_sync.py` - One-time migration (completed)
- `insert_stockx_sale_55476797.py` - Testing script (obsolete)
- `test_notion_sync_single.py` - Test completed
- `update_stockx_product_id.py` - Migration completed

**Result:** Root directory now contains only `main.py` (96% reduction)

---

## 📞 Quick Reference

### Most Used Scripts

| Script | Purpose | Location |
|--------|---------|----------|
| **sync_notion_to_postgres.py** | Main Notion sync | `notion_sync/` |
| **verify_synced_sales.py** | Verify sync results | `notion_sync/` |
| **migrate_remaining_views.py** | View migrations | `database/migrations/` |
| **check_data_overlap.py** | Data validation | `analysis/` |
| **remove_duplicate_orders.py** | Cleanup duplicates | `database/` |

---

**Last Updated:** 2025-10-02
**Version:** v2.2.4
