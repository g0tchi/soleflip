"""
Metabase Dashboard Service
==========================

Service for generating and managing Metabase dashboards programmatically.
"""

import logging
from typing import Dict, Optional

from ..schemas.metabase_models import MetabaseDashboard, DashboardCard, DashboardParameter

logger = logging.getLogger(__name__)


class MetabaseDashboardService:
    """
    Generates pre-configured Metabase dashboards for SoleFlipper.

    Features:
    - Executive dashboard templates
    - Product analytics dashboards
    - Platform performance dashboards
    - Inventory management dashboards
    """

    def __init__(self):
        self.dashboards: Dict[str, MetabaseDashboard] = {}

    def generate_executive_dashboard(self) -> MetabaseDashboard:
        """
        Generate executive dashboard with high-level KPIs.

        Cards:
        - Total Revenue (current month)
        - Total Profit (current month)
        - Average ROI
        - Active Orders
        - Revenue Trend (12 months)
        - Platform Performance Comparison
        - Top 10 Products by Revenue
        - Geographic Distribution
        """
        dashboard = MetabaseDashboard(
            name="Executive Dashboard - SoleFlipper",
            description="High-level KPIs and business metrics for executive decision making",
            parameters=[
                DashboardParameter(
                    name="Date Range", slug="date_range", type="date/range", default="past30days"
                )
            ],
            ordered_cards=[
                # Row 1: KPI Cards (4 scalars)
                DashboardCard(card_id=1, row=0, col=0, size_x=3, size_y=3),  # Total Revenue card
                DashboardCard(card_id=2, row=0, col=3, size_x=3, size_y=3),  # Total Profit card
                DashboardCard(card_id=3, row=0, col=6, size_x=3, size_y=3),  # Average ROI card
                DashboardCard(card_id=4, row=0, col=9, size_x=3, size_y=3),  # Active Orders card
                # Row 2: Revenue Trend (line chart)
                DashboardCard(card_id=5, row=3, col=0, size_x=12, size_y=6),  # Revenue trend card
                # Row 3: Platform Performance (bar chart) + Top Products (table)
                DashboardCard(
                    card_id=6, row=9, col=0, size_x=6, size_y=6  # Platform performance card
                ),
                DashboardCard(card_id=7, row=9, col=6, size_x=6, size_y=6),  # Top products card
                # Row 4: Geographic Distribution (map)
                DashboardCard(
                    card_id=8, row=15, col=0, size_x=12, size_y=6  # Geographic distribution card
                ),
            ],
        )

        self.dashboards["executive"] = dashboard
        return dashboard

    def generate_product_analytics_dashboard(self) -> MetabaseDashboard:
        """
        Generate product analytics dashboard.

        Cards:
        - Top Products by Revenue
        - Top Products by Units Sold
        - Product Performance Table
        - Brand Performance Comparison
        - Category Distribution
        - Price Distribution Analysis
        - Sell-Through Rate by Brand
        """
        dashboard = MetabaseDashboard(
            name="Product Analytics - SoleFlipper",
            description="Detailed product and brand performance analytics",
            parameters=[
                DashboardParameter(
                    name="Date Range", slug="date_range", type="date/range", default="past90days"
                ),
                DashboardParameter(name="Brand", slug="brand", type="string/=", default=None),
            ],
            ordered_cards=[
                # Row 1: Top Products (2 bar charts)
                DashboardCard(card_id=10, row=0, col=0, size_x=6, size_y=6),  # Top by revenue
                DashboardCard(card_id=11, row=0, col=6, size_x=6, size_y=6),  # Top by units
                # Row 2: Brand Performance (pie chart) + Category Distribution (donut)
                DashboardCard(card_id=12, row=6, col=0, size_x=6, size_y=6),  # Brand performance
                DashboardCard(
                    card_id=13, row=6, col=6, size_x=6, size_y=6  # Category distribution
                ),
                # Row 3: Product Performance Table
                DashboardCard(
                    card_id=14, row=12, col=0, size_x=12, size_y=8  # Detailed product table
                ),
                # Row 4: Price Distribution (histogram) + Sell-Through (bar)
                DashboardCard(card_id=15, row=20, col=0, size_x=6, size_y=6),  # Price distribution
                DashboardCard(card_id=16, row=20, col=6, size_x=6, size_y=6),  # Sell-through rate
            ],
        )

        self.dashboards["product_analytics"] = dashboard
        return dashboard

    def generate_platform_performance_dashboard(self) -> MetabaseDashboard:
        """
        Generate multi-platform performance dashboard.

        Cards:
        - Total Orders by Platform
        - Revenue by Platform
        - Average Fees by Platform
        - Payout Performance
        - Platform Profitability Comparison
        - Geographic Coverage by Platform
        """
        dashboard = MetabaseDashboard(
            name="Platform Performance - SoleFlipper",
            description="Multi-platform sales and profitability analysis",
            parameters=[
                DashboardParameter(
                    name="Date Range", slug="date_range", type="date/range", default="past30days"
                ),
                DashboardParameter(name="Platform", slug="platform", type="string/=", default=None),
            ],
            ordered_cards=[
                # Row 1: Platform KPIs (4 scalars)
                DashboardCard(card_id=20, row=0, col=0, size_x=3, size_y=3),  # Total orders
                DashboardCard(card_id=21, row=0, col=3, size_x=3, size_y=3),  # Total revenue
                DashboardCard(card_id=22, row=0, col=6, size_x=3, size_y=3),  # Average fees
                DashboardCard(card_id=23, row=0, col=9, size_x=3, size_y=3),  # Avg payout days
                # Row 2: Revenue by Platform (bar) + Fee Comparison (bar)
                DashboardCard(card_id=24, row=3, col=0, size_x=6, size_y=6),  # Revenue by platform
                DashboardCard(card_id=25, row=3, col=6, size_x=6, size_y=6),  # Fee comparison
                # Row 3: Platform Profitability Table
                DashboardCard(
                    card_id=26, row=9, col=0, size_x=12, size_y=8  # Detailed platform metrics
                ),
                # Row 4: Geographic Coverage (map)
                DashboardCard(
                    card_id=27, row=17, col=0, size_x=12, size_y=6  # Geographic coverage
                ),
            ],
        )

        self.dashboards["platform_performance"] = dashboard
        return dashboard

    def generate_inventory_management_dashboard(self) -> MetabaseDashboard:
        """
        Generate inventory management dashboard.

        Cards:
        - Current Stock Value
        - Dead Stock Count
        - Average Days in Stock
        - Inventory Aging Distribution
        - Stock Status by Category
        - Supplier Performance
        - Slow-Moving Items
        """
        dashboard = MetabaseDashboard(
            name="Inventory Management - SoleFlipper",
            description="Inventory status, aging analysis, and supplier performance",
            parameters=[
                DashboardParameter(
                    name="Stock Category", slug="stock_category", type="string/=", default=None
                ),
                DashboardParameter(name="Supplier", slug="supplier", type="string/=", default=None),
            ],
            ordered_cards=[
                # Row 1: Inventory KPIs (4 scalars)
                DashboardCard(card_id=30, row=0, col=0, size_x=3, size_y=3),  # Current stock value
                DashboardCard(card_id=31, row=0, col=3, size_x=3, size_y=3),  # Dead stock count
                DashboardCard(card_id=32, row=0, col=6, size_x=3, size_y=3),  # Avg days in stock
                DashboardCard(card_id=33, row=0, col=9, size_x=3, size_y=3),  # Slow-moving items
                # Row 2: Aging Distribution (bar) + Status by Category (pie)
                DashboardCard(card_id=34, row=3, col=0, size_x=6, size_y=6),  # Aging distribution
                DashboardCard(card_id=35, row=3, col=6, size_x=6, size_y=6),  # Status by category
                # Row 3: Inventory Status Table
                DashboardCard(
                    card_id=36, row=9, col=0, size_x=12, size_y=8  # Detailed inventory table
                ),
                # Row 4: Supplier Performance (table)
                DashboardCard(card_id=37, row=17, col=0, size_x=12, size_y=6),  # Supplier metrics
            ],
        )

        self.dashboards["inventory_management"] = dashboard
        return dashboard

    def get_dashboard(self, dashboard_name: str) -> Optional[MetabaseDashboard]:
        """Get generated dashboard by name"""
        return self.dashboards.get(dashboard_name)

    def get_all_dashboards(self) -> Dict[str, MetabaseDashboard]:
        """Get all generated dashboards"""
        return self.dashboards

    def generate_all_dashboards(self) -> Dict[str, MetabaseDashboard]:
        """Generate all pre-configured dashboards"""
        self.generate_executive_dashboard()
        self.generate_product_analytics_dashboard()
        self.generate_platform_performance_dashboard()
        self.generate_inventory_management_dashboard()

        logger.info(f"Generated {len(self.dashboards)} Metabase dashboards")
        return self.dashboards
