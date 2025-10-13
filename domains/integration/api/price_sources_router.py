"""
Price Sources API Router
Unified API endpoints for multi-source pricing data
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db_session
from domains.integration.services.unified_price_import_service import UnifiedPriceImportService

router = APIRouter(prefix="/price-sources", tags=["Price Sources"])


@router.get("/stats")
async def get_price_source_stats(session: AsyncSession = Depends(get_db_session)):
    """
    Get statistics about all price sources

    Returns:
        Statistics grouped by source_type and price_type
    """
    service = UnifiedPriceImportService(session)
    stats = await service.get_price_source_stats()

    return {
        "success": True,
        "stats": stats,
    }


@router.get("/profit-opportunities")
async def get_profit_opportunities_v2(
    min_profit_eur: float = Query(20.0, description="Minimum profit in EUR"),
    min_profit_percentage: float = Query(10.0, description="Minimum profit percentage (ROI)"),
    limit: int = Query(50, le=500, description="Maximum number of results"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get profit opportunities from unified price sources

    Uses the new `profit_opportunities_v2` view which works across ALL price sources
    (Awin, eBay, StockX, GOAT, etc.)

    Args:
        min_profit_eur: Minimum profit in EUR (default: 20.0)
        min_profit_percentage: Minimum ROI % (default: 10.0)
        limit: Max results (default: 50, max: 500)

    Returns:
        List of profit opportunities sorted by profit DESC
    """
    service = UnifiedPriceImportService(session)
    opportunities = await service.get_profit_opportunities(
        min_profit_eur=min_profit_eur, min_profit_percentage=min_profit_percentage, limit=limit
    )

    # Calculate summary stats
    total_profit = sum(opp["profit"]["amount_eur"] for opp in opportunities)
    avg_profit = total_profit / len(opportunities) if opportunities else 0
    avg_roi = (
        sum(opp["profit"]["percentage"] for opp in opportunities) / len(opportunities)
        if opportunities
        else 0
    )
    max_profit = max((opp["profit"]["amount_eur"] for opp in opportunities), default=0)

    return {
        "success": True,
        "message": f"Found {len(opportunities)} profit opportunities across all sources",
        "summary": {
            "total_opportunities": len(opportunities),
            "total_potential_profit_eur": round(total_profit, 2),
            "avg_profit_eur": round(avg_profit, 2),
            "avg_roi_percentage": round(avg_roi, 1),
            "max_profit_eur": round(max_profit, 2),
        },
        "opportunities": opportunities,
    }


@router.get("/sources/{source_type}")
async def get_prices_by_source(
    source_type: str,
    price_type: Optional[str] = Query(None, description="Filter by price_type (retail, resale, etc.)"),
    in_stock_only: bool = Query(True, description="Only show in-stock items"),
    limit: int = Query(100, le=1000),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get all price sources from a specific source

    Args:
        source_type: Source type (awin, stockx, ebay, goat, etc.)
        price_type: Optional price type filter (retail, resale, auction, wholesale)
        in_stock_only: Only show in-stock items
        limit: Max results

    Returns:
        List of price sources
    """
    from sqlalchemy import text

    query = """
        SELECT
            ps.id,
            ps.source_type,
            ps.source_product_id,
            ps.source_name,
            ps.price_type,
            ps.price_cents / 100.0 as price_eur,
            ps.currency,
            ps.in_stock,
            ps.stock_quantity,
            ps.affiliate_link,
            ps.source_url,
            ps.last_updated,
            p.name as product_name,
            p.ean as product_ean,
            p.sku as product_sku,
            b.name as brand_name
        FROM integration.price_sources ps
        JOIN products.products p ON ps.product_id = p.id
        LEFT JOIN core.brands b ON p.brand_id = b.id
        WHERE ps.source_type = :source_type
    """

    params = {"source_type": source_type}

    if price_type:
        query += " AND ps.price_type = :price_type"
        params["price_type"] = price_type

    if in_stock_only:
        query += " AND ps.in_stock = true"

    query += " ORDER BY ps.price_cents DESC LIMIT :limit"
    params["limit"] = limit

    result = await session.execute(text(query), params)
    rows = result.fetchall()

    prices = []
    for row in rows:
        prices.append(
            {
                "id": str(row[0]),
                "source_type": row[1],
                "source_product_id": row[2],
                "source_name": row[3],
                "price_type": row[4],
                "price_eur": float(row[5]) if row[5] else 0.0,
                "currency": row[6],
                "in_stock": row[7],
                "stock_quantity": row[8],
                "affiliate_link": row[9],
                "source_url": row[10],
                "last_updated": row[11].isoformat() if row[11] else None,
                "product": {
                    "name": row[12],
                    "ean": row[13],
                    "sku": row[14],
                    "brand": row[15],
                },
            }
        )

    return {
        "success": True,
        "source_type": source_type,
        "price_type": price_type,
        "count": len(prices),
        "prices": prices,
    }


@router.get("/product/{product_ean}/prices")
async def get_product_prices(
    product_ean: str, session: AsyncSession = Depends(get_db_session)
):
    """
    Get all price sources for a specific product by EAN

    Shows retail and resale prices from all sources for comparison

    Args:
        product_ean: Product EAN/GTIN code

    Returns:
        All prices for the product grouped by type
    """
    from sqlalchemy import text

    query = text("""
        SELECT
            ps.source_type,
            ps.source_name,
            ps.price_type,
            ps.price_cents / 100.0 as price_eur,
            ps.in_stock,
            ps.stock_quantity,
            ps.affiliate_link,
            ps.source_url,
            ps.last_updated,
            s.name as supplier_name
        FROM integration.price_sources ps
        JOIN products.products p ON ps.product_id = p.id
        LEFT JOIN core.suppliers s ON ps.supplier_id = s.id
        WHERE p.ean = :ean
        ORDER BY ps.price_type, ps.price_cents ASC
    """)

    result = await session.execute(query, {"ean": product_ean})
    rows = result.fetchall()

    if not rows:
        return {
            "success": False,
            "message": f"No prices found for product with EAN: {product_ean}",
            "product_ean": product_ean,
            "prices": [],
        }

    # Group by price type
    retail_prices = []
    resale_prices = []
    other_prices = []

    for row in rows:
        price_data = {
            "source_type": row[0],
            "source_name": row[1],
            "price_eur": float(row[3]) if row[3] else 0.0,
            "in_stock": row[4],
            "stock_quantity": row[5],
            "affiliate_link": row[6],
            "source_url": row[7],
            "last_updated": row[8].isoformat() if row[8] else None,
            "supplier_name": row[9],
        }

        if row[2] == "retail":
            retail_prices.append(price_data)
        elif row[2] == "resale":
            resale_prices.append(price_data)
        else:
            other_prices.append(price_data)

    # Calculate profit if both retail and resale exist
    min_retail = min((p["price_eur"] for p in retail_prices), default=0) if retail_prices else 0
    max_resale = max((p["price_eur"] for p in resale_prices), default=0) if resale_prices else 0
    potential_profit = max_resale - min_retail if min_retail > 0 and max_resale > min_retail else 0

    return {
        "success": True,
        "product_ean": product_ean,
        "price_summary": {
            "min_retail_eur": round(min_retail, 2),
            "max_resale_eur": round(max_resale, 2),
            "potential_profit_eur": round(potential_profit, 2),
            "potential_roi_percentage": (
                round((potential_profit / min_retail * 100), 1) if min_retail > 0 else 0
            ),
        },
        "prices": {
            "retail": retail_prices,
            "resale": resale_prices,
            "other": other_prices,
        },
    }


@router.get("/history/{price_source_id}")
async def get_price_history(
    price_source_id: str, limit: int = Query(100, le=1000), session: AsyncSession = Depends(get_db_session)
):
    """
    Get price history for a specific price source

    Shows historical price changes tracked by the automatic trigger

    Args:
        price_source_id: UUID of the price source
        limit: Max history records

    Returns:
        Historical price data
    """
    from sqlalchemy import text

    query = text("""
        SELECT
            ph.price_cents / 100.0 as price_eur,
            ph.in_stock,
            ph.stock_quantity,
            ph.recorded_at,
            ps.source_type,
            ps.source_name,
            p.name as product_name,
            p.ean as product_ean
        FROM integration.price_history ph
        JOIN integration.price_sources ps ON ph.price_source_id = ps.id
        JOIN products.products p ON ps.product_id = p.id
        WHERE ph.price_source_id = CAST(:price_source_id AS uuid)
        ORDER BY ph.recorded_at DESC
        LIMIT :limit
    """)

    result = await session.execute(query, {"price_source_id": price_source_id, "limit": limit})
    rows = result.fetchall()

    if not rows:
        return {
            "success": False,
            "message": f"No price history found for price source: {price_source_id}",
            "history": [],
        }

    history = []
    for row in rows:
        history.append(
            {
                "price_eur": float(row[0]) if row[0] else 0.0,
                "in_stock": row[1],
                "stock_quantity": row[2],
                "recorded_at": row[3].isoformat() if row[3] else None,
            }
        )

    # Calculate price trend
    if len(history) >= 2:
        latest_price = history[0]["price_eur"]
        oldest_price = history[-1]["price_eur"]
        price_change = latest_price - oldest_price
        price_change_pct = (
            round((price_change / oldest_price * 100), 1) if oldest_price > 0 else 0
        )
    else:
        price_change = 0
        price_change_pct = 0

    return {
        "success": True,
        "price_source_id": price_source_id,
        "source_type": rows[0][4],
        "source_name": rows[0][5],
        "product": {"name": rows[0][6], "ean": rows[0][7]},
        "summary": {
            "total_records": len(history),
            "latest_price_eur": history[0]["price_eur"] if history else 0,
            "oldest_price_eur": history[-1]["price_eur"] if history else 0,
            "price_change_eur": round(price_change, 2),
            "price_change_percentage": price_change_pct,
        },
        "history": history,
    }
