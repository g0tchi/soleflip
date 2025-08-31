"""
Unit Tests for Data Validators
Tests validation logic without external dependencies
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domains.integration.services.validators import (
    NotionValidator,
    SalesValidator,
    StockXValidator,
    ValidationError,
    ValidationResult,
)


@pytest.mark.unit
class TestStockXValidator:
    """Test suite for StockX data validator"""

    @pytest.fixture
    def validator(self):
        mock_session = MagicMock(spec=AsyncSession)
        validator = StockXValidator(mock_session)
        # Mock the brand extractor to avoid actual DB calls in unit tests
        validator.brand_extractor.extract_brand_from_name = AsyncMock(
            return_value=MagicMock(name="Nike")
        )
        return validator

    @pytest.fixture
    def valid_stockx_record(self):
        return {
            "Order Number": "SX-123456",
            "Sale Date": "01/15/2024 10:30:00",
            "Item": "Nike Air Jordan 1 High OG Chicago",
            "Size": "9",
            "Listing Price": "180.00",
            "SKU": "555088-101",
            "Seller Fee": "17.10",
            "Payment Processing": "5.40",
            "Shipping Fee": "13.95",
            "Total Payout": "143.55",
            "Seller Name": "TestSeller",
            "Buyer Country": "United States",
            "Invoice Number": "INV-123",
        }

    async def test_validate_record_success(self, validator, valid_stockx_record):
        """Test successful record validation"""
        normalized = await validator.validate_record(valid_stockx_record, 0)

        assert normalized["order_number"] == "SX-123456"
        assert normalized["item_name"] == "Nike Air Jordan 1 High OG Chicago"
        assert normalized["size"] == "US 9"  # Normalized
        assert normalized["listing_price"] == Decimal("180.00")
        assert normalized["seller_fee"] == Decimal("17.10")
        assert normalized["source"] == "stockx"
        assert "imported_at" in normalized

    async def test_validate_record_missing_required_field(self, validator):
        """Test validation with missing required field"""
        invalid_record = {
            "Sale Date": "01/15/2024 10:30:00",
            "Item": "Nike Air Jordan 1",
            "Size": "9",
            "Listing Price": "180.00",
            # Missing 'Order Number'
        }

        with pytest.raises(ValidationError) as exc_info:
            await validator.validate_record(invalid_record, 0)

        assert "Missing required field: Order Number" in str(exc_info.value)

    async def test_validate_batch_mixed_results(self, validator, valid_stockx_record):
        """Test batch validation with mixed valid/invalid records"""
        data = [
            valid_stockx_record,
            {
                "Order Number": "SX-789",
                "Sale Date": "01/16/2024",
                "Item": "Adidas Yeezy",
                "Size": "10",
                "Listing Price": "250.00",
            },
            {
                # Missing required fields
                "Item": "Invalid Record",
                "Size": "11",
            },
        ]

        result = await validator.validate_batch(data)

        assert isinstance(result, ValidationResult)
        assert not result.is_valid  # Should be invalid due to last record
        assert len(result.errors) > 0
        assert len(result.normalized_data) == 3  # All records included
        assert result.normalized_data[2]["_validation_error"] is True

    def test_normalize_size(self, validator):
        """Test size normalization"""
        assert validator._normalize_size("9") == "US 9"
        assert validator._normalize_size("9.5") == "US 9.5"
        assert validator._normalize_size("N/A") == "One Size"
        assert validator._normalize_size("") == "One Size"
        assert validator._normalize_size("US 10") == "US 10"
        assert validator._normalize_size(None) == "Unknown"

    def test_normalize_currency(self, validator):
        """Test currency normalization"""
        assert validator.normalize_currency("180.00") == Decimal("180.00")
        assert validator.normalize_currency("€180,50") == Decimal("180.50")
        assert validator.normalize_currency("$1,234.56") == Decimal("1234.56")
        assert validator.normalize_currency("") is None
        assert validator.normalize_currency(None) is None

        with pytest.raises(ValidationError):
            validator.normalize_currency("invalid")

    def test_normalize_date(self, validator):
        """Test date normalization"""
        # StockX format
        date1 = validator.normalize_date("01/15/2024 10:30:00", ["%m/%d/%Y %H:%M:%S"])
        assert date1.year == 2024
        assert date1.month == 1
        assert date1.day == 15

        # Simple date format
        date2 = validator.normalize_date("2024-01-15", ["%Y-%m-%d"])
        assert date2.year == 2024
        assert date2.month == 1
        assert date2.day == 15

        with pytest.raises(ValidationError):
            validator.normalize_date("invalid-date")


@pytest.mark.unit
class TestNotionValidator:
    """Test suite for Notion data validator"""

    @pytest.fixture
    def validator(self):
        mock_session = MagicMock(spec=AsyncSession)
        validator = NotionValidator(mock_session)
        validator.brand_extractor.extract_brand_from_name = AsyncMock(
            return_value=MagicMock(name="Nike")
        )
        return validator

    @pytest.fixture
    def valid_notion_record(self):
        return {
            "id": "page-123",
            "name": "Nike Air Jordan 1",
            "database_id": "db-456",
            "properties": {
                "brand": {"rich_text": [{"text": {"content": "Nike"}}]},
                "size": {"rich_text": [{"text": {"content": "US 9"}}]},
                "purchase_price": {"number": 120.00},
                "target_price": {"number": 180.00},
                "status": {"select": {"name": "In Stock"}},
                "stockx_order": {"rich_text": [{"text": {"content": "SX-123456"}}]},
            },
            "last_edited_time": "2024-01-15T10:30:00.000Z",
        }

    async def test_validate_record_success(self, validator, valid_notion_record):
        """Test successful Notion record validation"""
        normalized = await validator.validate_record(valid_notion_record, 0)

        assert normalized["notion_page_id"] == "page-123"
        assert normalized["item_name"] == "Nike Air Jordan 1"
        assert normalized["brand"] == "Nike"
        assert normalized["size"] == "US 9"
        assert normalized["purchase_price"] == Decimal("120.00")
        assert normalized["target_price"] == Decimal("180.00")
        assert normalized["status"] == "In Stock"
        assert normalized["stockx_order_number"] == "SX-123456"
        assert normalized["source"] == "notion"

    async def test_validate_record_missing_id(self, validator):
        """Test validation with missing ID"""
        invalid_record = {
            "name": "Nike Air Jordan 1",
            # Missing 'id'
        }

        with pytest.raises(ValidationError) as exc_info:
            await validator.validate_record(invalid_record, 0)

        assert "Missing required field: id" in str(exc_info.value)

    def test_extract_property_rich_text(self, validator):
        """Test property extraction for rich text"""
        properties = {"brand": {"rich_text": [{"text": {"content": "Nike"}}]}}

        result = validator._extract_property(properties, "brand")
        assert result == "Nike"

    def test_extract_property_select(self, validator):
        """Test property extraction for select"""
        properties = {"status": {"select": {"name": "In Stock"}}}

        result = validator._extract_property(properties, "status")
        assert result == "In Stock"

    def test_extract_currency_property(self, validator):
        """Test currency property extraction"""
        properties = {"price": {"number": 120.50}}

        result = validator._extract_currency_property(properties, "price")
        assert result == Decimal("120.50")

        # Test missing property
        result = validator._extract_currency_property(properties, "missing")
        assert result is None


@pytest.mark.unit
class TestSalesValidator:
    """Test suite for Sales CSV validator"""

    @pytest.fixture
    def validator(self):
        mock_session = MagicMock(spec=AsyncSession)
        validator = SalesValidator(mock_session)
        validator.brand_extractor.extract_brand_from_name = AsyncMock(
            return_value=MagicMock(name="Nike")
        )
        return validator

    @pytest.fixture
    def valid_sales_record(self):
        return {
            "SKU": "SALE-001",
            "Sale Date": "15. Januar 2024",
            "Status": "completed",
            "Gross Buy": "120,00",
            "Net Buy": "115,00",
            "Gross Sale": "180,00",
            "Net Sale": "170,00",
            "Platform": "StockX",
        }

    async def test_validate_record_success(self, validator, valid_sales_record):
        """Test successful sales record validation"""
        normalized = await validator.validate_record(valid_sales_record, 0)

        assert normalized["sku"] == "SALE-001"
        assert normalized["status"] == "completed"
        assert normalized["gross_buy"] == Decimal("120.00")
        assert normalized["net_buy"] == Decimal("115.00")
        assert normalized["gross_sale"] == Decimal("180.00")
        assert normalized["net_sale"] == Decimal("170.00")
        assert normalized["profit"] == Decimal("55.00")  # Calculated
        assert normalized["platform"] == "StockX"
        assert normalized["source"] == "sales"

    async def test_validate_record_missing_sku(self, validator):
        """Test validation with missing SKU"""
        invalid_record = {
            "Sale Date": "15. Januar 2024",
            "Status": "completed",
            # Missing 'SKU'
        }

        with pytest.raises(ValidationError) as exc_info:
            await validator.validate_record(invalid_record, 0)

        assert "Missing required field: SKU" in str(exc_info.value)

    async def test_german_date_format(self, validator):
        """Test German date format handling"""
        record = {"SKU": "SALE-001", "Sale Date": "15. Januar 2024", "Status": "completed"}

        normalized = await validator.validate_record(record, 0)

        # Should successfully parse German date format
        assert normalized["sale_date"] is not None
        assert normalized["sale_date"].day == 15
        assert normalized["sale_date"].month == 1
        assert normalized["sale_date"].year == 2024


@pytest.mark.unit
class TestBaseValidator:
    """Test base validator functionality"""

    @pytest.fixture
    def validator(self):
        mock_session = MagicMock(spec=AsyncSession)
        validator = StockXValidator(mock_session)
        validator.brand_extractor.extract_brand_from_name = AsyncMock(
            return_value=MagicMock(name="Nike")
        )
        return validator

    def test_normalize_currency_edge_cases(self, validator):
        """Test currency normalization edge cases"""
        # European format
        assert validator.normalize_currency("1.234,56") == Decimal("1234.56")

        # Mixed formats
        assert validator.normalize_currency("1,234.56") == Decimal("1234.56")

        # Various currency symbols
        assert validator.normalize_currency("€123.45") == Decimal("123.45")
        assert validator.normalize_currency("$123.45") == Decimal("123.45")
        assert validator.normalize_currency("£123.45") == Decimal("123.45")

        # Whitespace handling
        assert validator.normalize_currency("  123.45  ") == Decimal("123.45")

    def test_normalize_date_multiple_formats(self, validator):
        """Test date normalization with multiple formats"""
        formats = ["%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y"]

        # ISO format
        date1 = validator.normalize_date("2024-01-15", formats)
        assert date1.year == 2024

        # European format
        date2 = validator.normalize_date("15.01.2024", formats)
        assert date2.year == 2024

        # US format
        date3 = validator.normalize_date("01/15/2024", formats)
        assert date3.year == 2024

    async def test_validation_error_aggregation(self, validator):
        """Test that validation errors are properly aggregated"""
        invalid_data = [
            {
                "Item": "Valid Item",
                "Size": "9",
                "Order Number": "SX-001",
                "Sale Date": "2024-01-15",
                "Listing Price": "100",
            },
            {"Size": "10"},  # Missing required fields
            {"Order Number": "SX-003", "Item": "Another Item"},  # Missing required fields
        ]

        result = await validator.validate_batch(invalid_data)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert len(result.normalized_data) == 3

        # First record should be valid
        assert "_validation_error" not in result.normalized_data[0]

        # Other records should be marked as errors
        assert result.normalized_data[1]["_validation_error"] is True
        assert result.normalized_data[2]["_validation_error"] is True
