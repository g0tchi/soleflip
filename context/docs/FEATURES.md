# Feature-to-Code Mapping Guide

**Purpose**: Map high-level business features to their code implementations
**Last Updated**: 2025-11-06

---

## Overview

This guide helps developers quickly locate code responsible for specific business features. Each feature is mapped to its domain, services, API endpoints, and key files.

---

## Core Features

### 1. StockX Order Management

**Business Description**: Import, sync, and manage orders from StockX marketplace

**Code Location**:
- **Domain**: `domains/integration/`
- **Service**: `StockXService` (`domains/integration/services/stockx_service.py`)
- **API**: `/api/integration/webhooks/stockx/import-orders-background`
- **Repository**: `ImportRepository` (`domains/integration/repositories/import_repository.py`)

**Key Files**:
```
domains/integration/services/stockx_service.py:124-200  # Order fetching
domains/integration/api/webhooks.py:75-120              # Import webhook
domains/orders/services/order_import_service.py:45-89   # Order processing
```

**Related Features**:
- CSV Import System
- Webhook Processing
- Order Status Tracking

**Testing**: `tests/integration/api/test_stockx_webhook.py`

---

### 2. Smart Pricing Engine

**Business Description**: Multi-strategy pricing with AI-powered optimization

**Code Location**:
- **Domain**: `domains/pricing/`
- **Service**: `PricingEngine` (`domains/pricing/services/pricing_engine.py`)
- **API**: `/api/pricing/calculate`
- **Repository**: `PricingRepository` (`domains/pricing/repositories/pricing_repository.py`)

**Key Files**:
```
domains/pricing/services/pricing_engine.py:70-103      # calculate_optimal_price()
domains/pricing/services/pricing_engine.py:134-180     # Cost-plus strategy
domains/pricing/services/pricing_engine.py:200-245     # Market-based strategy
domains/pricing/services/smart_pricing_service.py:54-110  # optimize_inventory_pricing()
```

**Strategies Implemented**:
- COST_PLUS: Lines 134-180
- MARKET_BASED: Lines 200-245
- COMPETITIVE: Lines 260-305
- VALUE_BASED: Lines 320-365
- DYNAMIC: Lines 380-425

**Testing**: `tests/unit/services/test_pricing_engine.py`

---

### 3. Sales Forecasting

**Business Description**: AI-powered demand prediction using ML models (ARIMA, Random Forest, Ensemble)

**Code Location**:
- **Domain**: `domains/analytics/`
- **Service**: `ForecastEngine` (`domains/analytics/services/forecast_engine.py`)
- **API**: `/api/analytics/forecast/sales`
- **Repository**: `ForecastRepository` (`domains/analytics/repositories/forecast_repository.py`)

**Key Files**:
```
domains/analytics/services/forecast_engine.py:113-148  # generate_forecasts()
domains/analytics/services/forecast_engine.py:250-295  # ARIMA model
domains/analytics/services/forecast_engine.py:310-355  # Random Forest
domains/analytics/services/forecast_engine.py:370-420  # Ensemble
```

**Models Implemented**:
- Linear Trend: Lines 180-210
- ARIMA: Lines 250-295
- Random Forest: Lines 310-355
- Ensemble: Lines 370-420

**Testing**: `tests/unit/services/test_forecast_engine.py`

---

### 4. Dead Stock Detection

**Business Description**: Intelligent identification of slow-moving inventory

**Code Location**:
- **Domain**: `domains/inventory/`
- **Service**: `DeadStockService` (`domains/inventory/services/dead_stock_service.py`)
- **API**: `/api/inventory/dead-stock/analyze`

**Key Files**:
```
domains/inventory/services/dead_stock_service.py:95-150   # analyze_dead_stock()
domains/inventory/services/dead_stock_service.py:200-245  # Risk score calculation
domains/inventory/services/dead_stock_service.py:280-320  # Action recommendations
```

**Risk Levels** (defined at line 22-29):
- HOT: 0-30 days
- WARM: 31-60 days
- COLD: 61-120 days
- DEAD: 121-180 days
- CRITICAL: >180 days

**Testing**: `tests/unit/services/test_dead_stock_service.py`

---

### 5. CSV Import System

**Business Description**: Multi-source CSV imports with validation

**Code Location**:
- **Domain**: `domains/integration/`
- **Service**: `ImportProcessor` (`domains/integration/services/import_processor.py`)
- **API**: `/api/integration/upload/import`
- **Parsers**: `CSVParser`, `JSONParser`, `ExcelParser` (`domains/integration/services/parsers.py`)

**Key Files**:
```
domains/integration/services/import_processor.py:86-120      # create_initial_batch()
domains/integration/services/import_processor.py:150-200     # process_import()
domains/integration/services/parsers.py:10-50                # CSVParser
domains/integration/services/validators.py:20-80             # StockXValidator
domains/integration/api/upload_router.py:75-120              # Upload endpoints
```

**Supported Sources** (defined at line 39-44):
- STOCKX
- NOTION
- SALES
- ALIAS
- MANUAL

**Testing**: `tests/integration/test_import_pipeline.py`

---

### 6. Auto-Listing Service

**Business Description**: Automated marketplace listing creation

**Code Location**:
- **Domain**: `domains/pricing/`
- **Service**: `AutoListingService` (`domains/pricing/services/auto_listing_service.py`)
- **Integration**: StockX API integration

**Key Files**:
```
domains/pricing/services/auto_listing_service.py:45-90      # create_listing()
domains/pricing/services/auto_listing_service.py:120-165    # create_bulk_listings()
domains/pricing/services/auto_listing_service.py:200-240    # update_listing_price()
```

**Testing**: `tests/unit/services/test_auto_listing_service.py`

---

## Database Models

### Core Models (`shared/database/models.py`)

| Model | Purpose | Key Fields | Line Range |
|-------|---------|-----------|------------|
| `Product` | Product catalog | sku, name, brand_id, price | 100-150 |
| `InventoryItem` | Stock tracking | product_id, size_id, status, purchase_price | 200-250 |
| `Transaction` (orders) | Multi-platform orders | order_number, product_id, price, status | 300-350 |
| `Brand` | Brand intelligence | name, founders, sustainability_score | 50-90 |
| `ImportBatch` | Import tracking | source_type, status, total_records | 400-440 |
| `ImportRecord` | Individual import rows | batch_id, source_data, status | 460-500 |

---

## API Endpoint Index

### Integration Domain

```
POST   /api/integration/upload/validate          # Validate CSV
POST   /api/integration/upload/import            # Import CSV
GET    /api/integration/upload/batch/{id}/status # Poll import status
POST   /api/integration/webhooks/stockx/import-orders-background  # StockX webhook
```

### Pricing Domain

```
POST   /api/pricing/calculate                    # Calculate optimal price
POST   /api/pricing/optimize-inventory           # Bulk repricing
```

### Analytics Domain

```
POST   /api/analytics/forecast/sales             # Sales forecast
POST   /api/analytics/forecast/brand             # Brand forecast
GET    /api/analytics/trends                     # Market trends
```

### Inventory Domain

```
GET    /api/inventory                            # List inventory
GET    /api/inventory/stats                      # Statistics
POST   /api/inventory/dead-stock/analyze         # Dead stock analysis
POST   /api/inventory/insights/generate          # Predictive insights
```

### Orders Domain

```
GET    /api/orders/active                        # Active orders
GET    /api/orders/stockx-history                # Historical orders
```

---

## Common Development Tasks

### Add New Pricing Strategy

**Steps**:
1. Add strategy to `PricingStrategy` enum (`domains/pricing/services/pricing_engine.py:20`)
2. Implement `_calculate_{strategy}_price()` method (line ~400)
3. Add strategy to `_calculate_strategy_price()` switch (line 113)
4. Add tests in `tests/unit/services/test_pricing_engine.py`

**Example**:
```python
# File: domains/pricing/services/pricing_engine.py

# 1. Add to enum (line 20)
class PricingStrategy(Enum):
    # ... existing strategies
    NEW_STRATEGY = "new_strategy"

# 2. Implement method (line ~450)
async def _calculate_new_strategy_price(
    self, context: PricingContext, rules: List[PriceRule]
) -> PricingResult:
    # Implementation here
    pass

# 3. Add to switch (line 113)
elif strategy == PricingStrategy.NEW_STRATEGY:
    return await self._calculate_new_strategy_price(context, rules)
```

---

### Add New Forecast Model

**Steps**:
1. Add model to `ForecastModel` enum (`domains/analytics/services/forecast_engine.py:41`)
2. Implement `_forecast_{model}()` method (line ~350)
3. Update ensemble weights if needed (line 370)
4. Add tests

---

### Add New Import Source

**Steps**:
1. Add source to `SourceType` enum (`domains/integration/services/import_processor.py:39`)
2. Create validator class in `validators.py`
3. Add validator to processor `__init__` (line 72)
4. Add CSV format documentation to upload router (line 50)

---

## Quick Reference

### Finding Code

**By Feature**:
- StockX Integration → `domains/integration/services/stockx_service.py`
- Pricing Logic → `domains/pricing/services/pricing_engine.py`
- Forecasting → `domains/analytics/services/forecast_engine.py`
- Dead Stock → `domains/inventory/services/dead_stock_service.py`

**By Endpoint**:
```bash
# Search for endpoint definition
grep -r "POST.*pricing/calculate" domains/

# Find implementation
grep -r "@router.post" domains/ | grep pricing
```

**By Database Table**:
- Products → `shared/database/models.py:100`
- Orders → `shared/database/models.py:300`
- Inventory → `shared/database/models.py:200`

---

## Related Documentation

- [Integration Domain Guide](domains/INTEGRATION_DOMAIN.md)
- [Pricing Domain Guide](domains/PRICING_DOMAIN.md)
- [Analytics Domain Guide](domains/ANALYTICS_DOMAIN.md)
- [Inventory Domain Guide](domains/INVENTORY_DOMAIN.md)
- [API Endpoints Reference](API_ENDPOINTS.md)
- [Repository Pattern Guide](patterns/REPOSITORY_PATTERN.md)

---

**Last Updated**: 2025-11-06
**Maintainer**: SoleFlipper Development Team
