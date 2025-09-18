"""
SQLAlchemy Models for SoleFlipper
Clean, maintainable model definitions with proper relationships
"""

import os
import uuid

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Load environment variables from .env file
load_dotenv()

# Import the schema helper
from shared.database.utils import IS_POSTGRES, get_schema_ref

Base = declarative_base()

# --- Encryption Setup ---
ENCRYPTION_KEY = os.getenv("FIELD_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Fail loudly and clearly if the key is not set. Do not generate an ephemeral key.
    raise ValueError(
        "FATAL: The 'FIELD_ENCRYPTION_KEY' environment variable is not set or not passed to the container."
    )

try:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
except Exception as e:
    raise ValueError(
        f"FATAL: Invalid FIELD_ENCRYPTION_KEY. The key must be a valid Fernet key. Error: {e}"
    )
# -------------------------

# --- Dialect-specific Type Compilation ---
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(element, compiler, **kw):
    return compiler.visit_JSON(element, **kw)


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# =====================================================
# Core Domain Models
# =====================================================


class Brand(Base, TimestampMixin):
    __tablename__ = "brands"
    __table_args__ = {"schema": "core"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    products = relationship("Product", back_populates="brand")
    patterns = relationship(
        "BrandPattern", back_populates="brand", cascade="all, delete-orphan", lazy="selectin"
    )
    # Pricing relationships
    price_rules = relationship("PriceRule", back_populates="brand")
    brand_multipliers = relationship("BrandMultiplier", back_populates="brand")
    sales_forecasts = relationship("SalesForecast", back_populates="brand")
    demand_patterns = relationship("DemandPattern", back_populates="brand")
    pricing_kpis = relationship("PricingKPI", back_populates="brand")


class BrandPattern(Base, TimestampMixin):
    __tablename__ = "brand_patterns"
    __table_args__ = (
        Column("priority", Integer, default=100, nullable=False),
        {"schema": "core"} if IS_POSTGRES else {},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("brands.id", "core")), nullable=False
    )
    pattern_type = Column(String(50), nullable=False, default="regex")
    pattern = Column(String(255), nullable=False, unique=True)

    brand = relationship("Brand", back_populates="patterns")


class Category(Base, TimestampMixin):
    __tablename__ = "categories"
    __table_args__ = {"schema": "core"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("categories.id", "core")))
    path = Column(String(500))
    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent", overlaps="parent")
    products = relationship("Product", back_populates="category")
    # Pricing relationships
    price_rules = relationship("PriceRule", back_populates="category")
    sales_forecasts = relationship("SalesForecast", back_populates="category")
    demand_patterns = relationship("DemandPattern", back_populates="category")
    pricing_kpis = relationship("PricingKPI", back_populates="category")


class Size(Base, TimestampMixin):
    __tablename__ = "sizes"
    __table_args__ = {"schema": "core"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("categories.id", "core")))
    value = Column(String(20), nullable=False)
    standardized_value = Column(Numeric(4, 1))
    region = Column(String(10), nullable=False)
    category = relationship("Category")
    inventory_items = relationship("InventoryItem", back_populates="size")


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"
    __table_args__ = {"schema": "core"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(150))
    supplier_type = Column(String(50), nullable=False)
    business_size = Column(String(30))
    contact_person = Column(String(100))
    email = Column(String(100))
    phone = Column(String(50))
    website = Column(String(200))
    address_line1 = Column(String(200))
    address_line2 = Column(String(200))
    city = Column(String(100))
    state_province = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(50), default="Germany")
    tax_id = Column(String(50))
    vat_number = Column(String(50))
    business_registration = Column(String(100))
    return_policy_days = Column(Integer)
    return_policy_text = Column(Text)
    return_conditions = Column(String(500))
    accepts_exchanges = Column(Boolean, default=True)
    restocking_fee_percent = Column(Numeric(5, 2))
    payment_terms = Column(String(100))
    credit_limit = Column(Numeric(12, 2))
    discount_percent = Column(Numeric(5, 2))
    minimum_order_amount = Column(Numeric(10, 2))
    rating = Column(Numeric(3, 2))
    reliability_score = Column(Integer)
    quality_score = Column(Integer)
    status = Column(String(20), nullable=False, default="active")
    preferred = Column(Boolean, default=False)
    verified = Column(Boolean, default=False)
    average_processing_days = Column(Integer)
    ships_internationally = Column(Boolean, default=False)
    accepts_returns_by_mail = Column(Boolean, default=True)
    provides_authenticity_guarantee = Column(Boolean, default=False)
    has_api = Column(Boolean, default=False)
    api_endpoint = Column(String(200))
    api_key_encrypted = Column(Text)
    total_orders_count = Column(Integer, default=0)
    total_order_value = Column(Numeric(12, 2), default=0.00)
    average_order_value = Column(Numeric(10, 2))
    last_order_date = Column(DateTime(timezone=True))
    notes = Column(Text)
    internal_notes = Column(Text)
    tags = Column(JSONB)
    inventory_items = relationship("InventoryItem", back_populates="supplier_obj")


class Platform(Base, TimestampMixin):
    __tablename__ = "platforms"
    __table_args__ = {"schema": "core"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    fee_percentage = Column(Numeric(5, 2))
    supports_fees = Column(Boolean, default=True)
    active = Column(Boolean, default=True)
    transactions = relationship("Transaction", back_populates="platform")
    # Pricing relationships
    price_rules = relationship("PriceRule", back_populates="platform")
    sales_forecasts = relationship("SalesForecast", back_populates="platform")
    pricing_kpis = relationship("PricingKPI", back_populates="platform")
    price_history = relationship("PriceHistory", back_populates="platform")


class SystemConfig(Base, TimestampMixin):
    __tablename__ = "system_config"
    __table_args__ = {"schema": "core"} if IS_POSTGRES else None

    key = Column(String(100), primary_key=True)
    value_encrypted = Column(Text, nullable=False)
    description = Column(Text)

    def set_value(self, value: str):
        if not isinstance(value, str):
            raise TypeError("Value must be a string")
        self.value_encrypted = cipher_suite.encrypt(value.encode()).decode()

    def get_value(self) -> str:
        if not self.value_encrypted:
            return ""
        decrypted_bytes = cipher_suite.decrypt(self.value_encrypted.encode())
        return decrypted_bytes.decode()

    @staticmethod
    def get_encryption_key_for_setup() -> str:
        return ENCRYPTION_KEY


# =====================================================
# Product Domain Models
# =====================================================


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = {"schema": "products"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String(100), nullable=False, unique=True)
    brand_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("brands.id", "core")), nullable=True
    )
    category_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("categories.id", "core")), nullable=False
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)
    retail_price = Column(Numeric(10, 2))
    avg_resale_price = Column(Numeric(10, 2))
    release_date = Column(DateTime(timezone=True))
    brand = relationship("Brand", back_populates="products")
    category = relationship("Category", back_populates="products")
    inventory_items = relationship("InventoryItem", back_populates="product")
    # Pricing relationships
    price_history = relationship("PriceHistory", back_populates="product")
    market_prices = relationship("MarketPrice", back_populates="product")
    sales_forecasts = relationship("SalesForecast", back_populates="product")
    demand_patterns = relationship("DemandPattern", back_populates="product")
    pricing_kpis = relationship("PricingKPI", back_populates="product")

    def to_dict(self):
        return {
            "id": str(self.id),
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "retail_price": self.retail_price,
            "release_date": self.release_date,
            "brand_name": self.brand.name if self.brand else None,
            "category_name": self.category.name if self.category else None,
        }


class InventoryItem(Base, TimestampMixin):
    __tablename__ = "inventory"
    __table_args__ = {"schema": "products"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("products.id", "products")), nullable=False
    )
    size_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("sizes.id", "core")), nullable=False
    )
    supplier_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("suppliers.id", "core")), nullable=True
    )
    quantity = Column(Integer, nullable=False, default=1)
    purchase_price = Column(Numeric(10, 2))
    purchase_date = Column(DateTime(timezone=True))
    supplier = Column(String(100))
    status = Column(String(50), nullable=False, default="in_stock")
    notes = Column(Text)
    external_ids = Column(JSONB, nullable=True, default=dict)
    product = relationship("Product", back_populates="inventory_items")
    size = relationship("Size", back_populates="inventory_items")
    supplier_obj = relationship("Supplier", back_populates="inventory_items")
    transactions = relationship("Transaction", back_populates="inventory_item")
    price_history = relationship("PriceHistory", back_populates="inventory_item")

    def to_dict(self):
        return {
            "id": str(self.id),
            "product_id": str(self.product_id),
            "size": self.size.value if self.size else None,
            "quantity": self.quantity,
            "purchase_price": self.purchase_price,
            "purchase_date": self.purchase_date,
            "supplier": self.supplier,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# =====================================================
# Sales Domain Models
# =====================================================


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = {"schema": "sales"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("inventory.id", "products")), nullable=False
    )
    platform_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("platforms.id", "core")), nullable=False
    )
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    sale_price = Column(Numeric(10, 2), nullable=False)
    platform_fee = Column(Numeric(10, 2), nullable=False)
    shipping_cost = Column(Numeric(10, 2), nullable=False, default=0)
    net_profit = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    external_id = Column(String(100))
    buyer_destination_country = Column(String(100))
    buyer_destination_city = Column(String(100))
    notes = Column(Text)
    inventory_item = relationship("InventoryItem", back_populates="transactions")
    platform = relationship("Platform", back_populates="transactions")


class Listing(Base, TimestampMixin):
    __tablename__ = "listings"
    __table_args__ = {"schema": "products"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_item_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("inventory.id", "products")), nullable=False
    )

    stockx_listing_id = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(String(50), nullable=False, index=True)
    amount = Column(Numeric(10, 2))
    currency_code = Column(String(10))
    inventory_type = Column(String(50))
    expires_at = Column(DateTime(timezone=True))
    stockx_created_at = Column(DateTime(timezone=True))
    last_stockx_updated_at = Column(DateTime(timezone=True))

    raw_data = Column(JSONB)

    inventory_item = relationship("InventoryItem")  # Simplified relationship


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = {"schema": "sales"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_item_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("inventory.id", "products")), nullable=False
    )
    listing_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("listings.id", "products")), nullable=True
    )

    stockx_order_number = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(String(50), nullable=False, index=True)
    amount = Column(Numeric(10, 2))
    currency_code = Column(String(10))
    inventory_type = Column(String(50))

    shipping_label_url = Column(String(512))
    shipping_document_path = Column(String(512))  # For locally stored PDFs

    stockx_created_at = Column(DateTime(timezone=True))
    last_stockx_updated_at = Column(DateTime(timezone=True))

    raw_data = Column(JSONB)

    inventory_item = relationship("InventoryItem")
    listing = relationship("Listing")


# =====================================================
# Integration Domain Models
# =====================================================


class ImportBatch(Base, TimestampMixin):
    __tablename__ = "import_batches"
    __table_args__ = {"schema": "integration"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String(50), nullable=False)
    source_file = Column(String(255))
    total_records = Column(Integer, default=0)
    processed_records = Column(Integer, default=0)
    error_records = Column(Integer, default=0)
    status = Column(String(50), default="pending")
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Retry tracking fields
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_error = Column(String(1000))
    error_message = Column(String(1000))
    next_retry_at = Column(DateTime(timezone=True))
    
    import_records = relationship("ImportRecord", back_populates="batch")


class ImportRecord(Base, TimestampMixin):
    __tablename__ = "import_records"
    __table_args__ = {"schema": "integration"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey(get_schema_ref("import_batches.id", "integration")),
        nullable=False,
    )
    source_data = Column(JSONB, nullable=False)
    processed_data = Column(JSONB)
    validation_errors = Column(JSONB)
    status = Column(String(50), default="pending")
    processing_started_at = Column(DateTime(timezone=True))
    processing_completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    batch = relationship("ImportBatch", back_populates="import_records")


# =====================================================
# Logging Domain Models
# =====================================================


class SystemLog(Base):
    __tablename__ = "system_logs"
    __table_args__ = {"schema": "logging"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(String(20), nullable=False)
    component = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSONB)
    source_table = Column(String(100))
    source_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StockXPresaleMarking(Base, TimestampMixin):
    """Separate table for StockX presale markings without inventory constraints"""
    __tablename__ = "stockx_presale_markings"
    __table_args__ = {"schema": "products"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stockx_listing_id = Column(String(100), nullable=False, unique=True, index=True)
    product_name = Column(String(255))
    size = Column(String(20))
    is_presale = Column(Boolean, default=True)
    marked_at = Column(DateTime(timezone=True), default=func.now())
    unmarked_at = Column(DateTime(timezone=True))


class EventStore(Base, TimestampMixin):
    """Event store for domain events and event sourcing"""
    __tablename__ = "event_store"
    __table_args__ = {"schema": "logging"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False, index=True) 
    event_data = Column(JSONB, nullable=False)
    correlation_id = Column(UUID(as_uuid=True), index=True)
    causation_id = Column(UUID(as_uuid=True), index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    version = Column(Integer, default=1)


class MarketPrice(Base, TimestampMixin):
    """External market prices for QuickFlip detection"""
    __tablename__ = "market_prices"
    __table_args__ = {"schema": "integration"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("products.id", "products")), nullable=False
    )
    source = Column(String(100), nullable=False, comment="Data source: awin, webgains, scraping, etc.")
    supplier_name = Column(String(100), nullable=False, comment="Retailer/supplier name")
    external_id = Column(String(255), nullable=True, comment="External product ID from source")
    buy_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")
    availability = Column(String(50), nullable=True)
    stock_qty = Column(Integer, nullable=True)
    product_url = Column(Text, nullable=True)
    last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    raw_data = Column(JSONB, nullable=True, comment="Complete source data")

    # Relationships
    product = relationship("Product", back_populates="market_prices")

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "product_id": str(self.product_id),
            "source": self.source,
            "supplier_name": self.supplier_name,
            "external_id": self.external_id,
            "buy_price": float(self.buy_price) if self.buy_price else None,
            "currency": self.currency,
            "availability": self.availability,
            "stock_qty": self.stock_qty,
            "product_url": self.product_url,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Import pricing models to register them with SQLAlchemy
# This ensures the relationships defined above are properly linked
from domains.pricing.models import *  # noqa: F401,F403
