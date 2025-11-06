"""
Budibase Data Models
===================

Pydantic models for Budibase configuration management and API integration.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class BudibaseEnvironment(str, Enum):
    """Budibase deployment environments"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DataSourceType(str, Enum):
    """Supported data source types"""

    REST_API = "rest"
    POSTGRES = "postgres"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    REDIS = "redis"


class ComponentType(str, Enum):
    """Budibase component types"""

    CONTAINER = "container"
    CARD = "card"
    TABLE = "table"
    FORM = "form"
    CHART = "chart"
    TEXT = "text"
    BUTTON = "button"
    DATA_PROVIDER = "dataprovider"


class AutomationTrigger(str, Enum):
    """Automation trigger types"""

    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    DATABASE = "database"
    API_RESPONSE = "api_response"


class BudibaseDataSource(BaseModel):
    """Budibase data source configuration"""

    name: str = Field(..., description="Data source display name")
    type: DataSourceType = Field(..., description="Data source type")
    config: Dict[str, Any] = Field(..., description="Data source configuration")
    queries: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Predefined queries"
    )
    enabled: bool = Field(default=True, description="Data source enabled status")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "SoleFlipper API",
                "type": "rest",
                "config": {
                    "url": "http://127.0.0.1:8000/api/v1",
                    "defaultHeaders": {"Content-Type": "application/json"},
                },
                "queries": {
                    "getQuickFlipOpportunities": {
                        "method": "GET",
                        "path": "/quickflip/opportunities",
                    }
                },
            }
        }


class BudibaseConnector(BaseModel):
    """Enhanced API connector configuration"""

    name: str = Field(..., description="Connector name")
    description: str = Field(..., description="Connector description")
    base_url: str = Field(..., description="Base API URL")
    authentication: Dict[str, Any] = Field(
        default_factory=dict, description="Authentication config"
    )
    headers: Dict[str, str] = Field(default_factory=dict, description="Default headers")
    endpoints: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="API endpoints")
    rate_limiting: Optional[Dict[str, int]] = Field(None, description="Rate limiting config")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retries: int = Field(default=3, description="Retry attempts")


class BudibaseComponent(BaseModel):
    """Budibase UI component"""

    type: ComponentType = Field(..., description="Component type")
    props: Dict[str, Any] = Field(default_factory=dict, description="Component properties")
    children: List["BudibaseComponent"] = Field(
        default_factory=list, description="Child components"
    )
    conditions: Optional[Dict[str, Any]] = Field(None, description="Display conditions")

    class Config:
        # Allow self-referencing for nested components
        arbitrary_types_allowed = True


class BudibaseScreen(BaseModel):
    """Budibase screen configuration"""

    name: str = Field(..., description="Screen name")
    route: str = Field(..., description="Screen route path")
    layout: str = Field(default="basic", description="Screen layout type")
    access_level: str = Field(default="public", description="Access level requirement")
    components: List[BudibaseComponent] = Field(
        default_factory=list, description="Screen components"
    )
    data_sources: List[str] = Field(default_factory=list, description="Required data sources")

    @validator("route")
    def validate_route(cls, v):
        if not v.startswith("/"):
            return f"/{v}"
        return v


class BudibaseAutomation(BaseModel):
    """Budibase automation workflow"""

    name: str = Field(..., description="Automation name")
    description: str = Field(..., description="Automation description")
    trigger: AutomationTrigger = Field(..., description="Trigger type")
    trigger_config: Dict[str, Any] = Field(
        default_factory=dict, description="Trigger configuration"
    )
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="Automation steps")
    enabled: bool = Field(default=True, description="Automation enabled status")
    environment: BudibaseEnvironment = Field(default=BudibaseEnvironment.DEVELOPMENT)


class BudibaseApp(BaseModel):
    """Complete Budibase application configuration"""

    name: str = Field(..., description="Application name")
    description: str = Field(..., description="Application description")
    version: str = Field(default="2.2.1", description="Application version")
    environment: BudibaseEnvironment = Field(default=BudibaseEnvironment.DEVELOPMENT)

    # Core components
    data_sources: List[BudibaseDataSource] = Field(default_factory=list)
    connectors: List[BudibaseConnector] = Field(default_factory=list)
    screens: List[BudibaseScreen] = Field(default_factory=list)
    automations: List[BudibaseAutomation] = Field(default_factory=list)

    # Configuration
    theme: str = Field(default="midnight", description="Application theme")
    navigation: Dict[str, Any] = Field(default_factory=dict, description="Navigation configuration")
    roles: List[Dict[str, Any]] = Field(
        default_factory=list, description="User roles and permissions"
    )

    # Metadata
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Creator identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "SoleFlipper Business App",
                "description": "Professional sneaker resale management system",
                "version": "2.2.1",
                "environment": "development",
                "theme": "midnight",
                "navigation": {"title": "SoleFlipper", "hideTitle": False},
            }
        }


class BudibaseDeployment(BaseModel):
    """Budibase deployment configuration"""

    app_id: str = Field(..., description="Budibase application ID")
    environment: BudibaseEnvironment = Field(..., description="Target environment")
    config: BudibaseApp = Field(..., description="Application configuration")
    deployment_url: Optional[str] = Field(None, description="Deployed application URL")
    status: str = Field(default="pending", description="Deployment status")
    deployed_at: Optional[datetime] = Field(None, description="Deployment timestamp")
    logs: List[str] = Field(default_factory=list, description="Deployment logs")


class BudibaseValidationResult(BaseModel):
    """Configuration validation result"""

    is_valid: bool = Field(..., description="Validation status")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    api_compatibility: Dict[str, bool] = Field(
        default_factory=dict, description="API endpoint compatibility"
    )
    missing_endpoints: List[str] = Field(default_factory=list, description="Missing API endpoints")
    deprecated_features: List[str] = Field(
        default_factory=list, description="Deprecated features used"
    )


class BudibaseSyncStatus(BaseModel):
    """Synchronization status"""

    last_sync: Optional[datetime] = Field(None, description="Last synchronization timestamp")
    sync_status: str = Field(default="pending", description="Synchronization status")
    changes_detected: int = Field(default=0, description="Number of changes detected")
    sync_errors: List[str] = Field(default_factory=list, description="Synchronization errors")
    next_sync: Optional[datetime] = Field(None, description="Next scheduled sync")


# Update forward references for nested models
BudibaseComponent.model_rebuild()
