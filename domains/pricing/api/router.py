"""
Pricing API Router - Smart pricing recommendations and market analysis
"""

from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from domains.inventory.services.inventory_service import InventoryService
from shared.database.connection import get_db_session

from ..repositories.pricing_repository import PricingRepository
from ..services.pricing_engine import PricingContext, PricingEngine, PricingStrategy
from ..services.smart_pricing_service import SmartPricingService

logger = structlog.get_logger(__name__)

router = APIRouter()


# Pydantic models for API requests/responses
class PricingRequest(BaseModel):
    product_id: UUID
    inventory_id: Optional[UUID] = None
    strategy: Optional[PricingStrategy] = PricingStrategy.DYNAMIC
    target_margin: Optional[Decimal] = None
    condition: str = "new"
    size: Optional[str] = None


class PricingRecommendation(BaseModel):
    product_id: UUID
    suggested_price: Decimal
    strategy_used: str
    confidence_score: Decimal
    margin_percent: Decimal
    markup_percent: Decimal
    reasoning: List[str]
    market_position: Optional[str] = None
    price_range: Optional[Dict[str, Decimal]] = None


class MarketAnalysis(BaseModel):
    product_id: UUID
    current_market_price: Optional[Decimal]
    price_trend: str  # "increasing", "decreasing", "stable"
    market_position: str  # "below", "at", "above" market
    competitor_count: int
    demand_score: Decimal
    supply_score: Decimal
    recommended_action: str


class ProfitabilityCheckRequest(BaseModel):
    """Request model for pre-import profitability evaluation"""

    ean: Optional[str] = None  # EAN from affiliate feed
    sku: Optional[str] = None  # SKU (alternative identifier)
    supplier_price: float
    brand: str
    model: str
    size: Optional[str] = None


class ProfitabilityCheckResponse(BaseModel):
    """Response model for profitability evaluation"""

    profitable: bool
    margin_percent: float
    absolute_profit: float
    supplier_price: float
    market_price: Optional[float]
    should_import: bool
    reason: str
    min_margin_threshold: float


class BatchProfitabilityRequest(BaseModel):
    """Request model for batch profitability evaluation"""

    products: List[ProfitabilityCheckRequest]
    max_batch_size: int = 1000


class BatchProfitabilityResponse(BaseModel):
    """Response model for batch profitability evaluation"""

    total_evaluated: int
    profitable_count: int
    unprofitable_count: int
    processing_time_seconds: float
    results: List[ProfitabilityCheckResponse]


def get_pricing_repository(db: AsyncSession = Depends(get_db_session)) -> PricingRepository:
    return PricingRepository(db)


def get_pricing_engine(db: AsyncSession = Depends(get_db_session)) -> PricingEngine:
    pricing_repo = PricingRepository(db)
    return PricingEngine(pricing_repo, db)


@router.post(
    "/recommend",
    summary="Get Pricing Recommendation",
    description="Get AI-powered pricing recommendations for a product using advanced algorithms",
    response_model=PricingRecommendation,
)
async def get_pricing_recommendation(
    request: PricingRequest,
    pricing_engine: PricingEngine = Depends(get_pricing_engine),
    db: AsyncSession = Depends(get_db_session),
):
    """Get intelligent pricing recommendation for a product"""
    logger.info(
        "Received pricing recommendation request",
        product_id=str(request.product_id),
        strategy=request.strategy.value,
    )

    try:
        # Get product and inventory data
        from sqlalchemy import select

        from shared.database.models import InventoryItem, Product

        # Fetch product
        product_result = await db.execute(select(Product).where(Product.id == request.product_id))
        product = product_result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Fetch inventory item if provided
        inventory_item = None
        if request.inventory_id:
            inventory_result = await db.execute(
                select(InventoryItem).where(InventoryItem.id == request.inventory_id)
            )
            inventory_item = inventory_result.scalar_one_or_none()

        # Create pricing context
        context = PricingContext(
            product=product,
            inventory_item=inventory_item,
            condition=request.condition,
            size=request.size,
            target_margin=request.target_margin,
        )

        # Get pricing recommendation
        result = await pricing_engine.calculate_optimal_price(
            context=context, strategy=request.strategy
        )

        return PricingRecommendation(
            product_id=request.product_id,
            suggested_price=result.suggested_price,
            strategy_used=result.strategy_used.value,
            confidence_score=result.confidence_score,
            margin_percent=result.margin_percent,
            markup_percent=result.markup_percent,
            reasoning=result.reasoning,
            market_position=result.market_position,
            price_range=result.price_range,
        )

    except Exception as e:
        logger.error(
            "Failed to generate pricing recommendation",
            product_id=str(request.product_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to generate pricing recommendation: {str(e)}"
        )


@router.get(
    "/market-analysis/{product_id}",
    summary="Get Market Analysis",
    description="Analyze market conditions and competitive landscape for a product",
    response_model=MarketAnalysis,
)
async def get_market_analysis(
    product_id: UUID,
    pricing_engine: PricingEngine = Depends(get_pricing_engine),
    db: AsyncSession = Depends(get_db_session),
):
    """Get comprehensive market analysis for a product"""
    logger.info("Fetching market analysis", product_id=str(product_id))

    try:
        # Get product
        from sqlalchemy import select

        from shared.database.models import Product

        product_result = await db.execute(select(Product).where(Product.id == product_id))
        product = product_result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Get market analysis from pricing engine
        market_data = await pricing_engine.analyze_market_conditions(product)

        return MarketAnalysis(
            product_id=product_id,
            current_market_price=market_data.get("current_price"),
            price_trend=market_data.get("trend", "stable"),
            market_position=market_data.get("position", "unknown"),
            competitor_count=market_data.get("competitors", 0),
            demand_score=market_data.get("demand_score", Decimal("0.5")),
            supply_score=market_data.get("supply_score", Decimal("0.5")),
            recommended_action=market_data.get("recommended_action", "monitor"),
        )

    except Exception as e:
        logger.error(
            "Failed to fetch market analysis",
            product_id=str(product_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to fetch market analysis: {str(e)}")


@router.get(
    "/strategies",
    summary="Get Available Pricing Strategies",
    description="List all available pricing strategies with descriptions",
)
async def get_pricing_strategies():
    """Get list of available pricing strategies"""
    strategies = {
        "cost_plus": {
            "name": "Cost Plus",
            "description": "Add fixed margin to product cost",
            "use_case": "Simple, predictable pricing",
        },
        "market_based": {
            "name": "Market Based",
            "description": "Price based on current market conditions",
            "use_case": "Competitive positioning",
        },
        "competitive": {
            "name": "Competitive",
            "description": "Price to beat or match competitors",
            "use_case": "Market penetration",
        },
        "value_based": {
            "name": "Value Based",
            "description": "Price based on perceived customer value",
            "use_case": "Premium positioning",
        },
        "dynamic": {
            "name": "Dynamic",
            "description": "AI-powered adaptive pricing",
            "use_case": "Maximum profit optimization",
        },
    }
    return strategies


@router.post(
    "/evaluate-profitability",
    summary="Evaluate Product Profitability (Pre-Import)",
    description="Check if a product from affiliate feed would be profitable BEFORE importing to catalog. Used by n8n workflows.",
    response_model=ProfitabilityCheckResponse,
)
async def evaluate_profitability(
    request: ProfitabilityCheckRequest,
    db_session: AsyncSession = Depends(get_db_session),
):
    """
    Evaluate profitability of a product before import.

    This endpoint is designed for n8n workflows to pre-filter products from
    affiliate feeds (Webgains, Awin) before importing them to the catalog.

    Args:
        request: Product details including EAN, supplier price, brand, model

    Returns:
        Profitability assessment with margin calculations and import recommendation
    """
    logger.info(
        "Evaluating product profitability",
        ean=request.ean,
        brand=request.brand,
        supplier_price=request.supplier_price,
    )

    try:
        # Constants (could be moved to config/env vars)
        MIN_MARGIN_THRESHOLD = (
            15.0  # 15% minimum margin (matches AutoListingService "Quick Turnover Items")
        )
        OPERATIONAL_COST_FIXED = 5.0  # €5 fixed operational cost per item

        # Premium brands worth querying StockX for
        PREMIUM_BRANDS = {
            "Nike",
            "Jordan",
            "Air Jordan",
            "Adidas",
            "Yeezy",
            "New Balance",
            "Asics",
            "Puma",
            "Reebok",
            "Vans",
            "Converse",
            "Supreme",
            "Off-White",
            "Bape",
            "Palace",
        }

        # Try to get market price from StockX or existing catalog
        market_price = None
        reason = ""
        existing_product = None

        # Step 1: Check if product already exists in catalog by SKU or EAN
        from sqlalchemy import or_, select

        from shared.database.models import Product

        # Try to find product by SKU first (if provided), then by EAN
        if request.sku or request.ean:
            conditions = []
            if request.sku:
                conditions.append(Product.sku == request.sku)
            if request.ean:
                conditions.append(Product.ean == request.ean)

            product_query = await db_session.execute(
                select(Product).where(or_(*conditions)).limit(1)
            )
            existing_product = product_query.scalar_one_or_none()

        if existing_product:
            # Product exists in catalog - use retail price
            market_price = (
                float(existing_product.retail_price) if existing_product.retail_price else None
            )
            reason = "Market price from existing catalog entry (retail_price)"
            logger.info(
                "Found existing product in catalog",
                product_id=str(existing_product.id),
                sku=existing_product.sku,
                ean=existing_product.ean,
                market_price=market_price,
            )

        # Step 2: For unknown products, check if it's a premium brand worth querying StockX
        if not existing_product:
            brand_normalized = request.brand.strip().title()
            is_premium_brand = any(premium in brand_normalized for premium in PREMIUM_BRANDS)

            if is_premium_brand:
                # Premium brand - query StockX API for market data
                try:
                    from domains.integration.services.stockx_service import StockXService

                    stockx_service = StockXService(db_session)

                    # Search StockX by brand + model (EAN search not supported by StockX API)
                    search_query = f"{request.brand} {request.model}"
                    logger.info(
                        "Querying StockX for premium brand product",
                        brand=request.brand,
                        search_query=search_query,
                    )

                    # Try to find product on StockX
                    stockx_products = await stockx_service.search_products(
                        query=search_query, limit=1
                    )

                    if stockx_products and len(stockx_products) > 0:
                        stockx_product = stockx_products[0]
                        # Use lowest_ask as market price (conservative estimate)
                        market_price = float(stockx_product.get("market", {}).get("lowestAsk", 0))
                        if market_price > 0:
                            reason = "Market price from StockX (lowest ask)"
                            logger.info(
                                "Found product on StockX",
                                stockx_product_id=stockx_product.get("id"),
                                market_price=market_price,
                            )
                        else:
                            reason = "Found on StockX but no valid market price"
                    else:
                        reason = "Not found on StockX - no market data available"

                except Exception as stockx_error:
                    logger.warning(
                        "Failed to fetch StockX market data",
                        brand=request.brand,
                        error=str(stockx_error),
                    )
                    reason = f"StockX query failed: {str(stockx_error)}"
            else:
                # Non-premium brand - skip import
                reason = "Non-premium brand - not worth importing without existing catalog entry"
                logger.info(
                    "Skipping non-premium brand product",
                    brand=request.brand,
                )

        # Step 3: Fallback to estimation only if we have market data or it's premium
        if not market_price and existing_product:
            # Product in catalog but no retail price - use fallback estimation
            market_price = request.supplier_price * 1.25
            reason = "Estimated market price (product in catalog but no retail_price)"
            logger.info(
                "Using estimated market price for catalog product",
                product_id=str(existing_product.id),
                estimated_price=market_price,
            )

        # Calculate profitability metrics (only if we have market price)
        if market_price is None or market_price == 0:
            # No market data - cannot evaluate profitability
            absolute_profit = 0.0
            margin_percent = 0.0
            is_profitable = False
            should_import = False
            if not reason:  # Only set if not already set
                reason = "Cannot evaluate: No market data available"
        else:
            # Calculate profitability with available market data
            absolute_profit = market_price - request.supplier_price - OPERATIONAL_COST_FIXED
            margin_percent = (
                ((market_price - request.supplier_price) / market_price) * 100
                if market_price > 0
                else 0.0
            )

            # Determine if profitable
            is_profitable = margin_percent >= MIN_MARGIN_THRESHOLD and absolute_profit > 0
            should_import = is_profitable

            # Enhanced reasoning
            if is_profitable:
                reason = f"Profitable: {margin_percent:.1f}% margin (min: {MIN_MARGIN_THRESHOLD}%)"
            elif absolute_profit <= 0:
                reason = f"Unprofitable: Negative profit (€{absolute_profit:.2f})"
            else:
                reason = f"Below threshold: {margin_percent:.1f}% margin < {MIN_MARGIN_THRESHOLD}% required"

        response = ProfitabilityCheckResponse(
            profitable=is_profitable,
            margin_percent=round(margin_percent, 2),
            absolute_profit=round(absolute_profit, 2),
            supplier_price=request.supplier_price,
            market_price=market_price,
            should_import=should_import,
            reason=reason,
            min_margin_threshold=MIN_MARGIN_THRESHOLD,
        )

        logger.info(
            "Profitability evaluation completed",
            ean=request.ean,
            profitable=is_profitable,
            margin_percent=margin_percent,
        )

        return response

    except Exception as e:
        logger.error(
            "Failed to evaluate profitability",
            ean=request.ean,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Profitability evaluation failed: {str(e)}")


@router.post(
    "/evaluate-profitability-batch",
    summary="Batch Evaluate Product Profitability (Pre-Import)",
    description="Check profitability for multiple products from affiliate feed in a single request. Optimized for n8n workflows processing large product feeds.",
    response_model=BatchProfitabilityResponse,
)
async def evaluate_profitability_batch(
    request: BatchProfitabilityRequest,
    db_session: AsyncSession = Depends(get_db_session),
):
    """
    Evaluate profitability of multiple products before import (batch processing).

    This endpoint processes up to 1000 products per request to efficiently filter
    large affiliate feeds (Webgains, Awin) before importing to catalog.

    Args:
        request: Batch of product details including EAN, supplier price, brand, model

    Returns:
        Batch profitability assessment with aggregated statistics and individual results
    """
    import time

    start_time = time.time()

    logger.info(
        "Starting batch profitability evaluation",
        total_products=len(request.products),
    )

    # Validate batch size
    if len(request.products) > request.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds maximum of {request.max_batch_size} products",
        )

    if len(request.products) == 0:
        raise HTTPException(status_code=400, detail="Products list cannot be empty")

    try:
        # Constants (shared with single endpoint)
        MIN_MARGIN_THRESHOLD = 15.0
        OPERATIONAL_COST_FIXED = 5.0

        # Premium brands worth querying StockX for
        PREMIUM_BRANDS = {
            "Nike",
            "Jordan",
            "Air Jordan",
            "Adidas",
            "Yeezy",
            "New Balance",
            "Asics",
            "Puma",
            "Reebok",
            "Vans",
            "Converse",
            "Supreme",
            "Off-White",
            "Bape",
            "Palace",
        }

        results = []
        profitable_count = 0
        unprofitable_count = 0

        from sqlalchemy import or_, select

        from shared.database.models import Product

        # Process each product
        for product_request in request.products:
            try:
                # Try to get market price from existing catalog or StockX
                market_price = None
                reason = ""
                existing_product = None

                # Step 1: Check if product exists in catalog by SKU or EAN
                if product_request.sku or product_request.ean:
                    conditions = []
                    if product_request.sku:
                        conditions.append(Product.sku == product_request.sku)
                    if product_request.ean:
                        conditions.append(Product.ean == product_request.ean)

                    product_query = await db_session.execute(
                        select(Product).where(or_(*conditions)).limit(1)
                    )
                    existing_product = product_query.scalar_one_or_none()

                if existing_product:
                    market_price = (
                        float(existing_product.retail_price)
                        if existing_product.retail_price
                        else None
                    )
                    reason = "Market price from existing catalog entry"

                # Step 2: For unknown products, check if premium brand (worth StockX query)
                is_premium_brand = False
                if not existing_product and product_request.brand:
                    brand_normalized = product_request.brand.strip().title()
                    is_premium_brand = any(
                        premium in brand_normalized for premium in PREMIUM_BRANDS
                    )

                    if is_premium_brand:
                        # Premium brand - try StockX lookup for market price
                        try:
                            from domains.integration.services.stockx_catalog_service import (
                                StockXCatalogService,
                            )
                            from domains.integration.services.stockx_service import StockXService

                            stockx_service = StockXService(db_session)
                            catalog_service = StockXCatalogService(stockx_service)

                            # Search StockX
                            search_query = f"{product_request.brand} {product_request.model}"
                            search_results = await catalog_service.search_catalog(
                                query=search_query, page_number=1, page_size=1
                            )

                            if search_results and search_results.get("products"):
                                stockx_product = search_results["products"][0]
                                stockx_product_id = stockx_product.get("productId")

                                if stockx_product_id:
                                    # Get variants
                                    variants = await catalog_service.get_product_variants(
                                        stockx_product_id
                                    )

                                    if variants and len(variants) > 0:
                                        # Use first variant or match by size if provided
                                        variant = variants[0]
                                        if product_request.size:
                                            # Try to find matching size
                                            for v in variants:
                                                size_value = v.get("sizeChart", {}).get(
                                                    "baseSize", ""
                                                )
                                                if size_value == product_request.size:
                                                    variant = v
                                                    break

                                        variant_id = variant.get("variantId")
                                        if variant_id:
                                            # Get market data
                                            market_data = await catalog_service.get_market_data(
                                                product_id=stockx_product_id,
                                                variant_id=variant_id,
                                                currency_code="EUR",
                                            )

                                            highest_bid = market_data.get("highestBidAmount")
                                            if highest_bid:
                                                market_price = float(highest_bid)
                                                reason = "Market price from StockX highest_bid"

                        except Exception as stockx_error:
                            logger.debug(
                                "StockX lookup failed in batch mode",
                                brand=product_request.brand,
                                model=product_request.model,
                                error=str(stockx_error),
                            )
                            # Continue without market_price - will be handled below

                    else:
                        # Non-premium brand - skip without StockX query
                        reason = "Non-premium brand - skipped"
                        # Leave market_price as None - will be marked as should_import=False below

                # Step 3: Fallback to estimation only for existing products
                if not market_price and existing_product:
                    market_price = product_request.supplier_price * 1.25
                    reason = "Estimated market price (product in catalog but no retail_price)"

                # Calculate profitability metrics (only if we have market price)
                if market_price is None or market_price == 0:
                    # Special case: Premium brands without market price should still be imported
                    # The product import endpoint will do StockX enrichment
                    if is_premium_brand:
                        absolute_profit = 0.0
                        margin_percent = 0.0
                        is_profitable = False
                        should_import = True  # ✅ Import premium brands for enrichment
                        if not reason:
                            reason = "Premium brand - import for StockX enrichment"
                        profitable_count += 1  # Count as potential profitable
                    else:
                        # No market data - cannot evaluate profitability
                        absolute_profit = 0.0
                        margin_percent = 0.0
                        is_profitable = False
                        should_import = False
                        if not reason:
                            reason = "Cannot evaluate: No market data available"
                        unprofitable_count += 1
                else:
                    # Calculate profitability with available market data
                    absolute_profit = (
                        market_price - product_request.supplier_price - OPERATIONAL_COST_FIXED
                    )
                    margin_percent = (
                        ((market_price - product_request.supplier_price) / market_price) * 100
                        if market_price > 0
                        else 0.0
                    )

                    # Determine if profitable
                    is_profitable = margin_percent >= MIN_MARGIN_THRESHOLD and absolute_profit > 0
                    should_import = is_profitable

                    # Enhanced reasoning
                    if is_profitable:
                        reason = f"Profitable: {margin_percent:.1f}% margin (min: {MIN_MARGIN_THRESHOLD}%)"
                        profitable_count += 1
                    elif absolute_profit <= 0:
                        reason = f"Unprofitable: Negative profit (€{absolute_profit:.2f})"
                        unprofitable_count += 1
                    else:
                        reason = f"Below threshold: {margin_percent:.1f}% margin < {MIN_MARGIN_THRESHOLD}% required"
                        unprofitable_count += 1

                result = ProfitabilityCheckResponse(
                    profitable=is_profitable,
                    margin_percent=round(margin_percent, 2),
                    absolute_profit=round(absolute_profit, 2),
                    supplier_price=product_request.supplier_price,
                    market_price=market_price,
                    should_import=should_import,
                    reason=reason,
                    min_margin_threshold=MIN_MARGIN_THRESHOLD,
                )

                results.append(result)

            except Exception as product_error:
                logger.warning(
                    "Failed to evaluate individual product in batch",
                    ean=product_request.ean,
                    error=str(product_error),
                )
                # Add failed result with error reason
                results.append(
                    ProfitabilityCheckResponse(
                        profitable=False,
                        margin_percent=0.0,
                        absolute_profit=0.0,
                        supplier_price=product_request.supplier_price,
                        market_price=None,
                        should_import=False,
                        reason=f"Evaluation failed: {str(product_error)}",
                        min_margin_threshold=MIN_MARGIN_THRESHOLD,
                    )
                )
                unprofitable_count += 1

        processing_time = time.time() - start_time

        response = BatchProfitabilityResponse(
            total_evaluated=len(request.products),
            profitable_count=profitable_count,
            unprofitable_count=unprofitable_count,
            processing_time_seconds=round(processing_time, 2),
            results=results,
        )

        logger.info(
            "Batch profitability evaluation completed",
            total_evaluated=len(request.products),
            profitable_count=profitable_count,
            unprofitable_count=unprofitable_count,
            processing_time_seconds=processing_time,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to evaluate batch profitability",
            total_products=len(request.products),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Batch profitability evaluation failed: {str(e)}"
        )


# =====================================================
# SMART PRICING ENDPOINTS
# =====================================================


@router.post(
    "/smart/optimize-inventory",
    summary="Smart Inventory Pricing Optimization",
    description="Optimize pricing for entire inventory using AI and real-time StockX market data",
)
async def optimize_inventory_pricing(
    strategy: str = Query(
        "profit_maximization",
        description="Repricing strategy: profit_maximization, market_competitive, quick_turnover, premium_positioning",
    ),
    limit: int = Query(50, description="Maximum items to optimize (1-100)"),
    db_session: AsyncSession = Depends(get_db_session),
):
    """Optimize pricing for inventory using smart algorithms"""
    logger.info("Starting smart inventory pricing optimization", strategy=strategy, limit=limit)

    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    try:
        smart_pricing = SmartPricingService(db_session)

        # Get inventory items to optimize
        inventory_service = InventoryService(db_session)
        items = await inventory_service.get_items_for_repricing(limit=limit)

        # Run optimization
        optimization_result = await smart_pricing.optimize_inventory_pricing(
            inventory_items=items, repricing_strategy=strategy
        )

        return {
            "success": True,
            "message": f"Optimized pricing for {optimization_result['successful_optimizations']} items",
            "data": optimization_result,
        }

    except Exception as e:
        logger.error("Smart pricing optimization failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.get(
    "/smart/recommend/{item_id}",
    summary="Get Smart Price Recommendation",
    description="Get AI-powered price recommendation for specific inventory item with market analysis",
)
async def get_smart_price_recommendation(
    item_id: UUID,
    target_days: Optional[int] = Query(None, description="Target sell timeframe in days"),
    db_session: AsyncSession = Depends(get_db_session),
):
    """Get intelligent price recommendation for specific item"""
    logger.info("Getting smart price recommendation", item_id=str(item_id))

    try:
        inventory_service = InventoryService(db_session)
        inventory_item = await inventory_service.get_item_by_id(item_id)

        if not inventory_item:
            raise HTTPException(status_code=404, detail="Inventory item not found")

        smart_pricing = SmartPricingService(db_session)
        recommendation = await smart_pricing.get_dynamic_price_recommendation(
            inventory_item=inventory_item, target_sell_timeframe=target_days
        )

        return {
            "success": True,
            "message": "Price recommendation generated successfully",
            "data": recommendation,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get price recommendation", item_id=str(item_id), error=str(e))
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


@router.post(
    "/smart/auto-reprice",
    summary="Implement Automatic Repricing",
    description="Automatically reprice inventory based on market movements and custom rules",
)
async def implement_auto_repricing(
    dry_run: bool = Query(True, description="Run simulation without actual price changes"),
    price_drop_threshold: float = Query(5.0, description="Price drop % to trigger repricing"),
    max_increase: float = Query(10.0, description="Maximum price increase % per adjustment"),
    min_margin: float = Query(15.0, description="Minimum profit margin to maintain"),
    db_session: AsyncSession = Depends(get_db_session),
):
    """Implement automatic repricing based on market conditions"""
    logger.info("Starting auto-repricing", dry_run=dry_run)

    try:
        repricing_rules = {
            "price_drop_threshold": price_drop_threshold,
            "max_price_increase": max_increase,
            "min_margin_percent": min_margin,
            "check_interval_hours": 6,
            "enabled_categories": ["footwear", "streetwear", "accessories"],
        }

        smart_pricing = SmartPricingService(db_session)
        repricing_result = await smart_pricing.implement_auto_repricing(
            repricing_rules=repricing_rules, dry_run=dry_run
        )

        return {
            "success": True,
            "message": f"Auto-repricing {'simulated' if dry_run else 'completed'}: {repricing_result['total_adjustments']} adjustments made",
            "data": repricing_result,
        }

    except Exception as e:
        logger.error("Auto-repricing failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Auto-repricing failed: {str(e)}")


@router.get(
    "/smart/market-trends",
    summary="Analyze Market Trends",
    description="Analyze market trends for pricing insights and investment opportunities",
)
async def analyze_market_trends(
    days: int = Query(30, description="Time horizon in days (7-90)"),
    limit: int = Query(20, description="Number of products to analyze (1-50)"),
    db_session: AsyncSession = Depends(get_db_session),
):
    """Analyze market trends for strategic pricing insights"""
    logger.info("Analyzing market trends", days=days, limit=limit)

    if days < 7 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 7 and 90")
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 50")

    try:
        smart_pricing = SmartPricingService(db_session)
        trends_analysis = await smart_pricing.analyze_market_trends(time_horizon_days=days)

        return {
            "success": True,
            "message": f"Market trends analyzed for {len(trends_analysis['product_trends'])} products",
            "data": trends_analysis,
        }

    except Exception as e:
        logger.error("Market trends analysis failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Trends analysis failed: {str(e)}")


@router.get(
    "/smart/profit-forecast",
    summary="Profit Optimization Forecast",
    description="Forecast potential profit improvements with smart pricing strategies",
)
async def get_profit_forecast(
    strategy: str = Query("profit_maximization", description="Optimization strategy"),
    timeframe_days: int = Query(30, description="Forecast timeframe in days"),
    db_session: AsyncSession = Depends(get_db_session),
):
    """Generate profit optimization forecast"""
    logger.info("Generating profit forecast", strategy=strategy, timeframe=timeframe_days)

    try:
        smart_pricing = SmartPricingService(db_session)
        inventory_service = InventoryService(db_session)

        # Get current inventory value
        inventory_summary = await inventory_service.get_detailed_summary()
        current_value = inventory_summary.get("total_value", 0)

        # Simulate optimization on sample of inventory
        sample_items = await inventory_service.get_items_for_repricing(limit=20)
        optimization_sample = await smart_pricing.optimize_inventory_pricing(
            inventory_items=sample_items, repricing_strategy=strategy
        )

        # Extrapolate results
        if optimization_sample["total_items_processed"] > 0:
            avg_improvement = (
                optimization_sample["potential_profit_increase"]
                / optimization_sample["total_items_processed"]
            )
            total_inventory_items = inventory_summary.get("total_items", 1)
            projected_improvement = avg_improvement * total_inventory_items
        else:
            projected_improvement = 0

        forecast = {
            "current_inventory_value": float(current_value),
            "projected_profit_increase": float(projected_improvement),
            "projected_improvement_percent": round(
                (projected_improvement / max(current_value, 1)) * 100, 2
            ),
            "strategy_used": strategy,
            "forecast_timeframe_days": timeframe_days,
            "confidence_level": "medium",  # Based on sample size
            "sample_results": optimization_sample,
        }

        return {
            "success": True,
            "message": f"Profit forecast generated: ${projected_improvement:.2f} potential increase",
            "data": forecast,
        }

    except Exception as e:
        logger.error("Profit forecast failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Forecast failed: {str(e)}")


# Pricing rules endpoint removed - use external configuration
async def get_pricing_rules(pricing_repo: PricingRepository = Depends(get_pricing_repository)):
    """Get active pricing rules"""
    try:
        rules = await pricing_repo.get_active_rules()
        multipliers = await pricing_repo.get_brand_multipliers()

        return {
            "rules": [
                {
                    "id": str(rule.id),
                    "name": rule.name,
                    "rule_type": rule.rule_type,
                    "conditions": rule.conditions,
                    "actions": rule.actions,
                    "priority": rule.priority,
                    "is_active": rule.is_active,
                }
                for rule in rules
            ],
            "brand_multipliers": [
                {
                    "brand_id": str(mult.brand_id),
                    "brand_name": mult.brand.name if mult.brand else "Unknown",
                    "multiplier": float(mult.multiplier),
                    "category": mult.category,
                    "condition": mult.condition,
                }
                for mult in multipliers
            ],
        }

    except Exception as e:
        logger.error("Failed to fetch pricing rules", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch pricing rules: {str(e)}")


# Pricing insights endpoint removed - redundant with Analytics
# Function removed - redundant with Analytics


# Smart Pricing Auto-Repricing Status and Control Endpoints
@router.get(
    "/smart/auto-repricing/status",
    summary="Get Auto-Repricing Status",
    description="Get current status of the auto-repricing system",
)
async def get_auto_repricing_status(db_session: AsyncSession = Depends(get_db_session)):
    """Get auto-repricing system status"""
    logger.info("Getting auto-repricing status")

    try:
        smart_pricing = SmartPricingService(db_session)
        status = await smart_pricing.get_auto_repricing_status()

        return {
            "enabled": status.get("enabled", False),
            "last_run": status.get("last_run"),
            "items_repriced": status.get("items_repriced", 0),
            "strategy": status.get("strategy", "profit_maximization"),
            "next_run": status.get("next_run"),
            "rules_applied": status.get("rules_applied", 0),
        }

    except Exception as e:
        logger.error("Failed to get auto-repricing status", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get auto-repricing status: {str(e)}"
        )


class AutoRepricingToggleRequest(BaseModel):
    enabled: bool


@router.post(
    "/smart/auto-repricing/toggle",
    summary="Toggle Auto-Repricing",
    description="Enable or disable the auto-repricing system",
)
async def toggle_auto_repricing(
    request: AutoRepricingToggleRequest, db_session: AsyncSession = Depends(get_db_session)
):
    """Toggle auto-repricing system on/off"""
    logger.info("Toggling auto-repricing", enabled=request.enabled)

    try:
        smart_pricing = SmartPricingService(db_session)
        result = await smart_pricing.toggle_auto_repricing(request.enabled)

        return {
            "success": True,
            "enabled": result.get("enabled", request.enabled),
            "message": f"Auto-repricing {'enabled' if request.enabled else 'disabled'} successfully",
        }

    except Exception as e:
        logger.error("Failed to toggle auto-repricing", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to toggle auto-repricing: {str(e)}")
