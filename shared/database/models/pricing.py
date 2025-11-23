"""
Pricing domain models
Pricing history and strategies
"""

import uuid

from sqlalchemy import Column, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from shared.database.models.base import Base, TimestampMixin
from shared.database.utils import IS_POSTGRES, get_schema_ref


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
