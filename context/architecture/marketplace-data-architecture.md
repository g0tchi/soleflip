# Marketplace Data Architecture

## Overview

This document describes the architecture for storing and managing market data from multiple platforms (StockX, Alias, GOAT, etc.) in a unified, scalable way that supports intelligent pricing and cross-platform analytics.

## Problem Statement

Different marketplaces provide various types of market data that are crucial for:
- **Intelligent Pricing**: Setting competitive ask/bid prices
- **Market Analytics**: Understanding volatility and trends
- **Cross-Platform Optimization**: Finding the best platform for each item
- **Automated Repricing**: Dynamic price adjustments based on market conditions

## Architecture Design

### Core Principle: Separation of Concerns

We separate **identifiers** (in `external_ids`) from **business data** (in dedicated tables) for better maintainability and query performance.

### Database Schema

```sql
CREATE TABLE marketplace_data (
    id UUID PRIMARY KEY,
    inventory_item_id UUID REFERENCES inventory_items(id),

    -- Platform Reference (FK to existing core.platforms)
    platform_id UUID REFERENCES core.platforms(id) NOT NULL,
    marketplace_listing_id VARCHAR(255),

    -- Universal Pricing Fields
    ask_price DECIMAL(10,2),
    bid_price DECIMAL(10,2),
    market_lowest_ask DECIMAL(10,2),
    market_highest_bid DECIMAL(10,2),
    last_sale_price DECIMAL(10,2),

    -- Market Analytics
    sales_frequency INTEGER,              -- Sales in last 30 days
    volatility DECIMAL(5,4),             -- Price volatility (0.0-1.0)
    fees_percentage DECIMAL(5,4),        -- Platform fees (0.08 = 8%)

    -- Platform-specific data (JSON for flexibility)
    platform_specific JSONB,

    -- Metadata
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    UNIQUE(inventory_item_id, platform_id),
    CHECK (volatility >= 0 AND volatility <= 1),
    CHECK (fees_percentage >= 0 AND fees_percentage <= 1)
);

-- Indexes for performance
CREATE INDEX idx_marketplace_data_platform ON marketplace_data(platform_id);
CREATE INDEX idx_marketplace_data_item ON marketplace_data(inventory_item_id);
CREATE INDEX idx_marketplace_data_updated ON marketplace_data(updated_at);
CREATE INDEX idx_marketplace_data_ask_price ON marketplace_data(ask_price) WHERE ask_price IS NOT NULL;
```

## Data Model

### SQLAlchemy Model

```python
class MarketplaceData(Base, TimestampMixin):
    __tablename__ = "marketplace_data"
    __table_args__ = {"schema": "analytics"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    inventory_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id"),
        nullable=False
    )
    platform_id = Column(
        UUID(as_uuid=True),
        ForeignKey(get_schema_ref("platforms.id", "core")),
        nullable=False
    )
    marketplace_listing_id = Column(String(255))

    # Pricing data
    ask_price = Column(Numeric(10, 2))
    bid_price = Column(Numeric(10, 2))
    market_lowest_ask = Column(Numeric(10, 2))
    market_highest_bid = Column(Numeric(10, 2))
    last_sale_price = Column(Numeric(10, 2))

    # Analytics
    sales_frequency = Column(Integer)
    volatility = Column(Numeric(5, 4))
    fees_percentage = Column(Numeric(5, 4))

    # Platform-specific data
    platform_specific = Column(JSON)

    # Relationships
    inventory_item = relationship("InventoryItem", back_populates="marketplace_data")
    platform = relationship("Platform", back_populates="marketplace_data")

    __table_args__ = (
        UniqueConstraint('inventory_item_id', 'platform_id'),
        CheckConstraint('volatility >= 0 AND volatility <= 1'),
        CheckConstraint('fees_percentage >= 0 AND fees_percentage <= 1'),
    )
```

### Relationship Updates

```python
# In InventoryItem model
class InventoryItem(Base, TimestampMixin):
    # ... existing fields ...
    marketplace_data = relationship("MarketplaceData", back_populates="inventory_item")

# In Platform model
class Platform(Base, TimestampMixin):
    # ... existing fields ...
    marketplace_data = relationship("MarketplaceData", back_populates="platform")
```

## Platform-Specific Data Structures

### StockX Platform Data

```json
{
  "ask_price": 150.00,
  "bid_price": 140.00,
  "market_lowest_ask": 145.00,
  "market_highest_bid": 142.00,
  "last_sale_price": 147.50,
  "sales_frequency": 12,
  "volatility": 0.05,
  "fees_percentage": 0.095,
  "platform_specific": {
    "askId": "uuid-ask-id",
    "variantId": "uuid-variant-id",
    "authentication": "required",
    "condition_grade": "new",
    "processing_time_days": 3
  }
}
```

### Alias Platform Data

```json
{
  "ask_price": 148.00,
  "market_lowest_ask": 142.00,
  "last_sale_price": 145.00,
  "sales_frequency": 8,
  "volatility": 0.07,
  "fees_percentage": 0.08,
  "platform_specific": {
    "condition_notes": "VNDS",
    "authentication": "optional",
    "shipping_included": true,
    "processing_time_days": 1
  }
}
```

## Business Logic & Use Cases

### 1. Intelligent Pricing

```sql
-- Find optimal pricing for an item across platforms
SELECT
    p.name as platform,
    md.ask_price,
    md.market_lowest_ask,
    md.fees_percentage,
    (md.market_lowest_ask * (1 - md.fees_percentage)) as estimated_net,
    md.sales_frequency,
    md.volatility
FROM marketplace_data md
JOIN core.platforms p ON md.platform_id = p.id
WHERE md.inventory_item_id = 'item-uuid'
ORDER BY estimated_net DESC;
```

### 2. Cross-Platform Analytics

```sql
-- Platform performance comparison
SELECT
    p.name as platform,
    COUNT(md.id) as listings_count,
    AVG(md.ask_price) as avg_ask_price,
    AVG(md.fees_percentage) as avg_fees,
    AVG(md.sales_frequency) as avg_sales_frequency,
    AVG(md.volatility) as avg_volatility
FROM marketplace_data md
JOIN core.platforms p ON md.platform_id = p.id
WHERE md.updated_at > NOW() - INTERVAL '30 days'
GROUP BY p.name
ORDER BY avg_sales_frequency DESC;
```

### 3. Repricing Opportunities

```sql
-- Items that could be repriced for better competitiveness
SELECT
    ii.id,
    ii.product_id,
    md.ask_price as current_ask,
    md.market_lowest_ask,
    p.name as platform,
    (md.market_lowest_ask - md.ask_price) as price_gap
FROM inventory_items ii
JOIN marketplace_data md ON ii.id = md.inventory_item_id
JOIN core.platforms p ON md.platform_id = p.id
WHERE md.ask_price > md.market_lowest_ask * 1.05  -- 5% above market
AND md.sales_frequency > 0
ORDER BY price_gap DESC;
```

## Integration with Existing Systems

### External IDs Strategy

Keep `external_ids` for **identifiers only**:

```json
{
  "external_ids": {
    "stockx_listing_id": "listing_123",
    "stockx_product_id": "uuid-product",
    "stockx_variant_id": "uuid-variant",
    "created_from_sync": true,
    "sync_timestamp": "2024-01-15T10:30:00Z"
  }
}
```

All **business data** goes to `marketplace_data` table.

### Service Layer Integration

```python
class MarketplaceDataService:
    async def update_market_data(self, inventory_item_id: UUID, platform_slug: str, data: dict):
        """Update marketplace data for an inventory item"""

    async def get_best_platform_for_item(self, inventory_item_id: UUID) -> dict:
        """Find the best platform to sell an item based on net profit"""

    async def get_pricing_recommendations(self, inventory_item_id: UUID) -> list:
        """Get pricing recommendations based on market data"""

    async def track_price_changes(self, platform_slug: str) -> dict:
        """Track significant price changes for repricing alerts"""
```

## Migration Strategy

### Phase 1: Database Setup
1. Create `marketplace_data` table
2. Add relationships to existing models
3. Create indexes for performance

### Phase 2: Data Migration
1. Migrate existing StockX price data from other tables
2. Populate platform_id references
3. Clean up redundant fields

### Phase 3: Service Integration
1. Update StockX sync to populate marketplace_data
2. Implement MarketplaceDataService
3. Add Alias integration
4. Build pricing optimization features

## Performance Considerations

### Indexing Strategy
- Primary indexes on foreign keys (inventory_item_id, platform_id)
- Secondary indexes on frequently queried fields (ask_price, updated_at)
- Partial indexes for non-null price fields

### Query Optimization
- Use JOINs efficiently with proper indexes
- Consider materialized views for complex analytics queries
- Implement caching for frequently accessed market data

### Data Retention
- Keep historical data for trend analysis
- Implement archiving for very old data (>2 years)
- Regular cleanup of stale marketplace listings

## Security & Compliance

### Data Privacy
- No personal buyer/seller information stored
- Only public market data and our own listing information
- Compliance with marketplace API terms of service

### API Rate Limiting
- Respect marketplace API rate limits
- Implement exponential backoff for failed requests
- Cache frequently accessed data appropriately

## Benefits

1. **Unified Data Model**: All marketplace data in consistent format
2. **Historical Analysis**: Track price trends and market evolution
3. **Cross-Platform Optimization**: Data-driven platform selection
4. **Automated Pricing**: AI-powered price optimization
5. **Scalability**: Easy to add new marketplaces
6. **Performance**: Optimized queries with proper indexing
7. **Maintainability**: Clear separation of concerns

## Future Enhancements

- Machine learning models for price prediction
- Real-time pricing alerts and notifications
- Advanced analytics dashboard
- API endpoints for external integrations
- Mobile app integration for on-the-go pricing decisions