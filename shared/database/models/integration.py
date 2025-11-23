"""
Integration domain models
Data imports, external integrations, and marketplace data
"""

import uuid

from sqlalchemy import (
    CheckConstraint,
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

from shared.database.models.base import Base, TimestampMixin
from shared.database.utils import IS_POSTGRES, get_schema_ref


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


class MarketplaceData(Base, TimestampMixin):
    """Market data from multiple platforms (StockX, Alias, GOAT, etc.) for pricing intelligence"""

    __tablename__ = "marketplace_data"
    __table_args__ = (
        UniqueConstraint(
            "inventory_item_id", "platform_id", name="uq_marketplace_data_item_platform"
        ),
        CheckConstraint("volatility >= 0 AND volatility <= 1", name="chk_volatility_range"),
        CheckConstraint("fees_percentage >= 0 AND fees_percentage <= 1", name="chk_fees_range"),
        {"schema": "analytics"} if IS_POSTGRES else {},
    ) if IS_POSTGRES else (
        UniqueConstraint(
            "inventory_item_id", "platform_id", name="uq_marketplace_data_item_platform"
        ),
    )

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
