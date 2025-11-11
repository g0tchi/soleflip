#!/usr/bin/env python3
"""
Pricing CLI - Command-line interface for pricing operations
Production-ready tool for price calculations and updates
"""
import argparse
import asyncio
import json
import logging
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, ".")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from domains.pricing.repositories.pricing_repository import PricingRepository  # noqa: E402
from domains.pricing.services.pricing_engine import (  # noqa: E402
    PricingContext,
    PricingEngine,
    PricingStrategy,
)
from shared.database.connection import get_db_session  # noqa: E402
from shared.database.models import InventoryItem, Product  # noqa: E402


class PricingCLI:
    """Command-line interface for pricing operations"""

    def __init__(self):
        self.db_session = None
        self.pricing_engine = None
        self.repository = None

    async def initialize(self):
        """Initialize database connections and services"""
        self.db_session = get_db_session()
        self.pricing_engine = PricingEngine(self.db_session)
        self.repository = PricingRepository(self.db_session)
        logger.info("Pricing CLI initialized successfully")

    async def cleanup(self):
        """Cleanup database connections"""
        if self.db_session:
            await self.db_session.close()
        logger.info("Pricing CLI cleanup completed")

    # =====================================================
    # PRICING COMMANDS
    # =====================================================

    async def calculate_price(self, args):
        """Calculate optimal price for a product or inventory item"""
        try:
            # Get product information
            if args.product_id:
                product_id = uuid.UUID(args.product_id)
                query = (
                    select(Product)
                    .where(Product.id == product_id)
                    .options(selectinload(Product.brand))
                )
                result = await self.db_session.execute(query)
                product = result.scalar_one_or_none()

                if not product:
                    print(f"❌ Product {args.product_id} not found")
                    return
            elif args.sku:
                query = (
                    select(Product)
                    .where(Product.sku == args.sku)
                    .options(selectinload(Product.brand))
                )
                result = await self.db_session.execute(query)
                product = result.scalar_one_or_none()

                if not product:
                    print(f"❌ Product with SKU {args.sku} not found")
                    return
            else:
                print("❌ Either --product-id or --sku must be provided")
                return

            # Get inventory item if specified
            inventory_item = None
            if args.inventory_item_id:
                inventory_id = uuid.UUID(args.inventory_item_id)
                query = select(InventoryItem).where(InventoryItem.id == inventory_id)
                result = await self.db_session.execute(query)
                inventory_item = result.scalar_one_or_none()

                if not inventory_item:
                    print(f"❌ Inventory item {args.inventory_item_id} not found")
                    return

            # Create pricing context
            context = PricingContext(
                product=product,
                inventory_item=inventory_item,
                platform_id=uuid.UUID(args.platform_id) if args.platform_id else None,
                condition=args.condition or "new",
                size=args.size,
                target_margin=Decimal(args.target_margin) if args.target_margin else None,
            )

            # Parse strategies
            strategies = []
            if args.strategies:
                for strategy_name in args.strategies.split(","):
                    try:
                        strategy = PricingStrategy(strategy_name.strip().lower())
                        strategies.append(strategy)
                    except ValueError:
                        print(f"⚠️ Unknown strategy: {strategy_name}")

            # Calculate optimal price
            logger.info(f"Calculating price for product {product.sku}")
            result = await self.pricing_engine.calculate_optimal_price(
                context=context, strategies=strategies if strategies else None
            )

            # Display results
            self._display_pricing_result(product, result, args)

            # Save to database if requested
            if args.save_price and result.suggested_price > 0:
                await self._save_price_to_history(
                    product.id,
                    result.suggested_price,
                    "calculated",
                    inventory_item.id if inventory_item else None,
                    context.platform_id,
                    result,
                )
                print("💾 Price saved to history")

        except Exception as e:
            logger.error(f"Error calculating price: {str(e)}")
            print(f"❌ Error: {str(e)}")

    async def update_pricing_rules(self, args):
        """Update or create pricing rules"""
        try:
            rule_data = {
                "name": args.name,
                "rule_type": args.rule_type,
                "priority": args.priority or 100,
                "active": not args.inactive,
                "effective_from": datetime.now(),
            }

            # Add optional fields
            if args.brand_id:
                rule_data["brand_id"] = uuid.UUID(args.brand_id)
            if args.category_id:
                rule_data["category_id"] = uuid.UUID(args.category_id)
            if args.platform_id:
                rule_data["platform_id"] = uuid.UUID(args.platform_id)
            if args.markup_percent:
                rule_data["base_markup_percent"] = Decimal(args.markup_percent)
            if args.minimum_margin:
                rule_data["minimum_margin_percent"] = Decimal(args.minimum_margin)
            if args.maximum_discount:
                rule_data["maximum_discount_percent"] = Decimal(args.maximum_discount)
            if args.effective_until:
                rule_data["effective_until"] = datetime.fromisoformat(args.effective_until)

            # Handle condition multipliers
            if args.condition_multipliers:
                try:
                    rule_data["condition_multipliers"] = json.loads(args.condition_multipliers)
                except json.JSONDecodeError:
                    print("❌ Invalid JSON format for condition multipliers")
                    return

            # Handle seasonal adjustments
            if args.seasonal_adjustments:
                try:
                    rule_data["seasonal_adjustments"] = json.loads(args.seasonal_adjustments)
                except json.JSONDecodeError:
                    print("❌ Invalid JSON format for seasonal adjustments")
                    return

            # Create or update rule
            if args.rule_id:
                rule_id = uuid.UUID(args.rule_id)
                rule = await self.repository.update_price_rule(rule_id, rule_data)
                if rule:
                    print(f"✅ Updated pricing rule: {rule.name}")
                else:
                    print(f"❌ Rule {args.rule_id} not found")
            else:
                rule = await self.repository.create_price_rule(rule_data)
                print(f"✅ Created pricing rule: {rule.name} (ID: {rule.id})")

            await self.db_session.commit()

        except Exception as e:
            logger.error(f"Error updating pricing rules: {str(e)}")
            print(f"❌ Error: {str(e)}")
            await self.db_session.rollback()

    async def bulk_price_update(self, args):
        """Update prices for multiple products"""
        try:
            # Parse filters
            filters = {}
            if args.brand_id:
                filters["brand_id"] = uuid.UUID(args.brand_id)
            if args.category_id:
                filters["category_id"] = uuid.UUID(args.category_id)
            if args.sku_pattern:
                filters["sku_pattern"] = args.sku_pattern

            # Build query for products
            query = select(Product).options(selectinload(Product.brand))

            if "brand_id" in filters:
                query = query.where(Product.brand_id == filters["brand_id"])
            if "category_id" in filters:
                query = query.where(Product.category_id == filters["category_id"])
            if "sku_pattern" in filters:
                query = query.where(Product.sku.like(f"%{filters['sku_pattern']}%"))

            if args.limit:
                query = query.limit(args.limit)

            result = await self.db_session.execute(query)
            products = result.scalars().all()

            if not products:
                print("❌ No products found matching criteria")
                return

            print(f"🔄 Processing {len(products)} products...")

            # Parse strategies
            strategies = []
            if args.strategies:
                for strategy_name in args.strategies.split(","):
                    try:
                        strategy = PricingStrategy(strategy_name.strip().lower())
                        strategies.append(strategy)
                    except ValueError:
                        print(f"⚠️ Unknown strategy: {strategy_name}")

            updated_count = 0
            failed_count = 0

            for i, product in enumerate(products, 1):
                try:
                    print(f"Processing {i}/{len(products)}: {product.sku}")

                    # Create pricing context
                    context = PricingContext(
                        product=product,
                        condition=args.condition or "new",
                        platform_id=uuid.UUID(args.platform_id) if args.platform_id else None,
                    )

                    # Calculate price
                    pricing_result = await self.pricing_engine.calculate_optimal_price(
                        context=context, strategies=strategies if strategies else None
                    )

                    # Save price if successful
                    if pricing_result.suggested_price > 0:
                        await self._save_price_to_history(
                            product.id,
                            pricing_result.suggested_price,
                            "bulk_update",
                            None,
                            context.platform_id,
                            pricing_result,
                        )
                        updated_count += 1

                        if args.verbose:
                            print(f"  ✅ {product.sku}: €{pricing_result.suggested_price:.2f}")
                    else:
                        failed_count += 1
                        if args.verbose:
                            print(f"  ❌ {product.sku}: Failed to calculate price")

                except Exception as e:
                    failed_count += 1
                    if args.verbose:
                        print(f"  ❌ {product.sku}: {str(e)}")
                    continue

            # Commit all changes
            await self.db_session.commit()

            print("✅ Bulk update completed:")
            print(f"   Updated: {updated_count}")
            print(f"   Failed: {failed_count}")

        except Exception as e:
            logger.error(f"Error in bulk price update: {str(e)}")
            print(f"❌ Error: {str(e)}")
            await self.db_session.rollback()

    async def pricing_performance(self, args):
        """Analyze pricing performance and generate reports"""
        try:
            # Parse date range
            end_date = date.today()
            start_date = end_date - timedelta(days=args.days or 30)

            # Get performance metrics
            metrics = await self.repository.get_pricing_performance_metrics(
                brand_id=uuid.UUID(args.brand_id) if args.brand_id else None,
                category_id=uuid.UUID(args.category_id) if args.category_id else None,
                start_date=start_date,
                end_date=end_date,
            )

            # Display performance report
            print("📊 PRICING PERFORMANCE REPORT")
            print("=" * 50)
            print(f"Period: {start_date} to {end_date}")
            print(f"Total Price Changes: {metrics['total_price_changes']}")
            print(f"Average Price: €{metrics['average_price']:.2f}")
            print(
                f"Price Range: €{metrics['price_range']['min']:.2f} - €{metrics['price_range']['max']:.2f}"
            )
            print(f"Price Volatility: {metrics['price_volatility']:.2f}")

            # Get top performing products
            if args.include_products:
                top_products = await self.repository.get_top_performing_products(
                    limit=args.product_limit or 10,
                    metric=args.metric or "volume",
                    days_back=args.days or 30,
                )

                print(f"\n🏆 TOP PERFORMING PRODUCTS ({args.metric or 'volume'}):")
                print("-" * 50)
                for i, product in enumerate(top_products, 1):
                    print(f"{i:2d}. {product['sku']} ({product['brand']})")
                    if "total_volume" in product:
                        print(
                            f"     Volume: {product['total_volume']} | Avg Price: €{product['avg_sale_price']:.2f}"
                        )
                    elif "growth_percent" in product:
                        print(
                            f"     Growth: {product['growth_percent']:.1f}% | €{product['first_price']:.2f} → €{product['latest_price']:.2f}"
                        )

        except Exception as e:
            logger.error(f"Error generating pricing performance report: {str(e)}")
            print(f"❌ Error: {str(e)}")

    async def market_analysis(self, args):
        """Analyze market prices and competitive positioning"""
        try:
            if not args.product_id:
                print("❌ --product-id is required for market analysis")
                return

            product_id = uuid.UUID(args.product_id)

            # Get competitive pricing data
            competitive_data = await self.repository.get_competitive_pricing_data(
                product_id=product_id, condition=args.condition or "new"
            )

            if not competitive_data:
                print("❌ No competitive data available for this product")
                return

            print("🏪 MARKET ANALYSIS REPORT")
            print("=" * 50)

            platforms = competitive_data.get("platforms", {})
            for platform, data in platforms.items():
                print(f"\n{platform.upper()}:")
                print(f"  Latest Date: {data['latest_date']}")
                if data.get("last_sale"):
                    print(f"  Last Sale: €{data['last_sale']:.2f}")
                if data.get("lowest_ask"):
                    print(f"  Lowest Ask: €{data['lowest_ask']:.2f}")
                if data.get("highest_bid"):
                    print(f"  Highest Bid: €{data['highest_bid']:.2f}")
                if data.get("sales_volume"):
                    print(f"  Volume: {data['sales_volume']} units")

            # Market summary
            market_avg = competitive_data.get("market_average")
            market_range = competitive_data.get("market_range", {})

            print("\n📈 MARKET SUMMARY:")
            if market_avg:
                print(f"  Market Average: €{market_avg:.2f}")
            if market_range.get("min") and market_range.get("max"):
                print(f"  Price Range: €{market_range['min']:.2f} - €{market_range['max']:.2f}")
            print(f"  Data Points: {competitive_data.get('data_points', 0)}")
            print(f"  Total Volume: {competitive_data.get('total_volume', 0)} units")

        except Exception as e:
            logger.error(f"Error generating market analysis: {str(e)}")
            print(f"❌ Error: {str(e)}")

    # =====================================================
    # HELPER METHODS
    # =====================================================

    def _display_pricing_result(self, product, result, args):
        """Display pricing calculation results"""
        print("\n💰 PRICING CALCULATION RESULTS")
        print("=" * 50)
        print(f"Product: {product.name}")
        print(f"SKU: {product.sku}")
        print(f"Brand: {product.brand.name if product.brand else 'Unknown'}")
        print(f"Condition: {args.condition or 'new'}")

        print(f"\n🎯 RECOMMENDED PRICE: €{result.suggested_price:.2f}")
        print(f"Strategy Used: {result.strategy_used.value}")
        print(f"Confidence Score: {result.confidence_score:.2f}")
        print(f"Margin: {result.margin_percent:.1f}%")
        print(f"Markup: {result.markup_percent:.1f}%")

        if result.market_position:
            print(f"Market Position: {result.market_position}")

        if result.price_range:
            print("\n📊 COMPETITIVE RANGE:")
            for key, value in result.price_range.items():
                print(f"  {key.replace('_', ' ').title()}: €{value:.2f}")

        print("\n💭 REASONING:")
        for i, reason in enumerate(result.reasoning, 1):
            print(f"  {i}. {reason}")

        if result.adjustments_applied:
            print("\n⚙️ ADJUSTMENTS APPLIED:")
            for adjustment in result.adjustments_applied:
                print(f"  • {adjustment['type']}: {adjustment['adjustment']}")

    async def _save_price_to_history(
        self,
        product_id: uuid.UUID,
        price: Decimal,
        price_type: str,
        inventory_item_id: Optional[uuid.UUID],
        platform_id: Optional[uuid.UUID],
        pricing_result,
    ):
        """Save calculated price to price history"""
        price_data = {
            "product_id": product_id,
            "inventory_item_id": inventory_item_id,
            "platform_id": platform_id,
            "price_date": date.today(),
            "price_type": price_type,
            "price_amount": price,
            "currency": "EUR",
            "source": "internal",
            "confidence_score": pricing_result.confidence_score,
            "metadata": {
                "strategy_used": pricing_result.strategy_used.value,
                "margin_percent": float(pricing_result.margin_percent),
                "markup_percent": float(pricing_result.markup_percent),
                "market_position": pricing_result.market_position,
                "reasoning": pricing_result.reasoning,
            },
        }

        await self.repository.record_price_history(price_data)


def create_parser():
    """Create command-line argument parser"""
    parser = argparse.ArgumentParser(description="SoleFlipper Pricing CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Calculate Price Command
    calc_parser = subparsers.add_parser("calculate", help="Calculate optimal price for a product")
    calc_parser.add_argument("--product-id", help="Product UUID")
    calc_parser.add_argument("--sku", help="Product SKU")
    calc_parser.add_argument("--inventory-item-id", help="Specific inventory item UUID")
    calc_parser.add_argument("--platform-id", help="Target platform UUID")
    calc_parser.add_argument(
        "--condition", default="new", help="Item condition (new, excellent, etc.)"
    )
    calc_parser.add_argument("--size", help="Item size")
    calc_parser.add_argument("--target-margin", type=float, help="Target margin percentage")
    calc_parser.add_argument("--strategies", help="Comma-separated pricing strategies")
    calc_parser.add_argument(
        "--save-price", action="store_true", help="Save calculated price to database"
    )

    # Update Pricing Rules Command
    rules_parser = subparsers.add_parser("update-rules", help="Update or create pricing rules")
    rules_parser.add_argument("--rule-id", help="Rule ID to update (create new if not provided)")
    rules_parser.add_argument("--name", required=True, help="Rule name")
    rules_parser.add_argument(
        "--rule-type",
        required=True,
        choices=["cost_plus", "market_based", "competitive"],
        help="Rule type",
    )
    rules_parser.add_argument(
        "--priority", type=int, help="Rule priority (lower = higher priority)"
    )
    rules_parser.add_argument("--inactive", action="store_true", help="Mark rule as inactive")
    rules_parser.add_argument("--brand-id", help="Apply to specific brand")
    rules_parser.add_argument("--category-id", help="Apply to specific category")
    rules_parser.add_argument("--platform-id", help="Apply to specific platform")
    rules_parser.add_argument("--markup-percent", type=float, help="Base markup percentage")
    rules_parser.add_argument("--minimum-margin", type=float, help="Minimum margin percentage")
    rules_parser.add_argument("--maximum-discount", type=float, help="Maximum discount percentage")
    rules_parser.add_argument("--effective-until", help="Rule expiry date (ISO format)")
    rules_parser.add_argument(
        "--condition-multipliers", help="JSON object with condition multipliers"
    )
    rules_parser.add_argument(
        "--seasonal-adjustments", help="JSON object with seasonal adjustments"
    )

    # Bulk Update Command
    bulk_parser = subparsers.add_parser("bulk-update", help="Update prices for multiple products")
    bulk_parser.add_argument("--brand-id", help="Filter by brand UUID")
    bulk_parser.add_argument("--category-id", help="Filter by category UUID")
    bulk_parser.add_argument("--sku-pattern", help="Filter by SKU pattern")
    bulk_parser.add_argument("--platform-id", help="Target platform for pricing")
    bulk_parser.add_argument("--condition", default="new", help="Item condition")
    bulk_parser.add_argument("--strategies", help="Comma-separated pricing strategies")
    bulk_parser.add_argument("--limit", type=int, help="Maximum number of products to process")
    bulk_parser.add_argument("--verbose", action="store_true", help="Show detailed progress")

    # Performance Analysis Command
    perf_parser = subparsers.add_parser("performance", help="Analyze pricing performance")
    perf_parser.add_argument("--days", type=int, default=30, help="Number of days to analyze")
    perf_parser.add_argument("--brand-id", help="Filter by brand UUID")
    perf_parser.add_argument("--category-id", help="Filter by category UUID")
    perf_parser.add_argument("--include-products", action="store_true", help="Include top products")
    perf_parser.add_argument("--product-limit", type=int, default=10, help="Number of top products")
    perf_parser.add_argument(
        "--metric", choices=["volume", "price_growth"], default="volume", help="Performance metric"
    )

    # Market Analysis Command
    market_parser = subparsers.add_parser(
        "market-analysis", help="Analyze market prices and competition"
    )
    market_parser.add_argument("--product-id", required=True, help="Product UUID to analyze")
    market_parser.add_argument("--condition", default="new", help="Item condition")

    return parser


async def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = PricingCLI()

    try:
        await cli.initialize()

        # Route to appropriate command handler
        if args.command == "calculate":
            await cli.calculate_price(args)
        elif args.command == "update-rules":
            await cli.update_pricing_rules(args)
        elif args.command == "bulk-update":
            await cli.bulk_price_update(args)
        elif args.command == "performance":
            await cli.pricing_performance(args)
        elif args.command == "market-analysis":
            await cli.market_analysis(args)
        else:
            print(f"❌ Unknown command: {args.command}")

    except KeyboardInterrupt:
        print("\n⏹️ Operation cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"❌ Unexpected error: {str(e)}")
    finally:
        await cli.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
