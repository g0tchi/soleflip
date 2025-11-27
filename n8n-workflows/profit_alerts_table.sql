-- Create analytics schema and profit_opportunities table for n8n workflow
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.profit_opportunities (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL,
    product_name TEXT NOT NULL,
    variant_id UUID,
    
    -- Pricing
    lowest_ask NUMERIC(10, 2),
    sell_faster NUMERIC(10, 2),
    earn_more NUMERIC(10, 2),
    retail_price NUMERIC(10, 2),
    
    -- Profit Calculation
    estimated_cost NUMERIC(10, 2),
    stockx_fees NUMERIC(10, 2),
    net_proceeds NUMERIC(10, 2),
    profit NUMERIC(10, 2),
    roi_percentage NUMERIC(5, 1),
    
    -- Metadata
    alert_priority VARCHAR(10) CHECK (alert_priority IN ('LOW', 'MEDIUM', 'HIGH')),
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Index for fast queries
    CONSTRAINT unique_alert UNIQUE (sku, variant_id, checked_at)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_profit_opportunities_roi ON analytics.profit_opportunities(roi_percentage DESC);
CREATE INDEX IF NOT EXISTS idx_profit_opportunities_priority ON analytics.profit_opportunities(alert_priority, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_profit_opportunities_checked_at ON analytics.profit_opportunities(checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_profit_opportunities_sku ON analytics.profit_opportunities(sku);

-- Comments
COMMENT ON TABLE analytics.profit_opportunities IS 'Stores profitable product opportunities identified by n8n workflow';
COMMENT ON COLUMN analytics.profit_opportunities.roi_percentage IS 'Return on Investment percentage after StockX fees';
COMMENT ON COLUMN analytics.profit_opportunities.alert_priority IS 'HIGH: >50% ROI, MEDIUM: 35-50% ROI, LOW: 25-35% ROI';
