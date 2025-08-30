"""
Common validation utilities shared across domains.
Extracted to reduce code duplication in validation patterns.
"""

from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Any, Optional, Union
import re
from dateutil import parser as date_parser


class ValidationUtils:
    """Centralized validation utilities for common data normalization patterns."""

    # Common regex patterns
    EMAIL_PATTERN = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
    PHONE_PATTERN = re.compile(r"^[\+\d\s\-\(\)]{7,20}$")
    SKU_PATTERN = re.compile(r"^[A-Z0-9\-]{3,50}$")

    @staticmethod
    def normalize_currency(value: Any) -> Optional[Decimal]:
        """
        Normalize currency values to Decimal.
        Handles strings, floats, ints, and existing Decimals.

        Args:
            value: Currency value to normalize

        Returns:
            Normalized Decimal value or None if invalid
        """
        if value is None:
            return None

        if isinstance(value, Decimal):
            return value

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        if isinstance(value, str):
            # Remove currency symbols and spaces
            clean_value = re.sub(r"[^\d\.-]", "", value.strip())
            if not clean_value:
                return None

            try:
                return Decimal(clean_value)
            except InvalidOperation:
                return None

        return None

    @staticmethod
    def normalize_date(value: Any) -> Optional[datetime]:
        """
        Normalize date values to timezone-aware datetime.
        Handles various string formats and datetime objects.

        Args:
            value: Date value to normalize

        Returns:
            Normalized datetime with timezone or None if invalid
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            # Ensure timezone aware
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value

        if isinstance(value, str):
            try:
                # Parse various date formats
                parsed_date = date_parser.parse(value)
                # Ensure timezone aware
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                return parsed_date
            except (ValueError, TypeError):
                return None

        return None

    @staticmethod
    def normalize_size(value: Any) -> Optional[str]:
        """
        Normalize size values to standard format.
        Handles various size representations (US, EU, UK).

        Args:
            value: Size value to normalize

        Returns:
            Normalized size string or None if invalid
        """
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, str):
            size_str = value.strip().upper()

            # Handle common size formats
            if size_str in ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]:
                return size_str

            # Handle numeric sizes (remove non-numeric chars except decimal point)
            numeric_size = re.sub(r"[^\d\.]", "", size_str)
            if numeric_size:
                try:
                    # Convert to float and back to standardize format
                    size_float = float(numeric_size)
                    # Return as int if it's a whole number, otherwise as float
                    return str(int(size_float)) if size_float.is_integer() else str(size_float)
                except ValueError:
                    pass

            return size_str if size_str else None

        return None

    @staticmethod
    def normalize_phone(value: Any) -> Optional[str]:
        """
        Normalize phone numbers to standard format.

        Args:
            value: Phone number to normalize

        Returns:
            Normalized phone string or None if invalid
        """
        if value is None:
            return None

        if isinstance(value, str):
            phone_str = value.strip()
            if ValidationUtils.PHONE_PATTERN.match(phone_str):
                return phone_str

        return None

    @staticmethod
    def normalize_email(value: Any) -> Optional[str]:
        """
        Normalize email addresses.

        Args:
            value: Email to normalize

        Returns:
            Normalized email string or None if invalid
        """
        if value is None:
            return None

        if isinstance(value, str):
            email_str = value.strip().lower()
            if ValidationUtils.EMAIL_PATTERN.match(email_str):
                return email_str

        return None

    @staticmethod
    def normalize_sku(value: Any) -> Optional[str]:
        """
        Normalize SKU values to standard format.

        Args:
            value: SKU to normalize

        Returns:
            Normalized SKU string or None if invalid
        """
        if value is None:
            return None

        if isinstance(value, str):
            sku_str = value.strip().upper()
            if ValidationUtils.SKU_PATTERN.match(sku_str):
                return sku_str

        return None

    @staticmethod
    def normalize_status(value: Any, valid_statuses: list[str]) -> Optional[str]:
        """
        Normalize status values against a list of valid statuses.

        Args:
            value: Status value to normalize
            valid_statuses: List of valid status strings

        Returns:
            Normalized status string or None if invalid
        """
        if value is None:
            return None

        if isinstance(value, str):
            status_str = value.strip().lower()
            valid_statuses_lower = [s.lower() for s in valid_statuses]

            if status_str in valid_statuses_lower:
                # Return the original case from valid_statuses
                index = valid_statuses_lower.index(status_str)
                return valid_statuses[index]

        return None

    @staticmethod
    def clean_string(value: Any, max_length: Optional[int] = None) -> Optional[str]:
        """
        Clean and normalize string values.

        Args:
            value: String value to clean
            max_length: Optional maximum length to truncate to

        Returns:
            Cleaned string or None if invalid
        """
        if value is None:
            return None

        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return None

            if max_length and len(cleaned) > max_length:
                cleaned = cleaned[:max_length].strip()

            return cleaned

        return None

    @staticmethod
    def is_valid_uuid(value: Any) -> bool:
        """
        Check if a value is a valid UUID string.

        Args:
            value: Value to check

        Returns:
            True if valid UUID, False otherwise
        """
        if not isinstance(value, str):
            return False

        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
        )
        return bool(uuid_pattern.match(value.strip()))


class ValidationErrors:
    """Common validation error messages."""

    REQUIRED_FIELD = "This field is required"
    INVALID_EMAIL = "Invalid email format"
    INVALID_PHONE = "Invalid phone number format"
    INVALID_CURRENCY = "Invalid currency value"
    INVALID_DATE = "Invalid date format"
    INVALID_SKU = "Invalid SKU format"
    INVALID_UUID = "Invalid UUID format"
    STRING_TOO_LONG = "String exceeds maximum length"
    INVALID_STATUS = "Invalid status value"
