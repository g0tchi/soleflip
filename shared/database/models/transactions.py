"""
Transaction and sales domain models
Orders, listings, and financial transactions
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from shared.database.models.base import Base, TimestampMixin
from shared.database.utils import IS_POSTGRES, get_schema_ref


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
