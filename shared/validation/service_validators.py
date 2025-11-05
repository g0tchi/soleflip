"""
Service-Level Validators
Reusable validation logic for business operations across domains
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator
from shared.utils.validation_utils import ValidationUtils


class ValidationResult:
    """Result of a validation operation"""

    def __init__(self, is_valid: bool = True, errors: Optional[Dict[str, List[str]]] = None):
        self.is_valid = is_valid
        self.errors = errors or {}

    def add_error(self, field: str, message: str):
        """Add a validation error"""
        if field not in self.errors:
            self.errors[field] = []
        self.errors[field].append(message)
        self.is_valid = False

    def merge(self, other: "ValidationResult"):
        """Merge another validation result into this one"""
        if not other.is_valid:
            self.is_valid = False
            for field, messages in other.errors.items():
                if field not in self.errors:
                    self.errors[field] = []
                self.errors[field].extend(messages)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors
        }


class InventoryItemValidator:
    """Validators for inventory item operations"""

    @staticmethod
    def validate_purchase_price(price: Any) -> ValidationResult:
        """Validate purchase price is positive and reasonable"""
        result = ValidationResult()

        normalized = ValidationUtils.normalize_currency(price)
        if normalized is None:
            result.add_error("purchase_price", "Invalid currency format")
            return result

        if normalized <= 0:
            result.add_error("purchase_price", "Purchase price must be greater than 0")

        if normalized > Decimal("100000.00"):  # 100k EUR seems like a reasonable max
            result.add_error("purchase_price", "Purchase price exceeds reasonable maximum (100,000 EUR)")

        return result

    @staticmethod
    def validate_quantity(quantity: Any) -> ValidationResult:
        """Validate quantity is a positive integer"""
        result = ValidationResult()

        if not isinstance(quantity, int):
            try:
                quantity = int(quantity)
            except (ValueError, TypeError):
                result.add_error("quantity", "Quantity must be an integer")
                return result

        if quantity < 0:
            result.add_error("quantity", "Quantity cannot be negative")

        if quantity > 10000:  # Reasonable max for single inventory item
            result.add_error("quantity", "Quantity exceeds reasonable maximum (10,000)")

        return result

    @staticmethod
    def validate_status(status: str) -> ValidationResult:
        """Validate inventory status is valid"""
        result = ValidationResult()

        valid_statuses = [
            "in_stock", "sold", "reserved", "damaged", "returned",
            "shipped", "pending", "cancelled"
        ]

        normalized = ValidationUtils.normalize_status(status, valid_statuses)
        if normalized is None:
            result.add_error("status", f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

        return result

    @staticmethod
    def validate_create_request(data: Dict[str, Any]) -> ValidationResult:
        """Validate complete inventory item creation request"""
        result = ValidationResult()

        # Required fields
        if "product_id" not in data or not data["product_id"]:
            result.add_error("product_id", "Product ID is required")
        elif not ValidationUtils.is_valid_uuid(str(data["product_id"])):
            result.add_error("product_id", "Invalid product ID format")

        if "size_id" not in data or not data["size_id"]:
            result.add_error("size_id", "Size ID is required")
        elif not ValidationUtils.is_valid_uuid(str(data["size_id"])):
            result.add_error("size_id", "Invalid size ID format")

        # Optional but validated fields
        if "purchase_price" in data and data["purchase_price"] is not None:
            result.merge(InventoryItemValidator.validate_purchase_price(data["purchase_price"]))

        if "quantity" in data:
            result.merge(InventoryItemValidator.validate_quantity(data["quantity"]))
        else:
            result.add_error("quantity", "Quantity is required")

        if "status" in data and data["status"]:
            result.merge(InventoryItemValidator.validate_status(data["status"]))

        return result


class ProductValidator:
    """Validators for product operations"""

    @staticmethod
    def validate_sku(sku: str) -> ValidationResult:
        """Validate SKU format"""
        result = ValidationResult()

        normalized = ValidationUtils.normalize_sku(sku)
        if normalized is None:
            result.add_error("sku", "Invalid SKU format (must be 3-50 alphanumeric characters)")

        return result

    @staticmethod
    def validate_retail_price(price: Any) -> ValidationResult:
        """Validate retail price"""
        result = ValidationResult()

        if price is None:
            return result  # Retail price is optional

        normalized = ValidationUtils.normalize_currency(price)
        if normalized is None:
            result.add_error("retail_price", "Invalid currency format")
            return result

        if normalized < 0:
            result.add_error("retail_price", "Retail price cannot be negative")

        return result

    @staticmethod
    def validate_create_request(data: Dict[str, Any]) -> ValidationResult:
        """Validate product creation request"""
        result = ValidationResult()

        # Required fields
        if "sku" not in data or not data["sku"]:
            result.add_error("sku", "SKU is required")
        else:
            result.merge(ProductValidator.validate_sku(data["sku"]))

        if "name" not in data or not data["name"]:
            result.add_error("name", "Product name is required")
        else:
            name = ValidationUtils.clean_string(data["name"], max_length=255)
            if name is None:
                result.add_error("name", "Product name cannot be empty")

        if "category_id" not in data or not data["category_id"]:
            result.add_error("category_id", "Category ID is required")
        elif not ValidationUtils.is_valid_uuid(str(data["category_id"])):
            result.add_error("category_id", "Invalid category ID format")

        # Optional validated fields
        if "retail_price" in data and data["retail_price"] is not None:
            result.merge(ProductValidator.validate_retail_price(data["retail_price"]))

        if "brand_id" in data and data["brand_id"] is not None:
            if not ValidationUtils.is_valid_uuid(str(data["brand_id"])):
                result.add_error("brand_id", "Invalid brand ID format")

        return result


class PricingValidator:
    """Validators for pricing operations"""

    @staticmethod
    def validate_margin(margin_percent: Any) -> ValidationResult:
        """Validate profit margin percentage"""
        result = ValidationResult()

        try:
            margin = Decimal(str(margin_percent))
        except (ValueError, TypeError, InvalidOperation):
            result.add_error("margin_percent", "Invalid margin percentage format")
            return result

        if margin < -100:
            result.add_error("margin_percent", "Margin cannot be less than -100%")

        if margin > 1000:
            result.add_error("margin_percent", "Margin exceeds reasonable maximum (1000%)")

        return result

    @staticmethod
    def validate_price_range(
        min_price: Any,
        max_price: Any,
        field_prefix: str = "price"
    ) -> ValidationResult:
        """Validate price range (min <= max)"""
        result = ValidationResult()

        min_normalized = ValidationUtils.normalize_currency(min_price)
        max_normalized = ValidationUtils.normalize_currency(max_price)

        if min_normalized is None:
            result.add_error(f"{field_prefix}_min", "Invalid minimum price format")

        if max_normalized is None:
            result.add_error(f"{field_prefix}_max", "Invalid maximum price format")

        if min_normalized and max_normalized:
            if min_normalized > max_normalized:
                result.add_error(
                    field_prefix,
                    "Minimum price cannot be greater than maximum price"
                )

        return result

    @staticmethod
    def validate_listing_price(
        listing_price: Any,
        purchase_price: Any,
        minimum_margin_percent: Optional[Decimal] = None
    ) -> ValidationResult:
        """Validate listing price meets minimum margin requirements"""
        result = ValidationResult()

        listing = ValidationUtils.normalize_currency(listing_price)
        purchase = ValidationUtils.normalize_currency(purchase_price)

        if listing is None:
            result.add_error("listing_price", "Invalid listing price format")
            return result

        if purchase is None:
            result.add_error("purchase_price", "Invalid purchase price format")
            return result

        if listing <= 0:
            result.add_error("listing_price", "Listing price must be greater than 0")

        # Calculate margin if minimum is specified
        if minimum_margin_percent and purchase > 0:
            actual_margin = ((listing - purchase) / purchase) * 100
            if actual_margin < minimum_margin_percent:
                result.add_error(
                    "listing_price",
                    f"Price does not meet minimum margin requirement ({minimum_margin_percent}%). "
                    f"Current margin: {actual_margin:.2f}%"
                )

        return result


class TransactionValidator:
    """Validators for transaction/order operations"""

    @staticmethod
    def validate_sale_price(sale_price: Any, purchase_price: Any) -> ValidationResult:
        """Validate sale price is reasonable compared to purchase price"""
        result = ValidationResult()

        sale = ValidationUtils.normalize_currency(sale_price)
        purchase = ValidationUtils.normalize_currency(purchase_price)

        if sale is None:
            result.add_error("sale_price", "Invalid sale price format")
            return result

        if sale <= 0:
            result.add_error("sale_price", "Sale price must be greater than 0")

        # Warning if selling at a loss (but not an error - might be legitimate)
        if purchase and sale < purchase * Decimal("0.5"):
            result.add_error(
                "sale_price",
                f"Sale price is significantly below purchase price (>50% loss)"
            )

        return result

    @staticmethod
    def validate_platform_fee(fee: Any, sale_price: Any) -> ValidationResult:
        """Validate platform fee is reasonable"""
        result = ValidationResult()

        fee_normalized = ValidationUtils.normalize_currency(fee)
        sale_normalized = ValidationUtils.normalize_currency(sale_price)

        if fee_normalized is None:
            result.add_error("platform_fee", "Invalid platform fee format")
            return result

        if fee_normalized < 0:
            result.add_error("platform_fee", "Platform fee cannot be negative")

        if sale_normalized and fee_normalized > sale_normalized:
            result.add_error("platform_fee", "Platform fee cannot exceed sale price")

        # Platform fees typically 5-15%, warn if outside this range
        if sale_normalized and sale_normalized > 0:
            fee_percent = (fee_normalized / sale_normalized) * 100
            if fee_percent > 50:
                result.add_error(
                    "platform_fee",
                    f"Platform fee ({fee_percent:.1f}%) seems unusually high"
                )

        return result


class DateValidator:
    """Validators for date-related operations"""

    @staticmethod
    def validate_date_range(
        start_date: Any,
        end_date: Any,
        max_range_days: Optional[int] = None
    ) -> ValidationResult:
        """Validate date range (start <= end, within max range if specified)"""
        result = ValidationResult()

        start = ValidationUtils.normalize_date(start_date)
        end = ValidationUtils.normalize_date(end_date)

        if start is None:
            result.add_error("start_date", "Invalid start date format")

        if end is None:
            result.add_error("end_date", "Invalid end date format")

        if start and end:
            if start > end:
                result.add_error("date_range", "Start date cannot be after end date")

            if max_range_days:
                range_delta = end - start
                if range_delta.days > max_range_days:
                    result.add_error(
                        "date_range",
                        f"Date range exceeds maximum of {max_range_days} days"
                    )

        return result

    @staticmethod
    def validate_future_date(date_value: Any, field_name: str = "date") -> ValidationResult:
        """Validate that a date is not in the future"""
        result = ValidationResult()

        normalized = ValidationUtils.normalize_date(date_value)

        if normalized is None:
            result.add_error(field_name, "Invalid date format")
            return result

        if normalized > datetime.now(normalized.tzinfo):
            result.add_error(field_name, "Date cannot be in the future")

        return result


# Import-specific validators
class ImportValidator:
    """Validators for import operations"""

    @staticmethod
    def validate_batch_size(batch_size: int) -> ValidationResult:
        """Validate import batch size is reasonable"""
        result = ValidationResult()

        if not isinstance(batch_size, int) or batch_size <= 0:
            result.add_error("batch_size", "Batch size must be a positive integer")
            return result

        if batch_size > 10000:
            result.add_error("batch_size", "Batch size exceeds maximum (10,000 records)")

        return result

    @staticmethod
    def validate_file_format(filename: str, allowed_extensions: List[str]) -> ValidationResult:
        """Validate file format is allowed"""
        result = ValidationResult()

        if not filename:
            result.add_error("filename", "Filename is required")
            return result

        file_ext = filename.lower().split(".")[-1] if "." in filename else ""

        if file_ext not in [ext.lower() for ext in allowed_extensions]:
            result.add_error(
                "filename",
                f"Invalid file format. Allowed: {', '.join(allowed_extensions)}"
            )

        return result


# Convenience functions for quick validation
def validate_inventory_create(data: Dict[str, Any]) -> ValidationResult:
    """Quick validation for inventory item creation"""
    return InventoryItemValidator.validate_create_request(data)


def validate_product_create(data: Dict[str, Any]) -> ValidationResult:
    """Quick validation for product creation"""
    return ProductValidator.validate_create_request(data)


def validate_price_update(
    listing_price: Any,
    purchase_price: Any,
    min_margin: Optional[Decimal] = None
) -> ValidationResult:
    """Quick validation for price updates"""
    return PricingValidator.validate_listing_price(listing_price, purchase_price, min_margin)
