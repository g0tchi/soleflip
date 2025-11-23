"""
Inventory domain models
Stock management and inventory tracking
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from shared.database.models.base import Base, TimestampMixin
from shared.database.utils import IS_POSTGRES, get_schema_ref


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
        }


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
