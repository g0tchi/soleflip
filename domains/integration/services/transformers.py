"""
Data Transformers for Import Processing
Handles data normalization, cleaning, and transformation from various
source formats into standardized database-ready structures.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import structlog

logger = structlog.get_logger(__name__)


class TransformError(Exception):
    """Custom exception for transformation errors"""

    pass


@dataclass
class TransformResult:
    """Result of data transformation"""

    transformed_data: List[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]
    records_processed: int
    records_transformed: int

    def __post_init__(self):
        self.records_processed = len(self.transformed_data) + len(self.errors)


class FieldType(Enum):
    """Supported field types for transformation"""

    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    UUID = "uuid"
    EMAIL = "email"
    URL = "url"
    CURRENCY = "currency"


@dataclass
class FieldMapping:
    """Configuration for field transformation"""

    source_field: str
    target_field: str
    field_type: FieldType
    required: bool = False
    default_value: Any = None
    transform_func: Optional[Callable] = None
    validation_pattern: Optional[str] = None
    description: Optional[str] = None


class DataTransformer:
    """Universal data transformer for import processing"""

    def __init__(self):
        self.warnings = []
        self.errors = []

        # Common transformation patterns
        self.date_patterns = [
            "%Y-%m-%d %H:%M:%S %z",  # 2022-07-07 21:40:06 +00
            "%Y-%m-%d %H:%M:%S",  # 2022-07-07 21:40:06
            "%Y-%m-%d",  # 2022-07-07
            "%m/%d/%Y",  # 07/07/2022
            "%d.%m.%Y",  # 07.07.2022
            "%Y-%m-%dT%H:%M:%SZ",  # ISO format
            "%Y-%m-%dT%H:%M:%S",  # ISO without Z
        ]

        self.currency_pattern = re.compile(r"[\$€£¥₹]?([0-9,]+\.?[0-9]*)")

    def transform(
        self,
        data: List[Dict[str, Any]],
        field_mappings: List[FieldMapping],
        source_type: str = "unknown",
    ) -> TransformResult:
        """
        Transform raw data using field mappings

        Args:
            data: Raw data records
            field_mappings: List of field transformation configurations
            source_type: Source identifier for logging

        Returns:
            TransformResult with transformed data and statistics
        """
        logger.info(
            "Starting data transformation",
            records=len(data),
            mappings=len(field_mappings),
            source=source_type,
        )

        self.warnings = []
        self.errors = []
        transformed_records = []

        for idx, record in enumerate(data):
            try:
                transformed_record = self._transform_record(record, field_mappings, idx)
                if transformed_record:
                    transformed_records.append(transformed_record)
            except Exception as e:
                error_msg = f"Row {idx + 1}: {str(e)}"
                self.errors.append(error_msg)
                logger.warning("Record transformation failed", row=idx + 1, error=str(e))

        result = TransformResult(
            transformed_data=transformed_records,
            warnings=self.warnings.copy(),
            errors=self.errors.copy(),
            records_processed=len(data),
            records_transformed=len(transformed_records),
        )

        logger.info(
            "Data transformation completed",
            processed=result.records_processed,
            transformed=result.records_transformed,
            warnings=len(result.warnings),
            errors=len(result.errors),
        )

        return result

    def _transform_record(
        self, record: Dict[str, Any], field_mappings: List[FieldMapping], row_idx: int
    ) -> Optional[Dict[str, Any]]:
        """Transform a single record"""
        transformed = {}
        record_errors = []

        for mapping in field_mappings:
            try:
                value = self._extract_field_value(record, mapping, row_idx)
                if value is not None:
                    transformed[mapping.target_field] = value
                elif mapping.required:
                    record_errors.append(
                        f"Required field '{mapping.source_field}' is missing or empty"
                    )
                elif mapping.default_value is not None:
                    transformed[mapping.target_field] = mapping.default_value

            except Exception as e:
                error_msg = f"Field '{mapping.source_field}': {str(e)}"
                record_errors.append(error_msg)

        # If there are critical errors, skip this record
        if record_errors:
            self.errors.extend([f"Row {row_idx + 1}: {error}" for error in record_errors])
            return None

        # Add metadata
        transformed["_source_row"] = row_idx + 1
        transformed["_transformed_at"] = datetime.now(timezone.utc)

        return transformed

    def _extract_field_value(
        self, record: Dict[str, Any], mapping: FieldMapping, row_idx: int
    ) -> Any:
        """Extract and transform a single field value"""
        # Get raw value
        raw_value = record.get(mapping.source_field)

        # Handle empty/null values
        if raw_value is None or (isinstance(raw_value, str) and raw_value.strip() == ""):
            return None

        # Apply custom transformation function if provided
        if mapping.transform_func:
            try:
                raw_value = mapping.transform_func(raw_value)
            except Exception as e:
                raise TransformError(f"Custom transformation failed: {str(e)}")

        # Type-specific transformations
        try:
            transformed_value = self._transform_by_type(raw_value, mapping.field_type)
        except Exception as e:
            raise TransformError(f"Type transformation failed: {str(e)}")

        # Validation pattern check
        if mapping.validation_pattern and isinstance(transformed_value, str):
            if not re.match(mapping.validation_pattern, transformed_value):
                raise TransformError(f"Value doesn't match validation pattern")

        return transformed_value

    def _transform_by_type(self, value: Any, field_type: FieldType) -> Any:
        """Transform value based on target field type"""
        if value is None:
            return None

        try:
            if field_type == FieldType.STRING:
                return str(value).strip()

            elif field_type == FieldType.INTEGER:
                if isinstance(value, str):
                    # Remove common formatting
                    clean_value = re.sub(r"[,\s]", "", value)
                    return int(float(clean_value))  # Handle "123.0" -> 123
                return int(value)

            elif field_type == FieldType.DECIMAL:
                if isinstance(value, str):
                    clean_value = re.sub(r"[,\s]", "", value)
                    return Decimal(clean_value)
                return Decimal(str(value))

            elif field_type == FieldType.BOOLEAN:
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on", "enabled")
                return bool(value)

            elif field_type == FieldType.DATE:
                return self._parse_date(value).date()

            elif field_type == FieldType.DATETIME:
                return self._parse_date(value)

            elif field_type == FieldType.UUID:
                if isinstance(value, str):
                    return uuid.UUID(value)
                return value

            elif field_type == FieldType.EMAIL:
                email = str(value).strip().lower()
                if "@" not in email:
                    raise ValueError("Invalid email format")
                return email

            elif field_type == FieldType.URL:
                url = str(value).strip()
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                return url

            elif field_type == FieldType.CURRENCY:
                return self._parse_currency(value)

            else:
                return value

        except Exception as e:
            raise TransformError(f"Cannot convert '{value}' to {field_type.value}: {str(e)}")

    def _parse_date(self, value: Any) -> datetime:
        """Parse date/datetime with multiple format support"""
        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            value = value.strip()

            for pattern in self.date_patterns:
                try:
                    parsed = datetime.strptime(value, pattern)
                    # Add timezone if missing
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    return parsed
                except ValueError:
                    continue

            raise ValueError(f"Could not parse date: {value}")

        raise ValueError(f"Invalid date format: {type(value)}")

    def _parse_currency(self, value: Any) -> Decimal:
        """Parse currency values with symbol and formatting support"""
        if isinstance(value, (int, float, Decimal)):
            return Decimal(str(value))

        if isinstance(value, str):
            # Remove currency symbols and extract number
            match = self.currency_pattern.search(value.replace(",", ""))
            if match:
                return Decimal(match.group(1))

            # Fallback to direct conversion
            clean_value = re.sub(r"[^0-9.-]", "", value)
            if clean_value:
                return Decimal(clean_value)

        raise ValueError(f"Cannot parse currency: {value}")


class StockXTransformer(DataTransformer):
    """Specialized transformer for StockX data"""

    @staticmethod
    def get_field_mappings() -> List[FieldMapping]:
        """Get standard field mappings for StockX normalized data (after validation)"""
        return [
            FieldMapping(
                source_field="item_name",  # Normalized by validator
                target_field="product_name",
                field_type=FieldType.STRING,
                required=True,
                description="Product name/title",
            ),
            FieldMapping(
                source_field="sku",  # Style field normalized to sku by validator
                target_field="sku",
                field_type=FieldType.STRING,
                required=False,  # Optional, will be generated if missing
                description="Product SKU from Style field",
            ),
            FieldMapping(
                source_field="size",  # Normalized by validator
                target_field="size",
                field_type=FieldType.STRING,
                required=False,
                description="Product size (optional for non-shoes)",
            ),
            FieldMapping(
                source_field="order_number",  # Normalized by validator
                target_field="order_number",
                field_type=FieldType.STRING,
                required=True,
                description="StockX order number",
            ),
            FieldMapping(
                source_field="sale_date",  # Normalized by validator
                target_field="sale_date",
                field_type=FieldType.DATETIME,
                required=True,
                description="Date and time of sale",
            ),
            FieldMapping(
                source_field="listing_price",  # Normalized by validator
                target_field="listing_price",
                field_type=FieldType.DECIMAL,
                required=True,
                description="Original listing price",
            ),
            FieldMapping(
                source_field="seller_fee",  # Normalized by validator
                target_field="seller_fee",
                field_type=FieldType.DECIMAL,
                required=False,  # Some StockX records may not have fees
                description="Fee charged by StockX",
            ),
            FieldMapping(
                source_field="total_payout",  # Normalized by validator
                target_field="payout_amount",
                field_type=FieldType.DECIMAL,
                required=False,  # Made optional since it might be missing
                description="Final payout amount received",
            ),
            FieldMapping(
                source_field="buyer_destination_country",  # Normalized by validator
                target_field="buyer_destination_country",
                field_type=FieldType.STRING,
                required=False,
                description="Country where item was shipped",
            ),
            FieldMapping(
                source_field="buyer_destination_city",  # Normalized by validator
                target_field="buyer_destination_city",
                field_type=FieldType.STRING,
                required=False,
                description="City where item was shipped",
            ),
        ]

    def transform_stockx_data(self, data: List[Dict[str, Any]]) -> TransformResult:
        """Transform StockX CSV data with predefined mappings"""
        logger.info("Transforming StockX data", records=len(data))

        field_mappings = self.get_field_mappings()
        result = self.transform(data, field_mappings, source_type="stockx")

        # Add StockX-specific metadata
        for record in result.transformed_data:
            record["source_platform"] = "stockx"
            record["import_type"] = "historical_sales"

        return result


class NotionTransformer(DataTransformer):
    """Specialized transformer for Notion API data"""

    def transform_notion_data(self, data: List[Dict[str, Any]]) -> TransformResult:
        """Transform Notion database data"""
        logger.info("Transforming Notion data", records=len(data))

        # Notion has nested property structure, so we need custom handling
        transformed_records = []

        for idx, record in enumerate(data):
            try:
                transformed = self._transform_notion_record(record, idx)
                if transformed:
                    transformed_records.append(transformed)
            except Exception as e:
                self.errors.append(f"Row {idx + 1}: {str(e)}")

        return TransformResult(
            transformed_data=transformed_records,
            warnings=self.warnings.copy(),
            errors=self.errors.copy(),
            records_processed=len(data),
            records_transformed=len(transformed_records),
        )

    def _transform_notion_record(
        self, record: Dict[str, Any], row_idx: int
    ) -> Optional[Dict[str, Any]]:
        """Transform a single Notion record"""
        properties = record.get("properties", {})
        transformed = {}

        # Extract common Notion property types
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type")

            if prop_type == "title":
                title_data = prop_data.get("title", [])
                if title_data:
                    transformed[prop_name.lower().replace(" ", "_")] = (
                        title_data[0].get("text", {}).get("content", "")
                    )

            elif prop_type == "rich_text":
                text_data = prop_data.get("rich_text", [])
                if text_data:
                    transformed[prop_name.lower().replace(" ", "_")] = (
                        text_data[0].get("text", {}).get("content", "")
                    )

            elif prop_type == "number":
                number_value = prop_data.get("number")
                if number_value is not None:
                    transformed[prop_name.lower().replace(" ", "_")] = Decimal(str(number_value))

            elif prop_type == "date":
                date_data = prop_data.get("date")
                if date_data and date_data.get("start"):
                    transformed[prop_name.lower().replace(" ", "_")] = self._parse_date(
                        date_data["start"]
                    )

            elif prop_type == "select":
                select_data = prop_data.get("select")
                if select_data:
                    transformed[prop_name.lower().replace(" ", "_")] = select_data.get("name", "")

        # Add metadata
        transformed["notion_id"] = record.get("id")
        transformed["source_platform"] = "notion"
        transformed["_source_row"] = row_idx + 1
        transformed["_transformed_at"] = datetime.now(timezone.utc)

        return transformed


class AliasTransformer(DataTransformer):
    """Specialized transformer for Alias data (GOAT's selling platform) with StockX name prioritization"""

    @staticmethod
    def get_field_mappings() -> List[FieldMapping]:
        """Get standard field mappings for Alias normalized data"""
        return [
            FieldMapping(
                source_field="item_name",
                target_field="product_name",
                field_type=FieldType.STRING,
                required=True,
                description="Product name from Alias",
            ),
            FieldMapping(
                source_field="brand",
                target_field="brand",
                field_type=FieldType.STRING,
                required=False,
                description="Brand extracted from product name",
            ),
            FieldMapping(
                source_field="sku",
                target_field="sku",
                field_type=FieldType.STRING,
                required=False,
                description="Product SKU",
            ),
            FieldMapping(
                source_field="size",
                target_field="size",
                field_type=FieldType.STRING,
                required=False,
                description="Product size",
            ),
            FieldMapping(
                source_field="order_number",
                target_field="order_number",
                field_type=FieldType.STRING,
                required=True,
                description="Alias (GOAT) order number",
            ),
            FieldMapping(
                source_field="sale_date",
                target_field="sale_date",
                field_type=FieldType.DATETIME,
                required=True,
                description="Sale completion date",
            ),
            FieldMapping(
                source_field="sale_price",
                target_field="sale_price",
                field_type=FieldType.DECIMAL,
                required=True,
                description="Final sale price in USD",
            ),
            FieldMapping(
                source_field="supplier",
                target_field="supplier",
                field_type=FieldType.STRING,
                required=False,
                description="GOAT/Alias supplier username",
            ),
        ]

    def transform_alias_data(self, data: List[Dict[str, Any]]) -> TransformResult:
        """Transform Alias (GOAT) CSV data with StockX name prioritization"""
        logger.info("Transforming Alias (GOAT) data with StockX prioritization", records=len(data))

        field_mappings = self.get_field_mappings()
        result = self.transform(data, field_mappings, source_type="alias")

        # Add Alias (GOAT) specific metadata and StockX prioritization flags
        for record in result.transformed_data:
            record["source_platform"] = "alias"  # Alias = GOAT's selling platform
            record["import_type"] = "completed_sales"

            # Flag records that need StockX name prioritization
            if record.get("_requires_stockx_name_priority"):
                record["requires_name_matching"] = True
                record["prioritize_stockx_names"] = True

            # Add unique external ID for deduplication
            if record.get("order_number"):
                record["external_transaction_id"] = f"alias_{record['order_number']}"

        return result

    async def prioritize_stockx_names(
        self, alias_records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply StockX name prioritization for Alias records
        This method would typically query the database for existing StockX products
        and replace Alias names with StockX equivalents when matches are found
        """
        logger.info("Applying StockX name prioritization", records=len(alias_records))

        prioritized_records = []

        for record in alias_records:
            if not record.get("requires_name_matching"):
                prioritized_records.append(record)
                continue

            # Extract key identifiers for matching
            sku = record.get("sku", "").strip()
            size = record.get("size", "").strip()
            brand = record.get("brand", "").strip()

            # Find StockX equivalent name (this would query the database in real implementation)
            stockx_name = await self._find_stockx_equivalent_name(sku, size, brand)

            if stockx_name:
                logger.debug(
                    "Found StockX equivalent",
                    alias_name=record.get("product_name"),
                    stockx_name=stockx_name,
                    sku=sku,
                )

                # Store original Alias name and use StockX name
                record["original_alias_name"] = record.get("product_name")
                record["product_name"] = stockx_name
                record["name_source"] = "stockx_prioritized"
            else:
                # Keep Alias name if no StockX equivalent found
                record["name_source"] = "alias_original"

            prioritized_records.append(record)

        return prioritized_records

    async def _find_stockx_equivalent_name(self, sku: str, size: str, brand: str) -> Optional[str]:
        """
        Find StockX equivalent product name based on SKU, size, and brand
        This would query the products database in a real implementation
        """
        # Placeholder implementation - in reality this would:
        # 1. Query the products table for StockX entries with matching SKU
        # 2. Consider size and brand as additional matching criteria
        # 3. Return the StockX product name if found

        # For now, we'll simulate with some logic
        if not sku:
            return None

        # This would be replaced with actual database query:
        # SELECT name FROM products WHERE sku = %s AND source_platform = 'stockx' LIMIT 1
        return None  # Placeholder


# Factory function for getting appropriate transformer
def get_transformer(source_type: str) -> DataTransformer:
    """
    Factory function to get appropriate transformer for source type

    Args:
        source_type: Type of data source ('stockx', 'notion', 'manual', etc.)

    Returns:
        Appropriate transformer instance
    """
    transformers = {
        "stockx": StockXTransformer(),
        "notion": NotionTransformer(),
        "alias": AliasTransformer(),
        "manual": DataTransformer(),  # Generic transformer
        "sales": DataTransformer(),  # Generic transformer
    }

    return transformers.get(source_type.lower(), DataTransformer())


# Convenience function for easy usage
def transform_data(
    data: List[Dict[str, Any]],
    source_type: str,
    custom_mappings: Optional[List[FieldMapping]] = None,
) -> TransformResult:
    """
    Convenience function to transform data with appropriate transformer

    Args:
        data: Raw data to transform
        source_type: Source type identifier
        custom_mappings: Optional custom field mappings

    Returns:
        TransformResult with transformed data

    Example:
        result = transform_data(csv_records, 'stockx')
        clean_data = result.transformed_data
    """
    transformer = get_transformer(source_type)

    if source_type.lower() == "stockx" and not custom_mappings:
        return transformer.transform_stockx_data(data)
    elif source_type.lower() == "notion" and not custom_mappings:
        return transformer.transform_notion_data(data)
    elif source_type.lower() == "alias" and not custom_mappings:
        return transformer.transform_alias_data(data)
    elif custom_mappings:
        return transformer.transform(data, custom_mappings, source_type)
    else:
        # Generic transformation - pass through with basic cleaning
        return transformer.transform(data, [], source_type)
