# 🚀 SoleFlipper Backend API Enhancement Plan - StockX Selling Integration

## 🎯 **Fokus: Backend API Erweiterung (main.py + Services)**

### **Aktuelle Architektur:**
```
SoleFlipper Backend API (main.py)
├── domains/integration/api/quickflip_router.py ✅
├── domains/integration/services/quickflip_detection_service.py ✅
├── domains/integration/services/market_price_import_service.py ✅
└── shared/database/models.py (MarketPrice) ✅
```

### **Neue Architektur-Erweiterungen:**
```
SoleFlipper Backend API (main.py)
├── domains/selling/ 🆕
│   ├── api/
│   │   ├── selling_router.py           # StockX Selling Endpoints
│   │   └── order_management_router.py  # Order Tracking Endpoints
│   ├── services/
│   │   ├── stockx_selling_service.py   # Automated Selling Logic
│   │   ├── order_tracking_service.py   # Sales & P&L Tracking
│   │   └── dynamic_pricing_service.py  # Pricing Algorithm
│   └── models/
│       ├── stockx_listing.py           # Listing Management
│       └── stockx_order.py             # Order/Sales Tracking
├── domains/automation/ 🆕
│   ├── services/
│   │   └── arbitrage_automation_service.py # End-to-End Automation
└── Enhanced QuickFlip Integration
```

## 📊 **Phase 1: Database Schema Extensions**

### **Neue Tabellen für Selling Management:**

**1. StockX Listings Table**
```sql
CREATE TABLE selling.stockx_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products.products(id),
    stockx_listing_id VARCHAR(100) UNIQUE NOT NULL,
    stockx_product_id VARCHAR(100) NOT NULL,
    variant_id VARCHAR(100),

    -- Listing Details
    ask_price DECIMAL(10,2) NOT NULL,
    original_ask_price DECIMAL(10,2),
    buy_price DECIMAL(10,2), -- Original purchase price
    expected_profit DECIMAL(10,2),
    expected_margin DECIMAL(5,2),

    -- Status Management
    status VARCHAR(20) NOT NULL, -- active, inactive, sold, expired
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMPTZ,

    -- Market Data
    current_lowest_ask DECIMAL(10,2),
    current_highest_bid DECIMAL(10,2),
    last_price_update TIMESTAMPTZ,

    -- Source Tracking
    source_opportunity_id UUID, -- Link to original QuickFlip opportunity
    created_from VARCHAR(50), -- 'quickflip', 'manual', 'bulk'

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    listed_at TIMESTAMPTZ,
    delisted_at TIMESTAMPTZ
);
```

**2. StockX Orders/Sales Table**
```sql
CREATE TABLE selling.stockx_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID REFERENCES selling.stockx_listings(id),
    stockx_order_number VARCHAR(100) UNIQUE NOT NULL,

    -- Sale Details
    sale_price DECIMAL(10,2) NOT NULL,
    buyer_premium DECIMAL(10,2),
    seller_fee DECIMAL(10,2),
    processing_fee DECIMAL(10,2),
    net_proceeds DECIMAL(10,2),

    -- Profit Calculation
    original_buy_price DECIMAL(10,2),
    gross_profit DECIMAL(10,2),
    net_profit DECIMAL(10,2),
    actual_margin DECIMAL(5,2),
    roi DECIMAL(5,2),

    -- Status & Tracking
    order_status VARCHAR(20), -- pending, authenticated, shipped, completed, cancelled
    shipping_status VARCHAR(20),
    tracking_number VARCHAR(100),

    -- Timeline
    sold_at TIMESTAMPTZ NOT NULL,
    shipped_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**3. Pricing History Table**
```sql
CREATE TABLE selling.pricing_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID REFERENCES selling.stockx_listings(id),

    old_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    change_reason VARCHAR(100), -- 'market_update', 'competition', 'algorithm', 'manual'
    market_lowest_ask DECIMAL(10,2),
    market_highest_bid DECIMAL(10,2),

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 🛠️ **Phase 2: StockX Selling Service Implementation**

### **domains/selling/services/stockx_selling_service.py**
```python
class StockXSellingService:
    """Automated StockX selling and listing management"""

    async def create_listing_from_opportunity(
        self,
        opportunity: QuickFlipOpportunity,
        pricing_strategy: str = "competitive"
    ) -> StockXListing:
        """Convert QuickFlip opportunity to StockX listing"""

    async def create_bulk_listings(
        self,
        opportunities: List[QuickFlipOpportunity]
    ) -> List[StockXListing]:
        """Batch create multiple listings"""

    async def update_listing_price(
        self,
        listing_id: UUID,
        new_price: Decimal,
        reason: str
    ) -> StockXListing:
        """Update individual listing price"""

    async def sync_listing_status(self) -> Dict[str, int]:
        """Sync all listing statuses with StockX"""

    async def activate_listing(self, listing_id: UUID) -> bool:
        """Activate a listing on StockX"""

    async def deactivate_listing(self, listing_id: UUID) -> bool:
        """Deactivate a listing on StockX"""
```

### **domains/selling/services/dynamic_pricing_service.py**
```python
class DynamicPricingService:
    """Intelligent pricing algorithm for listings"""

    async def calculate_optimal_price(
        self,
        listing: StockXListing,
        market_data: MarketData,
        strategy: str = "profit_maximization"
    ) -> Decimal:
        """Calculate optimal ask price based on market conditions"""

    async def update_all_pricing(self) -> Dict[str, int]:
        """Update pricing for all active listings"""

    async def get_pricing_strategy_performance(self) -> Dict[str, float]:
        """Analyze performance of different pricing strategies"""
```

### **domains/selling/services/order_tracking_service.py**
```python
class OrderTrackingService:
    """Track sales and calculate real profits"""

    async def sync_orders_from_stockx(self) -> Dict[str, int]:
        """Sync new orders from StockX API"""

    async def calculate_realized_profits(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Decimal]:
        """Calculate actual profits from completed sales"""

    async def get_sales_analytics(self) -> Dict[str, Any]:
        """Comprehensive sales performance analytics"""

    async def generate_tax_report(
        self,
        year: int
    ) -> List[Dict[str, Any]]:
        """Generate tax reporting data"""
```

## 🌐 **Phase 3: API Router Implementation**

### **domains/selling/api/selling_router.py**
```python
@router.post("/listings/create-from-opportunity")
async def create_listing_from_opportunity(
    opportunity_id: UUID,
    pricing_strategy: str = "competitive",
    db: AsyncSession = Depends(get_db_session)
):
    """Convert QuickFlip opportunity to StockX listing"""

@router.post("/listings/bulk-create")
async def create_bulk_listings(
    opportunity_ids: List[UUID],
    db: AsyncSession = Depends(get_db_session)
):
    """Create multiple listings from opportunities"""

@router.get("/listings")
async def get_my_listings(
    status: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
):
    """Get all my StockX listings"""

@router.put("/listings/{listing_id}/price")
async def update_listing_price(
    listing_id: UUID,
    new_price: Decimal,
    reason: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Update listing price"""

@router.post("/listings/{listing_id}/activate")
async def activate_listing(
    listing_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Activate listing on StockX"""

@router.post("/pricing/update-all")
async def update_all_pricing(
    strategy: str = "profit_maximization",
    db: AsyncSession = Depends(get_db_session)
):
    """Update pricing for all active listings"""
```

### **domains/selling/api/order_management_router.py**
```python
@router.get("/orders/active")
async def get_active_orders(
    db: AsyncSession = Depends(get_db_session)
):
    """Get all active sales orders"""

@router.get("/orders/history")
async def get_order_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
):
    """Get sales history with profit calculations"""

@router.get("/analytics/profits")
async def get_profit_analytics(
    period: str = "30d",
    db: AsyncSession = Depends(get_db_session)
):
    """Get profit analytics and performance metrics"""

@router.get("/analytics/tax-report/{year}")
async def get_tax_report(
    year: int,
    db: AsyncSession = Depends(get_db_session)
):
    """Generate tax reporting data"""

@router.post("/sync/orders")
async def sync_orders_from_stockx(
    db: AsyncSession = Depends(get_db_session)
):
    """Manually sync orders from StockX"""
```

## 🔄 **Phase 4: End-to-End Automation Service**

### **domains/automation/services/arbitrage_automation_service.py**
```python
class ArbitrageAutomationService:
    """Complete end-to-end arbitrage automation"""

    async def process_quickflip_to_sale(
        self,
        opportunity: QuickFlipOpportunity
    ) -> Dict[str, Any]:
        """
        Complete automation pipeline:
        1. Opportunity detected ✅ (existing)
        2. Purchase decision ✅ (existing)
        3. Create StockX listing 🆕
        4. Dynamic pricing updates 🆕
        5. Sale completion tracking 🆕
        6. Profit calculation 🆕
        """

    async def monitor_and_optimize(self) -> Dict[str, Any]:
        """Continuous monitoring and optimization"""
```

## 📝 **Phase 5: main.py Integration**

### **Updated main.py Router Registration:**
```python
# Existing routers
from domains.integration.api.quickflip_router import router as quickflip_router

# New selling routers 🆕
from domains.selling.api.selling_router import router as selling_router
from domains.selling.api.order_management_router import router as order_router
from domains.automation.api.automation_router import router as automation_router

# Register new routers
app.include_router(selling_router, prefix="/api/v1/selling", tags=["Selling"])
app.include_router(order_router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(automation_router, prefix="/api/v1/automation", tags=["Automation"])
```

## 🗄️ **Phase 6: Database Migration**

### **Migration Script:**
```python
# migrations/versions/add_selling_tables.py
def upgrade():
    # Create selling schema
    op.execute("CREATE SCHEMA IF NOT EXISTS selling")

    # Create tables
    op.create_table('stockx_listings', ..., schema='selling')
    op.create_table('stockx_orders', ..., schema='selling')
    op.create_table('pricing_history', ..., schema='selling')

    # Add indexes for performance
    op.create_index('idx_listings_status', 'stockx_listings', ['status'])
    op.create_index('idx_orders_status', 'stockx_orders', ['order_status'])
```

## 🚀 **Implementation Timeline**

### **Week 1: Foundation**
- [ ] Database schema design & migration
- [ ] StockX Selling Service skeleton
- [ ] Basic listing CRUD operations

### **Week 2: Core Selling Features**
- [ ] Create listing from opportunity
- [ ] Bulk listing operations
- [ ] Listing status synchronization

### **Week 3: Advanced Features**
- [ ] Dynamic pricing service
- [ ] Order tracking service
- [ ] Profit calculation engine

### **Week 4: Integration & Testing**
- [ ] API router implementation
- [ ] End-to-end automation pipeline
- [ ] Testing & optimization

## 💰 **Expected Business Impact**

**Automation Benefits:**
- **90% reduction** in manual listing work
- **25% profit increase** through dynamic pricing
- **100% accurate** profit tracking
- **24/7 automated** operations

**API Enhancement:**
- **15+ new endpoints** for selling management
- **Real-time** sales analytics
- **Automated** tax reporting
- **Scalable** listing operations

---

## ✅ **Next Steps für Backend Implementation**

1. **Create database migration** for selling tables
2. **Implement StockXSellingService** with core methods
3. **Build selling_router.py** with essential endpoints
4. **Integrate with existing QuickFlip pipeline**
5. **Add to main.py** router registration

**Focus: Backend-first, dann Budibase Integration als Frontend später!**