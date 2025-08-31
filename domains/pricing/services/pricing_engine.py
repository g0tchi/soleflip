"""
Pricing Engine - Core pricing calculation and strategy implementation
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Brand, InventoryItem, Product

from ..models import BrandMultiplier, MarketPrice, PriceHistory, PriceRule
from ..repositories.pricing_repository import PricingRepository


class PricingStrategy(Enum):
    """Available pricing strategies"""

    COST_PLUS = "cost_plus"
    MARKET_BASED = "market_based"
    COMPETITIVE = "competitive"
    VALUE_BASED = "value_based"
    DYNAMIC = "dynamic"


@dataclass
class PricingContext:
    """Context data for pricing calculations"""

    product: Product
    inventory_item: Optional[InventoryItem] = None
    platform_id: Optional[uuid.UUID] = None
    condition: str = "new"
    size: Optional[str] = None
    target_margin: Optional[Decimal] = None
    market_data: Optional[Dict[str, Any]] = None
    competitor_data: Optional[Dict[str, Any]] = None


@dataclass
class PricingResult:
    """Result of pricing calculation"""

    suggested_price: Decimal
    strategy_used: PricingStrategy
    confidence_score: Decimal
    margin_percent: Decimal
    markup_percent: Decimal
    reasoning: List[str]
    market_position: Optional[str] = None
    price_range: Optional[Dict[str, Decimal]] = None
    adjustments_applied: Optional[List[Dict[str, Any]]] = None


class PricingEngine:
    """Advanced pricing engine with multiple strategies and rules"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.repository = PricingRepository(db_session)

    # =====================================================
    # MAIN PRICING METHODS
    # =====================================================

    async def calculate_optimal_price(
        self, context: PricingContext, strategies: Optional[List[PricingStrategy]] = None
    ) -> PricingResult:
        """Calculate optimal price using multiple strategies and rules"""
        if not strategies:
            strategies = [
                PricingStrategy.MARKET_BASED,
                PricingStrategy.COMPETITIVE,
                PricingStrategy.COST_PLUS,
            ]

        # Get applicable pricing rules
        pricing_rules = await self._get_applicable_rules(context)

        # Calculate prices using different strategies
        strategy_results = {}
        for strategy in strategies:
            try:
                result = await self._calculate_strategy_price(context, strategy, pricing_rules)
                strategy_results[strategy] = result
            except Exception as e:
                continue

        if not strategy_results:
            # Fallback to cost-plus if no strategies work
            return await self._calculate_cost_plus_price(context, pricing_rules)

        # Select best strategy based on confidence and market conditions
        best_result = self._select_best_pricing_result(strategy_results, context)

        # Apply final adjustments
        final_result = await self._apply_final_adjustments(best_result, context, pricing_rules)

        return final_result

    async def _get_applicable_rules(self, context: PricingContext) -> List[PriceRule]:
        """Get pricing rules applicable to the context"""
        return await self.repository.get_active_price_rules(
            brand_id=context.product.brand_id,
            category_id=context.product.category_id,
            platform_id=context.platform_id,
        )

    async def _calculate_strategy_price(
        self, context: PricingContext, strategy: PricingStrategy, rules: List[PriceRule]
    ) -> PricingResult:
        """Calculate price using specific strategy"""
        if strategy == PricingStrategy.COST_PLUS:
            return await self._calculate_cost_plus_price(context, rules)
        elif strategy == PricingStrategy.MARKET_BASED:
            return await self._calculate_market_based_price(context, rules)
        elif strategy == PricingStrategy.COMPETITIVE:
            return await self._calculate_competitive_price(context, rules)
        elif strategy == PricingStrategy.VALUE_BASED:
            return await self._calculate_value_based_price(context, rules)
        elif strategy == PricingStrategy.DYNAMIC:
            return await self._calculate_dynamic_price(context, rules)
        else:
            raise ValueError(f"Unknown pricing strategy: {strategy}")

    # =====================================================
    # PRICING STRATEGIES IMPLEMENTATION
    # =====================================================

    async def _calculate_cost_plus_price(
        self, context: PricingContext, rules: List[PriceRule]
    ) -> PricingResult:
        """Cost-plus pricing strategy"""
        reasoning = ["Using cost-plus pricing strategy"]

        # Get base cost
        if context.inventory_item and context.inventory_item.purchase_price:
            base_cost = context.inventory_item.purchase_price
            reasoning.append(f"Base cost from inventory item: €{base_cost}")
        else:
            # Estimate cost from historical data or category averages
            base_cost = await self._estimate_product_cost(context.product)
            reasoning.append(f"Estimated base cost: €{base_cost}")

        # Find applicable cost-plus rules
        cost_plus_rules = [r for r in rules if r.rule_type == "cost_plus"]

        if cost_plus_rules:
            rule = cost_plus_rules[0]  # Use highest priority rule
            markup_percent = rule.base_markup_percent or Decimal("25.0")
            reasoning.append(f"Applied pricing rule '{rule.name}' with {markup_percent}% markup")
        else:
            markup_percent = context.target_margin or Decimal("25.0")
            reasoning.append(f"Using default markup of {markup_percent}%")

        # Calculate base price
        suggested_price = base_cost * (Decimal("1") + markup_percent / Decimal("100"))

        # Apply brand multipliers
        suggested_price, brand_adjustments = await self._apply_brand_multipliers(
            suggested_price, context.product.brand_id
        )
        reasoning.extend([f"Brand adjustment: {adj}" for adj in brand_adjustments])

        # Apply condition adjustments
        condition_multiplier = await self._get_condition_multiplier(context.condition, rules)
        if condition_multiplier != Decimal("1.0"):
            suggested_price *= condition_multiplier
            reasoning.append(f"Condition '{context.condition}' multiplier: {condition_multiplier}")

        # Calculate margins
        margin_percent = (
            (suggested_price - base_cost) / suggested_price * Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return PricingResult(
            suggested_price=suggested_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            strategy_used=PricingStrategy.COST_PLUS,
            confidence_score=Decimal("0.85"),  # Cost-plus is reliable but not optimal
            margin_percent=margin_percent,
            markup_percent=markup_percent,
            reasoning=reasoning,
        )

    async def _calculate_market_based_price(
        self, context: PricingContext, rules: List[PriceRule]
    ) -> PricingResult:
        """Market-based pricing using external market data"""
        reasoning = ["Using market-based pricing strategy"]

        # Get market data
        market_prices = await self.repository.get_market_prices(
            context.product.id, condition=context.condition, days_back=14
        )

        if not market_prices:
            raise ValueError("No market data available for market-based pricing")

        # Calculate market average
        valid_prices = [mp.last_sale for mp in market_prices if mp.last_sale]
        if not valid_prices:
            valid_prices = [mp.average_price for mp in market_prices if mp.average_price]

        if not valid_prices:
            raise ValueError("No valid market prices available")

        market_average = sum(valid_prices) / len(valid_prices)
        reasoning.append(f"Market average from {len(valid_prices)} data points: €{market_average}")

        # Find market-based rules
        market_rules = [r for r in rules if r.rule_type == "market_based"]

        # Apply positioning strategy
        if market_rules:
            rule = market_rules[0]
            if rule.seasonal_adjustments:
                seasonal_adj = rule.get_seasonal_adjustment(datetime.now().month)
                market_average *= seasonal_adj
                reasoning.append(
                    f"Seasonal adjustment for month {datetime.now().month}: {seasonal_adj}"
                )

        # Position slightly below market for competitive advantage
        suggested_price = market_average * Decimal("0.98")  # 2% below market
        reasoning.append("Positioned 2% below market average for competitiveness")

        # Ensure minimum margins are met
        base_cost = await self._estimate_product_cost(context.product)
        min_margin = Decimal("15.0")  # 15% minimum margin
        min_price = base_cost / (Decimal("1") - min_margin / Decimal("100"))

        if suggested_price < min_price:
            suggested_price = min_price
            reasoning.append(f"Adjusted to meet minimum {min_margin}% margin requirement")

        margin_percent = (
            (suggested_price - base_cost) / suggested_price * Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        markup_percent = ((suggested_price - base_cost) / base_cost * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return PricingResult(
            suggested_price=suggested_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            strategy_used=PricingStrategy.MARKET_BASED,
            confidence_score=Decimal("0.90"),
            margin_percent=margin_percent,
            markup_percent=markup_percent,
            reasoning=reasoning,
            market_position="slightly_below_market",
        )

    async def _calculate_competitive_price(
        self, context: PricingContext, rules: List[PriceRule]
    ) -> PricingResult:
        """Competitive pricing based on competitor analysis"""
        reasoning = ["Using competitive pricing strategy"]

        # Get competitive pricing data
        competitive_data = await self.repository.get_competitive_pricing_data(
            context.product.id, context.condition
        )

        if not competitive_data or not competitive_data.get("platforms"):
            raise ValueError("No competitive data available")

        platforms = competitive_data["platforms"]
        reasoning.append(f"Analyzing {len(platforms)} competitor platforms")

        # Extract competitive prices
        competitor_prices = []
        for platform, data in platforms.items():
            if data.get("last_sale"):
                competitor_prices.append(data["last_sale"])
            elif data.get("lowest_ask"):
                competitor_prices.append(data["lowest_ask"])

        if not competitor_prices:
            raise ValueError("No valid competitive prices found")

        # Calculate competitive positioning
        min_competitor = min(competitor_prices)
        max_competitor = max(competitor_prices)
        avg_competitor = sum(competitor_prices) / len(competitor_prices)

        reasoning.append(f"Competitor range: €{min_competitor:.2f} - €{max_competitor:.2f}")
        reasoning.append(f"Competitor average: €{avg_competitor:.2f}")

        # Strategic positioning - aim for competitive but profitable
        competitive_rules = [r for r in rules if r.rule_type == "competitive"]

        if competitive_rules and competitive_rules[0].maximum_discount_percent:
            max_discount = competitive_rules[0].maximum_discount_percent
            suggested_price = min_competitor * (Decimal("1") - max_discount / Decimal("100"))
            reasoning.append(f"Positioned {max_discount}% below lowest competitor")
        else:
            # Default: position between lowest and average competitor
            suggested_price = (min_competitor + avg_competitor) / Decimal("2")
            reasoning.append("Positioned between lowest competitor and market average")

        # Ensure profitability
        base_cost = await self._estimate_product_cost(context.product)
        min_margin = Decimal("10.0")  # 10% minimum for competitive pricing
        min_price = base_cost / (Decimal("1") - min_margin / Decimal("100"))

        if suggested_price < min_price:
            suggested_price = min_price
            reasoning.append(f"Adjusted to meet minimum {min_margin}% margin requirement")

        margin_percent = (
            (suggested_price - base_cost) / suggested_price * Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        markup_percent = ((suggested_price - base_cost) / base_cost * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return PricingResult(
            suggested_price=suggested_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            strategy_used=PricingStrategy.COMPETITIVE,
            confidence_score=Decimal("0.88"),
            margin_percent=margin_percent,
            markup_percent=markup_percent,
            reasoning=reasoning,
            market_position="competitive_positioning",
            price_range={
                "min_competitor": Decimal(str(min_competitor)),
                "max_competitor": Decimal(str(max_competitor)),
                "avg_competitor": Decimal(str(avg_competitor)),
            },
        )

    async def _calculate_value_based_price(
        self, context: PricingContext, rules: List[PriceRule]
    ) -> PricingResult:
        """Value-based pricing considering brand premium and demand"""
        reasoning = ["Using value-based pricing strategy"]

        # Start with market-based price as baseline
        try:
            market_result = await self._calculate_market_based_price(context, rules)
            base_price = market_result.suggested_price
            reasoning.append(f"Market baseline: €{base_price}")
        except ValueError:
            # Fallback to cost-plus
            cost_result = await self._calculate_cost_plus_price(context, rules)
            base_price = cost_result.suggested_price
            reasoning.append(f"Cost-plus baseline: €{base_price}")

        # Apply brand premium
        brand_premium = await self._calculate_brand_premium(context.product.brand_id)
        if brand_premium > Decimal("1.0"):
            base_price *= brand_premium
            reasoning.append(f"Brand premium applied: {((brand_premium - 1) * 100):.1f}%")

        # Apply demand-based adjustment
        demand_adjustment = await self._calculate_demand_adjustment(context.product.id)
        base_price *= demand_adjustment
        if demand_adjustment > Decimal("1.0"):
            reasoning.append(f"High demand premium: {((demand_adjustment - 1) * 100):.1f}%")
        else:
            reasoning.append(f"Low demand discount: {((1 - demand_adjustment) * 100):.1f}%")

        # Consider scarcity/exclusivity
        scarcity_multiplier = await self._calculate_scarcity_multiplier(context.product.id)
        if scarcity_multiplier > Decimal("1.0"):
            base_price *= scarcity_multiplier
            reasoning.append(f"Scarcity premium: {((scarcity_multiplier - 1) * 100):.1f}%")

        suggested_price = base_price

        # Calculate final margins
        base_cost = await self._estimate_product_cost(context.product)
        margin_percent = (
            (suggested_price - base_cost) / suggested_price * Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        markup_percent = ((suggested_price - base_cost) / base_cost * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return PricingResult(
            suggested_price=suggested_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            strategy_used=PricingStrategy.VALUE_BASED,
            confidence_score=Decimal("0.82"),
            margin_percent=margin_percent,
            markup_percent=markup_percent,
            reasoning=reasoning,
            market_position="value_premium",
        )

    async def _calculate_dynamic_price(
        self, context: PricingContext, rules: List[PriceRule]
    ) -> PricingResult:
        """Dynamic pricing combining multiple factors"""
        reasoning = ["Using dynamic pricing strategy"]

        # Calculate prices using multiple strategies
        strategies_to_try = [
            PricingStrategy.MARKET_BASED,
            PricingStrategy.COMPETITIVE,
            PricingStrategy.VALUE_BASED,
        ]

        strategy_prices = {}
        for strategy in strategies_to_try:
            try:
                result = await self._calculate_strategy_price(context, strategy, rules)
                strategy_prices[strategy] = result.suggested_price
            except ValueError:
                continue

        if not strategy_prices:
            # Fallback to cost-plus
            return await self._calculate_cost_plus_price(context, rules)

        # Weighted average of strategies
        weights = {
            PricingStrategy.MARKET_BASED: Decimal("0.4"),
            PricingStrategy.COMPETITIVE: Decimal("0.35"),
            PricingStrategy.VALUE_BASED: Decimal("0.25"),
        }

        weighted_sum = sum(
            price * weights.get(strategy, Decimal("0.3"))
            for strategy, price in strategy_prices.items()
        )
        total_weight = sum(
            weights.get(strategy, Decimal("0.3")) for strategy in strategy_prices.keys()
        )

        suggested_price = weighted_sum / total_weight
        reasoning.append(f"Weighted average of {len(strategy_prices)} strategies")

        # Apply real-time adjustments
        velocity_adj = await self._get_velocity_adjustment(context.product.id)
        suggested_price *= velocity_adj
        if velocity_adj != Decimal("1.0"):
            reasoning.append(f"Inventory velocity adjustment: {((velocity_adj - 1) * 100):.1f}%")

        # Calculate margins
        base_cost = await self._estimate_product_cost(context.product)
        margin_percent = (
            (suggested_price - base_cost) / suggested_price * Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        markup_percent = ((suggested_price - base_cost) / base_cost * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return PricingResult(
            suggested_price=suggested_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            strategy_used=PricingStrategy.DYNAMIC,
            confidence_score=Decimal("0.92"),
            margin_percent=margin_percent,
            markup_percent=markup_percent,
            reasoning=reasoning,
            market_position="dynamic_optimal",
        )

    # =====================================================
    # HELPER METHODS
    # =====================================================

    def _select_best_pricing_result(
        self, results: Dict[PricingStrategy, PricingResult], context: PricingContext
    ) -> PricingResult:
        """Select best pricing result based on confidence and context"""
        # Weight results by confidence score and strategy preference
        strategy_weights = {
            PricingStrategy.DYNAMIC: 1.0,
            PricingStrategy.MARKET_BASED: 0.9,
            PricingStrategy.VALUE_BASED: 0.85,
            PricingStrategy.COMPETITIVE: 0.8,
            PricingStrategy.COST_PLUS: 0.7,
        }

        best_score = 0
        best_result = None

        for strategy, result in results.items():
            score = float(result.confidence_score) * strategy_weights.get(strategy, 0.5)
            if score > best_score:
                best_score = score
                best_result = result

        return best_result or list(results.values())[0]

    async def _apply_final_adjustments(
        self, result: PricingResult, context: PricingContext, rules: List[PriceRule]
    ) -> PricingResult:
        """Apply final rule-based adjustments"""
        adjustments = []
        final_price = result.suggested_price

        # Apply minimum/maximum constraints from rules
        for rule in rules:
            if rule.minimum_margin_percent:
                base_cost = await self._estimate_product_cost(context.product)
                min_price = base_cost / (
                    Decimal("1") - rule.minimum_margin_percent / Decimal("100")
                )
                if final_price < min_price:
                    final_price = min_price
                    adjustments.append(
                        {
                            "type": "minimum_margin",
                            "rule": rule.name,
                            "adjustment": f"Raised to meet {rule.minimum_margin_percent}% margin",
                        }
                    )

        # Round to psychological pricing points
        final_price = self._apply_psychological_pricing(final_price)
        if final_price != result.suggested_price:
            adjustments.append(
                {
                    "type": "psychological_pricing",
                    "adjustment": "Rounded to psychological price point",
                }
            )

        # Update result with adjustments
        if adjustments:
            result.adjustments_applied = adjustments
            result.suggested_price = final_price
            result.reasoning.append("Applied final rule-based adjustments")

        return result

    async def _apply_brand_multipliers(
        self, base_price: Decimal, brand_id: uuid.UUID
    ) -> Tuple[Decimal, List[str]]:
        """Apply brand-specific multipliers"""
        multipliers = await self.repository.get_brand_multipliers(brand_id)
        adjustments = []
        final_price = base_price

        for multiplier in multipliers:
            if multiplier.is_effective():
                final_price *= multiplier.multiplier_value
                adjustments.append(
                    f"{multiplier.multiplier_type} multiplier: {multiplier.multiplier_value}"
                )

        return final_price, adjustments

    async def _estimate_product_cost(self, product: Product) -> Decimal:
        """Estimate product cost from various sources"""
        # Try to get from recent price history
        recent_purchase = await self.repository.get_latest_price(product.id, price_type="purchase")

        if recent_purchase:
            return recent_purchase.price_amount

        # Fallback to category/brand averages or market estimates
        market_prices = await self.repository.get_market_prices(product.id, days_back=30)
        if market_prices:
            avg_market = sum(
                mp.last_sale or mp.average_price or Decimal("0") for mp in market_prices
            ) / len(market_prices)
            # Estimate cost as 60-70% of market price
            return avg_market * Decimal("0.65")

        # Default fallback
        return Decimal("50.00")

    def _apply_psychological_pricing(self, price: Decimal) -> Decimal:
        """Apply psychological pricing rules (e.g., .99, .95 endings)"""
        if price < Decimal("20"):
            # For low prices, use .95 endings
            return (price.quantize(Decimal("1")) - Decimal("0.05")).max(Decimal("0.95"))
        elif price < Decimal("100"):
            # For medium prices, use .99 endings
            return (price.quantize(Decimal("1")) - Decimal("0.01")).max(Decimal("0.99"))
        else:
            # For high prices, round to nearest 5 or 10
            rounded = (price / Decimal("5")).quantize(Decimal("1")) * Decimal("5")
            return rounded.max(Decimal("5"))

    async def _get_condition_multiplier(self, condition: str, rules: List[PriceRule]) -> Decimal:
        """Get condition-based price multiplier"""
        condition_multipliers = {
            "new": Decimal("1.0"),
            "excellent": Decimal("0.92"),
            "very_good": Decimal("0.85"),
            "good": Decimal("0.75"),
            "fair": Decimal("0.65"),
            "poor": Decimal("0.50"),
        }

        # Check for rule-specific multipliers
        for rule in rules:
            if rule.condition_multipliers and condition in rule.condition_multipliers:
                return Decimal(str(rule.condition_multipliers[condition]))

        return condition_multipliers.get(condition, Decimal("1.0"))

    async def _calculate_brand_premium(self, brand_id: uuid.UUID) -> Decimal:
        """Calculate brand premium multiplier"""
        # This would typically be based on brand intelligence data
        # For now, return default premiums based on brand characteristics
        return Decimal("1.1")  # 10% premium as default

    async def _calculate_demand_adjustment(self, product_id: uuid.UUID) -> Decimal:
        """Calculate demand-based price adjustment"""
        # This would analyze sales velocity, search trends, etc.
        return Decimal("1.0")  # Neutral adjustment as default

    async def _calculate_scarcity_multiplier(self, product_id: uuid.UUID) -> Decimal:
        """Calculate scarcity-based price multiplier"""
        # This would analyze inventory levels, product lifecycle, etc.
        return Decimal("1.0")  # No scarcity premium as default

    async def _get_velocity_adjustment(self, product_id: uuid.UUID) -> Decimal:
        """Get inventory velocity-based adjustment"""
        # Fast-moving items might get slight discount to maintain velocity
        # Slow-moving items might get premium to improve margins
        return Decimal("1.0")  # Neutral as default
