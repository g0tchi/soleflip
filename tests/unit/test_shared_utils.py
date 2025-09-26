"""
Unit tests for shared utility functions
Testing financial calculations and validation utilities for coverage improvement
"""

import pytest
from decimal import Decimal
from datetime import datetime, date
from uuid import UUID, uuid4

from shared.utils.financial import FinancialCalculator
from shared.utils.validation_utils import ValidationUtils


class TestFinancialCalculations:
    """Test FinancialCalculator utility functions"""

    def test_to_decimal_basic(self):
        """Test basic decimal conversion"""
        assert FinancialCalculator.to_decimal("123.45") == Decimal("123.45")
        assert FinancialCalculator.to_decimal(100) == Decimal("100")
        assert FinancialCalculator.to_decimal(99.99) == Decimal("99.99")
        assert FinancialCalculator.to_decimal(None) == Decimal("0")

    def test_to_decimal_invalid_input(self):
        """Test decimal conversion with invalid input"""
        assert FinancialCalculator.to_decimal("invalid") == Decimal("0")
        assert FinancialCalculator.to_decimal("") == Decimal("0")

    def test_to_currency_basic(self):
        """Test currency conversion and rounding"""
        result = FinancialCalculator.to_currency("123.456")
        assert result == Decimal("123.46")  # Rounded to 2 decimal places

    def test_calculate_margin_basic(self):
        """Test margin calculation"""
        cost = Decimal("100.00")
        sale_price = Decimal("150.00")

        margin = FinancialCalculator.calculate_margin(cost, sale_price)
        expected = Decimal("33.33")  # (150-100)/150 * 100
        assert abs(margin - expected) < Decimal("0.01")

    def test_calculate_margin_zero_sale_price(self):
        """Test margin calculation with zero sale price"""
        result = FinancialCalculator.calculate_margin(Decimal("100"), Decimal("0"))
        assert result == Decimal("0")  # Should handle gracefully

    def test_calculate_roi_basic(self):
        """Test ROI calculation"""
        cost = Decimal("100.00")
        profit = Decimal("50.00")  # This is the profit, not sale price

        roi = FinancialCalculator.calculate_roi(cost, profit)
        expected = Decimal("50.00")  # 50/100 * 100
        assert roi == expected

    def test_calculate_roi_zero_cost(self):
        """Test ROI calculation with zero cost"""
        result = FinancialCalculator.calculate_roi(Decimal("0"), Decimal("50"))
        assert result == Decimal("0")  # Should handle gracefully

    def test_calculate_net_proceeds_basic(self):
        """Test net proceeds calculation"""
        sale_price = Decimal("200.00")
        seller_fee = Decimal("10.00")
        processing_fee = Decimal("5.00")
        other_fees = Decimal("3.00")

        net_proceeds = FinancialCalculator.calculate_net_proceeds(
            sale_price, seller_fee, processing_fee, other_fees
        )
        expected = Decimal("182.00")  # 200 - 18
        assert net_proceeds == expected

    def test_calculate_net_proceeds_no_fees(self):
        """Test net proceeds with no fees"""
        sale_price = Decimal("200.00")
        net_proceeds = FinancialCalculator.calculate_net_proceeds(sale_price)
        assert net_proceeds == sale_price

    def test_calculate_gross_profit_basic(self):
        """Test gross profit calculation"""
        sale_price = Decimal("200.00")
        cost = Decimal("120.00")

        gross_profit = FinancialCalculator.calculate_gross_profit(sale_price, cost)
        expected = Decimal("80.00")  # 200 - 120
        assert gross_profit == expected

    def test_calculate_net_profit_basic(self):
        """Test net profit calculation"""
        net_proceeds = Decimal("180.00")
        cost = Decimal("120.00")

        net_profit = FinancialCalculator.calculate_net_profit(net_proceeds, cost)
        expected = Decimal("60.00")  # 180 - 120
        assert net_profit == expected

    def test_safe_average_basic(self):
        """Test safe_average with normal values"""
        values = [100, 200, 300]
        result = FinancialCalculator.safe_average(values)
        assert result == Decimal("200.00")

    def test_safe_average_empty_list(self):
        """Test safe_average with empty list - covers lines 135-136"""
        result = FinancialCalculator.safe_average([])
        assert result == Decimal("0")

    def test_safe_average_all_none_values(self):
        """Test safe_average with all None values - covers lines 138-141"""
        result = FinancialCalculator.safe_average([None, None, None])
        assert result == Decimal("0")

    def test_safe_average_mixed_with_none(self):
        """Test safe_average filtering None values - covers line 138"""
        values = [100, None, 200, None, 300]
        result = FinancialCalculator.safe_average(values)
        assert result == Decimal("200.00")

    def test_safe_average_decimal_precision(self):
        """Test safe_average with decimal precision - covers lines 143-146"""
        values = [100, 200, 250]
        result = FinancialCalculator.safe_average(values)
        assert result == Decimal("183.33")  # (550/3 = 183.33)

    def test_safe_sum_basic(self):
        """Test safe_sum with normal values - covers lines 159-160"""
        values = [100, 200, 300]
        result = FinancialCalculator.safe_sum(values)
        assert result == Decimal("600.00")

    def test_safe_sum_with_none_values(self):
        """Test safe_sum filtering None values - covers line 159"""
        values = [100, None, 200, None, 300]
        result = FinancialCalculator.safe_sum(values)
        assert result == Decimal("600.00")

    def test_format_currency_basic(self):
        """Test format_currency with default symbol - covers lines 237-238"""
        result = FinancialCalculator.format_currency(1234.567)
        assert result == "$1,234.57"

    def test_format_currency_custom_symbol(self):
        """Test format_currency with custom symbol - covers lines 237-238"""
        result = FinancialCalculator.format_currency(1234.567, currency_symbol="€")
        assert result == "€1,234.57"

    def test_format_currency_large_number(self):
        """Test format_currency with large number - covers lines 237-238"""
        result = FinancialCalculator.format_currency(1234567.89)
        assert result == "$1,234,567.89"

    def test_format_percentage_basic(self):
        """Test format_percentage - covers lines 251-252"""
        result = FinancialCalculator.format_percentage(0.1234)
        assert result == "0.12%"  # Format expects decimal input (0.1234 -> 0.12%)

    def test_format_percentage_whole_number(self):
        """Test format_percentage with whole number - covers lines 251-252"""
        result = FinancialCalculator.format_percentage(1)
        assert result == "1.00%"  # Format expects decimal input (1 -> 1.00%)

    def test_format_percentage_zero(self):
        """Test format_percentage with zero - covers lines 251-252"""
        result = FinancialCalculator.format_percentage(0)
        assert result == "0.00%"


class TestValidationUtils:
    """Test ValidationUtils utility functions"""

    def test_normalize_currency_basic(self):
        """Test basic currency normalization"""
        assert ValidationUtils.normalize_currency("123.45") == Decimal("123.45")
        assert ValidationUtils.normalize_currency(100) == Decimal("100")
        assert ValidationUtils.normalize_currency(99.99) == Decimal("99.99")

    def test_normalize_currency_string_cleanup(self):
        """Test currency normalization with string cleanup"""
        assert ValidationUtils.normalize_currency("$123.45") == Decimal("123.45")
        assert ValidationUtils.normalize_currency("€1,234.56") == Decimal("1234.56")

    def test_normalize_currency_invalid(self):
        """Test currency normalization with invalid input"""
        assert ValidationUtils.normalize_currency("invalid") is None
        assert ValidationUtils.normalize_currency("") is None
        assert ValidationUtils.normalize_currency(None) is None

    def test_email_pattern_validation(self):
        """Test email pattern validation"""
        # Valid emails
        assert ValidationUtils.EMAIL_PATTERN.match("user@example.com") is not None
        assert ValidationUtils.EMAIL_PATTERN.match("test@domain.co.uk") is not None

        # Invalid emails
        assert ValidationUtils.EMAIL_PATTERN.match("invalid-email") is None
        assert ValidationUtils.EMAIL_PATTERN.match("@domain.com") is None
        assert ValidationUtils.EMAIL_PATTERN.match("user@") is None

    def test_phone_pattern_validation(self):
        """Test phone pattern validation"""
        # Valid phone numbers
        assert ValidationUtils.PHONE_PATTERN.match("+1234567890") is not None
        assert ValidationUtils.PHONE_PATTERN.match("123-456-7890") is not None
        assert ValidationUtils.PHONE_PATTERN.match("(123) 456-7890") is not None

        # Invalid phone numbers
        assert ValidationUtils.PHONE_PATTERN.match("abc") is None
        assert ValidationUtils.PHONE_PATTERN.match("123") is None  # too short

    def test_sku_pattern_validation(self):
        """Test SKU pattern validation"""
        # Valid SKUs
        assert ValidationUtils.SKU_PATTERN.match("ABC123") is not None
        assert ValidationUtils.SKU_PATTERN.match("NIKE-001") is not None
        assert ValidationUtils.SKU_PATTERN.match("555088-101") is not None

        # Invalid SKUs
        assert ValidationUtils.SKU_PATTERN.match("ab") is None  # too short
        assert ValidationUtils.SKU_PATTERN.match("lowercase") is None  # lowercase
        assert ValidationUtils.SKU_PATTERN.match("SKU WITH SPACES") is None  # spaces


class TestFinancialIntegration:
    """Integration tests for financial calculations"""

    def test_full_transaction_calculation(self):
        """Test complete transaction profit calculation"""
        # Simulate a full StockX transaction
        sale_price = Decimal("220.00")
        purchase_price = Decimal("150.00")
        seller_fee = Decimal("20.90")
        processing_fee = Decimal("6.60")
        other_fees = Decimal("13.95")

        # Calculate net proceeds
        net_proceeds = FinancialCalculator.calculate_net_proceeds(
            sale_price, seller_fee, processing_fee, other_fees
        )
        expected_proceeds = Decimal("178.55")  # 220 - 41.45
        assert net_proceeds == expected_proceeds

        # Calculate net profit
        net_profit = FinancialCalculator.calculate_net_profit(net_proceeds, purchase_price)
        expected_profit = Decimal("28.55")  # 178.55 - 150
        assert net_profit == expected_profit

        # Calculate margin
        margin = FinancialCalculator.calculate_margin(purchase_price, sale_price)
        assert margin > Decimal("30")  # Should be around 31-32%

    def test_breakeven_scenario(self):
        """Test breakeven transaction scenario"""
        sale_price = Decimal("100.00")
        purchase_price = Decimal("85.00")
        seller_fee = Decimal("15.00")

        net_proceeds = FinancialCalculator.calculate_net_proceeds(sale_price, seller_fee)
        net_profit = FinancialCalculator.calculate_net_profit(net_proceeds, purchase_price)

        assert net_proceeds == Decimal("85.00")
        assert net_profit == Decimal("0.00")

    def test_loss_scenario(self):
        """Test transaction resulting in loss"""
        sale_price = Decimal("100.00")
        purchase_price = Decimal("90.00")
        seller_fee = Decimal("15.00")

        net_proceeds = FinancialCalculator.calculate_net_proceeds(sale_price, seller_fee)
        net_profit = FinancialCalculator.calculate_net_profit(net_proceeds, purchase_price)

        assert net_proceeds == Decimal("85.00")
        assert net_profit == Decimal("-5.00")