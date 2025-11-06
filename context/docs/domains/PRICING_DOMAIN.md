# Pricing Domain Guide

**Domain**: `domains/pricing/`
**Purpose**: Intelligent pricing strategies, auto-listing, and profit optimization
**Last Updated**: 2025-11-06

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Pricing Strategies](#pricing-strategies)
4. [Core Services](#core-services)
5. [API Endpoints](#api-endpoints)
6. [Pricing Rules System](#pricing-rules-system)
7. [Usage Examples](#usage-examples)
8. [Error Handling](#error-handling)
9. [Testing](#testing)

---

## Overview

The Pricing domain handles intelligent pricing calculation, profit optimization, and automated listing creation. It combines multiple pricing strategies with real-time market data to determine optimal prices.

### Key Responsibilities

- **Smart Pricing**: Multi-strategy pricing engine with confidence scoring
- **Market-Based Pricing**: Real-time StockX market data integration
- **Auto-Listing**: Automated listing creation on StockX and other platforms
- **Profit Optimization**: Dynamic repricing to maximize profit margins
- **Price Rules**: Configurable pricing rules by brand, category, platform
- **Condition-Based Pricing**: Automatic price adjustments based on product condition

### Domain Structure

```
domains/pricing/
├── api/                          # REST API endpoints
│   └── router.py                 # Pricing calculation endpoints
├── services/                     # Business logic
│   ├── pricing_engine.py        # Core pricing strategies ⭐ CORE
│   ├── smart_pricing_service.py # StockX-integrated pricing ⭐ CORE
│   └── auto_listing_service.py  # Automated listing creation
├── repositories/                 # Data access
│   └── pricing_repository.py    # Price rules and history
└── models.py                     # Domain models (PriceRule, MarketPrice)
```

---

## Architecture

### Service Interaction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Pricing Domain                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │  Smart Pricing   │────────▶│  Pricing Engine  │             │
│  │  Service         │         │  (Strategies)    │             │
│  └──────────────────┘         └──────────────────┘             │
│         │                              │                        │
│         │                              ▼                        │
│         │                     ┌──────────────────┐             │
│         │                     │  Pricing Rules   │             │
│         │                     │  Repository      │             │
│         │                     └──────────────────┘             │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │  StockX Service  │         │  Auto Listing    │             │
│  │  (Market Data)   │         │  Service         │             │
│  └──────────────────┘         └──────────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Pattern

1. **Pricing Request** → Pricing Engine → Strategy Execution → Rule Application → Result
2. **Market Data Integration** → StockX API → Smart Pricing Service → Price Optimization
3. **Auto-Listing** → Pricing Calculation → Listing Creation → StockX API

---

## Pricing Strategies

### Available Strategies

The Pricing Engine supports 5 core pricing strategies:

```python
class PricingStrategy(Enum):
    COST_PLUS = "cost_plus"          # Cost + markup percentage
    MARKET_BASED = "market_based"    # Based on current market prices
    COMPETITIVE = "competitive"       # Beat competitor prices
    VALUE_BASED = "value_based"      # Based on perceived value
    DYNAMIC = "dynamic"              # Real-time market conditions
```

### Strategy Selection Matrix

| Strategy | Best For | Data Required | Confidence Score |
|----------|----------|---------------|------------------|
| **COST_PLUS** | New products, stable markets | Purchase price | High (90-100%) |
| **MARKET_BASED** | StockX listings, liquid markets | Market data (bids/asks) | Very High (95-100%) |
| **COMPETITIVE** | Multi-platform selling | Competitor prices | High (85-95%) |
| **VALUE_BASED** | Rare items, collectibles | Brand value, rarity | Medium (70-85%) |
| **DYNAMIC** | High-demand items, volatile markets | Historical trends, velocity | High (80-95%) |

---

## Core Services

### 1. PricingEngine (`pricing_engine.py`)

**Purpose**: Core pricing calculation engine with multiple strategies and confidence scoring.

**Location**: `domains/pricing/services/pricing_engine.py`

#### Key Features

- **Multi-Strategy Execution**: Runs multiple strategies in parallel
- **Confidence Scoring**: Each strategy returns confidence score (0-100%)
- **Price Rule Application**: Brand, category, and platform-specific rules
- **Price Range Calculation**: Min/max price boundaries
- **Margin Calculation**: Automatic profit margin and markup percentages

#### PricingContext Data Class

```python
@dataclass
class PricingContext:
    """Input data for pricing calculations"""

    product: Product                          # Required
    inventory_item: Optional[InventoryItem]   # Optional (for cost-based pricing)
    platform_id: Optional[UUID]               # Optional (for platform rules)
    condition: str = "new"                    # Product condition
    size: Optional[str] = None                # Shoe size or apparel size
    target_margin: Optional[Decimal] = None   # Desired profit margin %
    market_data: Optional[Dict]               # StockX market data
    competitor_data: Optional[Dict]           # Competitor prices
```

#### PricingResult Data Class

```python
@dataclass
class PricingResult:
    """Output of pricing calculation"""

    suggested_price: Decimal           # Final recommended price
    strategy_used: PricingStrategy     # Which strategy was selected
    confidence_score: Decimal          # 0-100% confidence
    margin_percent: Decimal            # Profit margin %
    markup_percent: Decimal            # Markup %
    reasoning: List[str]               # Human-readable explanation
    market_position: Optional[str]     # "competitive", "premium", "budget"
    price_range: Optional[Dict]        # {"min": X, "max": Y}
    adjustments_applied: Optional[List] # Rule adjustments
```

#### Usage Example: Basic Pricing

```python
from domains.pricing.services.pricing_engine import PricingEngine, PricingContext, PricingStrategy

async def calculate_price_example():
    async with db_manager.get_session() as session:
        engine = PricingEngine(session)

        # Get product and inventory
        product = await get_product(product_id)
        inventory_item = await get_inventory_item(inventory_id)

        # Create pricing context
        context = PricingContext(
            product=product,
            inventory_item=inventory_item,
            condition="new",
            size="US 10",
            target_margin=Decimal("25.0")  # 25% profit margin
        )

        # Calculate optimal price (tries multiple strategies)
        result = await engine.calculate_optimal_price(
            context=context,
            strategies=[
                PricingStrategy.MARKET_BASED,
                PricingStrategy.COMPETITIVE,
                PricingStrategy.COST_PLUS
            ]
        )

        print(f"Suggested Price: €{result.suggested_price}")
        print(f"Strategy Used: {result.strategy_used.value}")
        print(f"Confidence: {result.confidence_score}%")
        print(f"Profit Margin: {result.margin_percent}%")
        print(f"\nReasoning:")
        for reason in result.reasoning:
            print(f"  - {reason}")
```

**Example Output**:
```
Suggested Price: €189.99
Strategy Used: market_based
Confidence: 95.5%
Profit Margin: 28.3%

Reasoning:
  - Using market-based pricing strategy
  - StockX lowest ask: €199.99
  - Positioned 5% below market to sell quickly
  - Applied 10% brand premium for Nike Jordan
  - Target margin of 25% achieved (actual: 28.3%)
```

---

### Strategy Implementation Details

#### 1. COST_PLUS Strategy

**Formula**: `Price = Cost × (1 + Markup%)`

**Best For**:
- Products with known purchase price
- Stable markets with predictable demand
- Wholesale/retail pricing

**Example**:
```python
async def cost_plus_example():
    # Purchase price: €100
    # Target markup: 50%
    # Expected price: €150

    context = PricingContext(
        product=product,
        inventory_item=inventory_item,  # inventory_item.purchase_price = €100
        target_margin=Decimal("33.33")  # 50% markup = 33.33% margin
    )

    result = await engine.calculate_optimal_price(
        context=context,
        strategies=[PricingStrategy.COST_PLUS]
    )

    # result.suggested_price = €150.00
    # result.margin_percent = 33.33%
    # result.markup_percent = 50.0%
```

**Reasoning Logic**:
- Uses `inventory_item.purchase_price` as base cost
- If no purchase price, estimates cost from historical data
- Applies brand/category markup rules
- Ensures minimum profit margin is met

---

#### 2. MARKET_BASED Strategy

**Formula**: `Price = f(Lowest Ask, Highest Bid, Market Velocity, Competition)`

**Best For**:
- StockX listings with active market
- Liquid markets with high trading volume
- Time-sensitive repricing

**Example**:
```python
async def market_based_example():
    # StockX market data:
    # - Lowest Ask: €199.99
    # - Highest Bid: €175.00
    # - 30-day sales velocity: 25 sales/month

    market_data = {
        "lowest_ask": Decimal("199.99"),
        "highest_bid": Decimal("175.00"),
        "sales_velocity": 25,
        "ask_count": 50,
        "bid_count": 30
    }

    context = PricingContext(
        product=product,
        market_data=market_data
    )

    result = await engine.calculate_optimal_price(
        context=context,
        strategies=[PricingStrategy.MARKET_BASED]
    )

    # result.suggested_price = €189.99
    # (5% below lowest ask for competitive positioning)
```

**Reasoning Logic**:
1. **High Velocity Market** (>20 sales/month):
   - Price 5-10% below lowest ask for quick sale

2. **Medium Velocity Market** (10-20 sales/month):
   - Price at or slightly below lowest ask

3. **Low Velocity Market** (<10 sales/month):
   - Price at highest bid + 10% (patience pricing)

4. **Consider Competition**:
   - Many asks (>30): Price aggressively (10-15% below lowest ask)
   - Few asks (<10): Price at market (0-5% below lowest ask)

---

#### 3. COMPETITIVE Strategy

**Formula**: `Price = min(Competitor Prices) - Undercut%`

**Best For**:
- Multi-platform selling (eBay, GOAT, Alias)
- High competition markets
- Price wars

**Example**:
```python
async def competitive_example():
    competitor_data = {
        "ebay_price": Decimal("210.00"),
        "goat_price": Decimal("205.00"),
        "alias_price": Decimal("215.00"),
        "stockx_lowest_ask": Decimal("199.99")
    }

    context = PricingContext(
        product=product,
        competitor_data=competitor_data
    )

    result = await engine.calculate_optimal_price(
        context=context,
        strategies=[PricingStrategy.COMPETITIVE]
    )

    # result.suggested_price = €194.99
    # (€5 below lowest competitor: StockX €199.99)
```

**Reasoning Logic**:
- Find lowest competitor price
- Undercut by configurable percentage (default: 2-5%)
- Ensure minimum profit margin is maintained
- Consider platform fees in calculation

---

#### 4. VALUE_BASED Strategy

**Formula**: `Price = f(Brand Value, Rarity, Condition, Hype Score)`

**Best For**:
- Rare/limited edition items
- Collectibles with subjective value
- High-demand hyped releases

**Example**:
```python
async def value_based_example():
    # Nike x Off-White collaboration (high hype)
    # Limited release: 5,000 units worldwide
    # Brand collaboration premium

    context = PricingContext(
        product=product,  # product.brand = "Nike x Off-White"
        condition="new",
        size="US 10"
    )

    result = await engine.calculate_optimal_price(
        context=context,
        strategies=[PricingStrategy.VALUE_BASED]
    )

    # Applies premiums:
    # - Collaboration premium: +30%
    # - Limited edition premium: +20%
    # - Hype score premium: +15%
    # Total premium: +65%
```

**Reasoning Logic**:
- **Brand Premium**: Nike Jordan (+10%), Yeezy (+15%), Off-White (+30%)
- **Collaboration Premium**: Brand x Artist (+20-40%)
- **Rarity Premium**: Limited release (+10-30% based on unit count)
- **Condition Premium**: Deadstock (+20%), Excellent (+10%), Good (0%)
- **Hype Score**: Social media mentions, search trends (+0-25%)

---

#### 5. DYNAMIC Strategy

**Formula**: `Price = f(Time, Demand Trend, Inventory Age, Market Condition)`

**Best For**:
- Time-sensitive inventory (seasonal items)
- Dead stock optimization
- Market trend following

**Example**:
```python
async def dynamic_example():
    # Jordan 1 in inventory for 45 days
    # Price has dropped 15% in last 30 days
    # Market condition: BEARISH

    context = PricingContext(
        product=product,
        inventory_item=inventory_item,  # days_in_inventory = 45
        market_data={
            "price_trend_30d": Decimal("-15.0"),  # -15% in 30 days
            "market_condition": "bearish"
        }
    )

    result = await engine.calculate_optimal_price(
        context=context,
        strategies=[PricingStrategy.DYNAMIC]
    )

    # Applies dynamic adjustments:
    # - Age discount: -10% (>30 days old)
    # - Bearish market: -5%
    # - Quick turnover priority: -5%
    # Total adjustment: -20%
```

**Reasoning Logic**:

**Inventory Age Discount**:
- 0-30 days: 0% discount
- 31-60 days: -5% to -10%
- 61-90 days: -10% to -20%
- >90 days: -20% to -30% (dead stock)

**Market Condition Adjustment**:
- BULLISH: +5% to +10% (rising prices)
- STABLE: 0% (no adjustment)
- BEARISH: -5% to -10% (falling prices)
- VOLATILE: Use conservative pricing (-5%)

**Demand Trend**:
- Rising demand (+10% in 30d): Increase price +5%
- Falling demand (-10% in 30d): Decrease price -5%

---

### 2. SmartPricingService (`smart_pricing_service.py`)

**Purpose**: StockX-integrated pricing automation with real-time market data and profit optimization.

**Location**: `domains/pricing/services/smart_pricing_service.py`

#### Key Features

- **Market Data Integration**: Real-time StockX bids/asks/sales
- **Inventory Optimization**: Bulk repricing for entire inventory
- **Market Condition Analysis**: Detects bullish/bearish/stable/volatile markets
- **Profit Maximization**: Dynamic repricing to maximize margins
- **Batch Processing**: Handles large inventories with rate limiting

#### Market Conditions

```python
class MarketCondition:
    BULLISH = "bullish"      # Rising prices, high demand
    BEARISH = "bearish"      # Falling prices, low demand
    STABLE = "stable"        # Steady prices, moderate demand
    VOLATILE = "volatile"    # Rapid price swings
```

#### Repricing Strategies

```python
# Available repricing strategies:
"profit_maximization"     # Maximize profit margins
"market_competitive"      # Stay competitive with market
"quick_turnover"          # Price for fast sales
"premium_positioning"     # Price as premium option
```

#### Usage Example: Inventory Optimization

```python
from domains.pricing.services.smart_pricing_service import SmartPricingService

async def optimize_inventory_pricing():
    async with db_manager.get_session() as session:
        service = SmartPricingService(session)

        # Optimize all inventory
        result = await service.optimize_inventory_pricing(
            inventory_items=None,  # None = all items
            repricing_strategy="profit_maximization"
        )

        print(f"Items Processed: {result['total_items_processed']}")
        print(f"Successful Updates: {result['successful_optimizations']}")
        print(f"Potential Profit Increase: €{result['potential_profit_increase']}")
        print(f"Processing Time: {result['processing_time_ms']}ms")

        # View pricing updates
        for update in result['pricing_updates']:
            print(f"\n{update['product_name']}")
            print(f"  Old Price: €{update['old_price']}")
            print(f"  New Price: €{update['new_price']}")
            print(f"  Price Change: {update['price_change_percent']}%")
            print(f"  Profit Increase: €{update['profit_increase']}")
```

**Example Output**:
```
Items Processed: 150
Successful Updates: 142
Potential Profit Increase: €2,450.00
Processing Time: 45,320ms

Nike Air Jordan 1 Retro High OG "Chicago"
  Old Price: €199.99
  New Price: €214.99
  Price Change: +7.5%
  Profit Increase: €15.00

Adidas Yeezy Boost 350 V2 "Zebra"
  Old Price: €250.00
  New Price: €235.00
  Price Change: -6.0%
  Profit Increase: €8.50 (faster turnover)
```

#### Usage Example: Dynamic Price Recommendation

```python
async def get_price_recommendation_example():
    async with db_manager.get_session() as session:
        service = SmartPricingService(session)

        inventory_item = await get_inventory_item(item_id)

        # Get recommendation for 7-day sell target
        recommendation = await service.get_dynamic_price_recommendation(
            inventory_item=inventory_item,
            target_sell_timeframe=7  # days
        )

        print(f"Recommended Price: €{recommendation['suggested_price']}")
        print(f"Market Position: {recommendation['market_position']}")
        print(f"Expected Sell Time: {recommendation['estimated_sell_days']} days")
        print(f"Confidence: {recommendation['confidence_score']}%")

        # Market insights
        print(f"\nMarket Insights:")
        print(f"  Current Market: {recommendation['market_condition']}")
        print(f"  30-Day Trend: {recommendation['price_trend_30d']}%")
        print(f"  Sales Velocity: {recommendation['sales_velocity']}/month")
```

---

### 3. AutoListingService (`auto_listing_service.py`)

**Purpose**: Automated listing creation on StockX and other marketplaces.

**Location**: `domains/pricing/services/auto_listing_service.py`

#### Key Features

- **Automatic Price Calculation**: Uses PricingEngine for optimal pricing
- **Multi-Platform Support**: StockX, eBay, GOAT, Alias
- **Condition-Based Pricing**: Automatic adjustments for used items
- **Bulk Listing**: Process multiple items efficiently
- **Listing Validation**: Pre-flight checks before submission

#### Usage Example: Auto-List Inventory

```python
from domains.pricing.services.auto_listing_service import AutoListingService

async def auto_list_inventory():
    async with db_manager.get_session() as session:
        service = AutoListingService(session)

        # Get unlisted inventory
        inventory_items = await get_unlisted_inventory()

        # Create listings automatically
        result = await service.create_bulk_listings(
            inventory_items=inventory_items,
            platform="stockx",
            pricing_strategy=PricingStrategy.MARKET_BASED
        )

        print(f"Listings Created: {result['successful_listings']}")
        print(f"Failed: {result['failed_listings']}")

        # View created listings
        for listing in result['listings']:
            print(f"\n{listing['product_name']} (Size: {listing['size']})")
            print(f"  Price: €{listing['price']}")
            print(f"  Platform: {listing['platform']}")
            print(f"  Listing ID: {listing['listing_id']}")
```

---

## API Endpoints

### Pricing Calculation Endpoints

**Base Path**: `/api/pricing`

#### POST `/calculate`
Calculate optimal price for a product.

**Request**:
```bash
curl -X POST "http://localhost:8000/api/pricing/calculate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "550e8400-e29b-41d4-a716-446655440000",
    "inventory_item_id": "660e8400-e29b-41d4-a716-446655440001",
    "condition": "new",
    "size": "US 10",
    "target_margin": 25.0,
    "strategies": ["market_based", "competitive", "cost_plus"]
  }'
```

**Response**:
```json
{
  "suggested_price": 189.99,
  "strategy_used": "market_based",
  "confidence_score": 95.5,
  "margin_percent": 28.3,
  "markup_percent": 39.5,
  "reasoning": [
    "Using market-based pricing strategy",
    "StockX lowest ask: €199.99",
    "Positioned 5% below market to sell quickly",
    "Applied 10% brand premium for Nike Jordan",
    "Target margin of 25% achieved (actual: 28.3%)"
  ],
  "market_position": "competitive",
  "price_range": {
    "min": 179.99,
    "max": 209.99
  }
}
```

#### POST `/optimize-inventory`
Optimize pricing for entire inventory.

**Request**:
```bash
curl -X POST "http://localhost:8000/api/pricing/optimize-inventory" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repricing_strategy": "profit_maximization",
    "filter": {
      "brand": "Nike",
      "min_days_old": 30
    }
  }'
```

**Response**:
```json
{
  "total_items_processed": 150,
  "successful_optimizations": 142,
  "potential_profit_increase": 2450.00,
  "processing_time_ms": 45320,
  "pricing_updates": [
    {
      "product_id": "...",
      "product_name": "Nike Air Jordan 1",
      "old_price": 199.99,
      "new_price": 214.99,
      "price_change_percent": 7.5,
      "profit_increase": 15.00
    }
  ]
}
```

---

## Pricing Rules System

### Rule Types

Pricing rules allow fine-grained control over pricing calculations:

```python
class PriceRule:
    rule_type: str              # "cost_plus", "margin", "discount", "premium"
    target_type: str            # "brand", "category", "platform", "condition"
    target_value: str           # "Nike", "Sneakers", "stockx", "new"
    adjustment_type: str        # "percentage", "fixed"
    adjustment_value: Decimal   # 10.0 (10% or €10)
    priority: int               # Higher = applied first
    is_active: bool
```

### Example Rules

**Brand Premium Rule**:
```python
# Apply 10% premium to all Nike products
PriceRule(
    rule_type="premium",
    target_type="brand",
    target_value="Nike",
    adjustment_type="percentage",
    adjustment_value=Decimal("10.0"),
    priority=100
)
```

**Platform Fee Rule**:
```python
# Add 10% to cover StockX fees
PriceRule(
    rule_type="cost_plus",
    target_type="platform",
    target_value="stockx",
    adjustment_type="percentage",
    adjustment_value=Decimal("10.0"),
    priority=50
)
```

**Condition Discount Rule**:
```python
# 20% discount for used items
PriceRule(
    rule_type="discount",
    target_type="condition",
    target_value="used",
    adjustment_type="percentage",
    adjustment_value=Decimal("20.0"),
    priority=80
)
```

### Rule Application Order

Rules are applied in priority order (highest first):

1. **Priority 100+**: Brand/category premiums
2. **Priority 80-99**: Condition adjustments
3. **Priority 50-79**: Platform fees
4. **Priority 1-49**: General discounts/adjustments

---

## Usage Examples

### Complete Pricing Workflow

```python
async def complete_pricing_workflow():
    """
    Complete example: Calculate price, create listing, monitor sales
    """
    async with db_manager.get_session() as session:
        # Step 1: Get product and inventory
        product = await get_product(product_id)
        inventory_item = await get_inventory_item(inventory_id)

        # Step 2: Get real-time market data
        stockx_service = StockXService(session)
        market_data = await stockx_service.get_market_data_from_stockx(
            product.stockx_product_id
        )

        # Step 3: Calculate optimal price
        pricing_engine = PricingEngine(session)
        context = PricingContext(
            product=product,
            inventory_item=inventory_item,
            condition="new",
            size="US 10",
            target_margin=Decimal("25.0"),
            market_data={
                "lowest_ask": market_data["lowest_ask"],
                "highest_bid": market_data["highest_bid"],
                "sales_velocity": market_data["sales_last_30_days"]
            }
        )

        result = await pricing_engine.calculate_optimal_price(
            context=context,
            strategies=[PricingStrategy.MARKET_BASED, PricingStrategy.COST_PLUS]
        )

        print(f"✅ Calculated Price: €{result.suggested_price}")
        print(f"   Strategy: {result.strategy_used.value}")
        print(f"   Confidence: {result.confidence_score}%")

        # Step 4: Create listing on StockX
        auto_listing_service = AutoListingService(session)
        listing = await auto_listing_service.create_listing(
            inventory_item=inventory_item,
            price=result.suggested_price,
            platform="stockx"
        )

        print(f"✅ Listing Created: {listing.listing_id}")

        # Step 5: Monitor and reprice if needed
        await asyncio.sleep(86400)  # Wait 1 day

        # Check if listing sold
        listing_status = await auto_listing_service.get_listing_status(listing.id)

        if listing_status.status == "active":  # Not sold yet
            print("Listing still active, repricing...")

            # Get updated market data
            updated_market_data = await stockx_service.get_market_data_from_stockx(
                product.stockx_product_id
            )

            # Recalculate with dynamic strategy
            context.market_data = updated_market_data
            new_result = await pricing_engine.calculate_optimal_price(
                context=context,
                strategies=[PricingStrategy.DYNAMIC]
            )

            # Update listing price
            await auto_listing_service.update_listing_price(
                listing_id=listing.id,
                new_price=new_result.suggested_price
            )

            print(f"✅ Listing Repriced: €{new_result.suggested_price}")
```

---

## Error Handling

### Common Errors and Solutions

#### 1. No Market Data Available

**Error**: `ValueError: No market data available for pricing`

**Solution**:
```python
# Fallback to cost-plus strategy
try:
    result = await engine.calculate_optimal_price(
        context=context,
        strategies=[PricingStrategy.MARKET_BASED]
    )
except ValueError:
    # Fallback to cost-plus
    result = await engine.calculate_optimal_price(
        context=context,
        strategies=[PricingStrategy.COST_PLUS]
    )
```

#### 2. No Purchase Price (Cost-Plus)

**Error**: `ValueError: No purchase price for cost-plus strategy`

**Solution**:
```python
# Estimate cost from historical data
if not inventory_item.purchase_price:
    estimated_cost = await engine._estimate_product_cost(product)
    inventory_item.purchase_price = estimated_cost
```

#### 3. Price Below Minimum Margin

**Error**: `ValidationError: Price below minimum profit margin`

**Solution**:
```python
# Adjust target margin or use different strategy
context.target_margin = Decimal("10.0")  # Lower target
result = await engine.calculate_optimal_price(context)
```

---

## Testing

### Unit Tests

**Location**: `tests/unit/domains/pricing/`

```bash
# Test pricing engine
pytest tests/unit/domains/pricing/test_pricing_engine.py -v

# Test smart pricing service
pytest tests/unit/domains/pricing/test_smart_pricing_service.py -v

# Test auto-listing service
pytest tests/unit/domains/pricing/test_auto_listing_service.py -v
```

### Integration Tests

**Location**: `tests/integration/domains/pricing/`

```bash
# Test pricing with real market data
pytest tests/integration/domains/pricing/test_pricing_integration.py -v

# Test auto-listing workflow
pytest tests/integration/domains/pricing/test_auto_listing_workflow.py -v
```

### Testing Checklist

- [ ] Test all 5 pricing strategies with various inputs
- [ ] Test rule application order (priority handling)
- [ ] Test edge cases: zero cost, no market data, negative margins
- [ ] Test market condition detection (bullish, bearish, stable, volatile)
- [ ] Test inventory optimization with large datasets (>1000 items)
- [ ] Test auto-listing with rate limiting
- [ ] Test price repricing logic
- [ ] Test confidence score calculation
- [ ] Load test: 1000 pricing calculations per minute

---

## See Also

- [Integration Domain Guide](./INTEGRATION_DOMAIN.md) - StockX market data integration
- [API Endpoints Reference](../API_ENDPOINTS.md) - Complete API documentation
- [Repository Pattern Guide](../patterns/REPOSITORY_PATTERN.md) - Data access patterns
- [CLAUDE.md](../../CLAUDE.md) - Architecture overview

---

**Last Updated**: 2025-11-06
**Maintainer**: SoleFlipper Development Team
**Status**: ✅ Production Ready
