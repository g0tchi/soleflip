"""
Smart Pricing Service - Advanced StockX-integrated pricing automation
Combines real-time market data with intelligent pricing strategies
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import structlog
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from domains.integration.services.stockx_service import StockXService
from domains.inventory.services.inventory_service import InventoryService
from shared.database.models import InventoryItem, Product
from shared.caching.dashboard_cache import get_dashboard_cache

from ..models import MarketPrice
from ..services.pricing_engine import PricingEngine, PricingContext, PricingStrategy

logger = structlog.get_logger(__name__)


class MarketCondition:
    """Market condition analysis"""
    BULLISH = "bullish"      # Rising prices, high demand
    BEARISH = "bearish"      # Falling prices, low demand  
    STABLE = "stable"        # Steady prices, moderate demand
    VOLATILE = "volatile"    # Rapid price swings


class SmartPricingService:
    """
    Advanced pricing service that combines:
    - Real-time StockX market data
    - Machine learning-based price optimization
    - Dynamic repricing based on market conditions
    - Profit maximization algorithms
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.stockx_service = StockXService(db_session)
        self.pricing_engine = PricingEngine(db_session)
        self.inventory_service = InventoryService(db_session)
        self.cache = get_dashboard_cache()
    
    # =====================================================
    # SMART PRICING CORE METHODS
    # =====================================================
    
    async def optimize_inventory_pricing(
        self,
        inventory_items: Optional[List[InventoryItem]] = None,
        repricing_strategy: str = "profit_maximization"
    ) -> Dict[str, Any]:
        """
        Optimize pricing for entire inventory or specific items
        
        Strategies:
        - profit_maximization: Maximize profit margins
        - market_competitive: Stay competitive with market
        - quick_turnover: Price for fast sales
        - premium_positioning: Price as premium option
        """
        logger.info("Starting inventory pricing optimization", strategy=repricing_strategy)
        
        start_time = datetime.utcnow()
        
        if not inventory_items:
            # Get all active inventory items that need repricing
            inventory_items = await self._get_repriceable_inventory()
        
        optimization_results = {
            "total_items_processed": len(inventory_items),
            "successful_optimizations": 0,
            "pricing_updates": [],
            "potential_profit_increase": Decimal("0.00"),
            "market_insights": {},
            "processing_time_ms": 0
        }
        
        # Process items in batches to avoid API rate limits
        batch_size = 10
        for i in range(0, len(inventory_items), batch_size):
            batch = inventory_items[i:i + batch_size]
            batch_results = await self._optimize_batch_pricing(batch, repricing_strategy)
            
            # Aggregate results
            optimization_results["successful_optimizations"] += batch_results["successful_count"]
            optimization_results["pricing_updates"].extend(batch_results["updates"])
            optimization_results["potential_profit_increase"] += batch_results["profit_increase"]
            
            # Small delay to respect rate limits
            await asyncio.sleep(0.5)
        
        optimization_results["processing_time_ms"] = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )
        
        logger.info(
            "Inventory pricing optimization completed",
            items_processed=optimization_results["total_items_processed"],
            successful_updates=optimization_results["successful_optimizations"],
            profit_increase=str(optimization_results["potential_profit_increase"])
        )
        
        return optimization_results
    
    async def get_dynamic_price_recommendation(
        self, 
        inventory_item: InventoryItem,
        target_sell_timeframe: Optional[int] = None  # days
    ) -> Dict[str, Any]:
        """
        Get intelligent price recommendation for a specific item
        Considers market conditions, competition, and business objectives
        """
        logger.info("Generating dynamic price recommendation", item_id=str(inventory_item.id))
        
        # Get product and market data
        product_query = await self.db_session.execute(
            select(Product).where(Product.id == inventory_item.product_id)
        )
        product = product_query.scalar_one()
        
        # Fetch current market data from StockX
        market_data = await self._get_fresh_market_data(product, inventory_item.size)
        
        if not market_data:
            logger.warning("No market data available", product_id=str(product.id))
            return {"error": "Market data unavailable", "fallback_strategy": "cost_plus"}
        
        # Analyze market conditions
        market_condition = await self._analyze_market_condition(product.id, market_data)
        
        # Create pricing context
        context = PricingContext(
            product=product,
            inventory_item=inventory_item,
            size=inventory_item.size,
            market_data=market_data,
            target_margin=self._calculate_target_margin(market_condition, target_sell_timeframe)
        )
        
        # Get pricing recommendations using multiple strategies
        strategies = self._select_optimal_strategies(market_condition, target_sell_timeframe)
        pricing_result = await self.pricing_engine.calculate_optimal_price(context, strategies)
        
        # Calculate dynamic adjustments
        dynamic_adjustments = await self._calculate_dynamic_adjustments(
            inventory_item, market_data, market_condition
        )
        
        # Apply adjustments to base price
        final_price = self._apply_adjustments(pricing_result.suggested_price, dynamic_adjustments)
        
        recommendation = {
            "item_id": str(inventory_item.id),
            "current_price": float(inventory_item.current_price or 0),
            "recommended_price": float(final_price),
            "price_change_percent": self._calculate_price_change_percent(
                inventory_item.current_price, final_price
            ),
            "expected_margin_percent": float(pricing_result.margin_percent),
            "market_condition": market_condition,
            "confidence_score": float(pricing_result.confidence_score),
            "reasoning": pricing_result.reasoning + [f"Applied {len(dynamic_adjustments)} dynamic adjustments"],
            "market_data": {
                "highest_bid": market_data.get("highest_bid"),
                "lowest_ask": market_data.get("lowest_ask"),
                "last_sale": market_data.get("last_sale"),
                "market_position": self._calculate_market_position(final_price, market_data)
            },
            "adjustments_applied": dynamic_adjustments,
            "sell_probability": await self._calculate_sell_probability(final_price, market_data, target_sell_timeframe)
        }
        
        return recommendation
    
    async def implement_auto_repricing(
        self,
        repricing_rules: Dict[str, Any],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Implement automatic repricing based on market movements
        
        Rules example:
        {
            "price_drop_threshold": 5.0,  # % drop to trigger repricing
            "max_price_increase": 10.0,   # % max increase per adjustment
            "min_margin_percent": 15.0,   # Minimum margin to maintain
            "check_interval_hours": 6,    # How often to check
            "enabled_categories": ["footwear", "streetwear"]
        }
        """
        logger.info("Starting auto-repricing implementation", dry_run=dry_run)
        
        # Get items that meet repricing criteria
        eligible_items = await self._get_auto_repricing_candidates(repricing_rules)
        
        repricing_results = {
            "eligible_items": len(eligible_items),
            "repricing_actions": [],
            "total_adjustments": 0,
            "estimated_profit_impact": Decimal("0.00")
        }
        
        for item in eligible_items:
            try:
                # Get current market conditions
                recommendation = await self.get_dynamic_price_recommendation(item)
                
                # Determine if repricing is needed
                if self._should_reprice_item(item, recommendation, repricing_rules):
                    new_price = Decimal(str(recommendation["recommended_price"]))
                    
                    action = {
                        "item_id": str(item.id),
                        "current_price": float(item.current_price or 0),
                        "new_price": float(new_price),
                        "reason": recommendation["reasoning"][-1],
                        "expected_impact": float(new_price - (item.current_price or 0))
                    }
                    
                    if not dry_run:
                        # Actually update the price
                        success = await self.inventory_service.update_item_price(item.id, new_price)
                        action["implemented"] = success
                        
                        if success:
                            # Log price history
                            await self._log_price_change(item, new_price, "auto_repricing")
                    
                    repricing_results["repricing_actions"].append(action)
                    repricing_results["total_adjustments"] += 1
                    repricing_results["estimated_profit_impact"] += (new_price - (item.current_price or 0))
                    
            except Exception as e:
                logger.error("Failed to reprice item", item_id=str(item.id), error=str(e))
                continue
        
        logger.info(
            "Auto-repricing completed",
            eligible_items=repricing_results["eligible_items"],
            adjustments_made=repricing_results["total_adjustments"],
            profit_impact=str(repricing_results["estimated_profit_impact"])
        )
        
        return repricing_results
    
    # =====================================================
    # MARKET ANALYSIS METHODS
    # =====================================================
    
    async def analyze_market_trends(
        self, 
        product_ids: Optional[List[str]] = None,
        time_horizon_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze market trends for pricing insights
        """
        logger.info("Analyzing market trends", time_horizon_days=time_horizon_days)
        
        if not product_ids:
            # Get top products from inventory
            product_ids = await self._get_top_inventory_products(limit=20)
        
        trends_analysis = {
            "analysis_date": datetime.utcnow().isoformat(),
            "time_horizon_days": time_horizon_days,
            "product_trends": [],
            "market_summary": {
                "trending_up_count": 0,
                "trending_down_count": 0,
                "stable_count": 0,
                "average_price_change": 0.0
            }
        }
        
        for product_id in product_ids:
            try:
                trend_data = await self._analyze_product_trend(product_id, time_horizon_days)
                trends_analysis["product_trends"].append(trend_data)
                
                # Update market summary
                if trend_data["trend_direction"] == "up":
                    trends_analysis["market_summary"]["trending_up_count"] += 1
                elif trend_data["trend_direction"] == "down":  
                    trends_analysis["market_summary"]["trending_down_count"] += 1
                else:
                    trends_analysis["market_summary"]["stable_count"] += 1
                    
            except Exception as e:
                logger.error("Failed to analyze product trend", product_id=product_id, error=str(e))
                continue
        
        # Calculate average price change
        if trends_analysis["product_trends"]:
            avg_change = sum(
                trend["price_change_percent"] for trend in trends_analysis["product_trends"]
            ) / len(trends_analysis["product_trends"])
            trends_analysis["market_summary"]["average_price_change"] = round(avg_change, 2)
        
        return trends_analysis
    
    # =====================================================
    # HELPER METHODS
    # =====================================================
    
    async def _get_fresh_market_data(
        self, 
        product: Product, 
        size: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get fresh market data from StockX API"""
        cache_key = f"market_data_{product.id}_{size or 'all'}"
        
        # Check cache first (5 minute TTL for market data)
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Get fresh data from StockX
            market_data = await self.stockx_service.get_market_data_from_stockx(str(product.id))
            
            if market_data and size:
                # Filter for specific size
                size_data = next(
                    (item for item in market_data if item.get("size") == size), 
                    None
                )
                if size_data:
                    processed_data = {
                        "highest_bid": size_data.get("market", {}).get("highest_bid"),
                        "lowest_ask": size_data.get("market", {}).get("lowest_ask"),
                        "last_sale": size_data.get("market", {}).get("last_sale_price"),
                        "number_of_asks": size_data.get("market", {}).get("number_of_asks", 0),
                        "number_of_bids": size_data.get("market", {}).get("number_of_bids", 0),
                        "size": size
                    }
                    
                    # Cache for 5 minutes
                    await self.cache.set(cache_key, processed_data, ttl=300)
                    return processed_data
            
            return None
            
        except Exception as e:
            logger.error("Failed to fetch market data", product_id=str(product.id), error=str(e))
            return None
    
    async def _analyze_market_condition(
        self, 
        product_id: str, 
        current_market_data: Dict[str, Any]
    ) -> str:
        """Analyze current market condition for a product"""
        
        # Get historical price data
        historical_query = await self.db_session.execute(
            select(MarketPrice)
            .where(
                and_(
                    MarketPrice.product_id == product_id,
                    MarketPrice.recorded_at >= datetime.utcnow() - timedelta(days=7)
                )
            )
            .order_by(MarketPrice.recorded_at.desc())
        )
        historical_prices = historical_query.scalars().all()
        
        if len(historical_prices) < 3:
            return MarketCondition.STABLE  # Not enough data
        
        # Calculate price trend
        recent_prices = [p.lowest_ask for p in historical_prices[:5] if p.lowest_ask]
        if len(recent_prices) < 3:
            return MarketCondition.STABLE
        
        # Analyze price direction and volatility
        price_changes = [
            (recent_prices[i] - recent_prices[i+1]) / recent_prices[i+1] * 100
            for i in range(len(recent_prices) - 1)
        ]
        
        avg_change = sum(price_changes) / len(price_changes)
        volatility = sum(abs(change) for change in price_changes) / len(price_changes)
        
        # Determine market condition
        if volatility > 10:  # High volatility threshold
            return MarketCondition.VOLATILE
        elif avg_change > 3:  # Rising trend
            return MarketCondition.BULLISH
        elif avg_change < -3:  # Falling trend
            return MarketCondition.BEARISH
        else:
            return MarketCondition.STABLE
    
    def _calculate_target_margin(
        self, 
        market_condition: str, 
        target_timeframe: Optional[int] = None
    ) -> Decimal:
        """Calculate target margin based on market conditions and timeframe"""
        
        base_margin = Decimal("20.0")  # 20% base margin
        
        # Adjust for market conditions
        if market_condition == MarketCondition.BULLISH:
            margin_adjustment = Decimal("5.0")  # Increase margin in bull market
        elif market_condition == MarketCondition.BEARISH:
            margin_adjustment = Decimal("-3.0")  # Decrease margin to move inventory
        elif market_condition == MarketCondition.VOLATILE:
            margin_adjustment = Decimal("2.0")  # Slight premium for volatility
        else:
            margin_adjustment = Decimal("0.0")
        
        # Adjust for timeframe urgency
        if target_timeframe:
            if target_timeframe <= 7:  # Quick sale needed
                margin_adjustment -= Decimal("5.0")
            elif target_timeframe <= 30:  # Moderate urgency
                margin_adjustment -= Decimal("2.0")
        
        return max(base_margin + margin_adjustment, Decimal("10.0"))  # Minimum 10% margin
    
    def _select_optimal_strategies(
        self, 
        market_condition: str, 
        target_timeframe: Optional[int] = None
    ) -> List[PricingStrategy]:
        """Select optimal pricing strategies based on market conditions"""
        
        if market_condition == MarketCondition.BULLISH:
            return [PricingStrategy.VALUE_BASED, PricingStrategy.MARKET_BASED]
        elif market_condition == MarketCondition.BEARISH:
            return [PricingStrategy.COMPETITIVE, PricingStrategy.COST_PLUS]
        elif market_condition == MarketCondition.VOLATILE:
            return [PricingStrategy.DYNAMIC, PricingStrategy.COMPETITIVE]
        else:
            return [PricingStrategy.MARKET_BASED, PricingStrategy.COST_PLUS]
    
    async def _calculate_dynamic_adjustments(
        self,
        inventory_item: InventoryItem,
        market_data: Dict[str, Any],
        market_condition: str
    ) -> List[Dict[str, Any]]:
        """Calculate dynamic pricing adjustments"""
        
        adjustments = []
        
        # Inventory age adjustment
        if inventory_item.created_at:
            days_old = (datetime.utcnow() - inventory_item.created_at).days
            if days_old > 30:
                age_adjustment = min(days_old * 0.1, 5.0)  # Max 5% discount for age
                adjustments.append({
                    "type": "inventory_age",
                    "value": -age_adjustment,
                    "reason": f"Item is {days_old} days old"
                })
        
        # Market demand adjustment
        total_market_activity = market_data.get("number_of_asks", 0) + market_data.get("number_of_bids", 0)
        if total_market_activity > 100:  # High activity
            adjustments.append({
                "type": "high_demand",
                "value": 2.0,
                "reason": "High market activity detected"
            })
        elif total_market_activity < 10:  # Low activity
            adjustments.append({
                "type": "low_demand", 
                "value": -3.0,
                "reason": "Low market activity detected"
            })
        
        # Market condition adjustment
        if market_condition == MarketCondition.BULLISH:
            adjustments.append({
                "type": "bull_market_premium",
                "value": 3.0,
                "reason": "Bullish market conditions"
            })
        elif market_condition == MarketCondition.BEARISH:
            adjustments.append({
                "type": "bear_market_discount",
                "value": -4.0,
                "reason": "Bearish market conditions"  
            })
        
        return adjustments
    
    def _apply_adjustments(
        self, 
        base_price: Decimal, 
        adjustments: List[Dict[str, Any]]
    ) -> Decimal:
        """Apply percentage adjustments to base price"""
        
        total_adjustment_percent = sum(adj["value"] for adj in adjustments)
        adjustment_multiplier = Decimal("1.0") + (Decimal(str(total_adjustment_percent)) / Decimal("100.0"))
        
        return base_price * adjustment_multiplier
    
    def _calculate_price_change_percent(
        self, 
        current_price: Optional[Decimal], 
        new_price: Decimal
    ) -> float:
        """Calculate percentage change between current and new price"""
        
        if not current_price or current_price == 0:
            return 0.0
        
        change_percent = ((new_price - current_price) / current_price) * 100
        return round(float(change_percent), 2)
    
    def _calculate_market_position(
        self, 
        price: Decimal, 
        market_data: Dict[str, Any]
    ) -> str:
        """Calculate market position relative to bids/asks"""
        
        highest_bid = market_data.get("highest_bid")
        lowest_ask = market_data.get("lowest_ask")
        
        if not highest_bid or not lowest_ask:
            return "unknown"
        
        if price <= highest_bid:
            return "below_market"
        elif price >= lowest_ask:
            return "above_market"
        else:
            return "competitive"  # Between highest bid and lowest ask
    
    async def _calculate_sell_probability(
        self,
        price: Decimal,
        market_data: Dict[str, Any], 
        target_timeframe: Optional[int] = None
    ) -> float:
        """Calculate probability of selling at given price and timeframe"""
        
        # This is a simplified model - in production you'd use ML models
        base_probability = 0.5
        
        market_position = self._calculate_market_position(price, market_data)
        
        # Adjust for market position
        if market_position == "below_market":
            position_adjustment = 0.3
        elif market_position == "above_market":
            position_adjustment = -0.2
        else:
            position_adjustment = 0.1
        
        # Adjust for timeframe
        timeframe_adjustment = 0.0
        if target_timeframe:
            if target_timeframe <= 7:
                timeframe_adjustment = -0.1  # Less likely to sell quickly at good price
            elif target_timeframe >= 30:
                timeframe_adjustment = 0.2   # More likely with longer timeframe
        
        probability = max(0.0, min(1.0, base_probability + position_adjustment + timeframe_adjustment))
        return round(probability, 2)
    
    async def _get_repriceable_inventory(self) -> List[InventoryItem]:
        """Get inventory items eligible for repricing"""
        
        query = await self.db_session.execute(
            select(InventoryItem).where(
                and_(
                    InventoryItem.status.in_(["in_stock", "listed_stockx"]),
                    or_(
                        InventoryItem.last_price_update.is_(None),
                        InventoryItem.last_price_update < datetime.utcnow() - timedelta(hours=24)
                    )
                )
            ).limit(100)  # Process in manageable batches
        )
        
        return query.scalars().all()
    
    async def _optimize_batch_pricing(
        self,
        items: List[InventoryItem],
        strategy: str
    ) -> Dict[str, Any]:
        """Optimize pricing for a batch of items"""
        
        batch_results = {
            "successful_count": 0,
            "updates": [],
            "profit_increase": Decimal("0.00")
        }
        
        for item in items:
            try:
                recommendation = await self.get_dynamic_price_recommendation(item)
                
                if recommendation and "recommended_price" in recommendation:
                    current_price = item.current_price or Decimal("0.00")
                    new_price = Decimal(str(recommendation["recommended_price"]))
                    
                    if abs(new_price - current_price) > Decimal("1.00"):  # Minimum change threshold
                        update_data = {
                            "item_id": str(item.id),
                            "current_price": float(current_price),
                            "recommended_price": float(new_price),
                            "expected_margin": recommendation["expected_margin_percent"],
                            "confidence": recommendation["confidence_score"]
                        }
                        
                        batch_results["updates"].append(update_data)
                        batch_results["successful_count"] += 1
                        batch_results["profit_increase"] += (new_price - current_price)
                        
            except Exception as e:
                logger.error("Failed to optimize item pricing", item_id=str(item.id), error=str(e))
                continue
        
        return batch_results