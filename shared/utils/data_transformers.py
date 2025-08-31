"""
Data Transformation Utilities
Common patterns for data processing and transformation
"""

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")
ModelType = TypeVar("ModelType")


@dataclass
class TransformationRule:
    """Configuration for data transformation rule"""

    source_field: str
    target_field: str
    transformer: Optional[Callable] = None
    required: bool = False
    default_value: Any = None
    validation: Optional[Callable[[Any], bool]] = None


class DataTransformer:
    """Generic data transformer with configurable rules"""

    def __init__(self, rules: List[TransformationRule]):
        self.rules = rules
        self._field_map = {rule.source_field: rule for rule in rules}

    def transform(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform source data according to configured rules"""
        result = {}
        errors = []

        for rule in self.rules:
            try:
                value = source_data.get(rule.source_field)

                # Handle missing required fields
                if value is None and rule.required:
                    if rule.default_value is not None:
                        value = rule.default_value
                    else:
                        errors.append(f"Required field '{rule.source_field}' is missing")
                        continue

                # Apply transformation
                if value is not None and rule.transformer:
                    value = rule.transformer(value)

                # Validate transformed value
                if value is not None and rule.validation:
                    if not rule.validation(value):
                        errors.append(f"Validation failed for field '{rule.source_field}'")
                        continue

                # Set target field
                if value is not None:
                    result[rule.target_field] = value

            except Exception as e:
                errors.append(f"Error transforming field '{rule.source_field}': {str(e)}")

        if errors:
            logger.warning("Data transformation errors", errors=errors)

        return result

    def transform_batch(
        self, source_data_list: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """Transform a batch of data records"""
        results = []
        all_errors = []

        for i, source_data in enumerate(source_data_list):
            try:
                transformed = self.transform(source_data)
                results.append(transformed)
            except Exception as e:
                error_msg = f"Error transforming record {i}: {str(e)}"
                all_errors.append(error_msg)
                logger.error("Batch transformation error", record_index=i, error=str(e))

        return results, all_errors


class StockXDataTransformer(DataTransformer):
    """Specialized transformer for StockX data"""

    def __init__(self):
        rules = [
            TransformationRule(
                source_field="orderNumber", target_field="external_order_id", required=True
            ),
            TransformationRule(
                source_field="product.productId",
                target_field="product_sku",
                transformer=self._extract_nested_field,
                required=True,
            ),
            TransformationRule(
                source_field="variant.variantValue",
                target_field="size",
                transformer=self._extract_nested_field,
                required=True,
            ),
            TransformationRule(
                source_field="amount",
                target_field="sale_price",
                transformer=self._parse_decimal,
                required=True,
            ),
            TransformationRule(
                source_field="status",
                target_field="status",
                transformer=self._normalize_status,
                required=True,
            ),
            TransformationRule(
                source_field="createdAt",
                target_field="created_at",
                transformer=self._parse_datetime,
                required=True,
            ),
        ]
        super().__init__(rules)

    @staticmethod
    def _extract_nested_field(data: Dict[str, Any]) -> Any:
        """Extract value from nested dictionary structure"""
        if isinstance(data, dict):
            # For nested fields like "product.productId"
            return data
        return data

    @staticmethod
    def _parse_decimal(value: Union[str, int, float]) -> Decimal:
        """Parse value to Decimal"""
        try:
            return Decimal(str(value))
        except Exception:
            raise ValueError(f"Cannot convert to decimal: {value}")

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        """Parse ISO datetime string"""
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            raise ValueError(f"Cannot parse datetime: {value}")

    @staticmethod
    def _normalize_status(status: str) -> str:
        """Normalize status values"""
        status_map = {
            "COMPLETED": "completed",
            "PENDING": "pending",
            "CANCELLED": "cancelled",
            "SHIPPED": "shipped",
        }
        return status_map.get(status.upper(), status.lower())


class CSVDataTransformer(DataTransformer):
    """Specialized transformer for CSV data"""

    def __init__(self, column_mappings: Dict[str, str]):
        """
        Initialize with column mappings
        Args:
            column_mappings: Dict mapping CSV column names to target field names
        """
        rules = []
        for csv_col, target_field in column_mappings.items():
            rules.append(
                TransformationRule(
                    source_field=csv_col,
                    target_field=target_field,
                    transformer=self._clean_csv_value,
                )
            )
        super().__init__(rules)

    @staticmethod
    def _clean_csv_value(value: Any) -> Any:
        """Clean CSV value (remove quotes, whitespace, etc.)"""
        if isinstance(value, str):
            # Remove surrounding quotes and whitespace
            value = value.strip().strip("\"'")

            # Convert empty strings to None
            if value == "":
                return None

        return value


class ModelTransformer:
    """Transform data for database models"""

    @staticmethod
    def to_model_dict(
        data: Dict[str, Any],
        model_class: Type[ModelType],
        exclude_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Transform dictionary to model-compatible format"""
        exclude_fields = exclude_fields or []

        # Get model field names (assuming SQLAlchemy model)
        if hasattr(model_class, "__table__"):
            model_fields = set(model_class.__table__.columns.keys())
        else:
            # Fallback for non-SQLAlchemy models
            model_fields = set(data.keys())

        # Filter and transform data
        model_data = {}
        for key, value in data.items():
            if key in exclude_fields:
                continue

            if key in model_fields:
                # Transform specific field types
                if key.endswith("_id") and isinstance(value, str):
                    # Convert string UUIDs
                    try:
                        model_data[key] = UUID(value)
                    except (ValueError, TypeError):
                        model_data[key] = value
                elif key.endswith("_at") and isinstance(value, str):
                    # Convert datetime strings
                    try:
                        model_data[key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        model_data[key] = value
                elif key.endswith("_price") and value is not None:
                    # Convert prices to Decimal
                    try:
                        model_data[key] = Decimal(str(value))
                    except (ValueError, TypeError):
                        model_data[key] = value
                else:
                    model_data[key] = value

        return model_data

    @staticmethod
    def from_model(
        model_instance: ModelType,
        include_relationships: bool = False,
        exclude_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        exclude_fields = exclude_fields or []

        if hasattr(model_instance, "to_dict"):
            # Use model's own to_dict method if available
            data = model_instance.to_dict()
        elif hasattr(model_instance, "__dict__"):
            # Convert model attributes
            data = {}
            for key, value in model_instance.__dict__.items():
                if key.startswith("_"):
                    continue

                if key in exclude_fields:
                    continue

                # Convert specific types
                if isinstance(value, UUID):
                    data[key] = str(value)
                elif isinstance(value, datetime):
                    data[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    data[key] = float(value)
                elif hasattr(value, "__dict__") and include_relationships:
                    # Handle relationships
                    data[key] = ModelTransformer.from_model(value, include_relationships=False)
                elif not callable(value):
                    data[key] = value
        else:
            # Fallback for dataclasses
            data = asdict(model_instance) if hasattr(model_instance, "__dataclass_fields__") else {}

        return data


class ValidationTransformer:
    """Data validation and cleaning"""

    @staticmethod
    def validate_and_clean(
        data: Dict[str, Any], validation_rules: Dict[str, Callable[[Any], Any]]
    ) -> tuple[Dict[str, Any], List[str]]:
        """Validate and clean data according to rules"""
        cleaned_data = {}
        errors = []

        for field, validator in validation_rules.items():
            value = data.get(field)

            try:
                cleaned_value = validator(value)
                if cleaned_value is not None:
                    cleaned_data[field] = cleaned_value
            except Exception as e:
                errors.append(f"Validation error for field '{field}': {str(e)}")

        return cleaned_data, errors

    @staticmethod
    def email_validator(value: Any) -> Optional[str]:
        """Validate email address"""
        if value is None:
            return None

        email = str(value).strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            raise ValueError(f"Invalid email format: {email}")

        return email

    @staticmethod
    def phone_validator(value: Any) -> Optional[str]:
        """Validate and normalize phone number"""
        if value is None:
            return None

        phone = re.sub(r"[^\d]", "", str(value))
        if not (10 <= len(phone) <= 15):
            raise ValueError(f"Invalid phone number: {value}")

        return phone

    @staticmethod
    def price_validator(value: Any) -> Optional[Decimal]:
        """Validate price"""
        if value is None:
            return None

        try:
            price = Decimal(str(value))
            if price < 0:
                raise ValueError("Price cannot be negative")
            return price.quantize(Decimal("0.01"))
        except (ValueError, TypeError):
            raise ValueError(f"Invalid price: {value}")

    @staticmethod
    def sku_validator(value: Any) -> Optional[str]:
        """Validate SKU format"""
        if value is None:
            return None

        sku = str(value).strip()
        if not re.match(r"^[A-Za-z0-9_-]+$", sku):
            raise ValueError(f"Invalid SKU format: {sku}")

        if not (3 <= len(sku) <= 100):
            raise ValueError(f"SKU length must be between 3 and 100 characters: {sku}")

        return sku


class BulkDataProcessor:
    """Process large datasets in batches"""

    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size

    async def process_in_batches(
        self,
        data: List[Dict[str, Any]],
        processor: Callable[[List[Dict[str, Any]]], Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        """Process data in batches"""
        total_records = len(data)
        processed_records = 0
        errors = []
        results = []

        logger.info(
            "Starting batch processing", total_records=total_records, batch_size=self.batch_size
        )

        for i in range(0, total_records, self.batch_size):
            batch = data[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total_records + self.batch_size - 1) // self.batch_size

            try:
                logger.debug(
                    "Processing batch",
                    batch_num=batch_num,
                    total_batches=total_batches,
                    batch_size=len(batch),
                )

                batch_result = (
                    await processor(batch)
                    if asyncio.iscoroutinefunction(processor)
                    else processor(batch)
                )
                results.append(batch_result)
                processed_records += len(batch)

                if progress_callback:
                    progress_callback(processed_records, total_records)

            except Exception as e:
                error_msg = f"Error processing batch {batch_num}: {str(e)}"
                errors.append(error_msg)
                logger.error("Batch processing error", batch_num=batch_num, error=str(e))

        logger.info(
            "Batch processing completed",
            processed_records=processed_records,
            total_records=total_records,
            error_count=len(errors),
        )

        return {
            "total_records": total_records,
            "processed_records": processed_records,
            "error_count": len(errors),
            "errors": errors,
            "results": results,
        }


# Common transformer instances
stockx_transformer = StockXDataTransformer()
csv_transformer = CSVDataTransformer(
    {
        "Order Number": "order_number",
        "Product Name": "product_name",
        "Size": "size",
        "Sale Price": "sale_price",
        "Date": "transaction_date",
    }
)

# Common validation rules
product_validation_rules = {
    "sku": ValidationTransformer.sku_validator,
    "price": ValidationTransformer.price_validator,
    "name": lambda x: str(x).strip() if x else None,
}

supplier_validation_rules = {
    "email": ValidationTransformer.email_validator,
    "phone": ValidationTransformer.phone_validator,
    "name": lambda x: str(x).strip() if x else None,
}
