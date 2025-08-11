"""
SQLAlchemy Models for SoleFlipper
Clean, maintainable model definitions with proper relationships
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, Numeric, Boolean, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from cryptography.fernet import Fernet
import os

Base = declarative_base()

# --- Encryption Setup ---
# In a real production environment, this key MUST be set as a persistent environment variable.
# For development, we generate a temporary key if it's not found.
# NOTE: If this key is lost, all encrypted data will be unrecoverable.
ENCRYPTION_KEY = os.getenv("FIELD_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    print("WARNING: FIELD_ENCRYPTION_KEY not set. Generating ephemeral key for this session.")
    ENCRYPTION_KEY = Fernet.generate_key().decode()

try:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
except Exception as e:
    raise ValueError(f"Invalid FIELD_ENCRYPTION_KEY: {e}")
# -------------------------

# --- Dialect-specific Type Compilation ---
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import JSON

@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(element, compiler, **kw):
    """
    Tells SQLAlchemy to treat JSONB as JSON for SQLite,
    which has good JSON support. This is for migration generation.
    """
    return compiler.visit_json(element, **kw)

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

# =====================================================
# Core Domain Models
# =====================================================

class Brand(Base, TimestampMixin):
    """Brand entity - Nike, Adidas, etc."""
    __tablename__ = "brands"
    __table_args__ = {'schema': 'core'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    
    # Relationships
    products = relationship("Product", back_populates="brand")

class Category(Base, TimestampMixin):
    """Product categories with hierarchy support"""
    __tablename__ = "categories"
    __table_args__ = {'schema': 'core'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("core.categories.id"))
    path = Column(String(500))  # Hierarchical path for queries
    
    # Self-referential relationship
    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent", overlaps="parent")
    
    # Relationships
    products = relationship("Product", back_populates="category")

class Size(Base, TimestampMixin):
    """Size management with regional standardization"""
    __tablename__ = "sizes"
    __table_args__ = {'schema': 'core'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("core.categories.id"))
    value = Column(String(20), nullable=False)
    standardized_value = Column(Numeric(4, 1))
    region = Column(String(10), nullable=False)  # EU, US, UK
    
    # Relationships
    category = relationship("Category")
    inventory_items = relationship("InventoryItem", back_populates="size")

class Supplier(Base, TimestampMixin):
    """Suppliers with comprehensive business information"""
    __tablename__ = "suppliers"
    __table_args__ = {'schema': 'core'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic Information
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(150))
    
    # Business Classification
    supplier_type = Column(String(50), nullable=False)  # 'brand_official', 'authorized_retailer', 'reseller', etc.
    business_size = Column(String(30))  # 'enterprise', 'small_business', 'individual'
    
    # Contact Information
    contact_person = Column(String(100))
    email = Column(String(100))
    phone = Column(String(50))
    website = Column(String(200))
    
    # Address Information
    address_line1 = Column(String(200))
    address_line2 = Column(String(200))
    city = Column(String(100))
    state_province = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(50), default="Germany")
    
    # Business Details
    tax_id = Column(String(50))
    vat_number = Column(String(50))
    business_registration = Column(String(100))
    
    # Return Policy & Terms
    return_policy_days = Column(Integer)
    return_policy_text = Column(Text)
    return_conditions = Column(String(500))
    accepts_exchanges = Column(Boolean, default=True)
    restocking_fee_percent = Column(Numeric(5, 2))
    
    # Payment & Trading Terms
    payment_terms = Column(String(100))
    credit_limit = Column(Numeric(12, 2))
    discount_percent = Column(Numeric(5, 2))
    minimum_order_amount = Column(Numeric(10, 2))
    
    # Performance & Status
    rating = Column(Numeric(3, 2))  # 1.00 to 5.00
    reliability_score = Column(Integer)  # 1 to 10
    quality_score = Column(Integer)  # 1 to 10
    status = Column(String(20), nullable=False, default="active")
    preferred = Column(Boolean, default=False)
    verified = Column(Boolean, default=False)
    
    # Operational Information
    average_processing_days = Column(Integer)
    ships_internationally = Column(Boolean, default=False)
    accepts_returns_by_mail = Column(Boolean, default=True)
    provides_authenticity_guarantee = Column(Boolean, default=False)
    
    # Integration & Technical
    has_api = Column(Boolean, default=False)
    api_endpoint = Column(String(200))
    api_key_encrypted = Column(Text)
    
    # Financial Tracking
    total_orders_count = Column(Integer, default=0)
    total_order_value = Column(Numeric(12, 2), default=0.00)
    average_order_value = Column(Numeric(10, 2))
    last_order_date = Column(DateTime(timezone=True))
    
    # Metadata
    notes = Column(Text)
    internal_notes = Column(Text)
    tags = Column(JSONB)
    
    # Relationships
    inventory_items = relationship("InventoryItem", back_populates="supplier_obj")


class Platform(Base, TimestampMixin):
    """Sales platforms - StockX, Alias, GOAT, etc. (Master Data)"""
    __tablename__ = "platforms"
    __table_args__ = {'schema': 'core'}  # ✅ MOVED TO CORE
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    fee_percentage = Column(Numeric(5, 2))  # Default fee percentage
    supports_fees = Column(Boolean, default=True)  # Whether platform has explicit fees
    active = Column(Boolean, default=True)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="platform")


class SystemConfig(Base, TimestampMixin):
    """Stores system-wide configuration and secrets, encrypted."""
    __tablename__ = "system_config"
    __table_args__ = {'schema': 'core'}

    key = Column(String(100), primary_key=True)
    value_encrypted = Column(Text, nullable=False)
    description = Column(Text)

    def set_value(self, value: str):
        """Encrypts and sets the value."""
        if not isinstance(value, str):
            raise TypeError("Value must be a string")
        self.value_encrypted = cipher_suite.encrypt(value.encode()).decode()

    def get_value(self) -> str:
        """Decrypts and returns the value."""
        if not self.value_encrypted:
            return ""
        decrypted_bytes = cipher_suite.decrypt(self.value_encrypted.encode())
        return decrypted_bytes.decode()

    @staticmethod
    def get_encryption_key_for_setup() -> str:
        """
        Helper method for setup/admin purposes to show the key
        that needs to be set in the environment.
        """
        return ENCRYPTION_KEY


# =====================================================
# Product Domain Models
# =====================================================

class Product(Base, TimestampMixin):
    """Main product entity"""
    __tablename__ = "products"
    __table_args__ = {'schema': 'products'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String(100), nullable=False, unique=True)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("core.brands.id"), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("core.categories.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    retail_price = Column(Numeric(10, 2))  # Official manufacturer retail price (UVP)
    avg_resale_price = Column(Numeric(10, 2))  # Average resale price from StockX/GOAT etc.
    release_date = Column(DateTime(timezone=True))
    
    # Relationships
    brand = relationship("Brand", back_populates="products")
    category = relationship("Category", back_populates="products")
    inventory_items = relationship("InventoryItem", back_populates="product")

class InventoryItem(Base, TimestampMixin):
    """Individual inventory items with status tracking"""
    __tablename__ = "inventory"
    __table_args__ = {'schema': 'products'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.products.id"), nullable=False)
    size_id = Column(UUID(as_uuid=True), ForeignKey("core.sizes.id"), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("core.suppliers.id"), nullable=True)  # New normalized supplier
    quantity = Column(Integer, nullable=False, default=1)
    purchase_price = Column(Numeric(10, 2))
    purchase_date = Column(DateTime(timezone=True))
    supplier = Column(String(100))  # Keep for migration compatibility, will be deprecated
    status = Column(String(50), nullable=False, default="in_stock")
    notes = Column(Text)
    
    # Relationships
    product = relationship("Product", back_populates="inventory_items")
    size = relationship("Size", back_populates="inventory_items")
    supplier_obj = relationship("Supplier", back_populates="inventory_items")  # New relationship
    transactions = relationship("Transaction", back_populates="inventory_item")

# =====================================================
# Sales Domain Models
# =====================================================

class Transaction(Base, TimestampMixin):
    """Sales transactions with detailed financial tracking"""
    __tablename__ = "transactions"
    __table_args__ = {'schema': 'sales'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id = Column(UUID(as_uuid=True), ForeignKey("products.inventory.id"), nullable=False)
    platform_id = Column(UUID(as_uuid=True), ForeignKey("core.platforms.id"), nullable=False)  # ✅ UPDATED REFERENCE
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    sale_price = Column(Numeric(10, 2), nullable=False)
    platform_fee = Column(Numeric(10, 2), nullable=False)
    shipping_cost = Column(Numeric(10, 2), nullable=False, default=0)
    net_profit = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    external_id = Column(String(100))  # Platform-specific ID
    buyer_destination_country = Column(String(100))  # Country where item was shipped
    buyer_destination_city = Column(String(100))  # City where item was shipped
    notes = Column(Text)
    
    # Relationships
    inventory_item = relationship("InventoryItem", back_populates="transactions")
    platform = relationship("Platform", back_populates="transactions")

# =====================================================
# Integration Domain Models
# =====================================================

class ImportBatch(Base, TimestampMixin):
    """Batch tracking for data imports"""
    __tablename__ = "import_batches"
    __table_args__ = {'schema': 'integration'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String(50), nullable=False)  # stockx, notion, manual
    source_file = Column(String(255))
    total_records = Column(Integer, default=0)
    processed_records = Column(Integer, default=0)
    error_records = Column(Integer, default=0)
    status = Column(String(50), default="pending")
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    import_records = relationship("ImportRecord", back_populates="batch")

class ImportRecord(Base, TimestampMixin):
    """Individual import records with validation"""
    __tablename__ = "import_records"
    __table_args__ = {'schema': 'integration'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("integration.import_batches.id"), nullable=False)
    source_data = Column(JSONB, nullable=False)
    processed_data = Column(JSONB)
    validation_errors = Column(JSONB)
    status = Column(String(50), default="pending")
    processing_started_at = Column(DateTime(timezone=True))
    processing_completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    
    # Relationships
    batch = relationship("ImportBatch", back_populates="import_records")

# =====================================================
# Logging Domain Models
# =====================================================

class SystemLog(Base):
    """Structured system logging"""
    __tablename__ = "system_logs"
    __table_args__ = {'schema': 'logging'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    component = Column(String(50), nullable=False)  # IMPORT, PROCESSING, ANALYTICS, etc.
    message = Column(Text, nullable=False)
    details = Column(JSONB)
    source_table = Column(String(100))
    source_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)