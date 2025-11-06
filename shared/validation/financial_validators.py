"""
Financial Input Validators
Comprehensive validation for financial data in APIs
"""

from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Union
from uuid import UUID
import re

from fastapi import Query, Path, HTTPException, status
from pydantic import BaseModel, Field, validator


class FinancialValidationMixin:
    """Mixin class providing financial validation methods"""

    @staticmethod
    def validate_currency_amount(value: Union[str, int, float, Decimal]) -> Decimal:
        """
        Validate and convert currency amount to Decimal

        Args:
            value: The value to validate

        Returns:
            Decimal: Validated currency amount

        Raises:
            ValueError: If the value is invalid
        """
        if value is None:
            raise ValueError("Currency amount cannot be None")

        try:
            decimal_value = Decimal(str(value))
        except (ValueError, InvalidOperation):
            raise ValueError(f"Invalid currency amount: {value}")

        if decimal_value < 0:
            raise ValueError("Currency amount cannot be negative")

        if decimal_value > Decimal("999999.99"):
            raise ValueError("Currency amount too large (max: $999,999.99)")

        # Ensure proper decimal places for currency
        if decimal_value.as_tuple().exponent < -2:
            raise ValueError("Currency amount cannot have more than 2 decimal places")

        return decimal_value.quantize(Decimal("0.01"))

    @staticmethod
    def validate_percentage(value: Union[str, int, float, Decimal]) -> Decimal:
        """
        Validate percentage value

        Args:
            value: The percentage value to validate

        Returns:
            Decimal: Validated percentage

        Raises:
            ValueError: If the value is invalid
        """
        if value is None:
            raise ValueError("Percentage cannot be None")

        try:
            decimal_value = Decimal(str(value))
        except (ValueError, InvalidOperation):
            raise ValueError(f"Invalid percentage: {value}")

        if decimal_value < 0:
            raise ValueError("Percentage cannot be negative")

        if decimal_value > 100:
            raise ValueError("Percentage cannot exceed 100%")

        return decimal_value.quantize(Decimal("0.01"))

    @staticmethod
    def validate_margin_buffer(value: Union[str, int, float]) -> float:
        """
        Validate margin buffer percentage

        Args:
            value: The margin buffer percentage

        Returns:
            float: Validated margin buffer

        Raises:
            ValueError: If the value is invalid
        """
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid margin buffer: {value}")

        if float_value < 0:
            raise ValueError("Margin buffer cannot be negative")

        if float_value > 50:
            raise ValueError("Margin buffer cannot exceed 50%")

        return float_value


# FastAPI Query Parameter Validators
def PriceQuery(
    default: Any = ..., description: str = "Price amount in USD", example: float = 100.00
) -> Annotated[float, Query(...)]:
    """
    Validated price query parameter

    Args:
        default: Default value
        description: Parameter description
        example: Example value

    Returns:
        Annotated query parameter
    """
    return Query(
        default,
        description=description,
        example=example,
        ge=0.01,  # Minimum $0.01
        le=99999.99,  # Maximum $99,999.99
        title="Price Amount",
    )


def MarginQuery(
    default: float = 5.0,
    description: str = "Margin buffer percentage (0-50%)",
    example: float = 5.0,
) -> Annotated[float, Query(...)]:
    """
    Validated margin query parameter

    Args:
        default: Default value
        description: Parameter description
        example: Example value

    Returns:
        Annotated query parameter
    """
    return Query(
        default,
        description=description,
        example=example,
        ge=0.0,  # Minimum 0%
        le=50.0,  # Maximum 50%
        title="Margin Buffer",
    )


def QuantityQuery(
    default: int = 1, description: str = "Quantity of items", example: int = 1
) -> Annotated[int, Query(...)]:
    """
    Validated quantity query parameter

    Args:
        default: Default value
        description: Parameter description
        example: Example value

    Returns:
        Annotated query parameter
    """
    return Query(
        default,
        description=description,
        example=example,
        ge=1,  # Minimum 1
        le=1000,  # Maximum 1000
        title="Quantity",
    )


def PricingStrategyQuery(
    default: str = "competitive",
    description: str = "Pricing strategy to use",
    example: str = "competitive",
) -> Annotated[str, Query(...)]:
    """
    Validated pricing strategy query parameter

    Args:
        default: Default value
        description: Parameter description
        example: Example value

    Returns:
        Annotated query parameter
    """
    return Query(
        default,
        description=description,
        example=example,
        regex="^(competitive|premium|aggressive)$",
        title="Pricing Strategy",
    )


# Path Parameter Validators
def UUIDPath(
    description: str = "UUID identifier", example: str = "123e4567-e89b-12d3-a456-426614174000"
) -> Annotated[UUID, Path(...)]:
    """
    Validated UUID path parameter

    Args:
        description: Parameter description
        example: Example value

    Returns:
        Annotated path parameter
    """
    return Path(..., description=description, example=example, title="UUID")


def YearPath(
    description: str = "Year (2020-2030)", example: int = 2025
) -> Annotated[int, Path(...)]:
    """
    Validated year path parameter

    Args:
        description: Parameter description
        example: Example value

    Returns:
        Annotated path parameter
    """
    return Path(..., description=description, example=example, ge=2020, le=2030, title="Year")


# Pydantic Model Validators
class ValidatedFinancialModel(BaseModel, FinancialValidationMixin):
    """Base model with financial validation methods"""

    class Config:
        # Enable validation on assignment
        validate_assignment = True
        # Use enum values
        use_enum_values = True
        # Allow population by field name or alias (Pydantic v2 compatible)
        populate_by_name = True
        # Generate schema with examples (Pydantic v2 compatible)
        json_schema_extra = {"example": {"description": "Example financial data model"}}


class PriceUpdateRequest(ValidatedFinancialModel):
    """Validated price update request"""

    new_price: float = Field(
        ...,
        gt=0.01,
        le=99999.99,
        description="New price amount in USD",
        example=125.50,
        title="New Price",
    )

    reason: str = Field(
        default="manual_update",
        min_length=1,
        max_length=100,
        description="Reason for price change",
        example="market_adjustment",
        title="Update Reason",
    )

    @validator("new_price")
    def validate_price_precision(cls, v):
        """Ensure price has max 2 decimal places"""
        return cls.validate_currency_amount(v)

    @validator("reason")
    def validate_reason_format(cls, v):
        """Ensure reason is properly formatted"""
        if not re.match(r"^[a-zA-Z0-9_\s\-]+$", v):
            raise ValueError("Reason contains invalid characters")
        return v.strip().lower()


class ListingCreationRequest(ValidatedFinancialModel):
    """Validated listing creation request"""

    opportunity_id: UUID = Field(
        ...,
        description="QuickFlip opportunity ID",
        example="123e4567-e89b-12d3-a456-426614174000",
        title="Opportunity ID",
    )

    pricing_strategy: str = Field(
        default="competitive",
        description="Pricing strategy: competitive, premium, aggressive",
        example="competitive",
        title="Pricing Strategy",
    )

    margin_buffer: float = Field(
        default=5.0,
        ge=0.0,
        le=50.0,
        description="Additional margin buffer percentage",
        example=5.0,
        title="Margin Buffer",
    )

    @validator("pricing_strategy")
    def validate_pricing_strategy(cls, v):
        """Validate pricing strategy"""
        allowed_strategies = {"competitive", "premium", "aggressive"}
        if v.lower() not in allowed_strategies:
            raise ValueError(f'Pricing strategy must be one of: {", ".join(allowed_strategies)}')
        return v.lower()

    @validator("margin_buffer")
    def validate_margin_buffer_precision(cls, v):
        """Validate margin buffer"""
        return cls.validate_margin_buffer(v)


class BulkListingRequest(ValidatedFinancialModel):
    """Validated bulk listing request"""

    opportunity_ids: list[UUID] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of QuickFlip opportunity IDs (max 100)",
        example=["123e4567-e89b-12d3-a456-426614174000"],
        title="Opportunity IDs",
    )

    pricing_strategy: str = Field(
        default="competitive",
        description="Pricing strategy for all listings",
        example="competitive",
        title="Pricing Strategy",
    )

    @validator("opportunity_ids")
    def validate_unique_opportunities(cls, v):
        """Ensure all opportunity IDs are unique"""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate opportunity IDs are not allowed")
        return v

    @validator("pricing_strategy")
    def validate_bulk_pricing_strategy(cls, v):
        """Validate pricing strategy for bulk operations"""
        allowed_strategies = {"competitive", "premium", "aggressive"}
        if v.lower() not in allowed_strategies:
            raise ValueError(f'Pricing strategy must be one of: {", ".join(allowed_strategies)}')
        return v.lower()


class OrderTrackingUpdate(ValidatedFinancialModel):
    """Validated order tracking update"""

    tracking_number: str = Field(
        ...,
        min_length=5,
        max_length=50,
        description="Shipping tracking number",
        example="1Z999AA1234567890",
        title="Tracking Number",
    )

    @validator("tracking_number")
    def validate_tracking_format(cls, v):
        """Validate tracking number format"""
        # Remove whitespace
        cleaned = v.strip().upper()

        # Basic format validation (alphanumeric with some special chars)
        if not re.match(r"^[A-Z0-9\-]+$", cleaned):
            raise ValueError("Tracking number contains invalid characters")

        return cleaned


# Custom Exception for Validation Errors
class FinancialValidationError(HTTPException):
    """Custom exception for financial validation errors"""

    def __init__(self, detail: str, field: str = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": detail, "field": field, "type": "financial_validation_error"},
        )


# Dependency Functions for FastAPI
async def validate_price_update(request: PriceUpdateRequest) -> PriceUpdateRequest:
    """
    Dependency for validating price update requests

    Args:
        request: Price update request

    Returns:
        PriceUpdateRequest: Validated request

    Raises:
        FinancialValidationError: If validation fails
    """
    try:
        # Additional business logic validation
        if request.new_price < 10.00:
            raise FinancialValidationError("Price cannot be less than $10.00", field="new_price")

        return request
    except ValueError as e:
        raise FinancialValidationError(str(e), field="new_price")


async def validate_bulk_request(request: BulkListingRequest) -> BulkListingRequest:
    """
    Dependency for validating bulk listing requests

    Args:
        request: Bulk listing request

    Returns:
        BulkListingRequest: Validated request

    Raises:
        FinancialValidationError: If validation fails
    """
    try:
        # Additional business logic validation
        if len(request.opportunity_ids) > 50:
            raise FinancialValidationError(
                "Bulk operations limited to 50 items maximum", field="opportunity_ids"
            )

        return request
    except ValueError as e:
        raise FinancialValidationError(str(e), field="opportunity_ids")
