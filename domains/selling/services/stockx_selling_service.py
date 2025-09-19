"""
StockX Selling Service
Automated selling and listing management for StockX marketplace
"""

import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from shared.database.models import StockXListing, StockXOrder, PricingHistory, Product
from shared.repositories.base_repository import BaseRepository
from shared.database.transaction_manager import TransactionMixin, transactional
from shared.utils.financial import FinancialCalculator
from shared.error_handling.selling_exceptions import (
    ListingCreationError,
    PriceUpdateError,
    ListingNotFoundError,
    OpportunityNotFoundError,
    StockXAPIError,
    BulkOperationError,
    DatabaseError,
    ConfigurationError,
    handle_database_error,
    handle_api_error
)
from shared.security.api_security import InputSanitizer
from domains.integration.services.quickflip_detection_service import QuickFlipOpportunity
from domains.selling.services.stockx_api_client import StockXAPIClient

logger = structlog.get_logger(__name__)



class StockXSellingService(TransactionMixin):
    """Main service for StockX selling operations with transaction safety"""

    def __init__(self, db: AsyncSession, api_token: str):
        super().__init__(db_session=db)

        if not api_token:
            raise ConfigurationError("StockX API token not configured")

        self.api_client = StockXAPIClient(api_token)
        self.listing_repo = BaseRepository(StockXListing, db)
        self.order_repo = BaseRepository(StockXOrder, db)
        self.pricing_repo = BaseRepository(PricingHistory, db)
        self.product_repo = BaseRepository(Product, db)
        self.input_sanitizer = InputSanitizer()

    @transactional()
    async def create_listing_from_opportunity(
        self,
        opportunity: QuickFlipOpportunity,
        pricing_strategy: str = "competitive",
        margin_buffer: float = 5.0
    ) -> StockXListing:
        """
        Convert a QuickFlip opportunity to a StockX listing

        Args:
            opportunity: QuickFlip opportunity to convert
            pricing_strategy: 'competitive', 'premium', 'aggressive'
            margin_buffer: Additional margin buffer for safety
        """
        try:
            # Validate and sanitize input
            pricing_strategy = self.input_sanitizer.sanitize_pricing_strategy(pricing_strategy)

            if margin_buffer < 0 or margin_buffer > 50:
                raise ListingCreationError("Margin buffer must be between 0% and 50%", field="margin_buffer")

            # Get product details
            product = await self.product_repo.get_by_id(opportunity.product_id)
            if not product:
                raise OpportunityNotFoundError(str(opportunity.product_id))

            if not product.stockx_product_id:
                raise ListingCreationError(
                    "Product missing StockX integration data",
                    field="stockx_product_id"
                )
        except SQLAlchemyError as e:
            raise handle_database_error("fetch product", e)

        # Calculate optimal selling price with safe financial calculations
        optimal_price = await self._calculate_optimal_price(
            product.stockx_product_id,
            opportunity.sell_price,
            pricing_strategy,
            margin_buffer
        )

        # Create listing on StockX (external API call outside transaction)
        try:
            stockx_response = await self.api_client.create_listing(
                product_id=product.stockx_product_id,
                variant_id=product.sku,  # Assuming SKU maps to variant
                amount=float(optimal_price),
                expires_at=(datetime.utcnow() + timedelta(days=30)).isoformat()
            )

            if not stockx_response or not stockx_response.get("listingId"):
                raise StockXAPIError("Invalid response from StockX API")

        except Exception as api_error:
            logger.error(
                "StockX API call failed",
                error=str(api_error),
                product_id=str(product.id),
                pricing_strategy=pricing_strategy
            )
            raise handle_api_error("StockX", api_error)

        # Use safe financial calculations
        buy_price = FinancialCalculator.to_currency(opportunity.buy_price)
        expected_profit = FinancialCalculator.calculate_gross_profit(
            sale_price=optimal_price,
            cost=buy_price
        )
        expected_margin = FinancialCalculator.calculate_margin(
            cost=buy_price,
            sale_price=optimal_price
        )

        # Save to our database (within transaction)
        try:
            listing = StockXListing(
                product_id=opportunity.product_id,
                stockx_listing_id=stockx_response.get("listingId"),
                stockx_product_id=product.stockx_product_id,
                variant_id=product.sku,
                ask_price=optimal_price,
                original_ask_price=optimal_price,
                buy_price=buy_price,
                expected_profit=expected_profit,
                expected_margin=expected_margin,
                status="active",
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=30),
                source_opportunity_id=opportunity.product_id,  # Linking back to opportunity
                created_from="quickflip",
                listed_at=datetime.utcnow()
            )

            await self.listing_repo.create(listing)

        except SQLAlchemyError as e:
            logger.error(
                "Failed to save listing to database",
                error=str(e),
                stockx_listing_id=stockx_response.get("listingId")
            )
            raise handle_database_error("create listing", e)

        logger.info(
            "Created listing from opportunity",
            listing_id=listing.stockx_listing_id,
            product_id=str(product.id),
            ask_price=float(optimal_price),
            expected_profit=float(expected_profit)
        )

        return listing

    @transactional()
    async def create_bulk_listings(self, opportunities: List[QuickFlipOpportunity]) -> List[StockXListing]:
        """Create multiple listings from opportunities efficiently"""
        try:
            # Prepare bulk listing data
            bulk_data = []
            opportunity_map = {}

            for opportunity in opportunities:
                product = await self.product_repo.get_by_id(opportunity.product_id)
                if not product or not product.stockx_product_id:
                    logger.warning("Skipping opportunity - no StockX product ID", product_id=str(opportunity.product_id))
                    continue

                optimal_price = await self._calculate_optimal_price(
                    product.stockx_product_id,
                    opportunity.sell_price,
                    "competitive"
                )

                listing_data = {
                    "productId": product.stockx_product_id,
                    "variantId": product.sku,
                    "amount": float(optimal_price),
                    "expiresAt": (datetime.utcnow() + timedelta(days=30)).isoformat()
                }
                bulk_data.append(listing_data)
                opportunity_map[product.stockx_product_id] = (opportunity, product, optimal_price)

            if not bulk_data:
                logger.warning("No valid opportunities for bulk listing")
                return []

            # Create bulk listings on StockX
            stockx_response = await self.api_client.create_bulk_listings(bulk_data)

            # Process response and save to database
            created_listings = []
            for listing_result in stockx_response.get("results", []):
                if listing_result.get("success"):
                    product_id = listing_result.get("productId")
                    if product_id in opportunity_map:
                        opportunity, product, optimal_price = opportunity_map[product_id]

                        listing = StockXListing(
                            product_id=opportunity.product_id,
                            stockx_listing_id=listing_result.get("listingId"),
                            stockx_product_id=product_id,
                            variant_id=product.sku,
                            ask_price=optimal_price,
                            original_ask_price=optimal_price,
                            buy_price=opportunity.buy_price,
                            expected_profit=optimal_price - opportunity.buy_price,
                            expected_margin=((optimal_price - opportunity.buy_price) / opportunity.buy_price) * 100,
                            status="active",
                            is_active=True,
                            expires_at=datetime.utcnow() + timedelta(days=30),
                            source_opportunity_id=opportunity.product_id,
                            created_from="quickflip_bulk",
                            listed_at=datetime.utcnow()
                        )

                        await self.listing_repo.create(listing)
                        created_listings.append(listing)

            logger.info("Created bulk listings", count=len(created_listings), total_attempted=len(bulk_data))
            return created_listings

        except Exception as e:
            logger.error("Failed to create bulk listings", error=str(e))
            raise

    async def update_listing_price(
        self,
        listing_id: UUID,
        new_price: Decimal,
        reason: str = "manual_update"
    ) -> StockXListing:
        """Update the price of an existing listing"""
        try:
            # Validate inputs
            if new_price <= 0:
                raise PriceUpdateError("Price must be greater than 0", field="new_price")

            if new_price > Decimal('99999.99'):
                raise PriceUpdateError("Price exceeds maximum limit", field="new_price")

            reason = self.input_sanitizer.sanitize_string(reason, max_length=100)

            # Get listing
            listing = await self.listing_repo.get_by_id(listing_id)
            if not listing:
                raise ListingNotFoundError(str(listing_id))

            if not listing.is_active:
                raise PriceUpdateError("Cannot update price of inactive listing", field="listing_id")

            old_price = listing.ask_price

            # Update on StockX
            try:
                await self.api_client.update_listing_price(
                    listing.stockx_listing_id,
                    float(new_price)
                )
            except Exception as api_error:
                raise handle_api_error("StockX price update", api_error)

            # Update in our database
            try:
                listing.ask_price = new_price
                listing.updated_at = datetime.utcnow()
                await self.listing_repo.update(listing)

                # Record pricing history
                pricing_history = PricingHistory(
                    listing_id=listing.id,
                    old_price=old_price,
                    new_price=new_price,
                    change_reason=reason
                )
                await self.pricing_repo.create(pricing_history)

            except SQLAlchemyError as e:
                raise handle_database_error("update listing price", e)

            logger.info(
                "Updated listing price",
                listing_id=str(listing.id),
                old_price=float(old_price),
                new_price=float(new_price),
                reason=reason
            )

            return listing

        except (PriceUpdateError, ListingNotFoundError, StockXAPIError, DatabaseError):
            raise
        except Exception as e:
            logger.error(
                "Unexpected error updating listing price",
                listing_id=str(listing_id),
                error=str(e)
            )
            raise PriceUpdateError(f"Failed to update listing price: {str(e)}")

    async def sync_listing_status(self) -> Dict[str, int]:
        """Sync all listing statuses with StockX using optimized batch operations"""
        try:
            # Get all active listings from StockX
            stockx_listings = await self.api_client.get_all_listings()
            stockx_listing_map = {listing["listingId"]: listing for listing in stockx_listings}

            # Get our listings with optimized query (no eager loading needed for sync)
            query = select(StockXListing).where(
                StockXListing.is_active == True
            ).order_by(StockXListing.updated_at)

            result = await self.db.execute(query)
            our_listings = result.scalars().all()

            stats = {"updated": 0, "deactivated": 0, "sold": 0}

            # Prepare batch updates for better performance
            listings_to_update = []
            bulk_updates = []

            for listing in our_listings:
                stockx_data = stockx_listing_map.get(listing.stockx_listing_id)

                update_data = {}
                if stockx_data:
                    # Prepare update data
                    new_status = stockx_data.get("status", listing.status)
                    new_is_active = stockx_data.get("isActive", listing.is_active)

                    if (new_status != listing.status or
                        new_is_active != listing.is_active or
                        stockx_data.get("lowestAsk") != listing.current_lowest_ask):

                        update_data = {
                            "status": new_status,
                            "is_active": new_is_active,
                            "current_lowest_ask": stockx_data.get("lowestAsk"),
                            "current_highest_bid": stockx_data.get("highestBid"),
                            "last_price_update": datetime.utcnow()
                        }
                        stats["updated"] += 1
                else:
                    # Listing not found on StockX - might be sold or expired
                    if listing.status == "active":
                        update_data = {
                            "status": "sold",
                            "is_active": False,
                            "last_price_update": datetime.utcnow()
                        }
                        stats["sold"] += 1

                if update_data:
                    bulk_updates.append({
                        "id": listing.id,
                        "update_data": update_data
                    })

            # Perform batch updates for better performance
            if bulk_updates:
                try:
                    for update_item in bulk_updates:
                        await self.db.execute(
                            update(StockXListing)
                            .where(StockXListing.id == update_item["id"])
                            .values(**update_item["update_data"])
                        )
                    await self.db.commit()
                except SQLAlchemyError as e:
                    await self.db.rollback()
                    raise handle_database_error("batch update listings", e)

            logger.info(
                "Synced listing statuses with optimized batch operations",
                total_processed=len(our_listings),
                batch_updates=len(bulk_updates),
                **stats
            )
            return stats

        except StockXAPIError:
            raise
        except Exception as e:
            logger.error("Failed to sync listing status", error=str(e))
            raise handle_api_error("StockX status sync", e)

    async def activate_listing(self, listing_id: UUID) -> bool:
        """Activate a listing on StockX"""
        try:
            listing = await self.listing_repo.get_by_id(listing_id)
            if not listing:
                raise ListingNotFoundError(str(listing_id))

            if listing.is_active:
                logger.warning("Listing already active", listing_id=str(listing_id))
                return True

            try:
                success = await self.api_client.activate_listing(listing.stockx_listing_id)
            except Exception as api_error:
                raise handle_api_error("StockX activate listing", api_error)

            if success:
                try:
                    listing.is_active = True
                    listing.status = "active"
                    await self.listing_repo.update(listing)
                except SQLAlchemyError as e:
                    raise handle_database_error("activate listing", e)

                logger.info("Activated listing", listing_id=str(listing_id))

            return success

        except (ListingNotFoundError, StockXAPIError, DatabaseError):
            raise
        except Exception as e:
            logger.error(
                "Unexpected error activating listing",
                listing_id=str(listing_id),
                error=str(e)
            )
            return False

    async def deactivate_listing(self, listing_id: UUID) -> bool:
        """Deactivate a listing on StockX"""
        try:
            listing = await self.listing_repo.get_by_id(listing_id)
            if not listing:
                raise ListingNotFoundError(str(listing_id))

            if not listing.is_active:
                logger.warning("Listing already inactive", listing_id=str(listing_id))
                return True

            try:
                success = await self.api_client.deactivate_listing(listing.stockx_listing_id)
            except Exception as api_error:
                raise handle_api_error("StockX deactivate listing", api_error)

            if success:
                try:
                    listing.is_active = False
                    listing.status = "inactive"
                    listing.delisted_at = datetime.utcnow()
                    await self.listing_repo.update(listing)
                except SQLAlchemyError as e:
                    raise handle_database_error("deactivate listing", e)

                logger.info("Deactivated listing", listing_id=str(listing_id))

            return success

        except (ListingNotFoundError, StockXAPIError, DatabaseError):
            raise
        except Exception as e:
            logger.error(
                "Unexpected error deactivating listing",
                listing_id=str(listing_id),
                error=str(e)
            )
            return False

    async def get_my_listings(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        include_product: bool = True,
        include_pricing_history: bool = False,
        include_orders: bool = False
    ) -> List[StockXListing]:
        """Get my listings with optional filtering and optimized eager loading"""
        try:
            query = select(StockXListing)

            # Apply filters
            if status:
                query = query.where(StockXListing.status == status)

            # Optimized eager loading with selectinload for better performance
            if include_product:
                query = query.options(
                    selectinload(StockXListing.product)
                )

            if include_pricing_history:
                query = query.options(
                    selectinload(StockXListing.pricing_history)
                )

            if include_orders:
                query = query.options(
                    selectinload(StockXListing.orders)
                )

            # Add comprehensive eager loading for all related data if needed
            if include_product and include_pricing_history and include_orders:
                query = query.options(
                    selectinload(StockXListing.product),
                    selectinload(StockXListing.pricing_history),
                    selectinload(StockXListing.orders)
                )

            # Optimize ordering and limiting
            query = query.order_by(desc(StockXListing.created_at)).limit(limit)

            result = await self.db.execute(query)
            listings = result.scalars().all()

            logger.info(
                "Retrieved listings with optimized loading",
                count=len(listings),
                include_product=include_product,
                include_pricing_history=include_pricing_history,
                include_orders=include_orders,
                status_filter=status
            )

            return listings

        except SQLAlchemyError as e:
            raise handle_database_error("get listings", e)
        except Exception as e:
            logger.error("Failed to get listings", error=str(e))
            return []

    async def _calculate_optimal_price(
        self,
        stockx_product_id: str,
        base_price: Decimal,
        strategy: str = "competitive",
        margin_buffer: float = 5.0
    ) -> Decimal:
        """Calculate optimal selling price based on market data and strategy"""
        try:
            # Get current market data
            market_data = await self.api_client.get_product_market_data(stockx_product_id)

            lowest_ask = market_data.get("lowestAsk")
            highest_bid = market_data.get("highestBid")

            if strategy == "competitive" and lowest_ask:
                # Price just below lowest ask
                optimal_price = Decimal(str(lowest_ask)) - Decimal("1.00")
            elif strategy == "aggressive" and highest_bid:
                # Price at or slightly above highest bid
                optimal_price = Decimal(str(highest_bid)) + Decimal("5.00")
            elif strategy == "premium":
                # Price at base price + margin buffer
                optimal_price = base_price * (1 + Decimal(str(margin_buffer)) / 100)
            else:
                # Fallback to base price + small margin
                optimal_price = base_price * Decimal("1.05")

            # Ensure minimum profitability
            min_price = base_price * Decimal("1.10")  # At least 10% margin

            return max(optimal_price, min_price)

        except Exception as e:
            logger.error("Failed to calculate optimal price", error=str(e))
            # Fallback to base price + 10%
            return base_price * Decimal("1.10")

    async def get_listing_with_full_details(self, listing_id: UUID) -> Optional[StockXListing]:
        """Get a single listing with all related data using optimized eager loading"""
        try:
            query = select(StockXListing).where(
                StockXListing.id == listing_id
            ).options(
                selectinload(StockXListing.product),
                selectinload(StockXListing.pricing_history),
                selectinload(StockXListing.orders)
            )

            result = await self.db.execute(query)
            listing = result.scalar_one_or_none()

            if listing:
                logger.info(
                    "Retrieved listing with full details",
                    listing_id=str(listing_id),
                    has_product=listing.product is not None,
                    pricing_history_count=len(listing.pricing_history) if listing.pricing_history else 0,
                    orders_count=len(listing.orders) if listing.orders else 0
                )

            return listing

        except SQLAlchemyError as e:
            raise handle_database_error("get listing details", e)

    async def get_listings_summary_optimized(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get optimized listing summary using aggregation queries"""
        try:
            from sqlalchemy import func, case

            # Single optimized query with aggregations
            query = select(
                func.count(StockXListing.id).label('total_listings'),
                func.sum(
                    case((StockXListing.status == 'active', 1), else_=0)
                ).label('active_listings'),
                func.sum(
                    case((StockXListing.status == 'inactive', 1), else_=0)
                ).label('inactive_listings'),
                func.sum(
                    case((StockXListing.status == 'sold', 1), else_=0)
                ).label('sold_listings'),
                func.sum(
                    case(
                        (StockXListing.status == 'active', StockXListing.expected_profit),
                        else_=0
                    )
                ).label('total_expected_profit'),
                func.avg(
                    case(
                        (StockXListing.status == 'active', StockXListing.expected_margin),
                        else_=None
                    )
                ).label('avg_expected_margin')
            )

            if user_id:
                # Add user filter if needed (would require user_id field in StockXListing)
                pass

            result = await self.db.execute(query)
            row = result.first()

            # Get most profitable listing separately for efficiency
            most_profitable_query = select(StockXListing).where(
                StockXListing.status == 'active',
                StockXListing.expected_profit.isnot(None)
            ).order_by(desc(StockXListing.expected_profit)).limit(1)

            most_profitable_result = await self.db.execute(most_profitable_query)
            most_profitable = most_profitable_result.scalar_one_or_none()

            summary = {
                'total_listings': row.total_listings or 0,
                'active_listings': row.active_listings or 0,
                'inactive_listings': row.inactive_listings or 0,
                'sold_listings': row.sold_listings or 0,
                'total_expected_profit': float(row.total_expected_profit or 0),
                'avg_expected_margin': float(row.avg_expected_margin or 0),
                'most_profitable_listing': most_profitable
            }

            logger.info(
                "Generated optimized listing summary",
                **{k: v for k, v in summary.items() if k != 'most_profitable_listing'}
            )

            return summary

        except SQLAlchemyError as e:
            raise handle_database_error("get listings summary", e)