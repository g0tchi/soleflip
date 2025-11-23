"""
Catalog domain models
Product catalog, brands, categories, and sizes
"""

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from shared.database.models.base import Base, TimestampMixin
from shared.database.utils import IS_POSTGRES, get_schema_ref


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
