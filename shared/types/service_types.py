"""
Service layer type definitions
"""

from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import NotRequired, TypedDict

from .base_types import EntityId
from .domain_types import *

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


# Service Result Types
class ServiceResultStatus(str, Enum):
    """Service operation result status"""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class ServiceResult(Generic[T]):
    """Generic service operation result"""

    def __init__(
        self,
        status: ServiceResultStatus,
        data: Optional[T] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.status = status
        self.data = data
        self.error = error
        self.metadata = metadata or {}

    @classmethod
    def success(cls, data: T, metadata: Optional[Dict[str, Any]] = None) -> "ServiceResult[T]":
        """Create successful result"""
        return cls(ServiceResultStatus.SUCCESS, data=data, metadata=metadata)

    @classmethod
    def failure(cls, error: str, metadata: Optional[Dict[str, Any]] = None) -> "ServiceResult[T]":
        """Create failure result"""
        return cls(ServiceResultStatus.FAILURE, error=error, metadata=metadata)

    @classmethod
    def partial(
        cls, data: T, error: str, metadata: Optional[Dict[str, Any]] = None
    ) -> "ServiceResult[T]":
        """Create partial success result"""
        return cls(ServiceResultStatus.PARTIAL, data=data, error=error, metadata=metadata)

    def is_success(self) -> bool:
        """Check if result is successful"""
        return self.status == ServiceResultStatus.SUCCESS

    def is_failure(self) -> bool:
        """Check if result is a failure"""
        return self.status == ServiceResultStatus.FAILURE

    def is_partial(self) -> bool:
        """Check if result is partial success"""
        return self.status == ServiceResultStatus.PARTIAL


# Repository Protocols
@runtime_checkable
class Repository(Protocol[T]):
    """Repository protocol for data access"""

    async def create(self, data: Dict[str, Any]) -> T:
        """Create new entity"""
        ...

    async def get_by_id(self, id: EntityId) -> Optional[T]:
        """Get entity by ID"""
        ...

    async def update(self, id: EntityId, data: Dict[str, Any]) -> Optional[T]:
        """Update entity"""
        ...

    async def delete(self, id: EntityId) -> bool:
        """Delete entity"""
        ...

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all entities with pagination"""
        ...


@runtime_checkable
class SearchableRepository(Repository[T], Protocol):
    """Repository with search capabilities"""

    async def search(
        self, query: str, filters: Optional[Dict[str, Any]] = None, skip: int = 0, limit: int = 100
    ) -> tuple[List[T], int]:
        """Search entities with filters and pagination"""
        ...


@runtime_checkable
class CacheableRepository(Repository[T], Protocol):
    """Repository with caching capabilities"""

    async def get_cached(self, id: EntityId, ttl: int = 300) -> Optional[T]:
        """Get entity from cache"""
        ...

    async def invalidate_cache(self, id: EntityId) -> None:
        """Invalidate cache for entity"""
        ...


# Service Protocols
@runtime_checkable
class DomainService(Protocol):
    """Domain service protocol"""

    def __init__(self, db_session: AsyncSession):
        """Initialize service with database session"""
        ...


@runtime_checkable
class CRUDService(Protocol[T]):
    """CRUD service protocol"""

    async def create(self, data: Dict[str, Any]) -> ServiceResult[T]:
        """Create new entity"""
        ...

    async def get(self, id: EntityId) -> ServiceResult[Optional[T]]:
        """Get entity by ID"""
        ...

    async def update(self, id: EntityId, data: Dict[str, Any]) -> ServiceResult[Optional[T]]:
        """Update entity"""
        ...

    async def delete(self, id: EntityId) -> ServiceResult[bool]:
        """Delete entity"""
        ...

    async def list(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> ServiceResult[tuple[List[T], int]]:
        """List entities with pagination"""
        ...


# External Service Protocols
@runtime_checkable
class ExternalAPIService(Protocol):
    """External API service protocol"""

    async def authenticate(self) -> ServiceResult[bool]:
        """Authenticate with external service"""
        ...

    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Check service health"""
        ...

    async def get_rate_limit_status(self) -> ServiceResult[Dict[str, Any]]:
        """Get rate limit information"""
        ...


@runtime_checkable
class DataSyncService(Protocol[T]):
    """Data synchronization service protocol"""

    async def sync_all(self) -> ServiceResult[Dict[str, int]]:
        """Sync all data from external source"""
        ...

    async def sync_entity(self, id: EntityId) -> ServiceResult[Optional[T]]:
        """Sync specific entity"""
        ...

    async def get_sync_status(self) -> ServiceResult[Dict[str, Any]]:
        """Get synchronization status"""
        ...


# Business Logic Service Types
class ValidationRule(TypedDict):
    """Validation rule structure"""

    field: str
    rule: str
    message: str
    params: NotRequired[Dict[str, Any]]


class BusinessRule(TypedDict):
    """Business rule structure"""

    name: str
    condition: str
    action: str
    message: str
    enabled: bool


class ServiceConfiguration(TypedDict):
    """Service configuration structure"""

    name: str
    version: str
    dependencies: List[str]
    settings: Dict[str, Any]
    validation_rules: List[ValidationRule]
    business_rules: List[BusinessRule]


# Event and Messaging Types
class DomainEvent(TypedDict):
    """Domain event structure"""

    event_type: str
    entity_id: EntityId
    entity_type: str
    data: Dict[str, Any]
    timestamp: datetime
    version: int
    correlation_id: Optional[str]


class EventHandler(Protocol):
    """Event handler protocol"""

    async def handle(self, event: DomainEvent) -> ServiceResult[None]:
        """Handle domain event"""
        ...


class MessageBroker(Protocol):
    """Message broker protocol"""

    async def publish(self, topic: str, message: Dict[str, Any]) -> ServiceResult[None]:
        """Publish message to topic"""
        ...

    async def subscribe(self, topic: str, handler: Callable) -> ServiceResult[None]:
        """Subscribe to topic with handler"""
        ...


# Import and Export Service Types
class ImportConfiguration(TypedDict):
    """Import configuration structure"""

    source_type: ImportSourceType
    batch_size: int
    validation_enabled: bool
    duplicate_handling: str  # "skip", "update", "error"
    field_mappings: Dict[str, str]
    transformations: List[Dict[str, Any]]


class ImportProgress(TypedDict):
    """Import progress structure"""

    batch_id: EntityId
    total_records: int
    processed_records: int
    successful_records: int
    failed_records: int
    current_batch: int
    total_batches: int
    estimated_completion: Optional[datetime]
    status: ImportStatus


class ExportConfiguration(TypedDict):
    """Export configuration structure"""

    format: str  # "csv", "json", "xlsx"
    fields: List[str]
    filters: Optional[Dict[str, Any]]
    batch_size: int
    compression: Optional[str]


# Analytics and Reporting Service Types
class MetricCalculation(TypedDict):
    """Metric calculation configuration"""

    name: str
    type: MetricType
    source_query: str
    dimensions: List[str]
    filters: Optional[Dict[str, Any]]
    aggregation: str


class ReportConfiguration(TypedDict):
    """Report configuration structure"""

    name: str
    description: str
    metrics: List[MetricCalculation]
    time_range: Dict[str, Any]
    grouping: List[str]
    output_format: str


class DashboardConfiguration(TypedDict):
    """Dashboard configuration structure"""

    name: str
    description: str
    widgets: List[Dict[str, Any]]
    filters: List[Dict[str, Any]]
    refresh_interval: int
    permissions: List[str]


# Notification Service Types
class NotificationChannel(str, Enum):
    """Notification channel enumeration"""

    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    PUSH = "push"


class NotificationPriority(str, Enum):
    """Notification priority enumeration"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationTemplate(TypedDict):
    """Notification template structure"""

    id: str
    name: str
    channel: NotificationChannel
    subject: str
    body: str
    variables: List[str]


class NotificationRequest(TypedDict):
    """Notification request structure"""

    template_id: str
    channel: NotificationChannel
    recipient: str
    variables: Dict[str, Any]
    priority: NotificationPriority
    scheduled_at: Optional[datetime]


# Audit and Logging Service Types
class AuditAction(str, Enum):
    """Audit action enumeration"""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"


class AuditEntry(TypedDict):
    """Audit entry structure"""

    id: EntityId
    user_id: Optional[EntityId]
    action: AuditAction
    entity_type: str
    entity_id: Optional[EntityId]
    changes: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime


# Cache Service Types
class CacheStrategy(str, Enum):
    """Cache strategy enumeration"""

    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"


class CacheConfiguration(TypedDict):
    """Cache configuration structure"""

    strategy: CacheStrategy
    max_size: int
    default_ttl: int
    namespace: str
    serialization: str  # "json", "pickle"


# Background Task Service Types
class TaskPriority(str, Enum):
    """Background task priority"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    """Background task status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class BackgroundTask(TypedDict):
    """Background task structure"""

    id: EntityId
    name: str
    function: str
    arguments: List[Any]
    keyword_arguments: Dict[str, Any]
    priority: TaskPriority
    status: TaskStatus
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    retry_count: int
    max_retries: int
    result: Optional[Any]
    error: Optional[str]


# Service Factory Types
ServiceFactory = Callable[..., T]
AsyncServiceFactory = Callable[..., Awaitable[T]]


class ServiceRegistry(Protocol):
    """Service registry protocol"""

    def register(self, name: str, factory: ServiceFactory[T]) -> None:
        """Register service factory"""
        ...

    def get(self, name: str) -> T:
        """Get service instance"""
        ...

    def has(self, name: str) -> bool:
        """Check if service is registered"""
        ...


# Monitoring and Health Check Types
class HealthStatus(str, Enum):
    """Health status enumeration"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(TypedDict):
    """Component health structure"""

    name: str
    status: HealthStatus
    message: Optional[str]
    details: Dict[str, Any]
    last_check: datetime
    response_time_ms: Optional[float]


class SystemHealth(TypedDict):
    """System health structure"""

    overall_status: HealthStatus
    components: List[ComponentHealth]
    version: str
    uptime_seconds: float
    timestamp: datetime


# Configuration Service Types
class ConfigurationScope(str, Enum):
    """Configuration scope enumeration"""

    GLOBAL = "global"
    ENVIRONMENT = "environment"
    SERVICE = "service"
    USER = "user"


class ConfigurationEntry(TypedDict):
    """Configuration entry structure"""

    key: str
    value: Any
    scope: ConfigurationScope
    description: Optional[str]
    type: str
    default_value: Optional[Any]
    encrypted: bool
    last_updated: datetime
