"""
Metabase Data Models
===================

Pydantic models for Metabase integration entities.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MetabaseDatabase(BaseModel):
    """Metabase database connection configuration"""
    id: Optional[int] = None
    name: str
    engine: str = "postgres"
    details: Dict[str, Any]
    is_sample: bool = False
    is_full_sync: bool = True
    is_on_demand: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MetabaseCollection(BaseModel):
    """Metabase collection for organizing dashboards and questions"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    color: str = "#509EE3"
    archived: bool = False
    location: str = "/"
    personal_owner_id: Optional[int] = None


class VisualizationType(str, Enum):
    """Metabase visualization types"""
    TABLE = "table"
    BAR = "bar"
    LINE = "line"
    AREA = "area"
    PIE = "pie"
    SCALAR = "scalar"
    SMARTSCALAR = "smartscalar"
    PROGRESS = "progress"
    GAUGE = "gauge"
    MAP = "map"
    FUNNEL = "funnel"
    WATERFALL = "waterfall"


class MetabaseCard(BaseModel):
    """Metabase card (question/chart) configuration"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    display: VisualizationType
    visualization_settings: Dict[str, Any] = Field(default_factory=dict)
    dataset_query: Dict[str, Any]
    database_id: Optional[int] = None
    table_id: Optional[int] = None
    collection_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MetabaseQuestion(BaseModel):
    """Metabase question (saved query)"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    query: Dict[str, Any]
    display: VisualizationType = VisualizationType.TABLE
    visualization_settings: Dict[str, Any] = Field(default_factory=dict)
    collection_id: Optional[int] = None
    database_id: Optional[int] = None


class DashboardParameter(BaseModel):
    """Metabase dashboard parameter (filter)"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    slug: str
    type: str  # e.g., "date/range", "string/=", "number/="
    default: Optional[Any] = None


class DashboardCard(BaseModel):
    """Card placement on dashboard"""
    id: Optional[int] = None
    card_id: int
    row: int = 0
    col: int = 0
    size_x: int = 4
    size_y: int = 4
    parameter_mappings: List[Dict[str, Any]] = Field(default_factory=list)
    visualization_settings: Dict[str, Any] = Field(default_factory=dict)


class MetabaseDashboard(BaseModel):
    """Metabase dashboard configuration"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    parameters: List[DashboardParameter] = Field(default_factory=list)
    ordered_cards: List[DashboardCard] = Field(default_factory=list)
    collection_id: Optional[int] = None
    archived: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MaterializedViewStatus(BaseModel):
    """Status of materialized view"""
    view_name: str
    exists: bool
    last_refresh: Optional[datetime] = None
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    indexes: List[str] = Field(default_factory=list)


class RefreshJobStatus(BaseModel):
    """Status of materialized view refresh job"""
    view_name: str
    job_id: Optional[str] = None
    status: str  # "pending", "running", "completed", "failed"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
