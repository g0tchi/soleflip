"""
Automated Listing Rules Engine
Advanced service for intelligent listing automation based on configurable rules
"""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import InventoryItem, Product

logger = structlog.get_logger(__name__)


class ListingRule:
    """Individual listing rule configuration"""
    
    def __init__(
        self,
        name: str,
        conditions: Dict[str, Any],
        actions: Dict[str, Any],
        priority: int = 100,
        active: bool = True
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.conditions = conditions
        self.actions = actions
        self.priority = priority
        self.active = active
        self.created_at = datetime.now(timezone.utc)


class AutoListingService:
    """
    Automated Listing Rules Engine
    
    Features:
    - Rule-based listing automation
    - Market condition triggers
    - Price threshold rules
    - Time-based scheduling
    - Platform-specific listing logic
    - Risk management and safety checks
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.logger = logger.bind(service="auto_listing")
        self._listing_rules: List[ListingRule] = []
        self._load_default_rules()

    def _load_default_rules(self):
        """Load default listing rules"""
        default_rules = [
            ListingRule(
                name="High Profit Margin Auto-List",
                conditions={
                    "min_profit_margin_percent": 25.0,
                    "status": ["in_stock"],
                    "purchase_age_days": 7,
                    "market_condition": ["bullish", "stable"]
                },
                actions={
                    "list_on_platform": "stockx",
                    "pricing_strategy": "market_based",
                    "markup_percent": 20.0,
                    "expires_in_days": 30
                },
                priority=10
            ),
            
            ListingRule(
                name="Quick Turnover Items",
                conditions={
                    "brand_names": ["Nike", "Adidas", "Jordan"],
                    "status": ["in_stock"],
                    "min_profit_margin_percent": 15.0,
                    "category": "Sneakers",
                    "purchase_price_range": [100, 500]
                },
                actions={
                    "list_on_platform": "stockx",
                    "pricing_strategy": "competitive",
                    "markup_percent": 18.0,
                    "expires_in_days": 14
                },
                priority=20
            ),
            
            ListingRule(
                name="Premium Items Strategy",
                conditions={
                    "min_purchase_price": 500.0,
                    "status": ["in_stock"],
                    "age_days": 3,
                    "market_volatility": ["low", "moderate"]
                },
                actions={
                    "list_on_platform": "stockx",
                    "pricing_strategy": "premium",
                    "markup_percent": 30.0,
                    "expires_in_days": 45
                },
                priority=30
            ),
            
            ListingRule(
                name="Dead Stock Prevention",
                conditions={
                    "status": ["in_stock"],
                    "age_days": 90,
                    "market_trend": ["declining", "stable"]
                },
                actions={
                    "list_on_platform": "stockx",
                    "pricing_strategy": "clearance",
                    "markup_percent": 8.0,
                    "expires_in_days": 7
                },
                priority=5
            ),
            
            ListingRule(
                name="Market Opportunity Capture",
                conditions={
                    "market_condition": "bullish",
                    "status": ["in_stock"],
                    "competitor_gap_percent": 15.0,
                    "demand_score": 0.7
                },
                actions={
                    "list_on_platform": "stockx",
                    "pricing_strategy": "aggressive",
                    "markup_percent": 25.0,
                    "expires_in_days": 7
                },
                priority=5
            )
        ]
        
        self._listing_rules = default_rules
        self.logger.info(f"Loaded {len(default_rules)} default listing rules")

    async def add_custom_rule(self, rule: ListingRule) -> bool:
        """Add a custom listing rule"""
        try:
            # Validate rule
            if not self._validate_rule(rule):
                return False
            
            self._listing_rules.append(rule)
            # Sort by priority (lower number = higher priority)
            self._listing_rules.sort(key=lambda r: r.priority)
            
            self.logger.info(f"Added custom rule: {rule.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add custom rule: {e}")
            return False

    def _validate_rule(self, rule: ListingRule) -> bool:
        """Validate a listing rule configuration"""
        required_condition_keys = ["status"]
        required_action_keys = ["list_on_platform"]
        
        # Check required conditions
        for key in required_condition_keys:
            if key not in rule.conditions:
                self.logger.error(f"Rule validation failed: missing condition '{key}'")
                return False
        
        # Check required actions
        for key in required_action_keys:
            if key not in rule.actions:
                self.logger.error(f"Rule validation failed: missing action '{key}'")
                return False
                
        return True

    async def execute_listing_automation(
        self, 
        max_items: int = 100,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute automated listing based on configured rules
        
        Args:
            max_items: Maximum number of items to process
            dry_run: If True, simulate without making actual changes
            
        Returns:
            Execution summary with statistics
        """
        self.logger.info(
            "Starting listing automation", 
            max_items=max_items, 
            dry_run=dry_run,
            active_rules=len([r for r in self._listing_rules if r.active])
        )
        
        stats = {
            "items_evaluated": 0,
            "items_listed": 0,
            "rules_matched": 0,
            "errors": 0,
            "skipped": 0,
            "listings_created": [],
            "execution_time": None
        }
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Get candidate items for listing
            candidate_items = await self._get_listing_candidates(max_items)
            stats["items_evaluated"] = len(candidate_items)
            
            if not candidate_items:
                self.logger.info("No candidate items found for listing")
                return stats
            
            # Process each item through the rule engine
            for item in candidate_items:
                try:
                    listing_decision = await self._evaluate_item_against_rules(item)
                    
                    if listing_decision["should_list"]:
                        stats["rules_matched"] += 1
                        
                        if not dry_run:
                            # Execute actual listing
                            listing_result = await self._execute_listing(item, listing_decision)
                            
                            if listing_result["success"]:
                                stats["items_listed"] += 1
                                stats["listings_created"].append({
                                    "item_id": str(item.id),
                                    "product_name": item.product.name if item.product else "Unknown",
                                    "rule_applied": listing_decision["rule_name"],
                                    "price": listing_result.get("price"),
                                    "platform": listing_decision["actions"]["list_on_platform"]
                                })
                            else:
                                stats["errors"] += 1
                        else:
                            # Dry run - just record what would happen
                            stats["items_listed"] += 1
                            stats["listings_created"].append({
                                "item_id": str(item.id),
                                "product_name": item.product.name if item.product else "Unknown",
                                "rule_applied": listing_decision["rule_name"],
                                "would_list": True,
                                "dry_run": True
                            })
                    else:
                        stats["skipped"] += 1
                        
                except Exception as item_error:
                    self.logger.error(f"Error processing item {item.id}: {item_error}")
                    stats["errors"] += 1
            
            end_time = datetime.now(timezone.utc)
            stats["execution_time"] = (end_time - start_time).total_seconds()
            
            self.logger.info("Listing automation completed", **stats)
            return stats
            
        except Exception as e:
            self.logger.error(f"Listing automation failed: {e}")
            stats["errors"] += 1
            return stats

    async def _get_listing_candidates(self, limit: int) -> List[InventoryItem]:
        """Get inventory items that are candidates for listing"""
        try:
            # Query for items that could be listed
            stmt = (
                select(InventoryItem)
                .join(Product, InventoryItem.product_id == Product.id)
                .where(
                    and_(
                        InventoryItem.status.in_(["in_stock"]),
                        InventoryItem.quantity > 0,
                        InventoryItem.purchase_price.isnot(None)
                    )
                )
                .order_by(InventoryItem.created_at.desc())
                .limit(limit)
            )
            
            result = await self.db_session.execute(stmt)
            items = result.scalars().all()
            
            # Ensure items have product relationship loaded
            for item in items:
                await self.db_session.refresh(item, ["product", "product.brand", "product.category"])
            
            self.logger.info(f"Found {len(items)} candidate items for listing")
            return list(items)
            
        except Exception as e:
            self.logger.error(f"Failed to get listing candidates: {e}")
            return []

    async def _evaluate_item_against_rules(self, item: InventoryItem) -> Dict[str, Any]:
        """Evaluate an inventory item against all active listing rules"""
        decision = {
            "should_list": False,
            "rule_name": None,
            "conditions_met": [],
            "actions": {},
            "confidence": 0.0
        }
        
        # Get market context for item evaluation
        market_context = await self._get_market_context_for_item(item)
        
        # Evaluate against each active rule in priority order
        for rule in self._listing_rules:
            if not rule.active:
                continue
                
            rule_match = await self._evaluate_rule_conditions(item, rule, market_context)
            
            if rule_match["matches"]:
                decision.update({
                    "should_list": True,
                    "rule_name": rule.name,
                    "conditions_met": rule_match["conditions_met"],
                    "actions": rule.actions,
                    "confidence": rule_match["confidence"]
                })
                
                self.logger.info(
                    f"Item matches rule '{rule.name}'", 
                    item_id=str(item.id),
                    confidence=rule_match["confidence"]
                )
                break  # Use first matching rule (highest priority)
        
        return decision

    async def _evaluate_rule_conditions(
        self, 
        item: InventoryItem, 
        rule: ListingRule,
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate if an item meets a rule's conditions"""
        conditions_met = []
        total_conditions = len(rule.conditions)
        confidence_score = 0.0
        
        for condition, value in rule.conditions.items():
            condition_met = False
            
            # Status condition
            if condition == "status":
                if isinstance(value, list):
                    condition_met = item.status in value
                else:
                    condition_met = item.status == value
                    
            # Profit margin condition
            elif condition == "min_profit_margin_percent":
                if item.purchase_price and market_context.get("market_price"):
                    margin = ((market_context["market_price"] - item.purchase_price) / item.purchase_price) * 100
                    condition_met = margin >= value
                    
            # Purchase age condition
            elif condition in ["purchase_age_days", "age_days"]:
                if item.purchase_date:
                    age_days = (datetime.now(timezone.utc) - item.purchase_date.replace(tzinfo=timezone.utc)).days
                    condition_met = age_days >= value
                    
            # Brand condition
            elif condition == "brand_names":
                if item.product and item.product.brand:
                    condition_met = item.product.brand.name in value
                    
            # Category condition
            elif condition == "category":
                if item.product and item.product.category:
                    condition_met = item.product.category.name == value
                    
            # Purchase price range condition
            elif condition == "purchase_price_range":
                if item.purchase_price:
                    min_price, max_price = value
                    condition_met = min_price <= float(item.purchase_price) <= max_price
                    
            # Minimum purchase price condition
            elif condition == "min_purchase_price":
                if item.purchase_price:
                    condition_met = float(item.purchase_price) >= value
                    
            # Market-based conditions
            elif condition == "market_condition":
                market_condition = market_context.get("condition", "unknown")
                if isinstance(value, list):
                    condition_met = market_condition in value
                else:
                    condition_met = market_condition == value
                    
            elif condition == "market_volatility":
                volatility = market_context.get("volatility", "unknown")
                if isinstance(value, list):
                    condition_met = volatility in value
                else:
                    condition_met = volatility == value
                    
            elif condition == "market_trend":
                trend = market_context.get("trend", "unknown")
                if isinstance(value, list):
                    condition_met = trend in value
                else:
                    condition_met = trend == value
                    
            elif condition == "competitor_gap_percent":
                gap = market_context.get("competitor_gap_percent", 0.0)
                condition_met = gap >= value
                
            elif condition == "demand_score":
                demand = market_context.get("demand_score", 0.0)
                condition_met = demand >= value
            
            if condition_met:
                conditions_met.append(condition)
                
        # Calculate confidence based on conditions met
        conditions_met_count = len(conditions_met)
        if conditions_met_count > 0:
            confidence_score = conditions_met_count / total_conditions
        
        # Rule matches if ALL conditions are met
        rule_matches = conditions_met_count == total_conditions
        
        return {
            "matches": rule_matches,
            "conditions_met": conditions_met,
            "confidence": confidence_score
        }

    async def _get_market_context_for_item(self, item: InventoryItem) -> Dict[str, Any]:
        """Get market context for an inventory item"""
        # Simulate market context - in real implementation, this would
        # integrate with the smart pricing service and market data APIs
        
        context = {
            "condition": "bullish",
            "volatility": "moderate", 
            "trend": "stable",
            "market_price": None,
            "competitor_gap_percent": 12.0,
            "demand_score": 0.75
        }
        
        # Estimate market price based on purchase price
        if item.purchase_price:
            # Simple markup estimation
            context["market_price"] = float(item.purchase_price) * 1.25
            
        return context

    async def _execute_listing(
        self, 
        item: InventoryItem, 
        listing_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the actual listing based on the decision"""
        try:
            actions = listing_decision["actions"]
            platform = actions.get("list_on_platform", "stockx")
            pricing_strategy = actions.get("pricing_strategy", "market_based")
            markup_percent = actions.get("markup_percent", 20.0)
            expires_in_days = actions.get("expires_in_days", 30)
            
            # Calculate listing price
            listing_price = await self._calculate_listing_price(
                item, 
                pricing_strategy, 
                markup_percent
            )
            
            if platform.lower() == "stockx":
                # Execute StockX listing
                listing_result = await self._create_stockx_listing(
                    item, 
                    listing_price, 
                    expires_in_days
                )
                
                if listing_result["success"]:
                    # Update item status
                    await self._update_item_status_after_listing(item, "listed_stockx")
                    
                return {
                    "success": True,
                    "platform": platform,
                    "price": listing_price,
                    "listing_id": listing_result.get("listing_id")
                }
            
            return {"success": False, "error": f"Unsupported platform: {platform}"}
            
        except Exception as e:
            self.logger.error(f"Failed to execute listing for item {item.id}: {e}")
            return {"success": False, "error": str(e)}

    async def _calculate_listing_price(
        self, 
        item: InventoryItem, 
        strategy: str, 
        markup_percent: float
    ) -> Decimal:
        """Calculate listing price based on strategy"""
        base_price = item.purchase_price or Decimal("100.00")
        
        if strategy == "cost_plus":
            return base_price * (1 + Decimal(markup_percent / 100))
            
        elif strategy == "market_based":
            # Simulate market-based pricing
            market_multiplier = Decimal("1.2")  # 20% above purchase
            return base_price * market_multiplier
            
        elif strategy == "competitive":
            # Slightly below market to be competitive
            return base_price * (1 + Decimal((markup_percent - 2) / 100))
            
        elif strategy == "premium":
            # Premium pricing
            return base_price * (1 + Decimal(markup_percent / 100))
            
        elif strategy == "clearance":
            # Lower markup for quick sale
            return base_price * (1 + Decimal(max(5, markup_percent) / 100))
            
        elif strategy == "aggressive":
            # Higher markup for market opportunities
            return base_price * (1 + Decimal((markup_percent + 5) / 100))
        
        # Default to cost-plus
        return base_price * (1 + Decimal(markup_percent / 100))

    async def _create_stockx_listing(
        self, 
        item: InventoryItem, 
        price: Decimal, 
        expires_in_days: int
    ) -> Dict[str, Any]:
        """Create a StockX listing for an inventory item"""
        try:
            # Import StockX service
            from domains.integration.services.stockx_service import StockXService
            
            stockx_service = StockXService(self.db_session)
            
            # Calculate expiration date
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            expires_at_str = expires_at.isoformat().replace("+00:00", "Z")
            
            # For demo purposes, we'll simulate the listing creation
            # In real implementation, you'd need the actual variant ID
            mock_variant_id = f"variant-{item.id}"
            
            # Simulate listing creation (replace with actual StockX API call)
            listing_response = {
                "listingId": f"listing-{uuid.uuid4()}",
                "variantId": mock_variant_id,
                "amount": str(price),
                "currencyCode": "USD",
                "expiresAt": expires_at_str,
                "active": True
            }
            
            self.logger.info(
                "Created StockX listing",
                item_id=str(item.id),
                listing_id=listing_response["listingId"],
                price=price
            )
            
            return {
                "success": True,
                "listing_id": listing_response["listingId"],
                "variant_id": mock_variant_id,
                "price": price
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create StockX listing: {e}")
            return {"success": False, "error": str(e)}

    async def _update_item_status_after_listing(
        self, 
        item: InventoryItem, 
        new_status: str
    ) -> bool:
        """Update inventory item status after successful listing"""
        try:
            item.status = new_status
            item.updated_at = datetime.now(timezone.utc)
            
            await self.db_session.commit()
            
            self.logger.info(f"Updated item {item.id} status to {new_status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update item status: {e}")
            await self.db_session.rollback()
            return False

    async def get_automation_status(self) -> Dict[str, Any]:
        """Get current status of the listing automation system"""
        active_rules_count = len([r for r in self._listing_rules if r.active])
        
        return {
            "enabled": True,
            "total_rules": len(self._listing_rules),
            "active_rules": active_rules_count,
            "last_run": None,  # Would track from database
            "next_scheduled_run": None,  # Would implement scheduling
            "rules": [
                {
                    "name": rule.name,
                    "active": rule.active,
                    "priority": rule.priority,
                    "conditions_count": len(rule.conditions),
                    "created_at": rule.created_at.isoformat()
                }
                for rule in self._listing_rules
            ]
        }

    async def simulate_rule_execution(
        self, 
        rule_name: Optional[str] = None,
        max_items: int = 10
    ) -> Dict[str, Any]:
        """Simulate rule execution without making changes"""
        if rule_name:
            # Test specific rule
            rule = next((r for r in self._listing_rules if r.name == rule_name), None)
            if not rule:
                return {"error": f"Rule '{rule_name}' not found"}
                
            # Temporarily disable other rules for simulation
            original_states = [(r, r.active) for r in self._listing_rules]
            for r in self._listing_rules:
                r.active = (r.name == rule_name)
        
        try:
            # Run automation in dry-run mode
            result = await self.execute_listing_automation(
                max_items=max_items, 
                dry_run=True
            )
            
            return {
                "simulation_complete": True,
                "rule_tested": rule_name,
                **result
            }
            
        finally:
            if rule_name:
                # Restore original rule states
                for rule, original_active in original_states:
                    rule.active = original_active

    def get_rule_by_name(self, name: str) -> Optional[ListingRule]:
        """Get a listing rule by name"""
        return next((rule for rule in self._listing_rules if rule.name == name), None)

    async def toggle_rule(self, rule_name: str, active: bool) -> bool:
        """Enable or disable a listing rule"""
        rule = self.get_rule_by_name(rule_name)
        if rule:
            rule.active = active
            self.logger.info(f"Rule '{rule_name}' {'enabled' if active else 'disabled'}")
            return True
        return False