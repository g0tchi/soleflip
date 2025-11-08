# SoleFlip Arbitrage & Monetization Strategy

**Document Version:** 1.0
**Last Updated:** 2025-11-08
**Status:** Planning Phase - No Implementation Yet

---

## Executive Summary

This document outlines the monetization strategy for the SoleFlip API, focusing on two primary revenue streams:
1. **Arbitrage Alert Service** - Real-time notifications of profitable arbitrage opportunities
2. **Smart Cross-Platform Listing Automation** - Automated multi-platform listing optimization

**Key Finding:** The SoleFlip codebase is already **70-80% ready** for arbitrage features, with existing infrastructure including QuickFlip detection, multi-platform integration, and ML forecasting capabilities.

---

## Current State Analysis

### ✅ Existing Capabilities (Production-Ready)

#### 1. Multi-Platform Integration
- **StockX Integration** (`domains/integration/services/stockx_service.py`)
  - OAuth2 with automatic token refresh
  - Product enrichment (lowest_ask, highest_bid, recommended prices)
  - Historical orders API with pagination

- **Unified Order Management** (Gibson v2.4 Schema)
  - Single `orders` table supporting StockX, eBay, GOAT/Alias
  - Platform-agnostic design with `platform_id` and `external_id`
  - Comprehensive profit tracking: `platform_fee`, `shipping_cost`, `net_proceeds`, `roi`

- **Awin Affiliate Network** (`domains/integration/services/awin_feed_service.py`)
  - Product feed download (CSV/gzip)
  - 96+ data fields including price, stock, delivery cost
  - Supplier linking and commission tracking

- **Unified Price Import Service** (`domains/integration/services/unified_price_import_service.py`)
  - Supports: Awin, eBay, StockX, GOAT, Klekt, WebGains
  - `SourcePrice` model for all retail/resale sources
  - Cross-platform profit opportunity detection

#### 2. Arbitrage Detection (Production-Ready)
**QuickFlip Detection Service** (`domains/integration/services/quickflip_detection_service.py`)
- Purpose-built arbitrage engine with configurable filters
- Default thresholds: 10% minimum margin, €20 minimum gross profit
- Data model includes: buy_price, sell_price, gross_profit, profit_margin, ROI
- API endpoints:
  - `GET /api/integration/quickflip/opportunities` - Find with filters
  - `GET /api/integration/quickflip/opportunities/summary` - Statistics
  - `GET /api/integration/quickflip/opportunities/product/{product_id}` - By product
  - `POST /api/integration/quickflip/opportunities/mark-acted` - Track actions

#### 3. Pricing & Analytics
- **Comprehensive Price Models:**
  - `SourcePrice` - Retail and resale prices from any source
  - `MarketPrice` - External market data with bid/ask spreads
  - `PriceHistory` - Historical price tracking by platform
  - `MarketplaceData` - Per-item platform metrics (volatility, sales frequency)

- **ML-Powered Forecasting** (`domains/analytics/services/forecast_engine.py`)
  - Models: Linear Trend, Seasonal Naive, ARIMA, Random Forest, Gradient Boost, Ensemble
  - Multi-level forecasting: Product, Brand, Category, Platform
  - Confidence intervals and accuracy tracking (MAPE, RMSE, MAE, R²)

- **Demand Analysis:**
  - `DemandPattern` model tracks velocity, seasonality, trend direction
  - `PricingKPI` for performance metrics (margin, markup, conversion rate)

#### 4. Inventory Management
- **Multi-Platform Listing Status:**
  - `listed_stockx`, `listed_alias`, `listed_local` flags
  - `detailed_status` enum: incoming, available, consigned, outgoing, sale_completed, etc.

- **Advanced Cost Tracking:**
  - Gross/net purchase price with VAT separation
  - ROI metrics: `roi_percentage`, `profit_per_shelf_day`, `shelf_life_days`
  - Location tracking for warehouse management

#### 5. Fee & Profit Calculation
- **Platform-Specific Fees:**
  - StockX: 8%
  - eBay: 12.8% (12% final value + 2.8% payment processing)
  - GOAT: 8%
  - Configurable via `Platform.fee_percentage`

- **Order Profit Tracking:**
  - `sale_price`, `platform_fee`, `shipping_cost`
  - `gross_sale`, `net_proceeds`, `net_profit`
  - VAT tracking (19% Germany default)

#### 6. Event & Notification Infrastructure
- **Event-Driven Architecture** (`shared/events/event_bus.py`)
  - Publish-subscribe pattern
  - Domain-level subscriptions (products.*, orders.*, integration.*)
  - Event history for debugging (last 1000 events)
  - Optional persistence to EventStore table

- **Webhook Infrastructure** (`domains/integration/api/webhooks.py`)
  - StockX order import with batch tracking
  - Import status tracking endpoint
  - Background job support

---

### ❌ Gaps Requiring Implementation

#### Gap 1: Advanced Arbitrage Execution Logic
- ❌ Automated opportunity action system
- ❌ Buy/sell execution coordination
- ❌ Inventory allocation per platform
- ❌ Simultaneous multi-platform listings
- ❌ Real-time price monitoring and alerts

#### Gap 2: Sophisticated Fee Modeling
- ❌ Destination-based shipping cost calculation
- ❌ Tax/VAT calculation per jurisdiction
- ❌ Buyer protection fees (variable by platform)
- ❌ Payment method-specific fees (card vs bank transfer)
- ❌ Volume-based fee discounts
- ❌ Dynamic fee percentage based on market conditions

#### Gap 3: Risk & Feasibility Scoring
- ❌ Demand score integration (referenced but not calculated)
- ❌ Market volatility assessment
- ❌ Seller rating impact on feasibility
- ❌ Competition analysis (number of sellers)
- ❌ Stock turnover velocity
- ❌ Risk scoring by product/brand/category
- ❌ "Days to sale" prediction

#### Gap 4: Execution Automation
- ❌ Automatic opportunity alert system
- ❌ Buy trigger and inventory allocation
- ❌ Multi-platform simultaneous listing
- ❌ Price synchronization across platforms
- ❌ Automated listing creation/updates
- ❌ Dynamic repricing based on market

#### Gap 5: Advanced Analytics
- ❌ Historical profit analysis by source/platform
- ❌ Win-rate tracking (conversion from opportunity to sale)
- ❌ Seasonality analysis by product/brand
- ❌ Competitor tracking and analysis
- ❌ Market share estimation
- ❌ Trend prediction beyond basic forecasting

#### Gap 6: Performance Optimization
- ❌ Batch opportunity detection (currently individual lookups)
- ❌ Real-time price feed integration
- ❌ Caching strategy for price comparisons
- ❌ Indexed query optimization for large datasets
- ❌ Background job prioritization

---

## Monetization Options

### Option 1: Freemium API Tiers (Simplest)
**Revenue Model:** Tiered subscription for API access

**Tiers:**
- **Free:** Limited requests/day, basic inventory management
- **Pro ($29-49/mo):** Higher limits, analytics, smart pricing
- **Enterprise ($199+/mo):** Unlimited, multi-platform sync, forecasting

**Pros:** Quick to implement, predictable revenue, low overhead
**Cons:** Requires user acquisition, limited by API value alone

---

### Option 2: Arbitrage Alert Service ⭐ (Recommended Start)
**Revenue Model:** Subscription for real-time arbitrage notifications

**How it Works:**
- Monitor price differences across StockX, eBay, GOAT
- Alert when: `(Platform A sell price - fees) > (Platform B buy price + fees + margin)`
- Deliver via webhook, email, or dashboard

**Pricing:**
```
FREE Tier:
- 10 Alerts per day
- Basic opportunity detection
- Email notifications only
- Min. €50 profit threshold

PRO Tier (€49/month):
- Unlimited Alerts
- Real-time notifications (Webhook + Email)
- Custom profit thresholds
- Risk scoring
- 7-day opportunity history

ENTERPRISE (€199/month):
- Everything in PRO
- API access
- White-label alerts
- Dedicated support
- Custom fee calculations
```

**Implementation Effort:** 2-3 weeks
**Pros:** High perceived value, uses existing data, targets active resellers
**Cons:** Requires real-time data feeds, competition may close gaps quickly

---

### Option 3: Smart Cross-Platform Listing Automation
**Revenue Model:** Subscription + performance-based fees

**How it Works:**
- Analyze inventory to determine optimal platform for each item
- Auto-list items where they'll sell for most profit (factoring fees, shipping, demand)
- Auto-delist/relist when better opportunities appear

**Pricing:**
```
BASIC (€99/month):
- Auto-list up to 50 items/month
- 2 platforms (StockX + 1 other)
- Smart pricing recommendations
- Manual approval required

PREMIUM (€299/month):
- Unlimited auto-listings
- All platforms
- Fully automated (no manual approval)
- Dynamic repricing
- Performance analytics

PROFIT SHARE (€99 + 3% of arbitrage profit):
- All PREMIUM features
- Payment only on success
- Detailed profit tracking
```

**Implementation Effort:** 3-4 weeks (builds on Option 2)
**Pros:** High automation value, stickiness (users depend on it)
**Cons:** Requires platform API integrations, legal/ToS considerations

---

### Option 4: Arbitrage Opportunity Marketplace
**Revenue Model:** Commission on completed deals

**How it Works:**
- Users with inventory list "arbitrage opportunities"
- Other users claim and execute opportunities
- Platform takes commission on completed deals

**Pricing:** 3-8% commission on deals + listing fees

**Implementation Effort:** 6-8 weeks
**Pros:** Network effects, scalable, minimal inventory risk
**Cons:** Requires critical mass of users, trust/fraud management

---

### Option 5: Full Arbitrage-as-a-Service Platform
**Revenue Model:** AUM management fee + performance fee

**How it Works:**
- Users fund account
- System automatically identifies, purchases, and resells items
- Uses ML forecasting for best opportunities
- Monthly profit share to users

**Pricing:** 2-3% AUM management fee + 20-30% performance fee

**Implementation Effort:** 12+ weeks
**Pros:** Highest revenue potential, recurring, defensible moat
**Cons:** High complexity, regulatory considerations, capital requirements, significant risk

---

## Recommended Implementation Plan

### Phase 1: Arbitrage Alert Service (Weeks 1-4) 🎯

#### Sprint 1: Alert Foundation (Weeks 1-2)
**Deliverables:**
- [ ] New database models: `ArbitrageAlert`, `ArbitrageOpportunity`, `ArbitrageExecution`
- [ ] Database migrations
- [ ] Enhanced `QuickFlipDetectionService` with demand score and risk scoring
- [ ] New `ArbitrageAlertService` for notification management
- [ ] API endpoints for CRUD operations on alerts
- [ ] Background job: `scan_opportunities()` (runs every 15 minutes)

**New Models:**
```python
class ArbitrageAlert:
    user_id: UUID
    min_profit: Decimal           # Minimum gross profit (€)
    min_margin: Decimal           # Minimum profit margin (%)
    max_buy_price: Decimal        # Maximum buy price filter
    platforms: List[str]          # StockX, eBay, GOAT
    notification_method: str      # email, webhook, dashboard
    alert_frequency: str          # real-time, hourly, daily
    active: bool

class ArbitrageOpportunity(QuickFlipOpportunity):
    risk_score: str               # LOW, MEDIUM, HIGH
    feasibility_score: int        # 0-100
    estimated_days_to_sell: int
    competition_level: str
    demand_score: float

class ArbitrageExecution:
    opportunity_id: UUID
    user_id: UUID
    claimed_at: DateTime
    purchased_at: DateTime
    listed_at: DateTime
    sold_at: DateTime
    actual_profit: Decimal
    expected_profit: Decimal
    execution_time_hours: int
    status: str                   # claimed, purchased, listed, sold, failed
```

**API Endpoints:**
```
POST   /api/arbitrage/alerts                    # Create alert rule
GET    /api/arbitrage/alerts                    # List user's alerts
PUT    /api/arbitrage/alerts/{id}              # Update alert
DELETE /api/arbitrage/alerts/{id}              # Delete alert
GET    /api/arbitrage/opportunities/live       # Real-time opportunities
POST   /api/arbitrage/opportunities/{id}/claim # Claim opportunity
GET    /api/arbitrage/alerts/performance       # Alert performance stats
```

#### Sprint 2: Fee & Shipping (Week 3)
**Deliverables:**
- [ ] `PlatformFeeCalculator` service for dynamic fee calculation
- [ ] `ShippingRate` model and database table
- [ ] Destination-based shipping cost calculator
- [ ] Integration with existing `Order.platform_fee` system
- [ ] API endpoint: `GET /api/arbitrage/fee-calculator`

**Fee Calculation Factors:**
- Platform-specific transaction fees (StockX 8%, eBay 12.8%, GOAT 8%)
- Payment processing fees (2-3%)
- Destination-based shipping costs
- VAT calculation per jurisdiction (19% Germany, variable EU)
- Currency conversion fees (if applicable)
- Volume discounts for power sellers

**Shipping Database:**
```python
class ShippingRate:
    origin_country: str
    destination_country: str
    service_level: str            # standard, express
    weight_min: float
    weight_max: float
    cost: Decimal
    currency: str
    estimated_days: int
```

#### Sprint 3: Dashboard & Tracking (Week 4)
**Deliverables:**
- [ ] Dashboard API endpoints
- [ ] Performance tracking (win-rate, profit accuracy)
- [ ] Claim/execute workflow
- [ ] Email notification templates
- [ ] Analytics: actual vs. expected profit analysis

**Dashboard Endpoints:**
```
GET /api/arbitrage/dashboard/overview
Response:
- total_opportunities_today: int
- total_potential_profit: Decimal
- best_opportunity: OpportunityDetail
- opportunities_by_platform: Dict[str, int]
- opportunities_by_category: Dict[str, int]
- avg_margin: float
- avg_profit: Decimal
```

**Performance Metrics:**
- Win-Rate: % of claimed opportunities that result in sales
- Average time to sale: Hours from claim to sale
- Profit accuracy: Actual profit vs. expected profit deviation
- Opportunity velocity: New opportunities per hour/day

---

### Phase 2: Smart Listing Automation (Weeks 5-8)

#### Sprint 4: Listing Intelligence (Weeks 5-6)
**Deliverables:**
- [ ] `SmartListingService` for platform selection
- [ ] Multi-platform pricing engine
- [ ] Dynamic repricing strategy
- [ ] Seasonal trend integration

**Platform Selection Logic:**
```python
def analyze_best_platform(inventory_item_id: UUID) -> PlatformRecommendation:
    """
    Analyzes which platform to list on based on:
    - Current market price per platform
    - Platform fees
    - Average days to sell (historical data)
    - Demand score
    - Competition level
    - Seasonal trends

    Returns:
    - recommended_platform: str
    - recommended_price: Decimal
    - confidence_score: float (0-100)
    - expected_days_to_sell: int
    - expected_net_profit: Decimal
    """
```

**Dynamic Pricing Strategy:**
```python
def repricing_strategy(listing_id: UUID, days_since_listed: int):
    """
    Auto price reduction after X days:
    - Day 0-7: List at optimal price
    - Day 8-14: Reduce by 5%
    - Day 15-21: Reduce by 10%
    - Day 22+: Reduce to floor price (minimum profit margin)

    Considers:
    - Competitive analysis (other listings)
    - Market trends (increasing/decreasing demand)
    - Inventory holding costs
    """
```

#### Sprint 5: Automated Listing Creation (Week 7)
**Deliverables:**
- [ ] `ListingAutomationService` for multi-platform listing
- [ ] Platform-specific API adapters (StockX, eBay, GOAT)
- [ ] Image upload and product description generation
- [ ] Listing sync service (prevent double-sells)

**Listing Automation Workflow:**
```python
async def create_listing(inventory_item_id: UUID, platform_id: UUID):
    """
    1. Get product details
    2. Calculate optimal price (SmartListingService)
    3. Generate platform-specific listing:
       - StockX: lowest_ask format
       - eBay: Fixed price or Auction
       - GOAT: Instant ship format
    4. Upload product images (if required)
    5. Set shipping options
    6. Activate listing
    7. Update InventoryItem flags (listed_stockx, listed_alias, etc.)
    """
```

**Sync Service (Background Job - Every 6 Hours):**
```python
async def sync_listings():
    """
    - Check for price changes on platforms
    - Update own listings if needed
    - Delist from other platforms when sold on one
    - Prevent double-sells
    - Update inventory status
    """
```

#### Sprint 6: Intelligence & Optimization (Week 8)
**Deliverables:**
- [ ] ML-based platform recommendation model
- [ ] Performance-based re-listing logic
- [ ] Feedback loop (actual vs. predicted performance)
- [ ] Monthly model retraining pipeline

**ML Optimization:**
```python
# Train model on historical successful listings
features = [
    'platform',
    'price',
    'demand_score',
    'season',
    'brand',
    'category',
    'competition_level'
]
target = 'days_to_sell'

# Predict best platform for new items
def predict_best_platform(inventory_item: InventoryItem) -> str:
    """Uses trained model to predict optimal platform"""

# Feedback loop
def track_performance(listing_id: UUID):
    """Track actual vs. predicted and retrain monthly"""
```

---

## Technical Architecture

### New Domain: `domains/arbitrage/`
```
domains/arbitrage/
├── api/
│   ├── router.py                    # Arbitrage API endpoints
│   └── schemas.py                   # Pydantic request/response models
├── services/
│   ├── alert_service.py             # Alert management
│   ├── opportunity_service.py       # Enhanced QuickFlip detection
│   ├── fee_calculator_service.py    # Dynamic fee calculation
│   ├── smart_listing_service.py     # Platform selection intelligence
│   └── listing_automation_service.py # Auto-listing logic
├── repositories/
│   ├── alert_repository.py          # Alert CRUD
│   ├── opportunity_repository.py    # Opportunity CRUD
│   └── execution_repository.py      # Execution tracking
├── models/
│   ├── alert.py                     # ArbitrageAlert model
│   ├── opportunity.py               # ArbitrageOpportunity model
│   └── execution.py                 # ArbitrageExecution model
└── events/
    └── handlers.py                  # Event-driven alerts
```

### Database Schema Changes
**New Tables:**
- `arbitrage_alerts` - User alert configurations
- `arbitrage_opportunities` - Enhanced opportunities with risk/demand scoring
- `arbitrage_executions` - Track claimed opportunities and outcomes
- `shipping_rates` - Destination-based shipping cost matrix
- `platform_fee_matrix` - Dynamic fee structure (volume discounts, special rates)

**Enhanced Tables:**
- `QuickFlipOpportunity` → Add risk_score, feasibility_score, demand_score
- `Order` → Already has required fields (platform_fee, net_profit, roi)
- `InventoryItem` → Already has multi-platform listing flags

### Background Jobs (APScheduler/Celery)
```python
@scheduler.scheduled_job('interval', minutes=15)
async def scan_arbitrage_opportunities():
    """
    Real-time opportunity scanning
    - Refresh price data from all sources
    - Run QuickFlip detection
    - Match opportunities to user alerts
    - Send notifications
    """

@scheduler.scheduled_job('interval', hours=6)
async def sync_platform_listings():
    """
    Multi-platform listing synchronization
    - Check for sales on all platforms
    - Update inventory status
    - Delist sold items from other platforms
    - Prevent double-sells
    """

@scheduler.scheduled_job('cron', hour=9, minute=0)
async def send_daily_opportunity_digest():
    """
    Daily summary email
    - Top 10 opportunities
    - Yesterday's performance
    - Market trends
    """

@scheduler.scheduled_job('cron', day=1, hour=2, minute=0)
async def retrain_ml_models():
    """
    Monthly ML model retraining
    - Collect last month's data
    - Retrain platform recommendation model
    - Update demand prediction model
    - Evaluate model performance
    """
```

---

## Integration Points

### Existing Services to Leverage
1. **QuickFlipDetectionService** - Extend with risk/demand scoring
2. **StockXService** - Already integrated, use for real-time price updates
3. **UnifiedPriceImportService** - Multi-source price aggregation
4. **ForecastEngine** - ML models for demand prediction
5. **Event Bus** - Notification delivery
6. **Order Processor** - Fee calculation and profit tracking

### External APIs Required
1. **eBay Trading API** - For automated listing creation
2. **GOAT API** - If available, for GOAT/Alias listings
3. **Shipping Carrier APIs** (Optional):
   - DHL API for real-time shipping rates
   - Hermes API for alternative rates
4. **Email Service** (SMTP) - For alert notifications
5. **SMS Service** (Optional) - Twilio for urgent alerts

---

## Revenue Projections

### Conservative Scenario (Year 1)
**Arbitrage Alert Service:**
- 50 PRO subscribers @ €49/mo = €2,450/mo = €29,400/year
- 10 ENTERPRISE @ €199/mo = €1,990/mo = €23,880/year
- **Total Alert Revenue:** €53,280/year

**Listing Automation (Starting Month 6):**
- 20 BASIC @ €99/mo = €1,980/mo = €11,880/year (6 months)
- 10 PREMIUM @ €299/mo = €2,990/mo = €17,940/year (6 months)
- **Total Automation Revenue:** €29,820/year

**Year 1 Total:** €83,100

### Optimistic Scenario (Year 1)
**Arbitrage Alert Service:**
- 150 PRO @ €49/mo = €7,350/mo = €88,200/year
- 30 ENTERPRISE @ €199/mo = €5,970/mo = €71,640/year
- **Total Alert Revenue:** €159,840/year

**Listing Automation (Starting Month 6):**
- 60 BASIC @ €99/mo = €5,940/mo = €35,640/year (6 months)
- 40 PREMIUM @ €299/mo = €11,960/mo = €71,760/year (6 months)
- 10 PROFIT SHARE @ €99 + 3% = ~€5,000/mo = €30,000/year (6 months)
- **Total Automation Revenue:** €137,400/year

**Year 1 Total:** €297,240

---

## Risk Mitigation

### Technical Risks
1. **Platform API Changes**
   - **Risk:** StockX, eBay, GOAT change APIs without notice
   - **Mitigation:** Version API adapters, monitor for changes, maintain fallback methods

2. **Rate Limiting**
   - **Risk:** Hit API rate limits during peak scanning
   - **Mitigation:** Implement exponential backoff, distribute requests, cache aggressively

3. **Data Quality**
   - **Risk:** Stale or incorrect price data leads to bad opportunities
   - **Mitigation:** Timestamp all data, validate against multiple sources, confidence scoring

### Business Risks
1. **Market Competition**
   - **Risk:** Competitors close arbitrage gaps quickly
   - **Mitigation:** Speed (15-min scanning), ML-based prediction, exclusive data sources

2. **Platform ToS Violations**
   - **Risk:** Automated listing violates platform terms of service
   - **Mitigation:** Legal review, rate limiting, manual approval options, transparency

3. **User Acquisition**
   - **Risk:** Difficulty reaching target reseller market
   - **Mitigation:** SEO, content marketing, partnerships with reseller communities

### Operational Risks
1. **Scalability**
   - **Risk:** Background jobs overload system at scale
   - **Mitigation:** Celery/Redis queue, horizontal scaling, job prioritization

2. **Data Privacy**
   - **Risk:** User profit data is sensitive
   - **Mitigation:** Encryption at rest, GDPR compliance, secure API authentication

---

## Success Metrics

### Phase 1 (Alert Service) - Month 1-3
- **User Acquisition:** 100+ active alert configurations
- **Opportunity Detection:** 500+ opportunities/day
- **Alert Accuracy:** 80%+ opportunities are still valid when user receives alert
- **Conversion Rate:** 10%+ of alerted opportunities are acted upon
- **User Retention:** 70%+ month-over-month retention

### Phase 2 (Listing Automation) - Month 4-6
- **Listing Volume:** 1,000+ automated listings/month
- **Platform Accuracy:** 75%+ items list on optimal platform (vs. actual sale platform)
- **Pricing Accuracy:** Average sale price within 5% of recommended price
- **Time to Sale:** 20% reduction vs. manual listing
- **User Satisfaction:** 4+ star average rating

### Financial Metrics
- **MRR Growth:** 20% month-over-month
- **Churn Rate:** <10% monthly
- **CAC Payback:** <6 months
- **LTV/CAC Ratio:** >3:1

---

## Next Steps & Decision Points

### Immediate Decisions Needed:
1. **Scope Confirmation:**
   - Start with Phase 1 (Alert Service) only, or develop both phases in parallel?
   - MVP approach (core features) or full feature set?

2. **Platform Priority:**
   - Which platforms to support first? (StockX ✅ ready, eBay, GOAT?)
   - Do we have API access to eBay and GOAT?

3. **Notification Method:**
   - Email (SMTP configured?)
   - Webhooks (for external integrations)
   - Push notifications (mobile app planned?)
   - Dashboard-only

4. **Shipping Costs:**
   - Use fixed rates or integrate with carrier APIs (DHL, Hermes)?
   - Build internal database or use external service?

5. **Testing Strategy:**
   - Closed beta with select users?
   - Public launch timeline?
   - Pricing validation (A/B testing tiers)?

### Recommended First Sprint:
**Sprint 1: Alert Foundation (2 weeks)**
- Set up `domains/arbitrage/` structure
- Create database models and migrations
- Enhance QuickFlipDetectionService with demand/risk scoring
- Build basic ArbitrageAlertService
- Implement core API endpoints
- Set up background job for opportunity scanning
- Basic email notification

**Deliverable:** Working MVP where users can create alerts and receive email notifications of arbitrage opportunities.

---

## Appendix: Key Database Models

### QuickFlipOpportunity (Existing)
```python
@dataclass
class QuickFlipOpportunity:
    product_id: UUID
    product_name: str
    product_sku: str
    brand_name: str
    buy_price: Decimal
    buy_source: str              # awin, webgains, etc.
    buy_supplier: str
    buy_url: str
    buy_stock_qty: int
    sell_price: Decimal
    stockx_listing_id: Optional[UUID]
    gross_profit: Decimal
    profit_margin: Decimal
    roi: Decimal
    days_since_last_sale: Optional[int]
    stockx_demand_score: Optional[float]
```

### Enhanced Models (To Be Created)
```python
class ArbitrageAlert(Base):
    __tablename__ = 'arbitrage_alerts'

    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    user_id: UUID = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    min_profit: Decimal = Column(Numeric(10, 2), nullable=False)
    min_margin: Decimal = Column(Numeric(5, 2), nullable=False)
    max_buy_price: Decimal = Column(Numeric(10, 2), nullable=True)
    platforms: List[str] = Column(ARRAY(String), nullable=False)
    notification_method: str = Column(String(50), nullable=False)
    alert_frequency: str = Column(String(20), nullable=False)
    active: bool = Column(Boolean, default=True)
    created_at: DateTime = Column(DateTime, server_default=func.now())
    updated_at: DateTime = Column(DateTime, onupdate=func.now())

class ArbitrageOpportunity(Base):
    __tablename__ = 'arbitrage_opportunities'

    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    product_id: UUID = Column(UUID(as_uuid=True), ForeignKey('catalog.products.id'))
    buy_price: Decimal = Column(Numeric(10, 2), nullable=False)
    sell_price: Decimal = Column(Numeric(10, 2), nullable=False)
    gross_profit: Decimal = Column(Numeric(10, 2), nullable=False)
    profit_margin: Decimal = Column(Numeric(5, 2), nullable=False)
    roi: Decimal = Column(Numeric(5, 2), nullable=False)

    # New fields
    risk_score: str = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH
    feasibility_score: int = Column(Integer, nullable=False)  # 0-100
    demand_score: float = Column(Float, nullable=True)
    estimated_days_to_sell: int = Column(Integer, nullable=True)
    competition_level: str = Column(String(20), nullable=True)

    detected_at: DateTime = Column(DateTime, server_default=func.now())
    expires_at: DateTime = Column(DateTime, nullable=True)

class ArbitrageExecution(Base):
    __tablename__ = 'arbitrage_executions'

    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    opportunity_id: UUID = Column(UUID(as_uuid=True), ForeignKey('arbitrage_opportunities.id'))
    user_id: UUID = Column(UUID(as_uuid=True), ForeignKey('users.id'))

    claimed_at: DateTime = Column(DateTime, server_default=func.now())
    purchased_at: DateTime = Column(DateTime, nullable=True)
    listed_at: DateTime = Column(DateTime, nullable=True)
    sold_at: DateTime = Column(DateTime, nullable=True)

    expected_profit: Decimal = Column(Numeric(10, 2), nullable=False)
    actual_profit: Decimal = Column(Numeric(10, 2), nullable=True)
    execution_time_hours: int = Column(Integer, nullable=True)

    status: str = Column(String(20), nullable=False)
    # claimed, purchased, listed, sold, failed
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-08 | Claude | Initial strategy document based on codebase analysis |

---

**Status:** This document represents the planning phase. No implementation has started. Awaiting decision on scope and priorities before beginning Sprint 1.
