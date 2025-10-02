"""
Metabase Materialized Views Configuration
=========================================

Optimized materialized views for Metabase dashboards with automatic refresh scheduling.
Designed for fast query performance on large datasets.

Architecture:
- Materialized views for expensive aggregations
- Automatic refresh via pg_cron (hourly/daily/weekly)
- Indexed for optimal Metabase query performance
- Multi-platform support (StockX, eBay, GOAT, etc.)

Version: v2.2.3
"""

from enum import Enum
from typing import Dict, List


class RefreshStrategy(str, Enum):
    """Materialized view refresh strategies"""
    REALTIME = "realtime"  # Regular view (no materialization)
    HOURLY = "hourly"      # Refresh every hour
    DAILY = "daily"        # Refresh daily at 2 AM
    WEEKLY = "weekly"      # Refresh weekly on Monday
    MANUAL = "manual"      # Manual refresh only


class MetabaseViewConfig:
    """Configuration for Metabase-optimized materialized views"""

    # Executive Dashboard Views (Real-time)
    EXECUTIVE_METRICS = {
        "name": "metabase_executive_metrics",
        "refresh": RefreshStrategy.HOURLY,
        "description": "Real-time executive KPIs: revenue, profit, ROI, orders",
        "sql": """
            SELECT
                -- Time Metrics
                DATE_TRUNC('day', o.sold_at) AS sale_date,
                DATE_TRUNC('week', o.sold_at) AS sale_week,
                DATE_TRUNC('month', o.sold_at) AS sale_month,
                DATE_TRUNC('quarter', o.sold_at) AS sale_quarter,
                DATE_TRUNC('year', o.sold_at) AS sale_year,

                -- Platform Metrics
                p.name AS platform_name,
                p.slug AS platform_slug,

                -- Financial Metrics
                COUNT(o.id) AS total_orders,
                SUM(o.gross_sale) AS total_revenue,
                SUM(o.net_proceeds) AS total_net_proceeds,
                SUM(o.net_profit) AS total_profit,
                AVG(o.roi) AS avg_roi,
                SUM(o.platform_fee) AS total_fees,
                SUM(o.shipping_cost) AS total_shipping,

                -- Performance Metrics
                AVG(o.gross_sale) AS avg_order_value,
                MIN(o.sold_at) AS first_sale,
                MAX(o.sold_at) AS last_sale,
                COUNT(DISTINCT DATE_TRUNC('day', o.sold_at)) AS active_days

            FROM transactions.orders o
            JOIN core.platforms p ON o.platform_id = p.id
            WHERE o.status = 'completed'
            GROUP BY
                DATE_TRUNC('day', o.sold_at),
                DATE_TRUNC('week', o.sold_at),
                DATE_TRUNC('month', o.sold_at),
                DATE_TRUNC('quarter', o.sold_at),
                DATE_TRUNC('year', o.sold_at),
                p.name,
                p.slug
        """,
        "indexes": [
            "CREATE INDEX idx_exec_metrics_date ON metabase_executive_metrics(sale_date DESC)",
            "CREATE INDEX idx_exec_metrics_month ON metabase_executive_metrics(sale_month DESC)",
            "CREATE INDEX idx_exec_metrics_platform ON metabase_executive_metrics(platform_slug)"
        ]
    }

    # Product Performance Views (Daily refresh)
    PRODUCT_PERFORMANCE = {
        "name": "metabase_product_performance",
        "refresh": RefreshStrategy.DAILY,
        "description": "Product-level sales performance with brand and category breakdowns",
        "sql": """
            SELECT
                -- Product Info
                prod.id AS product_id,
                prod.name AS product_name,
                prod.sku AS product_sku,
                prod.category_id,
                cat.name AS category_name,

                -- Brand Info
                b.id AS brand_id,
                b.name AS brand_name,
                b.segment AS brand_segment,
                b.price_tier,
                b.is_collaboration,

                -- Sales Metrics
                COUNT(o.id) AS units_sold,
                SUM(o.gross_sale) AS total_revenue,
                AVG(o.gross_sale) AS avg_sale_price,
                MIN(o.gross_sale) AS min_sale_price,
                MAX(o.gross_sale) AS max_sale_price,
                STDDEV(o.gross_sale) AS price_volatility,

                -- Profit Metrics
                SUM(o.net_profit) AS total_profit,
                AVG(o.roi) AS avg_roi,
                SUM(o.platform_fee) AS total_fees_paid,

                -- Inventory Metrics
                AVG(i.purchase_price) AS avg_purchase_price,
                COUNT(DISTINCT i.supplier_id) AS supplier_count,

                -- Time Metrics
                MIN(o.sold_at) AS first_sale_date,
                MAX(o.sold_at) AS last_sale_date,
                MAX(o.sold_at) - MIN(o.sold_at) AS sales_duration

            FROM transactions.orders o
            JOIN products.inventory i ON o.inventory_item_id = i.id
            JOIN products.products prod ON i.product_id = prod.id
            LEFT JOIN core.brands b ON prod.brand_id = b.id
            LEFT JOIN products.categories cat ON prod.category_id = cat.id
            WHERE o.status = 'completed'
            GROUP BY
                prod.id, prod.name, prod.sku, prod.category_id,
                cat.name, b.id, b.name, b.segment, b.price_tier, b.is_collaboration
        """,
        "indexes": [
            "CREATE INDEX idx_prod_perf_product ON metabase_product_performance(product_id)",
            "CREATE INDEX idx_prod_perf_brand ON metabase_product_performance(brand_id)",
            "CREATE INDEX idx_prod_perf_revenue ON metabase_product_performance(total_revenue DESC)",
            "CREATE INDEX idx_prod_perf_units ON metabase_product_performance(units_sold DESC)"
        ]
    }

    # Brand Analytics Views (Daily refresh)
    BRAND_ANALYTICS = {
        "name": "metabase_brand_analytics",
        "refresh": RefreshStrategy.DAILY,
        "description": "Brand-level performance with market share and positioning",
        "sql": """
            WITH brand_sales AS (
                SELECT
                    b.id AS brand_id,
                    b.name AS brand_name,
                    b.segment,
                    b.price_tier,
                    b.target_demographic,
                    b.is_collaboration,
                    pb.name AS parent_brand_name,

                    COUNT(o.id) AS total_sales,
                    SUM(o.gross_sale) AS total_revenue,
                    AVG(o.gross_sale) AS avg_price,
                    STDDEV(o.gross_sale) AS price_variance,
                    SUM(o.net_profit) AS total_profit,
                    AVG(o.roi) AS avg_roi,

                    COUNT(DISTINCT prod.id) AS product_variety,
                    COUNT(DISTINCT DATE_TRUNC('month', o.sold_at)) AS active_months,
                    MIN(o.sold_at) AS first_sale,
                    MAX(o.sold_at) AS last_sale

                FROM core.brands b
                LEFT JOIN core.brands pb ON b.parent_brand_id = pb.id
                JOIN products.products prod ON prod.brand_id = b.id
                JOIN products.inventory i ON i.product_id = prod.id
                JOIN transactions.orders o ON o.inventory_item_id = i.id
                WHERE o.status = 'completed'
                GROUP BY b.id, b.name, b.segment, b.price_tier,
                         b.target_demographic, b.is_collaboration, pb.name
            ),
            market_totals AS (
                SELECT
                    SUM(total_revenue) AS market_revenue,
                    SUM(total_sales) AS market_sales
                FROM brand_sales
            )
            SELECT
                bs.*,
                ROUND((bs.total_revenue / mt.market_revenue) * 100, 2) AS market_share_pct,
                ROUND((bs.total_sales::numeric / mt.market_sales) * 100, 2) AS sales_share_pct,
                CASE
                    WHEN bs.avg_price > 200 THEN 'Premium'
                    WHEN bs.avg_price > 100 THEN 'Mid-Range'
                    ELSE 'Entry-Level'
                END AS price_positioning,
                CASE
                    WHEN bs.total_sales > 100 THEN 'High Volume'
                    WHEN bs.total_sales > 50 THEN 'Medium Volume'
                    ELSE 'Low Volume'
                END AS volume_tier
            FROM brand_sales bs
            CROSS JOIN market_totals mt
        """,
        "indexes": [
            "CREATE INDEX idx_brand_analytics_id ON metabase_brand_analytics(brand_id)",
            "CREATE INDEX idx_brand_analytics_revenue ON metabase_brand_analytics(total_revenue DESC)",
            "CREATE INDEX idx_brand_analytics_share ON metabase_brand_analytics(market_share_pct DESC)"
        ]
    }

    # Platform Performance Views (Hourly refresh)
    PLATFORM_PERFORMANCE = {
        "name": "metabase_platform_performance",
        "refresh": RefreshStrategy.HOURLY,
        "description": "Multi-platform comparison: fees, shipping, payout times",
        "sql": """
            SELECT
                p.id AS platform_id,
                p.name AS platform_name,
                p.slug AS platform_slug,

                -- Sales Volume
                COUNT(o.id) AS total_orders,
                COUNT(DISTINCT DATE_TRUNC('month', o.sold_at)) AS active_months,

                -- Revenue Metrics
                SUM(o.gross_sale) AS total_revenue,
                AVG(o.gross_sale) AS avg_order_value,
                MIN(o.gross_sale) AS min_order_value,
                MAX(o.gross_sale) AS max_order_value,

                -- Cost Structure
                SUM(o.platform_fee) AS total_fees,
                AVG(o.platform_fee) AS avg_fee,
                ROUND(AVG(o.platform_fee / NULLIF(o.gross_sale, 0)) * 100, 2) AS avg_fee_pct,
                SUM(o.shipping_cost) AS total_shipping,
                AVG(o.shipping_cost) AS avg_shipping,

                -- Profitability
                SUM(o.net_proceeds) AS total_proceeds,
                SUM(o.net_profit) AS total_profit,
                AVG(o.roi) AS avg_roi,
                ROUND(AVG(o.net_profit / NULLIF(o.gross_sale, 0)) * 100, 2) AS avg_profit_margin,

                -- Payout Performance
                COUNT(CASE WHEN o.payout_received THEN 1 END) AS payouts_received,
                AVG(EXTRACT(EPOCH FROM (o.payout_date - o.sold_at)) / 86400) AS avg_payout_days,

                -- Geographic Distribution
                COUNT(DISTINCT o.buyer_destination_country) AS countries_served,
                COUNT(DISTINCT o.buyer_destination_city) AS cities_served,

                -- Time Metrics
                MIN(o.sold_at) AS first_sale,
                MAX(o.sold_at) AS last_sale

            FROM transactions.orders o
            JOIN core.platforms p ON o.platform_id = p.id
            WHERE o.status = 'completed'
            GROUP BY p.id, p.name, p.slug
        """,
        "indexes": [
            "CREATE INDEX idx_platform_perf_id ON metabase_platform_performance(platform_id)",
            "CREATE INDEX idx_platform_perf_revenue ON metabase_platform_performance(total_revenue DESC)",
            "CREATE INDEX idx_platform_perf_orders ON metabase_platform_performance(total_orders DESC)"
        ]
    }

    # Inventory Status Views (Hourly refresh)
    INVENTORY_STATUS = {
        "name": "metabase_inventory_status",
        "refresh": RefreshStrategy.HOURLY,
        "description": "Current inventory status: stock levels, aging, valuation",
        "sql": """
            WITH inventory_sales AS (
                SELECT
                    inventory_item_id,
                    COUNT(*) AS times_sold,
                    MAX(sold_at) AS last_sold_at,
                    SUM(gross_sale) AS total_revenue,
                    SUM(net_profit) AS total_profit
                FROM transactions.orders
                WHERE status = 'completed'
                GROUP BY inventory_item_id
            )
            SELECT
                i.id AS inventory_id,
                i.product_id,
                prod.name AS product_name,
                prod.sku,
                b.name AS brand_name,
                cat.name AS category_name,

                -- Purchase Info
                i.purchase_price,
                i.gross_purchase_price,
                i.vat_amount,
                i.purchase_date,
                s.business_name AS supplier_name,

                -- Status
                i.status AS inventory_status,
                i.condition,
                i.size,
                i.color,

                -- Sales History
                COALESCE(sales.times_sold, 0) AS times_sold,
                sales.last_sold_at,
                sales.total_revenue,
                sales.total_profit,

                -- Aging
                EXTRACT(EPOCH FROM (NOW() - i.purchase_date)) / 86400 AS days_in_stock,
                CASE
                    WHEN EXTRACT(EPOCH FROM (NOW() - i.purchase_date)) / 86400 > 180 THEN 'Dead Stock'
                    WHEN EXTRACT(EPOCH FROM (NOW() - i.purchase_date)) / 86400 > 90 THEN 'Slow Moving'
                    WHEN EXTRACT(EPOCH FROM (NOW() - i.purchase_date)) / 86400 > 30 THEN 'Normal'
                    ELSE 'Fast Moving'
                END AS stock_category,

                -- Valuation
                CASE
                    WHEN sales.times_sold = 0 THEN i.gross_purchase_price
                    ELSE 0
                END AS current_inventory_value,

                i.created_at,
                i.updated_at

            FROM products.inventory i
            JOIN products.products prod ON i.product_id = prod.id
            LEFT JOIN core.brands b ON prod.brand_id = b.id
            LEFT JOIN products.categories cat ON prod.category_id = cat.id
            LEFT JOIN core.suppliers s ON i.supplier_id = s.id
            LEFT JOIN inventory_sales sales ON i.id = sales.inventory_item_id
        """,
        "indexes": [
            "CREATE INDEX idx_inv_status_id ON metabase_inventory_status(inventory_id)",
            "CREATE INDEX idx_inv_status_product ON metabase_inventory_status(product_id)",
            "CREATE INDEX idx_inv_status_brand ON metabase_inventory_status(brand_name)",
            "CREATE INDEX idx_inv_status_category ON metabase_inventory_status(stock_category)",
            "CREATE INDEX idx_inv_status_aging ON metabase_inventory_status(days_in_stock DESC)"
        ]
    }

    # Customer Geography Views (Daily refresh)
    CUSTOMER_GEOGRAPHY = {
        "name": "metabase_customer_geography",
        "refresh": RefreshStrategy.DAILY,
        "description": "Sales by country and city for market expansion insights",
        "sql": """
            SELECT
                o.buyer_destination_country AS country,
                o.buyer_destination_city AS city,

                -- Sales Volume
                COUNT(o.id) AS total_orders,
                COUNT(DISTINCT DATE_TRUNC('month', o.sold_at)) AS active_months,

                -- Revenue
                SUM(o.gross_sale) AS total_revenue,
                AVG(o.gross_sale) AS avg_order_value,

                -- Profitability
                SUM(o.net_profit) AS total_profit,
                AVG(o.roi) AS avg_roi,

                -- Shipping
                AVG(o.shipping_cost) AS avg_shipping_cost,

                -- Platform Mix
                COUNT(DISTINCT p.id) AS platforms_used,
                STRING_AGG(DISTINCT p.name, ', ') AS platform_names,

                -- Product Mix
                COUNT(DISTINCT prod.id) AS unique_products,
                COUNT(DISTINCT b.id) AS unique_brands,

                -- Time
                MIN(o.sold_at) AS first_order,
                MAX(o.sold_at) AS last_order

            FROM transactions.orders o
            JOIN core.platforms p ON o.platform_id = p.id
            JOIN products.inventory i ON o.inventory_item_id = i.id
            JOIN products.products prod ON i.product_id = prod.id
            LEFT JOIN core.brands b ON prod.brand_id = b.id
            WHERE o.status = 'completed'
              AND o.buyer_destination_country IS NOT NULL
            GROUP BY o.buyer_destination_country, o.buyer_destination_city
        """,
        "indexes": [
            "CREATE INDEX idx_cust_geo_country ON metabase_customer_geography(country)",
            "CREATE INDEX idx_cust_geo_city ON metabase_customer_geography(city)",
            "CREATE INDEX idx_cust_geo_revenue ON metabase_customer_geography(total_revenue DESC)"
        ]
    }

    # Supplier Performance Views (Weekly refresh)
    SUPPLIER_PERFORMANCE = {
        "name": "metabase_supplier_performance",
        "refresh": RefreshStrategy.WEEKLY,
        "description": "Supplier reliability, product quality, and profitability",
        "sql": """
            SELECT
                s.id AS supplier_id,
                s.business_name AS supplier_name,
                s.contact_email,
                s.phone,
                s.country,
                s.rating,

                -- Purchase Volume
                COUNT(i.id) AS total_purchases,
                SUM(i.gross_purchase_price) AS total_spent,
                AVG(i.gross_purchase_price) AS avg_purchase_price,

                -- Product Diversity
                COUNT(DISTINCT i.product_id) AS unique_products,
                COUNT(DISTINCT b.id) AS unique_brands,
                STRING_AGG(DISTINCT b.name, ', ') AS brand_list,

                -- Sales Performance
                COUNT(o.id) AS units_sold,
                ROUND((COUNT(o.id)::numeric / NULLIF(COUNT(i.id), 0)) * 100, 2) AS sell_through_rate,
                SUM(o.gross_sale) AS total_revenue_generated,
                SUM(o.net_profit) AS total_profit_generated,
                AVG(o.roi) AS avg_roi,

                -- Timing
                AVG(EXTRACT(EPOCH FROM (o.sold_at - i.purchase_date)) / 86400) AS avg_days_to_sell,

                -- Current Inventory
                COUNT(CASE WHEN o.id IS NULL THEN 1 END) AS unsold_units,
                SUM(CASE WHEN o.id IS NULL THEN i.gross_purchase_price ELSE 0 END) AS unsold_value,

                -- Time Range
                MIN(i.purchase_date) AS first_purchase,
                MAX(i.purchase_date) AS last_purchase

            FROM core.suppliers s
            JOIN products.inventory i ON i.supplier_id = s.id
            JOIN products.products prod ON i.product_id = prod.id
            LEFT JOIN core.brands b ON prod.brand_id = b.id
            LEFT JOIN transactions.orders o ON o.inventory_item_id = i.id AND o.status = 'completed'
            GROUP BY s.id, s.business_name, s.contact_email, s.phone, s.country, s.rating
        """,
        "indexes": [
            "CREATE INDEX idx_supp_perf_id ON metabase_supplier_performance(supplier_id)",
            "CREATE INDEX idx_supp_perf_revenue ON metabase_supplier_performance(total_revenue_generated DESC)",
            "CREATE INDEX idx_supp_perf_roi ON metabase_supplier_performance(avg_roi DESC)"
        ]
    }

    @classmethod
    def get_all_views(cls) -> List[Dict]:
        """Get all materialized view configurations"""
        return [
            cls.EXECUTIVE_METRICS,
            cls.PRODUCT_PERFORMANCE,
            cls.BRAND_ANALYTICS,
            cls.PLATFORM_PERFORMANCE,
            cls.INVENTORY_STATUS,
            cls.CUSTOMER_GEOGRAPHY,
            cls.SUPPLIER_PERFORMANCE
        ]

    @classmethod
    def get_view_by_name(cls, name: str) -> Dict:
        """Get specific view configuration by name"""
        for view in cls.get_all_views():
            if view["name"] == name:
                return view
        raise ValueError(f"View '{name}' not found")

    @classmethod
    def get_views_by_refresh_strategy(cls, strategy: RefreshStrategy) -> List[Dict]:
        """Get views by refresh strategy"""
        return [v for v in cls.get_all_views() if v["refresh"] == strategy]
