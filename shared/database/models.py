"""
SQLAlchemy Models for SoleFlipper
Clean, maintainable model definitions with proper relationships
"""

import os
import uuid

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
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


class EncryptedFieldMixin:
    """Mixin for models that need encrypted field support"""

    def get_encrypted_field(self, field_name: str) -> str:
        """Get decrypted field value"""
        encrypted_value = getattr(self, field_name, None)
        if not encrypted_value:
            return ""

        try:
            fernet = Fernet(ENCRYPTION_KEY.encode())
            return fernet.decrypt(encrypted_value.encode()).decode()
        except Exception:
            # Return empty string if decryption fails
            return ""

    def set_encrypted_field(self, field_name: str, value: str):
        """Set encrypted field value"""
        if not value:
            setattr(self, field_name, None)
            return

        try:
            fernet = Fernet(ENCRYPTION_KEY.encode())
            encrypted_value = fernet.encrypt(value.encode()).decode()
            setattr(self, field_name, encrypted_value)
        except Exception:
            # Set to None if encryption fails
            setattr(self, field_name, None)


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
    source_prices = relationship("SourcePrice", back_populates="product")
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


class SourcePrice(Base, TimestampMixin):
    """Source prices from retailers and affiliate platforms for arbitrage detection"""
    __tablename__ = "source_prices"
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
    product = relationship("Product", back_populates="source_prices")

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


# --- Selling & Order Management Models ---

class StockXListing(Base, TimestampMixin):
    """
    StockX listing management for automated selling
    Tracks listings created from QuickFlip opportunities
    """
    __tablename__ = "stockx_listings"
    __table_args__ = {"schema": "selling"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("products.id", "products")), nullable=False
    )
    stockx_listing_id = Column(String(100), unique=True, nullable=False, comment="StockX API listing ID")
    stockx_product_id = Column(String(100), nullable=False, comment="StockX product identifier")
    variant_id = Column(String(100), nullable=True, comment="Size/color variant ID")

    # Listing Details
    ask_price = Column(Numeric(10, 2), nullable=False, comment="Current asking price")
    original_ask_price = Column(Numeric(10, 2), nullable=True, comment="Initial asking price")
    buy_price = Column(Numeric(10, 2), nullable=True, comment="Original purchase price")
    expected_profit = Column(Numeric(10, 2), nullable=True, comment="Expected profit amount")
    expected_margin = Column(Numeric(5, 2), nullable=True, comment="Expected profit margin %")

    # Status Management
    status = Column(String(20), nullable=False, default="active",
                   comment="Listing status: active, inactive, sold, expired, cancelled")
    is_active = Column(Boolean, nullable=False, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Market Data
    current_lowest_ask = Column(Numeric(10, 2), nullable=True, comment="Current market lowest ask")
    current_highest_bid = Column(Numeric(10, 2), nullable=True, comment="Current market highest bid")
    last_price_update = Column(DateTime(timezone=True), nullable=True)

    # Source Tracking
    source_opportunity_id = Column(UUID(as_uuid=True), nullable=True, comment="Original QuickFlip opportunity")
    created_from = Column(String(50), nullable=True, default="manual", comment="Creation source: quickflip, manual, bulk")

    # Timeline
    listed_at = Column(DateTime(timezone=True), nullable=True, comment="When listed on StockX")
    delisted_at = Column(DateTime(timezone=True), nullable=True, comment="When removed from StockX")

    # Relationships
    product = relationship("Product", backref="stockx_listings")
    orders = relationship("StockXOrder", back_populates="listing", cascade="all, delete-orphan")
    pricing_history = relationship("PricingHistory", back_populates="listing", cascade="all, delete-orphan")

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "product_id": str(self.product_id),
            "stockx_listing_id": self.stockx_listing_id,
            "stockx_product_id": self.stockx_product_id,
            "variant_id": self.variant_id,
            "ask_price": float(self.ask_price) if self.ask_price else None,
            "original_ask_price": float(self.original_ask_price) if self.original_ask_price else None,
            "buy_price": float(self.buy_price) if self.buy_price else None,
            "expected_profit": float(self.expected_profit) if self.expected_profit else None,
            "expected_margin": float(self.expected_margin) if self.expected_margin else None,
            "status": self.status,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "current_lowest_ask": float(self.current_lowest_ask) if self.current_lowest_ask else None,
            "current_highest_bid": float(self.current_highest_bid) if self.current_highest_bid else None,
            "last_price_update": self.last_price_update.isoformat() if self.last_price_update else None,
            "source_opportunity_id": str(self.source_opportunity_id) if self.source_opportunity_id else None,
            "created_from": self.created_from,
            "listed_at": self.listed_at.isoformat() if self.listed_at else None,
            "delisted_at": self.delisted_at.isoformat() if self.delisted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class StockXOrder(Base, TimestampMixin):
    """
    StockX order/sale tracking for profit calculation
    Represents completed sales from listings
    """
    __tablename__ = "stockx_orders"
    __table_args__ = {"schema": "selling"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(
        UUID(as_uuid=True),
        ForeignKey(get_schema_ref("stockx_listings.id", "selling")),
        nullable=False
    )
    stockx_order_number = Column(String(100), unique=True, nullable=False, comment="StockX order number")

    # Sale Details
    sale_price = Column(Numeric(10, 2), nullable=False, comment="Final sale price")
    buyer_premium = Column(Numeric(10, 2), nullable=True, comment="StockX buyer premium")
    seller_fee = Column(Numeric(10, 2), nullable=True, comment="StockX seller fee")
    processing_fee = Column(Numeric(10, 2), nullable=True, comment="StockX processing fee")
    net_proceeds = Column(Numeric(10, 2), nullable=True, comment="Net amount received")

    # Profit Calculation
    original_buy_price = Column(Numeric(10, 2), nullable=True, comment="Original purchase price")
    gross_profit = Column(Numeric(10, 2), nullable=True, comment="Sale price - buy price")
    net_profit = Column(Numeric(10, 2), nullable=True, comment="Net proceeds - buy price")
    actual_margin = Column(Numeric(5, 2), nullable=True, comment="Actual profit margin %")
    roi = Column(Numeric(5, 2), nullable=True, comment="Return on investment %")

    # Status & Tracking
    order_status = Column(String(20), nullable=True, comment="Order status from StockX")
    shipping_status = Column(String(20), nullable=True, comment="Shipping status")
    tracking_number = Column(String(100), nullable=True, comment="Shipping tracking number")

    # Timeline
    sold_at = Column(DateTime(timezone=True), nullable=False, comment="When the sale occurred")
    shipped_at = Column(DateTime(timezone=True), nullable=True, comment="When item was shipped")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="When order was completed")

    # Relationships
    listing = relationship("StockXListing", back_populates="orders")

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "listing_id": str(self.listing_id),
            "stockx_order_number": self.stockx_order_number,
            "sale_price": float(self.sale_price) if self.sale_price else None,
            "buyer_premium": float(self.buyer_premium) if self.buyer_premium else None,
            "seller_fee": float(self.seller_fee) if self.seller_fee else None,
            "processing_fee": float(self.processing_fee) if self.processing_fee else None,
            "net_proceeds": float(self.net_proceeds) if self.net_proceeds else None,
            "original_buy_price": float(self.original_buy_price) if self.original_buy_price else None,
            "gross_profit": float(self.gross_profit) if self.gross_profit else None,
            "net_profit": float(self.net_profit) if self.net_profit else None,
            "actual_margin": float(self.actual_margin) if self.actual_margin else None,
            "roi": float(self.roi) if self.roi else None,
            "order_status": self.order_status,
            "shipping_status": self.shipping_status,
            "tracking_number": self.tracking_number,
            "sold_at": self.sold_at.isoformat() if self.sold_at else None,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PricingHistory(Base, TimestampMixin):
    """
    Track pricing changes for listings to analyze pricing strategy performance
    """
    __tablename__ = "pricing_history"
    __table_args__ = {"schema": "selling"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(
        UUID(as_uuid=True),
        ForeignKey(get_schema_ref("stockx_listings.id", "selling")),
        nullable=False
    )

    old_price = Column(Numeric(10, 2), nullable=True, comment="Previous price")
    new_price = Column(Numeric(10, 2), nullable=False, comment="New price")
    change_reason = Column(String(100), nullable=True, comment="Reason for price change")
    market_lowest_ask = Column(Numeric(10, 2), nullable=True, comment="Market lowest ask at time of change")
    market_highest_bid = Column(Numeric(10, 2), nullable=True, comment="Market highest bid at time of change")

    # Relationships
    listing = relationship("StockXListing", back_populates="pricing_history")

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "listing_id": str(self.listing_id),
            "old_price": float(self.old_price) if self.old_price else None,
            "new_price": float(self.new_price) if self.new_price else None,
            "change_reason": self.change_reason,
            "market_lowest_ask": float(self.market_lowest_ask) if self.market_lowest_ask else None,
            "market_highest_bid": float(self.market_highest_bid) if self.market_highest_bid else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Supplier Account Management Models
class SupplierAccount(Base, TimestampMixin, EncryptedFieldMixin):
    __tablename__ = "supplier_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("core.suppliers.id" if IS_POSTGRES else "suppliers.id"), nullable=False)

    # Account credentials
    email = Column(String(150), nullable=False)
    password_hash = Column(Text(), nullable=True)  # Encrypted password
    proxy_config = Column(Text(), nullable=True)  # Proxy configuration

    # Personal information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Address information
    address_line_1 = Column(String(200), nullable=True)
    address_line_2 = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    country_code = Column(String(5), nullable=True)
    zip_code = Column(String(20), nullable=True)
    state_code = Column(String(10), nullable=True)
    phone_number = Column(String(50), nullable=True)

    # Payment information (PCI-compliant tokenization)
    # REMOVED: Direct credit card storage violates PCI DSS
    # cc_number_encrypted = Column(Text(), nullable=True)  # SECURITY RISK - REMOVED
    # cvv_encrypted = Column(Text(), nullable=True)        # PCI VIOLATION - REMOVED

    # PCI-compliant payment method storage
    payment_provider = Column(String(50), nullable=True, comment="Payment provider: stripe, paypal, etc")
    payment_method_token = Column(String(255), nullable=True, comment="Tokenized payment method ID")
    payment_method_last4 = Column(String(4), nullable=True, comment="Last 4 digits for display only")
    payment_method_brand = Column(String(20), nullable=True, comment="Card brand: visa, mastercard, etc")
    expiry_month = Column(Integer(), nullable=True, comment="Expiry month for display/validation")
    expiry_year = Column(Integer(), nullable=True, comment="Expiry year for display/validation")

    # Account preferences
    browser_preference = Column(String(50), nullable=True)
    list_name = Column(String(100), nullable=True)

    # Account status and metadata
    account_status = Column(String(30), nullable=False, default="active")
    is_verified = Column(Boolean(), nullable=False, default=False)
    last_used_at = Column(DateTime(), nullable=True)

    # Statistics (computed fields)
    total_purchases = Column(Integer(), nullable=False, default=0)
    total_spent = Column(Numeric(12, 2), nullable=False, default=0.00)
    success_rate = Column(Numeric(5, 2), nullable=False, default=0.00)
    average_order_value = Column(Numeric(10, 2), nullable=False, default=0.00)

    # Additional notes
    notes = Column(Text(), nullable=True)

    # Relationships
    supplier = relationship("Supplier", back_populates="accounts")
    purchase_history = relationship("AccountPurchaseHistory", back_populates="account", cascade="all, delete-orphan")

    # Combined table args: schema and constraints
    __table_args__ = (
        UniqueConstraint('supplier_id', 'email', name='uq_supplier_account_email'),
        {"schema": "core"} if IS_POSTGRES else {}
    )

    def get_encrypted_password(self) -> str:
        """Get encrypted password"""
        return self.get_encrypted_field('password_hash')

    def set_encrypted_password(self, password: str):
        """Set encrypted password"""
        self.set_encrypted_field('password_hash', password)

    # REMOVED: Credit card encryption methods - PCI compliance violation
    # def get_encrypted_cc_number(self) -> str:
    # def set_encrypted_cc_number(self, cc_number: str):
    # def get_encrypted_cvv(self) -> str:
    # def set_encrypted_cvv(self, cvv: str):

    def set_payment_method(self, provider: str, token: str, last4: str = None, brand: str = None):
        """Set PCI-compliant payment method using tokenization"""
        self.payment_provider = provider
        self.payment_method_token = token
        self.payment_method_last4 = last4
        self.payment_method_brand = brand

    def get_payment_display_info(self) -> dict:
        """Get safe payment info for display (no sensitive data)"""
        return {
            "provider": self.payment_provider,
            "last4": self.payment_method_last4,
            "brand": self.payment_method_brand,
            "expiry_month": self.expiry_month,
            "expiry_year": self.expiry_year,
            "has_payment_method": bool(self.payment_method_token)
        }

    def to_dict(self, include_sensitive: bool = False):
        """Convert to dictionary for API responses"""
        data = {
            "id": str(self.id),
            "supplier_id": str(self.supplier_id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "address_line_1": self.address_line_1,
            "address_line_2": self.address_line_2,
            "city": self.city,
            "country_code": self.country_code,
            "zip_code": self.zip_code,
            "state_code": self.state_code,
            "phone_number": self.phone_number,
            "browser_preference": self.browser_preference,
            "list_name": self.list_name,
            "account_status": self.account_status,
            "is_verified": self.is_verified,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "total_purchases": self.total_purchases,
            "total_spent": float(self.total_spent),
            "success_rate": float(self.success_rate),
            "average_order_value": float(self.average_order_value),
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_sensitive:
            data.update({
                "proxy_config": self.proxy_config,
                "payment_provider": self.payment_provider,
                "payment_method_last4": self.payment_method_last4,
                "payment_method_brand": self.payment_method_brand,
                # Note: payment_method_token is never exposed - it's a secure token
            })

        return data


class AccountPurchaseHistory(Base, TimestampMixin):
    __tablename__ = "account_purchase_history"
    __table_args__ = {"schema": "core"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("core.supplier_accounts.id" if IS_POSTGRES else "supplier_accounts.id"), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("core.suppliers.id" if IS_POSTGRES else "suppliers.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.products.id" if IS_POSTGRES else "products.id"), nullable=True)

    # Purchase details
    order_reference = Column(String(100), nullable=True)
    purchase_amount = Column(Numeric(12, 2), nullable=False)
    purchase_date = Column(DateTime(), nullable=False)
    purchase_status = Column(String(30), nullable=False)  # 'pending', 'completed', 'failed', 'cancelled'
    success = Column(Boolean(), nullable=False, default=False)
    failure_reason = Column(Text(), nullable=True)

    # Performance metrics
    response_time_ms = Column(Integer(), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Relationships
    account = relationship("SupplierAccount", back_populates="purchase_history")
    supplier = relationship("Supplier")
    product = relationship("Product")

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "account_id": str(self.account_id),
            "supplier_id": str(self.supplier_id),
            "product_id": str(self.product_id) if self.product_id else None,
            "order_reference": self.order_reference,
            "purchase_amount": float(self.purchase_amount),
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "purchase_status": self.purchase_status,
            "success": self.success,
            "failure_reason": self.failure_reason,
            "response_time_ms": self.response_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Update Supplier model to include accounts relationship
Supplier.accounts = relationship("SupplierAccount", back_populates="supplier", cascade="all, delete-orphan")


# Import pricing models to register them with SQLAlchemy
# This ensures the relationships defined above are properly linked
from domains.pricing.models import *  # noqa: F401,F403
