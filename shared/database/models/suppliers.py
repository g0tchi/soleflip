"""
Supplier domain models
Supplier profiles, accounts, and performance tracking
"""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from shared.database.models.base import Base, EncryptedFieldMixin, TimestampMixin
from shared.database.utils import IS_POSTGRES, get_schema_ref


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
    accounts = relationship("SupplierAccount", back_populates="supplier", cascade="all, delete-orphan")


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
