"""
Budibase Configuration Generator
===============================

Automatically generates v2.2.1 compatible Budibase configurations from SoleFlipper API schemas.
Validates API compatibility and creates realistic, working configurations.
"""

import json
import logging
from datetime import datetime
from typing import List, Set

import httpx

from shared.config.settings import get_settings
from ..schemas.budibase_models import (
    BudibaseApp,
    BudibaseAutomation,
    BudibaseComponent,
    BudibaseConnector,
    BudibaseDataSource,
    BudibaseScreen,
    BudibaseValidationResult,
    AutomationTrigger,
    ComponentType,
    DataSourceType,
    BudibaseEnvironment
)

logger = logging.getLogger(__name__)


class BudibaseConfigGenerator:
    """
    Generates Budibase configurations from SoleFlipper API schemas.
    Ensures v2.2.1 compatibility and realistic feature mapping.
    """

    def __init__(self):
        self.settings = get_settings()
        self.api_base_url = f"http://{self.settings.api.host}:{self.settings.api.port}/api/v1"
        self.validated_endpoints: Set[str] = set()
        self.broken_endpoints: Set[str] = set()

    async def generate_app_config(
        self,
        app_name: str = "SoleFlipper Business App",
        environment: BudibaseEnvironment = BudibaseEnvironment.DEVELOPMENT,
        validate_endpoints: bool = True
    ) -> BudibaseApp:
        """
        Generate complete Budibase app configuration for v2.2.1.

        Args:
            app_name: Application name
            environment: Target environment
            validate_endpoints: Whether to validate API endpoints

        Returns:
            Complete Budibase application configuration
        """
        logger.info(f"Generating Budibase config for {app_name} in {environment}")

        # Validate API endpoints first
        if validate_endpoints:
            await self._validate_api_endpoints()

        # Generate core components
        data_sources = await self._generate_data_sources()
        connectors = await self._generate_connectors()
        screens = await self._generate_screens()
        automations = await self._generate_automations()

        # Create application configuration
        app_config = BudibaseApp(
            name=app_name,
            description="Professional sneaker resale management system - v2.2.1 Compatible",
            version="2.2.1",
            environment=environment,
            data_sources=data_sources,
            connectors=connectors,
            screens=screens,
            automations=automations,
            theme="midnight",
            navigation={
                "title": "SoleFlipper",
                "hideTitle": False,
                "logo": "/assets/soleflip-logo.png"
            },
            roles=[
                {
                    "name": "Admin",
                    "permissions": ["read", "write", "admin"]
                },
                {
                    "name": "User",
                    "permissions": ["read", "write"]
                },
                {
                    "name": "Viewer",
                    "permissions": ["read"]
                }
            ],
            created_at=datetime.utcnow(),
            created_by="SoleFlipper-ConfigGenerator-v2.2.1"
        )

        logger.info(f"Generated Budibase config with {len(data_sources)} data sources, {len(screens)} screens")
        return app_config

    async def _validate_api_endpoints(self) -> BudibaseValidationResult:
        """Validate SoleFlipper API endpoints for v2.2.1 compatibility"""
        logger.info("Validating SoleFlipper API endpoints...")

        # Test critical endpoints
        test_endpoints = [
            "/quickflip/opportunities",
            "/quickflip/opportunities/summary",
            "/dashboard/metrics",
            "/inventory/items",
            "/health"
        ]

        async with httpx.AsyncClient() as client:
            for endpoint in test_endpoints:
                try:
                    url = f"{self.api_base_url}{endpoint}"
                    response = await client.get(url, timeout=5.0)

                    if response.status_code == 200:
                        self.validated_endpoints.add(endpoint)
                        logger.debug(f"✅ Endpoint working: {endpoint}")
                    else:
                        self.broken_endpoints.add(endpoint)
                        logger.warning(f"❌ Endpoint failed: {endpoint} - Status: {response.status_code}")

                except Exception as e:
                    self.broken_endpoints.add(endpoint)
                    logger.error(f"❌ Endpoint error: {endpoint} - {str(e)}")

        logger.info(f"API Validation: {len(self.validated_endpoints)} working, {len(self.broken_endpoints)} broken")

    async def _generate_data_sources(self) -> List[BudibaseDataSource]:
        """Generate validated data sources for v2.2.1"""
        data_sources = []

        # 1. SoleFlipper Backend API (validated endpoints only)
        backend_queries = {}

        if "/quickflip/opportunities" in self.validated_endpoints:
            backend_queries["getQuickFlipOpportunities"] = {
                "method": "GET",
                "path": "/quickflip/opportunities",
                "parameters": {
                    "min_profit_margin": {"type": "number", "default": 15.0},
                    "limit": {"type": "number", "default": 50}
                }
            }

        if "/quickflip/opportunities/summary" in self.validated_endpoints:
            backend_queries["getOpportunitySummary"] = {
                "method": "GET",
                "path": "/quickflip/opportunities/summary"
            }

        if "/dashboard/metrics" in self.validated_endpoints:
            backend_queries["getDashboardMetrics"] = {
                "method": "GET",
                "path": "/dashboard/metrics"
            }
        elif "/inventory/items" in self.validated_endpoints:
            # Fallback: use inventory items if dashboard broken
            backend_queries["getInventoryItems"] = {
                "method": "GET",
                "path": "/inventory/items",
                "parameters": {
                    "limit": {"type": "number", "default": 10}
                }
            }

        backend_api = BudibaseDataSource(
            name="SoleFlipper Backend API",
            type=DataSourceType.REST_API,
            config={
                "url": self.api_base_url,
                "defaultHeaders": {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                "timeout": 10000
            },
            queries=backend_queries,
            enabled=True
        )
        data_sources.append(backend_api)

        # 2. PostgreSQL Database (only if available)
        postgres_ds = BudibaseDataSource(
            name="SoleFlipper Database",
            type=DataSourceType.POSTGRES,
            config={
                "host": "localhost",
                "port": 5432,
                "database": "soleflip",
                "schema": "public",
                "ssl": False
            },
            queries={
                "getProducts": {
                    "sql": "SELECT id, name, brand, sku FROM products.products LIMIT 100"
                },
                "getOrdersCount": {
                    "sql": "SELECT COUNT(*) as total_orders FROM orders.transactions WHERE created_at >= NOW() - INTERVAL '30 days'"
                }
            },
            enabled=True
        )
        data_sources.append(postgres_ds)

        logger.info(f"Generated {len(data_sources)} data sources with {len(backend_queries)} validated endpoints")
        return data_sources

    async def _generate_connectors(self) -> List[BudibaseConnector]:
        """Generate realistic API connectors (no fictional features)"""
        connectors = []

        # Only create connector for validated endpoints
        if self.validated_endpoints:
            soleflip_connector = BudibaseConnector(
                name="SoleFlipper API Connector",
                description="Validated v2.2.1 API endpoints only",
                base_url=self.api_base_url,
                authentication={"type": "none"},
                headers={"Content-Type": "application/json"},
                endpoints={
                    endpoint.replace("/", "_"): {
                        "method": "GET",
                        "path": endpoint,
                        "validated": True
                    }
                    for endpoint in self.validated_endpoints
                },
                timeout=30,
                retries=3
            )
            connectors.append(soleflip_connector)

        logger.info(f"Generated {len(connectors)} connectors")
        return connectors

    async def _generate_screens(self) -> List[BudibaseScreen]:
        """Generate working screens based on validated endpoints"""
        screens = []

        # 1. Dashboard Screen (adaptive based on available endpoints)
        dashboard_components = [
            BudibaseComponent(
                type=ComponentType.CONTAINER,
                props={"direction": "column", "gap": "M"},
                children=[
                    BudibaseComponent(
                        type=ComponentType.TEXT,
                        props={
                            "text": "SoleFlipper Dashboard v2.2.1",
                            "size": "L",
                            "weight": "bold"
                        }
                    )
                ]
            )
        ]

        # Add QuickFlip section if endpoint works
        if "/quickflip/opportunities/summary" in self.validated_endpoints:
            quickflip_card = BudibaseComponent(
                type=ComponentType.CARD,
                props={"title": "QuickFlip Opportunities", "width": "50%"},
                children=[
                    BudibaseComponent(
                        type=ComponentType.DATA_PROVIDER,
                        props={
                            "datasource": "SoleFlipper Backend API",
                            "query": "getOpportunitySummary"
                        },
                        children=[
                            BudibaseComponent(
                                type=ComponentType.TEXT,
                                props={"text": "{{ data.total_opportunities }} Opportunities"}
                            )
                        ]
                    )
                ]
            )
            dashboard_components[0].children.append(quickflip_card)

        # Add status info about broken endpoints
        if self.broken_endpoints:
            status_card = BudibaseComponent(
                type=ComponentType.CARD,
                props={"title": "API Status", "width": "50%"},
                children=[
                    BudibaseComponent(
                        type=ComponentType.TEXT,
                        props={
                            "text": f"⚠️ {len(self.broken_endpoints)} endpoints need fixing",
                            "color": "warning"
                        }
                    )
                ]
            )
            dashboard_components[0].children.append(status_card)

        dashboard_screen = BudibaseScreen(
            name="Dashboard",
            route="/",
            layout="basic",
            components=dashboard_components,
            data_sources=["SoleFlipper Backend API"]
        )
        screens.append(dashboard_screen)

        # 2. QuickFlip Screen (only if endpoint works)
        if "/quickflip/opportunities" in self.validated_endpoints:
            quickflip_screen = BudibaseScreen(
                name="QuickFlip Opportunities",
                route="/quickflip",
                layout="basic",
                components=[
                    BudibaseComponent(
                        type=ComponentType.CONTAINER,
                        props={"direction": "column", "gap": "M"},
                        children=[
                            BudibaseComponent(
                                type=ComponentType.TEXT,
                                props={"text": "QuickFlip Opportunities", "size": "L"}
                            ),
                            BudibaseComponent(
                                type=ComponentType.DATA_PROVIDER,
                                props={
                                    "datasource": "SoleFlipper Backend API",
                                    "query": "getQuickFlipOpportunities"
                                },
                                children=[
                                    BudibaseComponent(
                                        type=ComponentType.TABLE,
                                        props={
                                            "columns": [
                                                {"name": "product_name", "displayName": "Product"},
                                                {"name": "buy_price", "displayName": "Buy Price"},
                                                {"name": "sell_price", "displayName": "Sell Price"},
                                                {"name": "gross_profit", "displayName": "Profit"},
                                                {"name": "profit_margin", "displayName": "Margin %"}
                                            ]
                                        }
                                    )
                                ]
                            )
                        ]
                    )
                ],
                data_sources=["SoleFlipper Backend API"]
            )
            screens.append(quickflip_screen)

        logger.info(f"Generated {len(screens)} screens")
        return screens

    async def _generate_automations(self) -> List[BudibaseAutomation]:
        """Generate realistic automations (no fictional features)"""
        automations = []

        # Only create automations for working endpoints
        if "/quickflip/opportunities/summary" in self.validated_endpoints:
            opportunity_alert = BudibaseAutomation(
                name="QuickFlip Alert Monitor",
                description="Monitor for new high-profit opportunities (realistic version)",
                trigger=AutomationTrigger.SCHEDULE,
                trigger_config={
                    "interval": "*/30 * * * *",  # Every 30 minutes (realistic)
                    "description": "Check every 30 minutes"
                },
                steps=[
                    {
                        "name": "fetch_opportunities",
                        "type": "query",
                        "datasource": "SoleFlipper Backend API",
                        "query": "getOpportunitySummary"
                    },
                    {
                        "name": "check_threshold",
                        "type": "conditional",
                        "condition": "{{ data.total_opportunities > 10 }}",
                        "true_steps": [
                            {
                                "name": "log_alert",
                                "type": "log",
                                "message": "High opportunity count detected: {{ data.total_opportunities }}"
                            }
                        ]
                    }
                ],
                enabled=True,
                environment=BudibaseEnvironment.DEVELOPMENT
            )
            automations.append(opportunity_alert)

        logger.info(f"Generated {len(automations)} automations")
        return automations

    async def validate_config(self, config: BudibaseApp) -> BudibaseValidationResult:
        """Validate generated configuration"""
        errors = []
        warnings = []
        missing_endpoints = []

        # Check data source endpoints
        for ds in config.data_sources:
            if ds.type == DataSourceType.REST_API:
                for query_name, query_config in ds.queries.items():
                    endpoint = query_config.get("path", "")
                    if endpoint not in self.validated_endpoints:
                        if endpoint in self.broken_endpoints:
                            errors.append(f"Endpoint {endpoint} is broken")
                        else:
                            missing_endpoints.append(endpoint)

        # Check for deprecated features
        deprecated_features = []
        for ds in config.data_sources:
            if "selling" in str(ds.config):
                deprecated_features.append("Selling domain references (removed in v2.2.1)")

        is_valid = len(errors) == 0

        return BudibaseValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            api_compatibility={ep: True for ep in self.validated_endpoints},
            missing_endpoints=missing_endpoints,
            deprecated_features=deprecated_features
        )

    def export_config(self, config: BudibaseApp, file_path: str) -> None:
        """Export configuration to JSON file"""
        config_dict = config.dict()
        config_dict["_metadata"] = {
            "generated_by": "SoleFlipper-ConfigGenerator-v2.2.1",
            "generated_at": datetime.utcnow().isoformat(),
            "validated_endpoints": list(self.validated_endpoints),
            "broken_endpoints": list(self.broken_endpoints),
            "version": "2.2.1"
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, default=str)

        logger.info(f"Exported Budibase config to {file_path}")