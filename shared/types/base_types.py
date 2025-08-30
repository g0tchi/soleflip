"""
Base type definitions and type aliases
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
    Tuple,
    Set,
    Callable,
    Awaitable,
    AsyncGenerator,
    Generator,
    TypeVar,
    Generic,
    Protocol,
    runtime_checkable,
    Literal,
    Final,
    ClassVar,
    TYPE_CHECKING,
)
from typing_extensions import TypedDict, NotRequired
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from enum import Enum, IntEnum
from pathlib import Path
import sys

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

# Basic type aliases
JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONDict = Dict[str, JSONValue]
JSONList = List[JSONValue]

# Database types
DatabaseRow = Dict[str, Any]
DatabaseResult = List[DatabaseRow]

# ID types
EntityId = UUID
UserId = UUID
ProductId = UUID
InventoryItemId = UUID
TransactionId = UUID
SupplierId = UUID
BrandId = UUID
CategoryId = UUID
PlatformId = UUID

# String constraints
SKU = str  # Product SKU
Slug = str  # URL-friendly identifier
Email = str  # Email address
PhoneNumber = str  # Phone number
CountryCode = str  # ISO country code
CurrencyCode = str  # ISO currency code

# Numeric types
Price = Decimal
Quantity = int
Percentage = Decimal
Rating = Decimal

# Time types
Timestamp = datetime
DateOnly = date
ISOString = str  # ISO formatted datetime string

# File types
FilePath = Union[str, Path]
FileSize = int  # Size in bytes
MimeType = str

# Generic types
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
P = ParamSpec("P")

# Response types
ResponseData = TypeVar("ResponseData")
ErrorData = TypeVar("ErrorData")


class StatusEnum(str, Enum):
    """Base status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class PriorityEnum(IntEnum):
    """Priority levels"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class EnvironmentEnum(str, Enum):
    """Application environments"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


# Protocol definitions for type checking
@runtime_checkable
class Identifiable(Protocol):
    """Protocol for objects with an ID"""

    id: EntityId


@runtime_checkable
class Timestamped(Protocol):
    """Protocol for objects with timestamps"""

    created_at: datetime
    updated_at: datetime


@runtime_checkable
class Serializable(Protocol):
    """Protocol for objects that can be serialized to dict"""

    def to_dict(self) -> Dict[str, Any]: ...


@runtime_checkable
class Cacheable(Protocol):
    """Protocol for cacheable objects"""

    def cache_key(self) -> str: ...
    def cache_ttl(self) -> int: ...


# Configuration types
class DatabaseConfig(TypedDict):
    """Database configuration structure"""

    url: str
    pool_size: int
    max_overflow: int
    echo: bool


class APIConfig(TypedDict):
    """API configuration structure"""

    host: str
    port: int
    title: str
    version: str
    debug: bool


class SecurityConfig(TypedDict):
    """Security configuration structure"""

    secret_key: str
    encryption_key: str
    cors_origins: List[str]
    allowed_hosts: List[str]


# Error types
class ErrorInfo(TypedDict):
    """Error information structure"""

    code: str
    message: str
    details: NotRequired[Dict[str, Any]]
    timestamp: str


class ValidationError(TypedDict):
    """Validation error structure"""

    field: str
    message: str
    code: str
    value: NotRequired[Any]


# Pagination types
class PaginationInfo(TypedDict):
    """Pagination information"""

    skip: int
    limit: int
    total: int
    has_more: bool
    page: int
    total_pages: int


class FilterParams(TypedDict, total=False):
    """Filter parameters for queries"""

    search: str
    brand: str
    category: str
    status: str
    min_price: Decimal
    max_price: Decimal
    date_from: datetime
    date_to: datetime


# Callback types
ErrorHandler = Callable[[Exception], None]
AsyncErrorHandler = Callable[[Exception], Awaitable[None]]
ProgressCallback = Callable[[int, int], None]
AsyncProgressCallback = Callable[[int, int], Awaitable[None]]

# Service types
ServiceResult = Tuple[bool, Optional[str]]  # (success, error_message)
AsyncServiceResult = Awaitable[ServiceResult]

# Repository types
RepositoryFilter = Dict[str, Any]
RepositorySort = Dict[str, Union[Literal["asc"], Literal["desc"]]]


# External API types
class HTTPMethod(str, Enum):
    """HTTP methods"""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class HTTPStatus(IntEnum):
    """Common HTTP status codes"""

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503


# Utility types for complex operations
class AsyncContextManager(Protocol[T]):
    """Protocol for async context managers"""

    async def __aenter__(self) -> T: ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]: ...


class Comparable(Protocol):
    """Protocol for comparable objects"""

    def __lt__(self, other: Any) -> bool: ...
    def __le__(self, other: Any) -> bool: ...
    def __gt__(self, other: Any) -> bool: ...
    def __ge__(self, other: Any) -> bool: ...


# Factory types
Factory = Callable[[], T]
AsyncFactory = Callable[[], Awaitable[T]]
ParameterizedFactory = Callable[[K], T]
AsyncParameterizedFactory = Callable[[K], Awaitable[T]]

# Event types
EventHandler = Callable[[Dict[str, Any]], None]
AsyncEventHandler = Callable[[Dict[str, Any]], Awaitable[None]]

# Middleware types
MiddlewareFunction = Callable[[Any, Callable], Awaitable[Any]]
WSGIMiddleware = Callable[[Dict[str, Any], Callable], Awaitable[Any]]

# Constants
MAX_PAGE_SIZE: Final[int] = 1000
DEFAULT_PAGE_SIZE: Final[int] = 50
MAX_BULK_SIZE: Final[int] = 10000
DEFAULT_CACHE_TTL: Final[int] = 300


# Type guards
def is_uuid(value: Any) -> bool:
    """Type guard for UUID values"""
    if isinstance(value, UUID):
        return True
    if isinstance(value, str):
        try:
            UUID(value)
            return True
        except ValueError:
            pass
    return False


def is_decimal(value: Any) -> bool:
    """Type guard for Decimal values"""
    if isinstance(value, Decimal):
        return True
    if isinstance(value, (int, float, str)):
        try:
            Decimal(str(value))
            return True
        except (ValueError, TypeError):
            pass
    return False


def is_timestamp(value: Any) -> bool:
    """Type guard for datetime values"""
    return isinstance(value, datetime)


# Type conversion utilities
def ensure_uuid(value: Union[str, UUID]) -> UUID:
    """Ensure value is a UUID instance"""
    if isinstance(value, UUID):
        return value
    return UUID(value)


def ensure_decimal(value: Union[str, int, float, Decimal]) -> Decimal:
    """Ensure value is a Decimal instance"""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def ensure_list(value: Union[T, List[T]]) -> List[T]:
    """Ensure value is a list"""
    if isinstance(value, list):
        return value
    return [value]


# Generic result types
class Result(Generic[T]):
    """Result type for operations that can succeed or fail"""

    def __init__(self, success: bool, data: Optional[T] = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error

    @classmethod
    def ok(cls, data: T) -> "Result[T]":
        """Create successful result"""
        return cls(True, data=data)

    @classmethod
    def fail(cls, error: str) -> "Result[T]":
        """Create failed result"""
        return cls(False, error=error)

    def is_ok(self) -> bool:
        """Check if result is successful"""
        return self.success

    def is_err(self) -> bool:
        """Check if result is an error"""
        return not self.success

    def unwrap(self) -> T:
        """Get data or raise exception"""
        if not self.success:
            raise RuntimeError(self.error or "Operation failed")
        return self.data

    def unwrap_or(self, default: T) -> T:
        """Get data or default value"""
        return self.data if self.success else default


# Option type for nullable values
class Option(Generic[T]):
    """Option type for nullable values"""

    def __init__(self, value: Optional[T]):
        self._value = value

    @classmethod
    def some(cls, value: T) -> "Option[T]":
        """Create Some option"""
        return cls(value)

    @classmethod
    def none(cls) -> "Option[T]":
        """Create None option"""
        return cls(None)

    def is_some(self) -> bool:
        """Check if option has a value"""
        return self._value is not None

    def is_none(self) -> bool:
        """Check if option is None"""
        return self._value is None

    def unwrap(self) -> T:
        """Get value or raise exception"""
        if self._value is None:
            raise RuntimeError("Called unwrap on None option")
        return self._value

    def unwrap_or(self, default: T) -> T:
        """Get value or default"""
        return self._value if self._value is not None else default

    def map(self, func: Callable[[T], K]) -> "Option[K]":
        """Transform value if present"""
        if self._value is None:
            return Option.none()
        return Option.some(func(self._value))


if TYPE_CHECKING:
    # Additional imports only for type checking
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi import Request, Response
    from pydantic import BaseModel
