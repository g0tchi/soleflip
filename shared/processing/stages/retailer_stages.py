"""
Processing Stages for Retailer Data Imports
Concrete implementations of processing stages for large-scale retailer imports.
"""

import re
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from shared.database.connection import get_db_session
from shared.database.models import Product, Brand, Category, InventoryItem
from shared.events import publish_event, ProductCreatedEvent
from shared.processing.async_pipeline import ProcessingContext, ChunkResult
from shared.repositories.base_repository import BaseRepository

logger = structlog.get_logger(__name__)


class RetailerParsingStage:
    """Parsing stage for retailer product data"""

    def __init__(self):
        self.required_fields = ["name", "sku", "brand", "price"]
        self.optional_fields = [
            "description",
            "category",
            "size",
            "color",
            "material",
            "stock_quantity",
        ]

    async def setup(self, context: ProcessingContext) -> None:
        """Setup parsing stage"""
        logger.info(
            "Setting up retailer parsing stage",
            batch_id=str(context.batch_id),
            source_type=context.source_type,
        )

    async def cleanup(self, context: ProcessingContext) -> None:
        """Cleanup parsing stage"""
        logger.info("Cleaning up retailer parsing stage", batch_id=str(context.batch_id))

    async def process_chunk(
        self, chunk_data: List[Dict[str, Any]], context: ProcessingContext
    ) -> ChunkResult:
        """Parse and normalize retailer data"""

        parsed_records = []
        failed_records = 0
        errors = []

        for i, raw_record in enumerate(chunk_data):
            try:
                parsed_record = await self._parse_retailer_record(raw_record, context.source_type)
                if parsed_record:
                    parsed_records.append(parsed_record)
                else:
                    failed_records += 1
                    errors.append(f"Record {i}: Failed validation")

            except Exception as e:
                failed_records += 1
                errors.append(f"Record {i}: Parsing error - {str(e)}")
                logger.warning(
                    "Failed to parse retailer record",
                    record_index=i,
                    error=str(e),
                    batch_id=str(context.batch_id),
                )

        # Replace chunk data with parsed data
        chunk_data.clear()
        chunk_data.extend(parsed_records)

        return ChunkResult(
            chunk_index=context.current_chunk,
            records_processed=len(parsed_records),
            records_failed=failed_records,
            processing_time_ms=0,  # Will be calculated by pipeline
            errors=errors,
        )

    async def _parse_retailer_record(
        self, raw_record: Dict[str, Any], source_type: str
    ) -> Optional[Dict[str, Any]]:
        """Parse and normalize a single retailer record"""

        # Check required fields
        missing_fields = [field for field in self.required_fields if not raw_record.get(field)]
        if missing_fields:
            logger.debug(
                "Record missing required fields", missing_fields=missing_fields, record=raw_record
            )
            return None

        # Normalize the record
        parsed = {
            "name": self._clean_text(raw_record.get("name")),
            "sku": self._clean_sku(raw_record.get("sku")),
            "brand": self._clean_text(raw_record.get("brand")),
            "description": self._clean_text(raw_record.get("description")),
            "category": self._clean_text(raw_record.get("category")),
            "size": self._normalize_size(raw_record.get("size")),
            "color": self._clean_text(raw_record.get("color")),
            "material": self._clean_text(raw_record.get("material")),
            "price": self._parse_price(raw_record.get("price")),
            "cost": self._parse_price(raw_record.get("cost")),
            "stock_quantity": self._parse_integer(raw_record.get("stock_quantity")),
            "source_type": source_type,
            "raw_data": raw_record,  # Keep original for debugging
        }

        # Validate parsed data
        if not self._validate_parsed_record(parsed):
            return None

        return parsed

    def _clean_text(self, text: Any) -> Optional[str]:
        """Clean and normalize text fields"""
        if not text:
            return None

        text = str(text).strip()
        if not text:
            return None

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Limit length
        if len(text) > 255:
            text = text[:255]

        return text

    def _clean_sku(self, sku: Any) -> Optional[str]:
        """Clean and normalize SKU"""
        if not sku:
            return None

        sku = str(sku).strip().upper()

        # Remove invalid characters
        sku = re.sub(r"[^A-Z0-9\-_]", "", sku)

        if len(sku) < 2:
            return None

        return sku

    def _normalize_size(self, size: Any) -> Optional[str]:
        """Normalize size information"""
        if not size:
            return None

        size = str(size).strip().upper()

        # Common size normalizations
        size_mappings = {
            "XS": "XS",
            "EXTRA SMALL": "XS",
            "S": "S",
            "SMALL": "S",
            "M": "M",
            "MEDIUM": "M",
            "MED": "M",
            "L": "L",
            "LARGE": "L",
            "XL": "XL",
            "EXTRA LARGE": "XL",
            "XXL": "XXL",
            "2XL": "XXL",
            "XXXL": "XXXL",
            "3XL": "XXXL",
        }

        return size_mappings.get(size, size)

    def _parse_price(self, price: Any) -> Optional[Decimal]:
        """Parse price values"""
        if not price:
            return None

        try:
            # Remove currency symbols and spaces
            price_str = re.sub(r"[^\d.,]", "", str(price))

            if not price_str:
                return None

            # Handle different decimal separators
            if "," in price_str and "." in price_str:
                # Assume comma is thousands separator
                price_str = price_str.replace(",", "")
            elif "," in price_str:
                # Could be decimal separator (European style)
                if price_str.count(",") == 1 and len(price_str.split(",")[1]) <= 2:
                    price_str = price_str.replace(",", ".")
                else:
                    price_str = price_str.replace(",", "")

            return Decimal(price_str)

        except (ValueError, InvalidOperation):
            logger.debug(f"Failed to parse price: {price}")
            return None

    def _parse_integer(self, value: Any) -> Optional[int]:
        """Parse integer values"""
        if not value:
            return None

        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return None

    def _validate_parsed_record(self, record: Dict[str, Any]) -> bool:
        """Validate parsed record"""

        # Check required fields after parsing
        if not record.get("name") or not record.get("sku") or not record.get("brand"):
            return False

        # Validate price
        if record.get("price") and record["price"] <= 0:
            return False

        # Validate stock quantity
        if record.get("stock_quantity") and record["stock_quantity"] < 0:
            return False

        return True


class RetailerValidationStage:
    """Validation stage for retailer data"""

    async def setup(self, context: ProcessingContext) -> None:
        logger.info("Setting up retailer validation stage", batch_id=str(context.batch_id))

    async def cleanup(self, context: ProcessingContext) -> None:
        logger.info("Cleaning up retailer validation stage", batch_id=str(context.batch_id))

    async def process_chunk(
        self, chunk_data: List[Dict[str, Any]], context: ProcessingContext
    ) -> ChunkResult:
        """Validate retailer records"""

        valid_records = []
        failed_records = 0
        errors = []

        # Collect SKUs for duplicate checking
        chunk_skus = set()

        for i, record in enumerate(chunk_data):
            try:
                validation_errors = await self._validate_record(record, chunk_skus)

                if validation_errors:
                    failed_records += 1
                    errors.extend([f"Record {i}: {error}" for error in validation_errors])
                else:
                    valid_records.append(record)
                    chunk_skus.add(record["sku"])

            except Exception as e:
                failed_records += 1
                errors.append(f"Record {i}: Validation error - {str(e)}")

        # Replace chunk data with valid records
        chunk_data.clear()
        chunk_data.extend(valid_records)

        return ChunkResult(
            chunk_index=context.current_chunk,
            records_processed=len(valid_records),
            records_failed=failed_records,
            processing_time_ms=0,
            errors=errors,
        )

    async def _validate_record(self, record: Dict[str, Any], existing_skus: set) -> List[str]:
        """Validate a single record"""
        errors = []

        # Check for duplicate SKU in current chunk
        if record["sku"] in existing_skus:
            errors.append(f"Duplicate SKU in batch: {record['sku']}")

        # Validate SKU format
        if not re.match(r"^[A-Z0-9\-_]{2,50}$", record["sku"]):
            errors.append(f"Invalid SKU format: {record['sku']}")

        # Validate name length
        if len(record["name"]) > 255:
            errors.append("Product name too long (max 255 characters)")

        # Validate brand
        if len(record["brand"]) > 100:
            errors.append("Brand name too long (max 100 characters)")

        # Validate price
        if record.get("price"):
            if record["price"] <= 0:
                errors.append("Price must be positive")
            if record["price"] > Decimal("99999.99"):
                errors.append("Price too high")

        # Validate stock quantity
        if record.get("stock_quantity") is not None:
            if record["stock_quantity"] < 0:
                errors.append("Stock quantity cannot be negative")
            if record["stock_quantity"] > 999999:
                errors.append("Stock quantity too high")

        return errors


class RetailerTransformationStage:
    """Transformation stage for retailer data"""

    def __init__(self):
        self._brand_cache = {}
        self._category_cache = {}

    async def setup(self, context: ProcessingContext) -> None:
        logger.info("Setting up retailer transformation stage", batch_id=str(context.batch_id))

        # Pre-load brands and categories for faster lookups
        async with get_db_session() as session:
            brand_repo = BaseRepository(Brand, session)
            brands = await brand_repo.get_all()
            self._brand_cache = {brand.name.lower(): brand for brand in brands}

            category_repo = BaseRepository(Category, session)
            categories = await category_repo.get_all()
            self._category_cache = {cat.name.lower(): cat for cat in categories}

    async def cleanup(self, context: ProcessingContext) -> None:
        logger.info("Cleaning up retailer transformation stage", batch_id=str(context.batch_id))
        self._brand_cache.clear()
        self._category_cache.clear()

    async def process_chunk(
        self, chunk_data: List[Dict[str, Any]], context: ProcessingContext
    ) -> ChunkResult:
        """Transform retailer records for database storage"""

        transformed_records = []
        failed_records = 0
        errors = []

        for i, record in enumerate(chunk_data):
            try:
                transformed_record = await self._transform_record(record)
                if transformed_record:
                    transformed_records.append(transformed_record)
                else:
                    failed_records += 1
                    errors.append(f"Record {i}: Transformation failed")

            except Exception as e:
                failed_records += 1
                errors.append(f"Record {i}: Transformation error - {str(e)}")

        # Replace chunk data with transformed records
        chunk_data.clear()
        chunk_data.extend(transformed_records)

        return ChunkResult(
            chunk_index=context.current_chunk,
            records_processed=len(transformed_records),
            records_failed=failed_records,
            processing_time_ms=0,
            errors=errors,
        )

    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform record for database storage"""

        # Look up brand
        brand_name = record["brand"].lower()
        brand = self._brand_cache.get(brand_name)
        if not brand:
            # Create new brand if not found
            brand = await self._create_brand(record["brand"])
            if brand:
                self._brand_cache[brand_name] = brand

        # Look up category
        category = None
        if record.get("category"):
            category_name = record["category"].lower()
            category = self._category_cache.get(category_name)
            if not category:
                # Create new category if not found
                category = await self._create_category(record["category"])
                if category:
                    self._category_cache[category_name] = category

        # Build product data
        product_data = {
            "name": record["name"],
            "sku": record["sku"],
            "brand_id": brand.id if brand else None,
            "category_id": category.id if category else None,
            "description": record.get("description"),
            "size": record.get("size"),
            "color": record.get("color"),
            "material": record.get("material"),
            "base_price": record.get("price"),
            "cost": record.get("cost"),
            "source_system": record["source_type"],
            "is_active": True,
        }

        # Add inventory data if present
        inventory_data = None
        if record.get("stock_quantity") is not None:
            inventory_data = {
                "quantity_available": record["stock_quantity"],
                "quantity_reserved": 0,
                "reorder_point": max(5, record["stock_quantity"] // 10),  # Simple reorder logic
                "source_system": record["source_type"],
            }

        return {
            "product": product_data,
            "inventory": inventory_data,
            "raw_data": record.get("raw_data"),
        }

    async def _create_brand(self, brand_name: str) -> Optional[Brand]:
        """Create a new brand"""
        try:
            async with get_db_session() as session:
                brand_repo = BaseRepository(Brand, session)

                # Check if brand exists (race condition protection)
                existing = await brand_repo.find_one(name=brand_name)
                if existing:
                    return existing

                brand = await brand_repo.create(
                    name=brand_name, slug=brand_name.lower().replace(" ", "-"), is_active=True
                )

                logger.debug(f"Created new brand: {brand_name}")
                return brand

        except Exception as e:
            logger.error(f"Failed to create brand {brand_name}: {e}")
            return None

    async def _create_category(self, category_name: str) -> Optional[Category]:
        """Create a new category"""
        try:
            async with get_db_session() as session:
                category_repo = BaseRepository(Category, session)

                # Check if category exists (race condition protection)
                existing = await category_repo.find_one(name=category_name)
                if existing:
                    return existing

                category = await category_repo.create(
                    name=category_name, slug=category_name.lower().replace(" ", "-"), is_active=True
                )

                logger.debug(f"Created new category: {category_name}")
                return category

        except Exception as e:
            logger.error(f"Failed to create category {category_name}: {e}")
            return None


class RetailerPersistenceStage:
    """Persistence stage for retailer data"""

    async def setup(self, context: ProcessingContext) -> None:
        logger.info("Setting up retailer persistence stage", batch_id=str(context.batch_id))

    async def cleanup(self, context: ProcessingContext) -> None:
        logger.info("Cleaning up retailer persistence stage", batch_id=str(context.batch_id))

    async def process_chunk(
        self, chunk_data: List[Dict[str, Any]], context: ProcessingContext
    ) -> ChunkResult:
        """Persist retailer records to database"""

        persisted_records = 0
        failed_records = 0
        errors = []

        async with get_db_session() as session:
            product_repo = BaseRepository(Product, session)
            inventory_repo = BaseRepository(InventoryItem, session)

            for i, record in enumerate(chunk_data):
                try:
                    # Create or update product
                    product = await self._create_or_update_product(product_repo, record["product"])

                    if product:
                        # Create or update inventory
                        if record.get("inventory"):
                            await self._create_or_update_inventory(
                                inventory_repo, product.id, record["inventory"]
                            )

                        # Publish events
                        await publish_event(
                            ProductCreatedEvent(
                                aggregate_id=product.id,
                                product_id=product.id,
                                sku=product.sku,
                                name=product.name,
                                brand=record["product"].get("brand_name", ""),
                                category=record["product"].get("category_name", ""),
                                source=record["product"]["source_system"],
                            )
                        )

                        persisted_records += 1
                    else:
                        failed_records += 1
                        errors.append(f"Record {i}: Failed to create product")

                except Exception as e:
                    failed_records += 1
                    errors.append(f"Record {i}: Persistence error - {str(e)}")
                    logger.error(
                        "Failed to persist record",
                        record_index=i,
                        error=str(e),
                        batch_id=str(context.batch_id),
                    )

        return ChunkResult(
            chunk_index=context.current_chunk,
            records_processed=persisted_records,
            records_failed=failed_records,
            processing_time_ms=0,
            errors=errors,
        )

    async def _create_or_update_product(
        self, product_repo: BaseRepository, product_data: Dict[str, Any]
    ) -> Optional[Product]:
        """Create or update product"""
        try:
            # Check if product exists by SKU
            existing = await product_repo.find_one(sku=product_data["sku"])

            if existing:
                # Update existing product
                updated = await product_repo.update(existing.id, **product_data)
                return updated
            else:
                # Create new product
                created = await product_repo.create(**product_data)
                return created

        except Exception as e:
            logger.error(f"Failed to create/update product: {e}")
            return None

    async def _create_or_update_inventory(
        self, inventory_repo: BaseRepository, product_id: UUID, inventory_data: Dict[str, Any]
    ) -> Optional[InventoryItem]:
        """Create or update inventory"""
        try:
            inventory_data["product_id"] = product_id

            # Check if inventory exists
            existing = await inventory_repo.find_one(product_id=product_id)

            if existing:
                # Update existing inventory
                updated = await inventory_repo.update(existing.id, **inventory_data)
                return updated
            else:
                # Create new inventory
                created = await inventory_repo.create(**inventory_data)
                return created

        except Exception as e:
            logger.error(f"Failed to create/update inventory: {e}")
            return None
