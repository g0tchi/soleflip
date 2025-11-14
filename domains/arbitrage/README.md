# Arbitrage Domain

**Smart profit opportunity detection with demand scoring and risk assessment**

## Overview

The Arbitrage domain provides advanced services for identifying, scoring, and assessing arbitrage opportunities across multiple retail and resale platforms. It extends the existing QuickFlip detection with ML-based demand forecasting and comprehensive risk analysis.

## Services

### 1. Demand Score Calculator

**File:** `services/demand_score_calculator.py`

Calculates product demand scores (0-100) to assess how quickly items will sell.

**Scoring Components:**
- **Sales Frequency (40%)**: Orders per day over last 90 days
- **Price Trend (25%)**: Increasing prices indicate higher demand
- **Stock Turnover (20%)**: Average shelf_life_days from historical orders
- **Seasonal Adjustment (10%)**: Current month seasonality factor
- **Brand Popularity (5%)**: Brand's overall sales velocity

**Usage:**
```python
from domains.arbitrage.services import DemandScoreCalculator

async with session:
    calculator = DemandScoreCalculator(session)

    # Calculate demand score
    demand_score, breakdown = await calculator.calculate_product_demand_score(
        product_id, days_back=90
    )

    # Save to database
    pattern = await calculator.save_demand_pattern(
        product_id, demand_score, breakdown, trend_direction
    )
```

**Output:**
- `demand_score`: 0-100 (higher = faster turnover)
- `breakdown`: Detailed component scores
  - `sales_frequency_score`, `sales_per_day`
  - `price_trend_score`, `trend_direction`
  - `stock_turnover_score`, `avg_turnover_days`
  - `seasonal_score`, `brand_score`

---

### 2. Risk Scorer

**File:** `services/risk_scorer.py`

Assesses risk level (LOW/MEDIUM/HIGH) for arbitrage opportunities.

**Risk Components:**
- **Demand Score (30%)**: Low demand = higher risk
- **Price Volatility (25%)**: High volatility = higher risk
- **Stock Availability (20%)**: Low stock = higher risk
- **Profit Margin (15%)**: Low margin = higher risk
- **Supplier Reliability (10%)**: Less reliable suppliers = higher risk

**Usage:**
```python
from domains.arbitrage.services import RiskScorer, RiskLevel

async with session:
    risk_scorer = RiskScorer(session)

    # Assess single opportunity
    assessment = await risk_scorer.assess_opportunity_risk(
        opportunity, demand_score=75.5
    )

    print(f"Risk: {assessment.risk_level.value}")  # LOW/MEDIUM/HIGH
    print(f"Score: {assessment.risk_score}/100")
    print(f"Factors: {assessment.risk_factors}")
    print(f"Recommendations: {assessment.recommendations}")
```

**Supplier Reliability Scores:**
- Awin (affiliate network): 85
- WebGains (affiliate network): 80
- Afew Store: 95
- Asphaltgold: 90
- BSTN: 90
- Overkill: 85
- Allike: 80

**Note:** Awin/WebGains are data sources (affiliate networks) providing retail prices,
not sales platforms. Sales platforms (StockX, eBay, GOAT) are evaluated separately.

---

### 3. Enhanced Opportunity Service

**File:** `services/enhanced_opportunity_service.py`

Integrates Demand Score Calculator and Risk Scorer with QuickFlip detection.

**Features:**
- Demand score calculation for all opportunities
- Risk assessment with detailed breakdown
- Feasibility scoring (composite metric)
- Days-to-sell estimation
- Sorting and filtering by risk/feasibility

**Usage:**
```python
from domains.arbitrage.services import EnhancedOpportunityService, RiskLevel

async with session:
    service = EnhancedOpportunityService(session)

    # Get top opportunities
    opportunities = await service.get_top_opportunities(
        limit=10,
        min_feasibility=60,
        max_risk=RiskLevel.MEDIUM
    )

    for enh in opportunities:
        print(f"Product: {enh.opportunity.product_name}")
        print(f"Feasibility: {enh.feasibility_score}/100")
        print(f"Demand: {enh.demand_score}/100")
        print(f"Risk: {enh.risk_level_str}")
        print(f"Est. Days to Sell: {enh.estimated_days_to_sell}")
```

**Feasibility Score Calculation:**
- Demand score (40%)
- Inverted risk score (30%)
- Profit margin (20%)
- Stock availability (10%)

---

## Testing

Run the comprehensive test suite:

```bash
python scripts/test_arbitrage_services.py
```

**Test Coverage:**
1. **Demand Score Calculator**: Tests demand scoring across 5 products
2. **Risk Scorer**: Tests risk assessment on 5 opportunities
3. **Enhanced Opportunity Service**: Tests integrated workflow with summary stats

---

## Data Models

### DemandPattern (pricing schema)

Stores demand analysis results:

```python
- product_id: UUID
- demand_score: Decimal (0-100)
- trend_direction: str (increasing/decreasing/stable)
- pattern_metadata: JSON (detailed breakdown)
- pattern_date: Date
```

### Enhanced Opportunity Data Model

```python
@dataclass
class EnhancedOpportunity:
    opportunity: QuickFlipOpportunity  # Base opportunity
    demand_score: float  # 0-100
    demand_breakdown: dict
    risk_assessment: RiskAssessment
    feasibility_score: int  # 0-100
    estimated_days_to_sell: int  # 1-90
```

---

## Integration Points

### Existing Services Used:
- `QuickFlipDetectionService` - Base opportunity detection
- `ForecastRepository` - Historical sales data
- `Order` model - Sales frequency, turnover data
- `Product`, `Brand` models - Brand popularity

### Database Tables:
- `analytics.demand_patterns` - Stores demand scores
- `pricing.market_prices` - Price volatility analysis
- `transactions.orders` - Historical sales data
- `inventory.stock` - Stock turnover metrics

---

## Roadmap

### Phase 1: Foundation (Completed ✅)
- ✅ Demand Score Calculator (rule-based)
- ✅ Risk Scorer (rule-based)
- ✅ Enhanced Opportunity Service

### Phase 2: ML Enhancement (Planned)
- [ ] ML-based demand prediction using Random Forest
- [ ] Time-series forecasting for demand
- [ ] Competition analysis (seller count on platforms)
- [ ] Advanced volatility detection with ARIMA

### Phase 3: Automation (Planned)
- [ ] Real-time price monitoring
- [ ] Automatic opportunity alerts
- [ ] Batch opportunity scanning (performance optimization)
- [ ] Platform selection recommendation ML model

---

## Performance Considerations

**Current Implementation:**
- Individual product analysis: ~100-200ms
- Batch opportunity enhancement: ~500-1000ms for 10 opportunities
- Database queries optimized with proper indexing

**Optimization Roadmap:**
- Add caching for demand scores (15-min TTL)
- Batch SQL queries for risk assessment
- Background job for pre-calculating demand scores
- Redis caching for frequently accessed metrics

---

## API Endpoints

**Base URL:** `/api/v1/arbitrage`

### 1. Get Enhanced Opportunities
```http
GET /api/v1/arbitrage/opportunities/enhanced

Query Parameters:
- min_profit_margin: float (default: 10.0) - Minimum profit margin %
- min_gross_profit: float (default: 20.0) - Minimum gross profit €
- max_buy_price: float (optional) - Maximum buy price filter
- source_filter: string (optional) - Filter by source
- limit: int (default: 10, max: 100) - Max results
- calculate_demand: bool (default: true) - Calculate demand scores
- calculate_risk: bool (default: true) - Calculate risk assessments

Response: List[EnhancedOpportunityResponse]
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/arbitrage/opportunities/enhanced?min_feasibility=70&limit=5"
```

### 2. Get Top Opportunities
```http
GET /api/v1/arbitrage/opportunities/top

Query Parameters:
- limit: int (default: 10, max: 50) - Max results
- min_feasibility: int (default: 60) - Minimum feasibility score (0-100)
- max_risk: enum (default: MEDIUM) - Maximum risk level (LOW|MEDIUM|HIGH)

Response: List[EnhancedOpportunityResponse]
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/arbitrage/opportunities/top?limit=10&max_risk=LOW"
```

### 3. Get Product Demand Score
```http
GET /api/v1/arbitrage/demand/{product_id}

Path Parameters:
- product_id: UUID - Product UUID

Query Parameters:
- days_back: int (default: 90, min: 7, max: 365) - Analysis period
- save_pattern: bool (default: false) - Save to database

Response: DemandScoreResponse
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/arbitrage/demand/550e8400-e29b-41d4-a716-446655440000?days_back=60"
```

### 4. Batch Risk Assessment
```http
POST /api/v1/arbitrage/assess-batch

Request Body:
{
  "product_ids": ["uuid1", "uuid2", ...]  // Max 50
}

Response: BatchAssessResponse
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/arbitrage/assess-batch" \
  -H "Content-Type: application/json" \
  -d '{"product_ids": ["550e8400-e29b-41d4-a716-446655440000"]}'
```

### 5. Get Summary Statistics
```http
GET /api/v1/arbitrage/summary

Query Parameters:
- min_profit_margin: float (default: 10.0) - Minimum profit margin %
- min_gross_profit: float (default: 20.0) - Minimum gross profit €

Response: OpportunitySummaryResponse
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/arbitrage/summary"
```

### 6. Health Check
```http
GET /api/v1/arbitrage/health

Response: { "status": "healthy", "service": "arbitrage", ... }
```

**Interactive Documentation:**
- Swagger UI: http://localhost:8000/docs#/Arbitrage
- ReDoc: http://localhost:8000/redoc

---

## Alert System

### Overview

The Alert System enables users to receive automated notifications when arbitrage opportunities matching their criteria are detected. Alerts are processed by a background scanner every 60 seconds and notifications are sent via n8n webhooks.

### Features

- **Custom Filter Criteria**: Profit margin, gross profit, feasibility score, risk level
- **Flexible Scheduling**: Configure frequency, active hours, and active days
- **Multi-Channel Notifications**: Discord, Email, Telegram (via n8n)
- **Statistics Tracking**: Monitor alert performance and success rates
- **User Isolation**: Each user manages their own alerts

### Alert Endpoints

#### 1. Create Alert
```http
POST /api/v1/arbitrage/alerts

Request Body:
{
  "alert_name": "High Profit Opportunities",
  "n8n_webhook_url": "https://your-n8n-instance.com/webhook/soleflip-alert",
  "min_profit_margin": 20.0,
  "min_gross_profit": 50.0,
  "min_feasibility_score": 70,
  "max_risk_level": "MEDIUM",
  "notification_config": {
    "discord": true,
    "email": true
  },
  "alert_frequency_minutes": 15,
  "active": true
}

Response: AlertResponse (201 Created)
```

#### 2. List Alerts
```http
GET /api/v1/arbitrage/alerts?active_only=false

Response: List[AlertResponse]
```

#### 3. Get Alert Details
```http
GET /api/v1/arbitrage/alerts/{alert_id}

Response: AlertResponse
```

#### 4. Update Alert
```http
PUT /api/v1/arbitrage/alerts/{alert_id}

Request Body: (all fields optional)
{
  "active": true,
  "min_profit_margin": 25.0,
  "alert_frequency_minutes": 30
}

Response: AlertResponse
```

#### 5. Delete Alert
```http
DELETE /api/v1/arbitrage/alerts/{alert_id}

Response: 204 No Content
```

#### 6. Toggle Alert
```http
POST /api/v1/arbitrage/alerts/{alert_id}/toggle

Request Body:
{
  "active": true
}

Response: AlertResponse
```

#### 7. Get Alert Statistics
```http
GET /api/v1/arbitrage/alerts/{alert_id}/stats

Response:
{
  "alert_id": "uuid",
  "alert_name": "High Profit Opportunities",
  "active": true,
  "total_alerts_sent": 45,
  "total_opportunities_sent": 230,
  "avg_opportunities_per_alert": 5.1,
  "last_triggered_at": "2025-11-14T12:00:00Z",
  "last_scanned_at": "2025-11-14T12:15:00Z"
}
```

### n8n Integration

#### Setup

1. Import the workflow from `domains/arbitrage/docs/n8n-workflow-example.json`
2. Configure credentials for Discord/Email/Telegram
3. Activate the workflow and copy the webhook URL
4. Use the webhook URL when creating alerts

**Detailed Guide:** See `domains/arbitrage/docs/n8n-setup-guide.md`

#### Notification Payload

The n8n webhook receives:

```json
{
  "alert": {
    "id": "uuid",
    "name": "Alert Name",
    "user_id": "uuid"
  },
  "notification_config": {
    "discord": true,
    "email": false
  },
  "opportunities": [
    {
      "product_name": "Nike Air Max 90",
      "buy_price": 120.00,
      "sell_price": 180.00,
      "gross_profit": 60.00,
      "profit_margin": 50.0,
      "feasibility_score": 85,
      "risk_level": "LOW",
      ...
    }
  ],
  "summary": {
    "total_opportunities": 5,
    "avg_profit_margin": 45.2,
    "avg_feasibility": 82.5,
    "total_potential_profit": 450.50
  },
  "timestamp": "2025-11-14T12:00:00Z"
}
```

### Background Scanner

The alert scanner runs as a background task in the FastAPI lifespan:

- **Scan Interval**: 60 seconds
- **Processing**: Checks alerts ready to trigger based on frequency and schedule
- **Logging**: Detailed logs for monitoring and debugging

**Implementation:** `domains/arbitrage/jobs/alert_scanner.py`

### Schedule Configuration

Alerts support flexible scheduling:

```python
{
  "alert_frequency_minutes": 15,         # Check every 15 minutes
  "active_hours_start": "09:00",         # Only between 9 AM
  "active_hours_end": "22:00",           # and 10 PM
  "active_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
  "timezone": "Europe/Berlin"
}
```

### Database Model

**Table:** `arbitrage.arbitrage_alerts`

**Key Fields:**
- Filter criteria (profit, feasibility, risk)
- n8n webhook URL
- Notification preferences
- Schedule settings (frequency, hours, days)
- Statistics (alerts sent, opportunities sent)
- Error tracking

**Migration:** `migrations/versions/2025_11_14_1200_create_arbitrage_alerts_table.py`

---

## Contributing

When adding new risk factors or demand components:

1. Update weight constants in respective services
2. Add tests to `scripts/test_arbitrage_services.py`
3. Document in this README
4. Update `docs/features/arbitrage-monetization-strategy.md`

---

## Related Documentation

- [Arbitrage Monetization Strategy](../../docs/features/arbitrage-monetization-strategy.md)
- [QuickFlip Service](../integration/services/quickflip_detection_service.py)
- [Forecast Engine](../analytics/services/forecast_engine.py)
- [Demand Patterns Model](../pricing/models.py)
