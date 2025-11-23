"""
System domain models
Platform configuration, logging, and event store
"""

import os
import uuid

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from shared.database.models.base import Base, TimestampMixin
from shared.database.utils import IS_POSTGRES

# Load environment variables for encryption
load_dotenv()

# Encryption setup for SystemConfig
ENCRYPTION_KEY = os.getenv("FIELD_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError(
        "FATAL: The 'FIELD_ENCRYPTION_KEY' environment variable is not set or not passed to the container."
    )

try:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
except Exception as e:
    raise ValueError(
        f"FATAL: Invalid FIELD_ENCRYPTION_KEY. The key must be a valid Fernet key. Error: {e}"
    )


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
