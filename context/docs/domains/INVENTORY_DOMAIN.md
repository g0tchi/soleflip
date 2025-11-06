# Inventory Domain Guide

**Domain**: `domains/inventory/`
**Purpose**: Stock management, dead stock analysis, predictive insights, and inventory optimization
**Last Updated**: 2025-11-06

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Services](#core-services)
4. [Dead Stock Management](#dead-stock-management)
5. [Predictive Insights](#predictive-insights)
6. [API Endpoints](#api-endpoints)
7. [Usage Examples](#usage-examples)
8. [Inventory Optimization](#inventory-optimization)
9. [Testing](#testing)

---

## Overview

The Inventory domain manages physical stock, identifies slow-moving items (dead stock), provides predictive insights for restocking, and optimizes inventory investment for maximum ROI.

### Key Responsibilities

- **Inventory Tracking**: Real-time stock levels, locations, conditions
- **Dead Stock Detection**: Intelligent identification of slow-moving items
- **Predictive Insights**: AI-powered restock recommendations
- **StockX Integration**: Sync inventory with StockX listings
- **Risk Assessment**: Calculate inventory risk scores and financial impact
- **Optimization**: Maximize turnover, minimize locked capital

### Domain Structure

```
domains/inventory/
├── api/                          # REST API endpoints
│   └── router.py                 # Inventory management endpoints
├── services/                     # Business logic
│   ├── inventory_service.py     # Core inventory operations ⭐ CORE
│   ├── dead_stock_service.py    # Dead stock identification ⭐ CRITICAL
│   └── predictive_insights_service.py  # AI-powered insights ⭐ STRATEGIC
├── repositories/                 # Data access
│   ├── inventory_repository.py  # Inventory data access
│   └── product_repository.py    # Product data access
└── events/                       # Event handlers
    └── handlers.py              # Inventory events
```

---

## Architecture

### Service Interaction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Inventory Domain                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │ Inventory    │────▶│ Dead Stock   │────▶│ Risk         │   │
│  │ Service      │     │ Service      │     │ Assessment   │   │
│  └──────────────┘     └──────────────┘     └──────────────┘   │
│         │                    │                     │           │
│         │                    ▼                     ▼           │
│         │             ┌──────────────┐     ┌──────────────┐   │
│         │             │ Predictive   │     │ Forecast     │   │
│         │             │ Insights     │     │ Engine       │   │
│         │             └──────────────┘     └──────────────┘   │
│         │                                          │           │
│         ▼                                          ▼           │
│  ┌──────────────────────────────────────────────────────┐     │
│  │      StockX Integration (Real-time Market Data)      │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Patterns

1. **Inventory Addition**: Product creation → Size selection → Stock allocation → Location assignment
2. **Dead Stock Detection**: Age calculation → Market price check → Risk scoring → Action recommendation
3. **Predictive Insights**: Historical analysis → Forecast generation → Confidence scoring → Actionable recommendations

---

## Core Services

### 1. InventoryService (`inventory_service.py`)

**Purpose**: Core inventory management operations, stock tracking, and StockX synchronization.

**Location**: `domains/inventory/services/inventory_service.py`

#### Key Features

- **Inventory Overview**: Real-time statistics (total items, in stock, sold, listed)
- **Stock Management**: Add, update, remove inventory items
- **Multi-location Support**: Track items across warehouses/locations
- **StockX Sync**: Synchronize with StockX listings
- **Pre-sale Management**: Handle pre-sale inventory (listed before acquisition)
- **Purchase Price Tracking**: ROI and profit margin calculation

#### Inventory Statistics

```python
@dataclass
class InventoryStats:
    total_items: int          # Total inventory count
    in_stock: int             # Available for sale
    sold: int                 # Sold items
    listed: int               # Listed on marketplaces
    total_value: Decimal      # Total purchase price value
    avg_purchase_price: Decimal  # Average cost per item
```

#### Usage Example: Get Inventory Overview

```python
from domains.inventory.services.inventory_service import InventoryService

async def get_inventory_dashboard():
    async with db_manager.get_session() as session:
        service = InventoryService(session)

        # Get real-time stats
        stats = await service.get_inventory_overview()

        print(f"📦 Inventory Overview")
        print(f"=" * 50)
        print(f"Total Items: {stats.total_items}")
        print(f"In Stock: {stats.in_stock}")
        print(f"Sold: {stats.sold}")
        print(f"Listed: {stats.listed}")
        print(f"Total Value: €{stats.total_value:,.2f}")
        print(f"Avg Purchase Price: €{stats.avg_purchase_price:.2f}")
```

**Example Output**:
```
📦 Inventory Overview
==================================================
Total Items: 1,247
In Stock: 823
Sold: 324
Listed: 100
Total Value: €124,567.00
Avg Purchase Price: €151.42
```

---

### 2. DeadStockService (`dead_stock_service.py`)

**Purpose**: Intelligent identification and management of slow-moving inventory (dead stock).

**Location**: `domains/inventory/services/dead_stock_service.py`

#### Risk Levels

```python
class StockRiskLevel(Enum):
    HOT = "hot"         # 0-25% risk - Fast-moving items (0-30 days)
    WARM = "warm"       # 26-50% risk - Normal velocity (31-60 days)
    COLD = "cold"       # 51-75% risk - Slow-moving (61-120 days)
    DEAD = "dead"       # 76-100% risk - Very slow (121-180 days)
    CRITICAL = "critical"  # >100% risk - Immediate action (>180 days)
```

#### Dead Stock Item Data

```python
@dataclass
class DeadStockItem:
    item_id: UUID
    product_name: str
    brand_name: str
    size_value: str
    purchase_price: Decimal
    current_market_price: Optional[Decimal]
    days_in_inventory: int
    risk_score: float              # 0-1 scale
    risk_level: StockRiskLevel
    locked_capital: Decimal        # Money tied up
    potential_loss: Decimal        # Potential financial loss
    recommended_actions: List[str] # Actionable steps
    market_trend: str              # "declining", "stable", "rising"
    velocity_score: float          # Sales velocity metric
```

#### Risk Scoring Algorithm

**Formula**:
```
Risk Score = (Age Weight × Age Factor) +
             (Velocity Weight × Velocity Factor) +
             (Market Trend Weight × Trend Factor)

Where:
- Age Factor = days_in_inventory / max_days_threshold
- Velocity Factor = 1 - (recent_sales / expected_sales)
- Trend Factor = price_decline_percentage
```

**Configurable Weights** (default):
- Age Weight: 30%
- Velocity Weight: 40%
- Market Trend Weight: 30%

#### Usage Example: Analyze Dead Stock

```python
from domains.inventory.services.dead_stock_service import DeadStockService

async def analyze_slow_movers():
    async with db_manager.get_session() as session:
        service = DeadStockService(session)

        # Analyze inventory for dead stock
        analysis = await service.analyze_dead_stock(
            brand_filter="Nike",      # Optional: filter by brand
            min_risk_score=0.5        # Only items with 50%+ risk
        )

        print(f"🚨 Dead Stock Analysis")
        print(f"=" * 60)
        print(f"Items Analyzed: {analysis.total_items_analyzed}")
        print(f"Dead Stock Items: {len(analysis.dead_stock_items)}")

        # Risk breakdown
        print(f"\nRisk Summary:")
        for level, count in analysis.risk_summary.items():
            print(f"  {level.upper()}: {count} items")

        # Financial impact
        print(f"\nFinancial Impact:")
        print(f"  Locked Capital: €{analysis.financial_impact['locked_capital']:,.2f}")
        print(f"  Potential Loss: €{analysis.financial_impact['potential_loss']:,.2f}")

        # Top 10 worst items
        print(f"\n🔥 Top 10 Critical Items:")
        print(f"=" * 60)

        sorted_items = sorted(
            analysis.dead_stock_items,
            key=lambda x: x.risk_score,
            reverse=True
        )[:10]

        for item in sorted_items:
            print(f"\n- {item.product_name} (Size: {item.size_value})")
            print(f"  Risk: {item.risk_level.value.upper()} ({item.risk_score:.1%})")
            print(f"  Days in Stock: {item.days_in_inventory}")
            print(f"  Purchase Price: €{item.purchase_price:.2f}")
            print(f"  Market Price: €{item.current_market_price:.2f}" if item.current_market_price else "  Market Price: Unknown")
            print(f"  Locked Capital: €{item.locked_capital:.2f}")
            print(f"  Potential Loss: €{item.potential_loss:.2f}")
            print(f"  Actions: {', '.join(item.recommended_actions)}")
```

**Example Output**:
```
🚨 Dead Stock Analysis
============================================================
Items Analyzed: 823
Dead Stock Items: 127

Risk Summary:
  HOT: 456 items
  WARM: 240 items
  COLD: 89 items
  DEAD: 32 items
  CRITICAL: 6 items

Financial Impact:
  Locked Capital: €18,450.00
  Potential Loss: €4,230.00

🔥 Top 10 Critical Items:
============================================================

- Nike Air Max 97 "Silver Bullet" (Size: US 11.5)
  Risk: CRITICAL (94.5%)
  Days in Stock: 245
  Purchase Price: €189.99
  Market Price: €145.00
  Locked Capital: €189.99
  Potential Loss: €44.99
  Actions: Immediate discount (20-30%), List on multiple platforms, Bundle deal

- Adidas Yeezy Boost 700 "Wave Runner" (Size: US 13)
  Risk: DEAD (82.3%)
  Days in Stock: 165
  Purchase Price: €220.00
  Market Price: €195.00
  Locked Capital: €220.00
  Potential Loss: €25.00
  Actions: Price reduction (15%), Cross-platform listing, Marketing push
```

#### Recommended Actions by Risk Level

**HOT** (0-30 days):
- ✅ Monitor performance
- ✅ Maintain current pricing
- ✅ Consider increasing stock

**WARM** (31-60 days):
- ⚠️ Monitor closely
- ⚠️ Consider small price adjustments (5-10%)
- ⚠️ Ensure multi-platform visibility

**COLD** (61-120 days):
- 🟡 Price reduction (10-15%)
- 🟡 Cross-platform listing
- 🟡 Marketing campaign

**DEAD** (121-180 days):
- 🔴 Significant discount (15-25%)
- 🔴 Bundle deals
- 🔴 Promotional events

**CRITICAL** (>180 days):
- 🚨 Immediate action required
- 🚨 Liquidation pricing (25-40% off)
- 🚨 Consider donation/write-off for tax benefits

---

### 3. PredictiveInsightsService (`predictive_insights_service.py`)

**Purpose**: AI-powered inventory insights integrating forecasting with pricing and market data.

**Location**: `domains/inventory/services/predictive_insights_service.py`

#### Key Features

- **Demand Prediction**: Forecast future demand using Analytics domain
- **Restock Recommendations**: Optimal timing and quantity
- **Seasonal Analysis**: Identify seasonal patterns
- **ROI Projections**: Expected return on inventory investment
- **Market Trend Integration**: StockX real-time market data
- **Profit Optimization**: Dynamic pricing recommendations

#### Insight Types

```python
class InsightType(Enum):
    RESTOCK_OPPORTUNITY = "restock_opportunity"    # Low stock + high demand
    DEMAND_SURGE = "demand_surge"                  # Sudden demand increase
    SEASONAL_TREND = "seasonal_trend"              # Seasonal patterns detected
    MARKET_SHIFT = "market_shift"                  # Market price changes
    PROFIT_OPTIMIZATION = "profit_optimization"    # Pricing opportunity
    CLEARANCE_ALERT = "clearance_alert"            # Overstock warning
```

#### Insight Priorities

```python
class InsightPriority(Enum):
    CRITICAL = "critical"  # Immediate action (<24h)
    HIGH = "high"          # Act within 1-3 days
    MEDIUM = "medium"      # Act within 1 week
    LOW = "low"            # Monitor, no urgency
```

#### Usage Example: Get Predictive Insights

```python
from domains.inventory.services.predictive_insights_service import (
    PredictiveInsightsService
)

async def get_actionable_insights():
    async with db_manager.get_session() as session:
        service = PredictiveInsightsService(session)

        # Generate insights for all products
        insights = await service.generate_inventory_insights(
            min_confidence=0.75,     # 75% confidence minimum
            priority_filter=["critical", "high"]  # Focus on urgent items
        )

        print(f"💡 Predictive Inventory Insights")
        print(f"=" * 60)
        print(f"Total Insights: {len(insights)}\n")

        # Group by priority
        critical = [i for i in insights if i.priority.value == "critical"]
        high = [i for i in insights if i.priority.value == "high"]

        print(f"🚨 CRITICAL ({len(critical)} items) - Act immediately:")
        for insight in critical[:5]:
            print(f"\n- {insight.title}")
            print(f"  {insight.description}")
            print(f"  Product: {insight.product_name}")
            print(f"  Current Stock: {insight.current_inventory}")
            print(f"  Predicted Demand: {insight.predicted_demand:.0f} units (30d)")
            print(f"  Confidence: {insight.confidence_score:.1%}")
            print(f"  Potential Revenue: €{insight.potential_revenue:,.2f}")

            print(f"  Recommended Actions:")
            for action in insight.recommended_actions:
                print(f"    • {action['action']}: {action['description']}")

        print(f"\n⚠️  HIGH PRIORITY ({len(high)} items) - Act within 1-3 days:")
        for insight in high[:5]:
            print(f"\n- {insight.title}")
            print(f"  {insight.description}")
            print(f"  Confidence: {insight.confidence_score:.1%}")
```

**Example Output**:
```
💡 Predictive Inventory Insights
============================================================
Total Insights: 47

🚨 CRITICAL (8 items) - Act immediately:

- Restock Opportunity: Nike Air Jordan 1 "Chicago"
  Stock levels critically low with high predicted demand
  Product: Nike Air Jordan 1 Retro High OG "Chicago"
  Current Stock: 3
  Predicted Demand: 42 units (30d)
  Confidence: 94.5%
  Potential Revenue: €6,299.58
  Recommended Actions:
    • RESTOCK: Order 40-50 units immediately
    • INCREASE_PRICE: Raise price by 10% due to high demand
    • PRIORITIZE: Fast-track order processing

- Demand Surge Detected: Adidas Yeezy Boost 350 V2 "Zebra"
  25% demand increase detected in last 7 days
  Product: Adidas Yeezy Boost 350 V2 "Zebra"
  Current Stock: 12
  Predicted Demand: 38 units (30d)
  Confidence: 91.2%
  Potential Revenue: €8,360.00
  Recommended Actions:
    • RESTOCK: Order 25-30 units within 48h
    • HOLD_INVENTORY: Don't discount - demand is rising
    • MONITOR: Watch for continued trend

⚠️  HIGH PRIORITY (15 items) - Act within 1-3 days:

- Seasonal Trend: Air Jordan 11 "Concord"
  Holiday season approaching - historically +40% demand
  Confidence: 87.3%
```

#### Forecast Integration

```python
@dataclass
class InventoryForecast:
    product_id: UUID
    product_name: str
    current_stock: int
    predicted_demand_30d: float      # 30-day forecast
    predicted_demand_90d: float      # 90-day forecast
    restock_recommendation: str      # "urgent", "soon", "monitor"
    optimal_restock_quantity: int    # Calculated optimal order
    days_until_stockout: Optional[int]  # Estimated stockout date
    confidence_level: float          # Forecast confidence
    seasonal_factors: Dict[str, float]  # Seasonal multipliers
    market_trends: Dict[str, Any]    # StockX market data
```

---

## API Endpoints

### Inventory Management Endpoints

**Base Path**: `/api/inventory`

#### GET `/inventory`
Get inventory items with filtering and pagination.

```bash
curl "http://localhost:8000/api/inventory?status=in_stock&brand=Nike&limit=50" \
  -H "Authorization: Bearer $TOKEN"
```

**Response**:
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "product_name": "Nike Air Jordan 1",
      "brand": "Nike",
      "size": "US 10",
      "condition": "new",
      "status": "in_stock",
      "purchase_price": 159.99,
      "location": "Warehouse A",
      "days_in_inventory": 15,
      "created_at": "2025-10-22T10:00:00Z"
    }
  ],
  "pagination": {
    "total": 823,
    "skip": 0,
    "limit": 50
  }
}
```

#### GET `/inventory/stats`
Get real-time inventory statistics.

```bash
curl "http://localhost:8000/api/inventory/stats" \
  -H "Authorization: Bearer $TOKEN"
```

**Response**:
```json
{
  "total_items": 1247,
  "in_stock": 823,
  "sold": 324,
  "listed": 100,
  "total_value": 124567.00,
  "avg_purchase_price": 151.42
}
```

#### POST `/inventory/dead-stock/analyze`
Analyze dead stock and get recommendations.

```bash
curl -X POST "http://localhost:8000/api/inventory/dead-stock/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_filter": "Nike",
    "min_risk_score": 0.5
  }'
```

**Response**:
```json
{
  "total_items_analyzed": 823,
  "dead_stock_items": [
    {
      "item_id": "...",
      "product_name": "Nike Air Max 97",
      "risk_level": "critical",
      "risk_score": 0.945,
      "days_in_inventory": 245,
      "purchase_price": 189.99,
      "current_market_price": 145.00,
      "potential_loss": 44.99,
      "recommended_actions": [
        "Immediate discount (20-30%)",
        "List on multiple platforms",
        "Bundle deal"
      ]
    }
  ],
  "risk_summary": {
    "hot": 456,
    "warm": 240,
    "cold": 89,
    "dead": 32,
    "critical": 6
  },
  "financial_impact": {
    "locked_capital": 18450.00,
    "potential_loss": 4230.00
  }
}
```

#### POST `/inventory/insights/generate`
Generate AI-powered predictive insights.

```bash
curl -X POST "http://localhost:8000/api/inventory/insights/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "min_confidence": 0.75,
    "priority_filter": ["critical", "high"]
  }'
```

**Response**:
```json
{
  "insights": [
    {
      "insight_id": "INS-001",
      "insight_type": "restock_opportunity",
      "priority": "critical",
      "title": "Restock Opportunity: Nike Air Jordan 1",
      "description": "Stock levels critically low with high predicted demand",
      "product_id": "...",
      "product_name": "Nike Air Jordan 1",
      "current_inventory": 3,
      "predicted_demand": 42.0,
      "confidence_score": 0.945,
      "potential_revenue": 6299.58,
      "potential_profit": 1899.87,
      "recommended_actions": [
        {
          "action": "RESTOCK",
          "description": "Order 40-50 units immediately",
          "urgency": "immediate"
        },
        {
          "action": "INCREASE_PRICE",
          "description": "Raise price by 10% due to high demand"
        }
      ],
      "expires_at": "2025-11-08T00:00:00Z"
    }
  ]
}
```

---

## Usage Examples

### Complete Inventory Optimization Workflow

```python
async def optimize_inventory_workflow():
    """
    Complete workflow: Analyze dead stock, generate insights, take action
    """
    async with db_manager.get_session() as session:
        # Step 1: Analyze dead stock
        print("=" * 70)
        print("STEP 1: Dead Stock Analysis")
        print("=" * 70)

        dead_stock_service = DeadStockService(session)
        dead_analysis = await dead_stock_service.analyze_dead_stock(
            min_risk_score=0.5
        )

        print(f"\n✅ Analyzed {dead_analysis.total_items_analyzed} items")
        print(f"🚨 Found {len(dead_analysis.dead_stock_items)} dead stock items")
        print(f"💰 Locked Capital: €{dead_analysis.financial_impact['locked_capital']:,.2f}")

        # Step 2: Generate predictive insights
        print("\n" + "=" * 70)
        print("STEP 2: Predictive Insights Generation")
        print("=" * 70)

        insights_service = PredictiveInsightsService(session)
        insights = await insights_service.generate_inventory_insights(
            min_confidence=0.75
        )

        critical_insights = [i for i in insights if i.priority.value == "critical"]
        print(f"\n✅ Generated {len(insights)} insights")
        print(f"🚨 {len(critical_insights)} require immediate action")

        # Step 3: Execute actions for critical insights
        print("\n" + "=" * 70)
        print("STEP 3: Action Execution")
        print("=" * 70)

        pricing_service = SmartPricingService(session)

        for insight in critical_insights:
            print(f"\n📋 Processing: {insight.title}")

            if insight.insight_type == InsightType.RESTOCK_OPPORTUNITY:
                # Create purchase order
                print(f"   • Creating purchase order for {insight.optimal_restock_quantity} units")
                # await create_purchase_order(...)

            elif insight.insight_type == InsightType.CLEARANCE_ALERT:
                # Apply discount pricing
                print(f"   • Applying clearance discount")
                # Reduce price by 20-30%
                new_price = insight.current_price * Decimal("0.75")
                # await pricing_service.update_price(...)

            elif insight.insight_type == InsightType.PROFIT_OPTIMIZATION:
                # Increase price
                print(f"   • Increasing price by 10%")
                # await pricing_service.update_price(...)

            print(f"   ✅ Action completed")

        # Step 4: Generate summary report
        print("\n" + "=" * 70)
        print("STEP 4: Summary Report")
        print("=" * 70)

        total_potential_revenue = sum(
            i.potential_revenue for i in critical_insights
            if i.potential_revenue
        )

        print(f"\n📊 Optimization Summary:")
        print(f"   • Dead Stock Items: {len(dead_analysis.dead_stock_items)}")
        print(f"   • Locked Capital: €{dead_analysis.financial_impact['locked_capital']:,.2f}")
        print(f"   • Actions Taken: {len(critical_insights)}")
        print(f"   • Potential Revenue: €{total_potential_revenue:,.2f}")
        print(f"\n✅ Optimization Complete!")
```

---

## Inventory Optimization

### Key Metrics

**Inventory Turnover Ratio**:
```
Turnover = Cost of Goods Sold / Average Inventory Value

Target: 8-12x per year (healthy turnover)
```

**Days Inventory Outstanding (DIO)**:
```
DIO = (Average Inventory / COGS) × 365 days

Target: 30-45 days
```

**Inventory-to-Sales Ratio**:
```
Ratio = Inventory Value / Sales Revenue

Target: <0.2 (20% or less)
```

---

## Testing

### Unit Tests

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_dead_stock_risk_calculation():
    """Test dead stock risk scoring"""
    service = DeadStockService(mock_session)

    # Create mock inventory item (245 days old)
    item = InventoryItemFactory(
        purchase_price=Decimal("189.99"),
        created_at=datetime.now(timezone.utc) - timedelta(days=245)
    )

    risk_score = await service._calculate_risk_score(item)

    assert risk_score > 0.9  # Should be critical risk
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_predictive_insights_generation(db_session):
    """Test insights generation with real data"""
    # Create test products with varying demand
    products = [
        ProductFactory(name=f"Product {i}")
        for i in range(10)
    ]

    # Create historical sales data
    for product in products[:5]:
        for day in range(90):
            TransactionFactory(
                product_id=product.id,
                quantity=10 + (day % 5),
                order_date=date.today() - timedelta(days=90-day)
            )

    await db_session.commit()

    # Generate insights
    service = PredictiveInsightsService(db_session)
    insights = await service.generate_inventory_insights()

    # Verify insights generated
    assert len(insights) > 0
    assert any(i.insight_type == InsightType.RESTOCK_OPPORTUNITY for i in insights)
```

---

## See Also

- [Analytics Domain Guide](./ANALYTICS_DOMAIN.md) - Forecasting integration
- [Pricing Domain Guide](./PRICING_DOMAIN.md) - Pricing optimization
- [Integration Domain Guide](./INTEGRATION_DOMAIN.md) - StockX sync
- [Repository Pattern Guide](../patterns/REPOSITORY_PATTERN.md) - Data access patterns

---

**Last Updated**: 2025-11-06
**Maintainer**: SoleFlipper Development Team
**Status**: ✅ Production Ready
