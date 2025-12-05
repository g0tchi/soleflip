"""
SQLAlchemy Models for SoleFlipper
Clean, maintainable model definitions with proper relationships
"""

import os
import uuid

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Load environment variables from .env file
load_dotenv()

# Import the schema helper
from shared.database.utils import IS_POSTGRES, get_schema_ref  # noqa: E402

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
from sqlalchemy.ext.compiler import compiles  # noqa: E402


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
    __tablename__ = "brand"
    __table_args__ = {"schema": "catalog"} if IS_POSTGRES else None

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
        {"schema": "catalog"} if IS_POSTGRES else {},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("brand.id", "catalog")), nullable=False
    )
    pattern_type = Column(String(50), nullable=False, default="regex")
    pattern = Column(String(255), nullable=False, unique=True)

    brand = relationship("Brand", back_populates="patterns")


class Category(Base, TimestampMixin):
    __tablename__ = "category"
    __table_args__ = {"schema": "catalog"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("category.id", "catalog")))
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
    __table_args__ = {"schema": "catalog"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("category.id", "catalog")))
    value = Column(String(20), nullable=False)
    standardized_value = Column(Numeric(4, 1))
    region = Column(String(10), nullable=False)
    category = relationship("Category")
    inventory_items = relationship("InventoryItem", back_populates="size")


class Supplier(Base, TimestampMixin):
    __tablename__ = "profile"
    __table_args__ = {"schema": "supplier"} if IS_POSTGRES else None

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

    # Supplier Intelligence Fields (from Notion Analysis)
    supplier_category = Column(String(50), nullable=True)
    vat_rate = Column(Numeric(4, 2), nullable=True)
    return_policy = Column(Text, nullable=True)
    default_email = Column(String(255), nullable=True)

    inventory_items = relationship("InventoryItem", back_populates="supplier_obj")
    performance_records = relationship("SupplierPerformance", back_populates="supplier")


class Platform(Base, TimestampMixin):
    __tablename__ = "marketplace"
    __table_args__ = {"schema": "platform"} if IS_POSTGRES else None

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
    marketplace_data = relationship("MarketplaceData", back_populates="platform")


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
    __tablename__ = "product"
    __table_args__ = (
        # Performance indexes for enrichment queries
        Index("idx_product_description_null", "id", postgresql_where=text("description IS NULL")),
        Index("idx_product_retail_price_null", "id", postgresql_where=text("retail_price IS NULL")),
        Index("idx_product_release_date_null", "id", postgresql_where=text("release_date IS NULL")),
        Index(
            "idx_product_enrichment_status",
            "id",
            "description",
            "retail_price",
            "release_date",
            postgresql_where=text(
                "description IS NULL OR retail_price IS NULL OR release_date IS NULL"
            ),
        ),
        {"schema": "catalog"} if IS_POSTGRES else {},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String(100), nullable=False, unique=True)
    ean = Column(
        String(13), nullable=True, index=True, comment="EAN/GTIN product identifier (size-independent)"
    )
    brand_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("brand.id", "catalog")), nullable=True
    )
    category_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("category.id", "catalog")), nullable=False
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)
    retail_price = Column(Numeric(10, 2))
    avg_resale_price = Column(Numeric(10, 2))
    release_date = Column(DateTime(timezone=True))

    # StockX Enrichment Fields (Gibson AI Hybrid Schema)
    stockx_product_id = Column(
        String(255), nullable=True, unique=True, index=True, comment="StockX product UUID"
    )
    # Note: style_code removed - was always identical to sku (4x redundancy)
    enrichment_data = Column(JSONB, nullable=True, comment="Complete StockX product data")
    lowest_ask = Column(Numeric(10, 2), nullable=True, comment="Current lowest ask price")
    highest_bid = Column(Numeric(10, 2), nullable=True, comment="Current highest bid price")
    recommended_sell_faster = Column(
        Numeric(10, 2), nullable=True, comment="Recommended price for faster sale"
    )
    recommended_earn_more = Column(
        Numeric(10, 2), nullable=True, comment="Recommended price for maximum earnings"
    )
    last_enriched_at = Column(
        DateTime(timezone=True), nullable=True, comment="Last enrichment timestamp"
    )
    enrichment_version = Column(
        Integer, nullable=True, server_default="1", comment="StockX API version used for enrichment"
    )
    brand = relationship("Brand", back_populates="products")
    category = relationship("Category", back_populates="products")
    inventory_items = relationship("InventoryItem", back_populates="product")
    # Pricing relationships
    price_history = relationship("PriceHistory", back_populates="product")
    source_prices = relationship("SourcePrice", back_populates="product")
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
    __tablename__ = "stock"
    __table_args__ = {"schema": "inventory"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("product.id", "catalog")), nullable=False
    )
    size_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("sizes.id", "catalog")), nullable=False
    )
    ean = Column(
        String(13), nullable=True, index=True, comment="Size-specific EAN/GTIN identifier"
    )
    supplier_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("profile.id", "supplier")), nullable=True
    )
    quantity = Column(Integer, nullable=False, default=1)
    purchase_price = Column(Numeric(10, 2))  # Net purchase price (without VAT)
    purchase_date = Column(DateTime(timezone=True))
    supplier = Column(String(100))
    status = Column(String(50), nullable=False, default="in_stock")
    notes = Column(Text)
    external_ids = Column(JSONB, nullable=True, default=dict)

    # Notion Sync Fields (added 2025-09-30)
    delivery_date = Column(DateTime(timezone=True), nullable=True)
    gross_purchase_price = Column(Numeric(10, 2), nullable=True)  # Purchase price WITH VAT
    vat_amount = Column(Numeric(10, 2), nullable=True)
    vat_rate = Column(Numeric(5, 2), nullable=True, default=19.00)  # Default Germany VAT rate

    # Business Intelligence Fields (from Notion Analysis)
    shelf_life_days = Column(Integer, nullable=True)
    profit_per_shelf_day = Column(Numeric(10, 2), nullable=True)
    roi_percentage = Column(Numeric(5, 2), nullable=True)
    # sale_overview = Column(Text, nullable=True)  # REMOVED: Column doesn't exist in DB

    # Multi-Platform Operations Fields
    location = Column(String(50), nullable=True)
    listed_stockx = Column(Boolean, nullable=True, default=False)
    listed_alias = Column(Boolean, nullable=True, default=False)
    listed_local = Column(Boolean, nullable=True, default=False)

    # Advanced Status Tracking
    detailed_status = Column(
        Enum(
            "incoming",
            "available",
            "consigned",
            "need_shipping",
            "packed",
            "outgoing",
            "sale_completed",
            "cancelled",
            name="inventory_status",
        ),
        nullable=True,
    )

    # Phase 2: Schema Consolidation Fields (2025-11-29)
    listed_on_platforms = Column(
        JSONB, nullable=True, comment="Platform listing history (StockX, eBay, etc.)"
    )
    status_history = Column(
        JSONB, nullable=True, comment="Historical status changes with timestamps"
    )
    reserved_quantity = Column(
        Integer, nullable=False, default=0, comment="Currently reserved units"
    )

    product = relationship("Product", back_populates="inventory_items")
    size = relationship("Size", back_populates="inventory_items")
    supplier_obj = relationship("Supplier", back_populates="inventory_items")
    transactions = relationship("Transaction", back_populates="inventory_item")
    price_history = relationship("PriceHistory", back_populates="inventory_item")
    marketplace_data = relationship("MarketplaceData", back_populates="inventory_item")

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
            "reserved_quantity": self.reserved_quantity,
            "available_quantity": self.available_quantity,
            "listed_on_platforms": self.listed_on_platforms,
            "status_history": self.status_history,
        }

    @property
    def available_quantity(self) -> int:
        """Calculate available quantity (total - reserved)."""
        return max(0, self.quantity - (self.reserved_quantity or 0))

    def add_platform_listing(
        self,
        platform: str,
        listing_id: str,
        ask_price: float = None,
        metadata: dict = None,
    ):
        """Track platform listing."""
        from datetime import datetime, timezone

        if not self.listed_on_platforms:
            self.listed_on_platforms = []

        listing_entry = {
            "platform": platform,
            "listing_id": listing_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }

        # Add optional fields
        if ask_price is not None:
            listing_entry["ask_price"] = ask_price
        if metadata:
            listing_entry["metadata"] = metadata

        self.listed_on_platforms.append(listing_entry)

    def add_status_change(self, old_status: str, new_status: str, reason: str = None):
        """Track status change."""
        from datetime import datetime, timezone

        if not self.status_history:
            self.status_history = []

        self.status_history.append(
            {
                "from_status": old_status,
                "to_status": new_status,
                "changed_at": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
            }
        )


class StockMetricsView(Base):
    """
    Read-only materialized view for stock metrics.
    Refreshed hourly via inventory.refresh_stock_metrics()
    """

    __tablename__ = "stock_metrics_view"
    __table_args__ = {"schema": "inventory"} if IS_POSTGRES else None

    stock_id = Column(UUID(as_uuid=True), primary_key=True)
    total_quantity = Column(Integer, nullable=False)
    available_quantity = Column(Integer, nullable=False)
    reserved_quantity = Column(Integer, nullable=False, default=0)
    total_cost = Column(Numeric(10, 2))
    expected_profit = Column(Numeric(10, 2))
    last_calculated_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    def to_dict(self):
        return {
            "stock_id": str(self.stock_id),
            "total_quantity": self.total_quantity,
            "available_quantity": self.available_quantity,
            "reserved_quantity": self.reserved_quantity,
            "total_cost": float(self.total_cost) if self.total_cost else None,
            "expected_profit": float(self.expected_profit) if self.expected_profit else None,
            "last_calculated_at": self.last_calculated_at.isoformat(),
        }


# =====================================================
# Sales Domain Models
# =====================================================


class Transaction(Base, TimestampMixin):
    __tablename__ = "transaction"
    __table_args__ = {"schema": "financial"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("stock.id", "inventory")), nullable=False
    )
    platform_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("marketplace.id", "platform")), nullable=False
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
    __tablename__ = "listing"
    __table_args__ = {"schema": "sales"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_item_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("stock.id", "inventory")), nullable=False
    )

    stockx_listing_id = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(String(50), nullable=False, index=True)
    amount = Column(Numeric(10, 2))
    currency_code = Column(String(10))
    inventory_type = Column(String(50))
    expires_at = Column(DateTime(timezone=True))
    stockx_created_at = Column(DateTime(timezone=True))
    last_stockx_updated_at = Column(DateTime(timezone=True))

    # Unified multi-platform pattern (v2.3.3)
    platform_specific_data = Column(
        JSONB, comment="Platform-specific fields (StockX, eBay, GOAT, Alias)"
    )
    raw_data = Column(JSONB)

    # Relationships
    inventory_item = relationship("InventoryItem")
    pricing_history = relationship("PricingHistory", back_populates="listing")


class Order(Base, TimestampMixin):
    __tablename__ = "order"
    __table_args__ = {"schema": "sales"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_item_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("stock.id", "inventory")), nullable=False
    )
    listing_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("listing.id", "sales")), nullable=True
    )

    # Multi-platform support (Gibson v2.4)
    platform_id = Column(
        UUID(as_uuid=True),
        ForeignKey(get_schema_ref("marketplace.id", "platform")),
        nullable=False,
        index=True,
        comment="Platform (StockX, eBay, GOAT, Alias)",
    )
    external_id = Column(
        String(200), nullable=True, index=True, comment="Platform-specific order ID"
    )

    stockx_order_number = Column(
        String(100), nullable=True, unique=True, index=True
    )  # Now nullable
    status = Column(String(50), nullable=False, index=True)
    amount = Column(Numeric(10, 2))
    currency_code = Column(String(10))
    inventory_type = Column(String(50))

    # Multi-platform fields (added in Gibson migration)
    platform_fee = Column(Numeric(10, 2), nullable=True, comment="Platform transaction fee")
    shipping_cost = Column(Numeric(10, 2), nullable=True, comment="Shipping cost")
    buyer_destination_country = Column(String(100), nullable=True)
    buyer_destination_city = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)

    shipping_label_url = Column(String(512))
    shipping_document_path = Column(String(512))  # For locally stored PDFs

    stockx_created_at = Column(DateTime(timezone=True))
    last_stockx_updated_at = Column(DateTime(timezone=True))

    # Notion Sync Fields (added 2025-09-30)
    sold_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Sale completion date
    gross_sale = Column(Numeric(10, 2), nullable=True)  # Sale price before fees/taxes
    net_proceeds = Column(Numeric(10, 2), nullable=True)  # Net proceeds after platform fees
    gross_profit = Column(Numeric(10, 2), nullable=True)  # Sale price - Purchase price
    net_profit = Column(Numeric(10, 2), nullable=True)  # Net profit after all costs
    roi = Column(Numeric(5, 2), nullable=True)  # Return on investment percentage
    payout_received = Column(
        Boolean, nullable=True, default=False, index=True
    )  # Whether payout received
    payout_date = Column(DateTime(timezone=True), nullable=True)  # Date payout received
    shelf_life_days = Column(Integer, nullable=True)  # Days between purchase and sale

    # Unified multi-platform pattern (v2.3.3)
    platform_specific_data = Column(
        JSONB, comment="Platform-specific fields (StockX, eBay, GOAT, Alias)"
    )
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
    __table_args__ = {"schema": "logging"} if IS_POSTGRES else None

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
        UUID(as_uuid=True), ForeignKey(get_schema_ref("product.id", "catalog")), nullable=False
    )
    source = Column(
        String(100), nullable=False, comment="Data source: awin, webgains, scraping, etc."
    )
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
# NOTE: StockXListing and StockXOrder were removed in v2.3.3
# Replaced by unified multi-platform pattern in sales.listing and sales.order
# with platform_specific_data JSONB column for unlimited marketplace support


class PricingHistory(Base, TimestampMixin):
    """
    Track pricing changes for listings to analyze pricing strategy performance
    """

    __tablename__ = "pricing_history"
    __table_args__ = {"schema": "sales"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("listing.id", "sales")), nullable=False
    )

    old_price = Column(Numeric(10, 2), nullable=True, comment="Previous price")
    new_price = Column(Numeric(10, 2), nullable=False, comment="New price")
    change_reason = Column(String(100), nullable=True, comment="Reason for price change")
    market_lowest_ask = Column(
        Numeric(10, 2), nullable=True, comment="Market lowest ask at time of change"
    )
    market_highest_bid = Column(
        Numeric(10, 2), nullable=True, comment="Market highest bid at time of change"
    )

    # Relationships
    listing = relationship("Listing", back_populates="pricing_history")

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "listing_id": str(self.listing_id),
            "old_price": float(self.old_price) if self.old_price else None,
            "new_price": float(self.new_price) if self.new_price else None,
            "change_reason": self.change_reason,
            "market_lowest_ask": float(self.market_lowest_ask) if self.market_lowest_ask else None,
            "market_highest_bid": (
                float(self.market_highest_bid) if self.market_highest_bid else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Supplier Account Management Models
class SupplierAccount(Base, TimestampMixin, EncryptedFieldMixin):
    __tablename__ = "account"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(
        UUID(as_uuid=True),
        ForeignKey("supplier.profile.id" if IS_POSTGRES else "profile.id"),
        nullable=False,
    )

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
    payment_provider = Column(
        String(50), nullable=True, comment="Payment provider: stripe, paypal, etc"
    )
    payment_method_token = Column(String(255), nullable=True, comment="Tokenized payment method ID")
    payment_method_last4 = Column(
        String(4), nullable=True, comment="Last 4 digits for display only"
    )
    payment_method_brand = Column(
        String(20), nullable=True, comment="Card brand: visa, mastercard, etc"
    )
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
    purchase_history = relationship(
        "AccountPurchaseHistory", back_populates="account", cascade="all, delete-orphan"
    )

    # Combined table args: schema and constraints
    __table_args__ = (
        UniqueConstraint("supplier_id", "email", name="uq_supplier_account_email"),
        {"schema": "supplier"} if IS_POSTGRES else {},
    )

    def get_encrypted_password(self) -> str:
        """Get encrypted password"""
        return self.get_encrypted_field("password_hash")

    def set_encrypted_password(self, password: str):
        """Set encrypted password"""
        self.set_encrypted_field("password_hash", password)

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
            "has_payment_method": bool(self.payment_method_token),
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
            data.update(
                {
                    "proxy_config": self.proxy_config,
                    "payment_provider": self.payment_provider,
                    "payment_method_last4": self.payment_method_last4,
                    "payment_method_brand": self.payment_method_brand,
                    # Note: payment_method_token is never exposed - it's a secure token
                }
            )

        return data


class AccountPurchaseHistory(Base, TimestampMixin):
    __tablename__ = "purchase_history"
    __table_args__ = {"schema": "supplier"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("supplier.account.id" if IS_POSTGRES else "account.id"),
        nullable=False,
    )
    supplier_id = Column(
        UUID(as_uuid=True),
        ForeignKey("supplier.profile.id" if IS_POSTGRES else "profile.id"),
        nullable=False,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalog.product.id" if IS_POSTGRES else "product.id"),
        nullable=True,
    )

    # Purchase details
    order_reference = Column(String(100), nullable=True)
    purchase_amount = Column(Numeric(12, 2), nullable=False)
    purchase_date = Column(DateTime(), nullable=False)
    purchase_status = Column(
        String(30), nullable=False
    )  # 'pending', 'completed', 'failed', 'cancelled'
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


class SupplierPerformance(Base):
    """Monthly supplier performance metrics from Notion intelligence system"""

    __tablename__ = "supplier_performance"
    __table_args__ = {"schema": "core"} if IS_POSTGRES else None

    id = Column(Integer, primary_key=True)
    supplier_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("profile.id", "supplier")), nullable=False
    )
    month_year = Column(DateTime(timezone=True), nullable=False)
    total_orders = Column(Integer, nullable=True, default=0)
    avg_delivery_time = Column(Numeric(4, 1), nullable=True)
    return_rate = Column(Numeric(5, 2), nullable=True)
    avg_roi = Column(Numeric(5, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    supplier = relationship("Supplier", back_populates="performance_records")

    def to_dict(self):
        return {
            "id": self.id,
            "supplier_id": str(self.supplier_id),
            "month_year": self.month_year.isoformat() if self.month_year else None,
            "total_orders": self.total_orders,
            "avg_delivery_time": float(self.avg_delivery_time) if self.avg_delivery_time else None,
            "return_rate": float(self.return_rate) if self.return_rate else None,
            "avg_roi": float(self.avg_roi) if self.avg_roi else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Update Supplier model to include accounts relationship
Supplier.accounts = relationship(
    "SupplierAccount", back_populates="supplier", cascade="all, delete-orphan"
)


class MarketplaceData(Base, TimestampMixin):
    """Market data from multiple platforms (StockX, Alias, GOAT, etc.) for pricing intelligence"""

    __tablename__ = "marketplace_data"
    __table_args__ = {"schema": "analytics"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_item_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("stock.id", "inventory")), nullable=False
    )
    platform_id = Column(
        UUID(as_uuid=True), ForeignKey(get_schema_ref("marketplace.id", "platform")), nullable=False
    )
    marketplace_listing_id = Column(String(255), comment="External listing identifier")

    # Universal pricing fields
    ask_price = Column(Numeric(10, 2), comment="Current ask price")
    bid_price = Column(Numeric(10, 2), comment="Current bid price")
    market_lowest_ask = Column(Numeric(10, 2), comment="Lowest ask on the market")
    market_highest_bid = Column(Numeric(10, 2), comment="Highest bid on the market")
    last_sale_price = Column(Numeric(10, 2), comment="Most recent sale price")

    # Market analytics
    sales_frequency = Column(Integer, comment="Number of sales in last 30 days")
    volatility = Column(Numeric(5, 4), comment="Price volatility (0.0-1.0)")
    fees_percentage = Column(Numeric(5, 4), comment="Platform fees (0.08 = 8%)")

    # Platform-specific data (JSON for flexibility)
    platform_specific = Column(JSONB if IS_POSTGRES else Text, comment="Platform-specific metadata")

    # Metadata
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    inventory_item = relationship("InventoryItem", back_populates="marketplace_data")
    platform = relationship("Platform", back_populates="marketplace_data")

    # Constraints
    if IS_POSTGRES:
        __table_args__ = (
            UniqueConstraint(
                "inventory_item_id", "platform_id", name="uq_marketplace_data_item_platform"
            ),
            CheckConstraint("volatility >= 0 AND volatility <= 1", name="chk_volatility_range"),
            CheckConstraint("fees_percentage >= 0 AND fees_percentage <= 1", name="chk_fees_range"),
            {"schema": "analytics"},
        )
    else:
        __table_args__ = (
            UniqueConstraint(
                "inventory_item_id", "platform_id", name="uq_marketplace_data_item_platform"
            ),
        )

    def to_dict(self):
        return {
            "id": str(self.id),
            "inventory_item_id": str(self.inventory_item_id),
            "platform_id": str(self.platform_id),
            "marketplace_listing_id": self.marketplace_listing_id,
            "ask_price": float(self.ask_price) if self.ask_price else None,
            "bid_price": float(self.bid_price) if self.bid_price else None,
            "market_lowest_ask": float(self.market_lowest_ask) if self.market_lowest_ask else None,
            "market_highest_bid": (
                float(self.market_highest_bid) if self.market_highest_bid else None
            ),
            "last_sale_price": float(self.last_sale_price) if self.last_sale_price else None,
            "sales_frequency": self.sales_frequency,
            "volatility": float(self.volatility) if self.volatility else None,
            "fees_percentage": float(self.fees_percentage) if self.fees_percentage else None,
            "platform_specific": self.platform_specific,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Import pricing models to register them with SQLAlchemy
# This ensures the relationships defined above are properly linked
from domains.pricing.models import *  # noqa: F401,F403,E402
