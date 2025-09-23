"""
Financial Utilities
Safe financial calculations using Decimal for precision
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Union


class FinancialCalculator:
    """
    Utility class for safe financial calculations using Decimal precision
    All monetary values should be handled with Decimal to avoid floating-point errors
    """

    # Standard rounding for currency (2 decimal places)
    CURRENCY_PRECISION = Decimal('0.01')

    # Standard rounding for percentages (2 decimal places)
    PERCENTAGE_PRECISION = Decimal('0.01')

    # High precision for calculations (4 decimal places)
    CALCULATION_PRECISION = Decimal('0.0001')

    @staticmethod
    def to_decimal(value: Union[str, int, float, Decimal, None]) -> Decimal:
        """
        Convert various numeric types to Decimal safely

        Args:
            value: The value to convert

        Returns:
            Decimal representation of the value, or Decimal('0') if None/invalid
        """
        if value is None:
            return Decimal('0')

        if isinstance(value, Decimal):
            return value

        try:
            # Convert to string first to avoid float precision issues
            return Decimal(str(value))
        except (ValueError, TypeError):
            return Decimal('0')

    @classmethod
    def to_currency(cls, value: Union[str, int, float, Decimal, None]) -> Decimal:
        """
        Convert value to currency format (2 decimal places)

        Args:
            value: The value to convert

        Returns:
            Decimal rounded to 2 decimal places
        """
        decimal_value = cls.to_decimal(value)
        return decimal_value.quantize(cls.CURRENCY_PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def to_percentage(cls, value: Union[str, int, float, Decimal, None]) -> Decimal:
        """
        Convert value to percentage format (2 decimal places)

        Args:
            value: The value to convert

        Returns:
            Decimal rounded to 2 decimal places for percentage
        """
        decimal_value = cls.to_decimal(value)
        return decimal_value.quantize(cls.PERCENTAGE_PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_margin(cls, cost: Union[str, int, float, Decimal],
                        sale_price: Union[str, int, float, Decimal]) -> Decimal:
        """
        Calculate profit margin percentage

        Args:
            cost: The cost/buy price
            sale_price: The sale price

        Returns:
            Margin percentage as Decimal
        """
        cost_decimal = cls.to_decimal(cost)
        sale_decimal = cls.to_decimal(sale_price)

        if sale_decimal == 0:
            return Decimal('0')

        profit = sale_decimal - cost_decimal
        margin = (profit / sale_decimal) * Decimal('100')

        return cls.to_percentage(margin)

    @classmethod
    def calculate_roi(cls, cost: Union[str, int, float, Decimal],
                     profit: Union[str, int, float, Decimal]) -> Decimal:
        """
        Calculate Return on Investment (ROI) percentage

        Args:
            cost: The initial cost/investment
            profit: The profit amount

        Returns:
            ROI percentage as Decimal
        """
        cost_decimal = cls.to_decimal(cost)
        profit_decimal = cls.to_decimal(profit)

        if cost_decimal == 0:
            return Decimal('0')

        roi = (profit_decimal / cost_decimal) * Decimal('100')

        return cls.to_percentage(roi)

    @classmethod
    def safe_average(cls, values: List[Union[str, int, float, Decimal, None]]) -> Decimal:
        """
        Calculate average of numeric values safely

        Args:
            values: List of numeric values

        Returns:
            Average as Decimal, or Decimal('0') if empty list
        """
        if not values:
            return Decimal('0')

        decimal_values = [cls.to_decimal(v) for v in values if v is not None]

        if not decimal_values:
            return Decimal('0')

        total = sum(decimal_values)
        count = Decimal(str(len(decimal_values)))

        return cls.to_currency(total / count)

    @classmethod
    def safe_sum(cls, values: List[Union[str, int, float, Decimal, None]]) -> Decimal:
        """
        Calculate sum of numeric values safely

        Args:
            values: List of numeric values

        Returns:
            Sum as Decimal
        """
        decimal_values = [cls.to_decimal(v) for v in values if v is not None]
        return cls.to_currency(sum(decimal_values))

    @classmethod
    def calculate_net_proceeds(cls, sale_price: Union[str, int, float, Decimal],
                              seller_fee: Union[str, int, float, Decimal] = 0,
                              processing_fee: Union[str, int, float, Decimal] = 0,
                              other_fees: Union[str, int, float, Decimal] = 0) -> Decimal:
        """
        Calculate net proceeds after fees

        Args:
            sale_price: Gross sale price
            seller_fee: Seller fee amount
            processing_fee: Processing fee amount
            other_fees: Other fees amount

        Returns:
            Net proceeds as Decimal
        """
        sale_decimal = cls.to_decimal(sale_price)
        fee_total = (cls.to_decimal(seller_fee) +
                    cls.to_decimal(processing_fee) +
                    cls.to_decimal(other_fees))

        net_proceeds = sale_decimal - fee_total

        return cls.to_currency(net_proceeds)

    @classmethod
    def calculate_gross_profit(cls, sale_price: Union[str, int, float, Decimal],
                              cost: Union[str, int, float, Decimal]) -> Decimal:
        """
        Calculate gross profit

        Args:
            sale_price: Sale price
            cost: Original cost

        Returns:
            Gross profit as Decimal
        """
        sale_decimal = cls.to_decimal(sale_price)
        cost_decimal = cls.to_decimal(cost)

        return cls.to_currency(sale_decimal - cost_decimal)

    @classmethod
    def calculate_net_profit(cls, net_proceeds: Union[str, int, float, Decimal],
                            cost: Union[str, int, float, Decimal]) -> Decimal:
        """
        Calculate net profit after all fees

        Args:
            net_proceeds: Net proceeds after fees
            cost: Original cost

        Returns:
            Net profit as Decimal
        """
        proceeds_decimal = cls.to_decimal(net_proceeds)
        cost_decimal = cls.to_decimal(cost)

        return cls.to_currency(proceeds_decimal - cost_decimal)

    @classmethod
    def format_currency(cls, value: Union[str, int, float, Decimal, None],
                       currency_symbol: str = "$") -> str:
        """
        Format value as currency string

        Args:
            value: The value to format
            currency_symbol: Currency symbol to use

        Returns:
            Formatted currency string
        """
        decimal_value = cls.to_currency(value)
        return f"{currency_symbol}{decimal_value:,.2f}"

    @classmethod
    def format_percentage(cls, value: Union[str, int, float, Decimal, None]) -> str:
        """
        Format value as percentage string

        Args:
            value: The value to format

        Returns:
            Formatted percentage string
        """
        decimal_value = cls.to_percentage(value)
        return f"{decimal_value}%"