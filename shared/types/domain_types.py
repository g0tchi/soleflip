"""
Domain-specific type definitions
"""
from typing import Dict, List, Optional, Union, Literal
from typing_extensions import TypedDict, NotRequired
from datetime import datetime
from decimal import Decimal
from enum import Enum
from .base_types import EntityId, Price, Quantity, Timestamp, JSONDict


# Product Domain Types
class ProductStatus(str, Enum):
    """Product status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"
    OUT_OF_STOCK = "out_of_stock"


class InventoryStatus(str, Enum):
    """Inventory item status enumeration"""
    IN_STOCK = "in_stock"
    LISTED_STOCKX = "listed_stockx"
    LISTED_ALIAS = "listed_alias"
    SOLD = "sold"
    RESERVED = "reserved"
    ERROR = "error"


class SizeRegion(str, Enum):
    """Size region enumeration"""
    US = "US"
    UK = "UK"
    EU = "EU"
    JP = "JP"
    KR = "KR"
    CM = "CM"


class ProductData(TypedDict):
    """Product data structure"""
    id: NotRequired[EntityId]
    sku: str
    name: str
    brand_id: NotRequired[EntityId]
    category_id: EntityId
    description: NotRequired[str]
    retail_price: NotRequired[Price]
    avg_resale_price: NotRequired[Price]
    release_date: NotRequired[datetime]
    status: NotRequired[ProductStatus]
    created_at: NotRequired[Timestamp]
    updated_at: NotRequired[Timestamp]


class InventoryItemData(TypedDict):
    """Inventory item data structure"""
    id: NotRequired[EntityId]
    product_id: EntityId
    size_id: EntityId
    supplier_id: NotRequired[EntityId]
    quantity: Quantity
    purchase_price: NotRequired[Price]
    purchase_date: NotRequired[datetime]
    supplier: NotRequired[str]
    status: InventoryStatus
    notes: NotRequired[str]
    external_ids: NotRequired[JSONDict]
    created_at: NotRequired[Timestamp]
    updated_at: NotRequired[Timestamp]


class BrandData(TypedDict):
    """Brand data structure"""
    id: NotRequired[EntityId]
    name: str
    slug: str
    description: NotRequired[str]
    website: NotRequired[str]
    logo_url: NotRequired[str]
    created_at: NotRequired[Timestamp]
    updated_at: NotRequired[Timestamp]


class CategoryData(TypedDict):
    """Category data structure"""
    id: NotRequired[EntityId]
    name: str
    slug: str
    parent_id: NotRequired[EntityId]
    path: NotRequired[str]
    description: NotRequired[str]
    created_at: NotRequired[Timestamp]
    updated_at: NotRequired[Timestamp]


class SizeData(TypedDict):
    """Size data structure"""
    id: NotRequired[EntityId]
    category_id: NotRequired[EntityId]
    value: str
    standardized_value: NotRequired[Decimal]
    region: SizeRegion
    created_at: NotRequired[Timestamp]
    updated_at: NotRequired[Timestamp]


# Sales Domain Types
class TransactionStatus(str, Enum):
    """Transaction status enumeration"""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class PlatformType(str, Enum):
    """Platform type enumeration"""
    STOCKX = "stockx"
    GOAT = "goat"
    ALIAS = "alias"
    EBAY = "ebay"
    DIRECT = "direct"
    OTHER = "other"


class TransactionData(TypedDict):
    """Transaction data structure"""
    id: NotRequired[EntityId]
    inventory_id: EntityId
    platform_id: EntityId
    transaction_date: datetime
    sale_price: Price
    platform_fee: Price
    shipping_cost: Price
    net_profit: Price
    status: TransactionStatus
    external_id: NotRequired[str]
    buyer_destination_country: NotRequired[str]
    buyer_destination_city: NotRequired[str]
    notes: NotRequired[str]
    created_at: NotRequired[Timestamp]
    updated_at: NotRequired[Timestamp]


class PlatformData(TypedDict):
    """Platform data structure"""
    id: NotRequired[EntityId]
    name: str
    slug: str
    platform_type: PlatformType
    fee_percentage: NotRequired[Decimal]
    supports_fees: bool
    active: bool
    api_base_url: NotRequired[str]
    created_at: NotRequired[Timestamp]
    updated_at: NotRequired[Timestamp]


class ListingData(TypedDict):
    """Listing data structure"""
    id: NotRequired[EntityId]
    inventory_item_id: EntityId
    platform_id: NotRequired[EntityId]
    external_listing_id: str
    status: str
    amount: NotRequired[Price]
    currency_code: NotRequired[str]
    inventory_type: NotRequired[str]
    expires_at: NotRequired[datetime]
    external_created_at: NotRequired[datetime]
    last_external_updated_at: NotRequired[datetime]
    raw_data: NotRequired[JSONDict]
    created_at: NotRequired[Timestamp]
    updated_at: NotRequired[Timestamp]


class OrderData(TypedDict):
    """Order data structure"""
    id: NotRequired[EntityId]
    inventory_item_id: EntityId
    listing_id: NotRequired[EntityId]
    platform_id: NotRequired[EntityId]
    external_order_number: str
    status: str
    amount: NotRequired[Price]
    currency_code: NotRequired[str]
    inventory_type: NotRequired[str]
    shipping_label_url: NotRequired[str]
    shipping_document_path: NotRequired[str]
    external_created_at: NotRequired[datetime]
    last_external_updated_at: NotRequired[datetime]
    raw_data: NotRequired[JSONDict]
    created_at: NotRequired[Timestamp]
    updated_at: NotRequired[Timestamp]


# Supplier Domain Types
class SupplierType(str, Enum):
    """Supplier type enumeration"""
    RETAILER = "retailer"
    WHOLESALER = "wholesaler"
    MANUFACTURER = "manufacturer"
    INDIVIDUAL = "individual"
    CONSIGNMENT = "consignment"
    DROPSHIPPER = "dropshipper"


class SupplierStatus(str, Enum):
    """Supplier status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_APPROVAL = "pending_approval"


class BusinessSize(str, Enum):
    """Business size enumeration"""
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


class SupplierData(TypedDict):
    """Supplier data structure"""
    id: NotRequired[EntityId]
    name: str
    slug: str
    display_name: NotRequired[str]
    supplier_type: SupplierType
    business_size: NotRequired[BusinessSize]
    contact_person: NotRequired[str]
    email: NotRequired[str]
    phone: NotRequired[str]
    website: NotRequired[str]
    
    # Address information
    address_line1: NotRequired[str]
    address_line2: NotRequired[str]
    city: NotRequired[str]
    state_province: NotRequired[str]
    postal_code: NotRequired[str]
    country: NotRequired[str]
    
    # Business information
    tax_id: NotRequired[str]
    vat_number: NotRequired[str]
    business_registration: NotRequired[str]
    
    # Terms and conditions
    return_policy_days: NotRequired[int]
    return_policy_text: NotRequired[str]
    return_conditions: NotRequired[str]
    accepts_exchanges: NotRequired[bool]
    restocking_fee_percent: NotRequired[Decimal]
    payment_terms: NotRequired[str]
    credit_limit: NotRequired[Decimal]
    discount_percent: NotRequired[Decimal]
    minimum_order_amount: NotRequired[Decimal]
    
    # Performance metrics
    rating: NotRequired[Decimal]
    reliability_score: NotRequired[int]
    quality_score: NotRequired[int]
    
    # Status and flags
    status: SupplierStatus
    preferred: NotRequired[bool]
    verified: NotRequired[bool]
    
    # Operational details
    average_processing_days: NotRequired[int]
    ships_internationally: NotRequired[bool]
    accepts_returns_by_mail: NotRequired[bool]
    provides_authenticity_guarantee: NotRequired[bool]
    
    # API integration
    has_api: NotRequired[bool]
    api_endpoint: NotRequired[str]
    api_key_encrypted: NotRequired[str]
    
    # Statistics
    total_orders_count: NotRequired[int]
    total_order_value: NotRequired[Decimal]
    average_order_value: NotRequired[Decimal]
    last_order_date: NotRequired[datetime]
    
    # Notes and metadata
    notes: NotRequired[str]
    internal_notes: NotRequired[str]
    tags: NotRequired[JSONDict]
    
    created_at: NotRequired[Timestamp]
    updated_at: NotRequired[Timestamp]


# Integration Domain Types
class ImportSourceType(str, Enum):
    """Import source type enumeration"""
    CSV_UPLOAD = "csv_upload"
    STOCKX_API = "stockx_api"
    MANUAL_ENTRY = "manual_entry"
    WEBHOOK = "webhook"
    BATCH_IMPORT = "batch_import"


class ImportStatus(str, Enum):
    """Import status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class ImportBatchData(TypedDict):
    """Import batch data structure"""
    id: NotRequired[EntityId]
    source_type: ImportSourceType
    source_file: NotRequired[str]
    total_records: int
    processed_records: int
    error_records: int
    status: ImportStatus
    started_at: NotRequired[datetime]
    completed_at: NotRequired[datetime]
    metadata: NotRequired[JSONDict]
    created_at: NotRequired[Timestamp]
    updated_at: NotRequired[Timestamp]


class ImportRecordData(TypedDict):
    """Import record data structure"""
    id: NotRequired[EntityId]
    batch_id: EntityId
    source_data: JSONDict
    processed_data: NotRequired[JSONDict]
    validation_errors: NotRequired[List[str]]
    status: ImportStatus
    processing_started_at: NotRequired[datetime]
    processing_completed_at: NotRequired[datetime]
    error_message: NotRequired[str]
    created_at: NotRequired[Timestamp]
    updated_at: NotRequired[Timestamp]


# Analytics Types
class MetricType(str, Enum):
    """Metric type enumeration"""
    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    PERCENTAGE = "percentage"
    RATIO = "ratio"


class TimeGranularity(str, Enum):
    """Time granularity for analytics"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class AnalyticsMetric(TypedDict):
    """Analytics metric structure"""
    name: str
    type: MetricType
    value: Union[int, float, Decimal]
    previous_value: NotRequired[Union[int, float, Decimal]]
    change_percent: NotRequired[float]
    timestamp: datetime
    granularity: TimeGranularity
    dimensions: NotRequired[Dict[str, str]]


class DashboardData(TypedDict):
    """Dashboard data structure"""
    title: str
    metrics: List[AnalyticsMetric]
    charts: List[Dict[str, any]]
    filters: NotRequired[Dict[str, any]]
    last_updated: datetime


# Search and Filter Types
class SearchScope(str, Enum):
    """Search scope enumeration"""
    PRODUCTS = "products"
    INVENTORY = "inventory"
    TRANSACTIONS = "transactions"
    SUPPLIERS = "suppliers"
    BRANDS = "brands"
    ALL = "all"


class SortDirection(str, Enum):
    """Sort direction enumeration"""
    ASC = "asc"
    DESC = "desc"


class SearchQuery(TypedDict):
    """Search query structure"""
    query: NotRequired[str]
    scope: SearchScope
    filters: NotRequired[Dict[str, any]]
    sort_by: NotRequired[str]
    sort_direction: NotRequired[SortDirection]
    skip: NotRequired[int]
    limit: NotRequired[int]


class SearchResult(TypedDict):
    """Search result structure"""
    items: List[Dict[str, any]]
    total: int
    query: SearchQuery
    facets: NotRequired[Dict[str, List[Dict[str, any]]]]
    suggestions: NotRequired[List[str]]


# Webhook Types
class WebhookEvent(str, Enum):
    """Webhook event enumeration"""
    PRODUCT_CREATED = "product.created"
    PRODUCT_UPDATED = "product.updated"
    INVENTORY_UPDATED = "inventory.updated"
    TRANSACTION_CREATED = "transaction.created"
    ORDER_STATUS_CHANGED = "order.status_changed"
    IMPORT_COMPLETED = "import.completed"


class WebhookPayload(TypedDict):
    """Webhook payload structure"""
    event: WebhookEvent
    data: Dict[str, any]
    timestamp: datetime
    source: str
    version: str
    signature: NotRequired[str]


# Configuration Types
class ExternalServiceConfig(TypedDict):
    """External service configuration"""
    enabled: bool
    base_url: str
    api_key: NotRequired[str]
    timeout: int
    retry_attempts: int
    rate_limit: NotRequired[Dict[str, int]]


class StockXConfig(ExternalServiceConfig):
    """StockX specific configuration"""
    client_id: str
    client_secret: str
    refresh_token: str


class IntegrationSettings(TypedDict):
    """Integration settings structure"""
    stockx: NotRequired[StockXConfig]
    metabase: NotRequired[ExternalServiceConfig]
    n8n: NotRequired[ExternalServiceConfig]