"""
Awin-StockX Enrichment Service
Matches Awin products to StockX via EAN and fetches market data
Built for reproducibility and scalability with Budibase integration
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from domains.integration.services.stockx_catalog_service import StockXCatalogService
from domains.integration.services.stockx_service import StockXService

logger = structlog.get_logger(__name__)


class AwinStockXEnrichmentService:
    """
    Service for enriching Awin products with StockX market data

    Features:
    - EAN-based matching
    - Rate limiting (configurable)
    - Progress tracking
    - Batch processing
    - Reproducible and scalable
    """

    def __init__(
        self,
        session: AsyncSession,
        rate_limit_requests_per_minute: int = 60,  # Conservative default
        batch_size: int = 50,
    ):
        self.session = session
        self.stockx_service = StockXService(session)
        self.catalog_service = StockXCatalogService(self.stockx_service)

        # Rate limiting configuration
        self.rate_limit = rate_limit_requests_per_minute
        self.request_interval = 60.0 / rate_limit_requests_per_minute  # seconds between requests
        self.batch_size = batch_size

        logger.info(
            "Enrichment service initialized",
            rate_limit=rate_limit_requests_per_minute,
            request_interval=f"{self.request_interval:.2f}s",
            batch_size=batch_size,
        )

    async def create_enrichment_job(self, job_type: str = "stockx_match") -> UUID:
        """Create a new enrichment job and return its ID"""
        job_id = uuid4()

        # Count total products to process
        count_query = text(
            """
            SELECT COUNT(*) as total
            FROM integration.awin_products
            WHERE ean IS NOT NULL
              AND in_stock = true
              AND (enrichment_status = 'pending' OR enrichment_status IS NULL OR last_enriched_at IS NULL)
        """
        )

        result = await self.session.execute(count_query)
        total_products = result.fetchone().total

        # Create job record
        insert_query = text(
            """
            INSERT INTO integration.awin_enrichment_jobs
                (id, job_type, status, total_products, started_at)
            VALUES
                (:job_id, :job_type, 'running', :total_products, NOW())
        """
        )

        await self.session.execute(
            insert_query,
            {"job_id": str(job_id), "job_type": job_type, "total_products": total_products},
        )
        await self.session.commit()

        logger.info("Enrichment job created", job_id=str(job_id), total_products=total_products)
        return job_id

    async def update_job_progress(self, job_id: UUID, processed: int, matched: int, failed: int):
        """Update job progress"""
        update_query = text(
            """
            UPDATE integration.awin_enrichment_jobs
            SET processed_products = :processed,
                matched_products = :matched,
                failed_products = :failed,
                updated_at = NOW()
            WHERE id = :job_id
        """
        )

        await self.session.execute(
            update_query,
            {"job_id": str(job_id), "processed": processed, "matched": matched, "failed": failed},
        )
        await self.session.commit()

    async def complete_job(
        self,
        job_id: UUID,
        status: str,
        results_summary: Dict[str, Any],
        error_log: Optional[str] = None,
    ):
        """Mark job as completed"""
        import json

        update_query = text(
            """
            UPDATE integration.awin_enrichment_jobs
            SET status = :status,
                completed_at = NOW(),
                results_summary = CAST(:results_summary AS jsonb),
                error_log = :error_log,
                updated_at = NOW()
            WHERE id = :job_id
        """
        )

        await self.session.execute(
            update_query,
            {
                "job_id": str(job_id),
                "status": status,
                "results_summary": json.dumps(results_summary),
                "error_log": error_log,
            },
        )
        await self.session.commit()

        logger.info("Enrichment job completed", job_id=str(job_id), status=status)

    async def enrich_all_products(
        self, job_id: Optional[UUID] = None, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Main enrichment method - matches all Awin products with StockX

        Args:
            job_id: Optional job ID for tracking (creates new if None)
            limit: Optional limit for testing (processes all if None)

        Returns:
            Dict with enrichment results
        """
        if job_id is None:
            job_id = await self.create_enrichment_job()

        stats = {
            "total_processed": 0,
            "matched": 0,
            "not_found": 0,
            "errors": 0,
            "started_at": datetime.utcnow().isoformat(),
        }

        errors_log = []

        try:
            # Get products to enrich (in stock, with EAN, not yet enriched)
            products_query = text(
                """
                SELECT
                    id,
                    awin_product_id,
                    product_name,
                    brand_name,
                    size,
                    ean,
                    retail_price_cents
                FROM integration.awin_products
                WHERE ean IS NOT NULL
                  AND ean != ''
                  AND in_stock = true
                  AND (enrichment_status = 'pending' OR enrichment_status IS NULL OR last_enriched_at IS NULL)
                ORDER BY retail_price_cents ASC
                """
                + (f"LIMIT {limit}" if limit else "")
            )

            result = await self.session.execute(products_query)
            products = result.fetchall()

            logger.info(f"Starting enrichment for {len(products)} products", job_id=str(job_id))

            # Process in batches with rate limiting
            for i, product in enumerate(products, 1):
                try:
                    # Rate limiting: wait between requests
                    if i > 1:
                        await asyncio.sleep(self.request_interval)

                    # Search StockX by EAN
                    search_results = await self.catalog_service.search_catalog(
                        query=product.ean, page_number=1, page_size=1
                    )

                    if search_results and search_results.get("products"):
                        # Match found!
                        stockx_product = search_results["products"][0]

                        # Get product ID and fetch variants for size matching
                        stockx_product_id = stockx_product.get("productId")

                        # Try to get market data for the specific size
                        # Note: Size matching might require additional logic
                        # For now, we store the product match

                        await self._update_product_match(
                            product.id,
                            stockx_product_id,
                            stockx_product.get("urlKey"),
                            stockx_product.get("styleId"),
                            stockx_product,
                            product.retail_price_cents,
                        )

                        stats["matched"] += 1
                        logger.debug(
                            f"Matched product {i}/{len(products)}",
                            ean=product.ean,
                            stockx_id=stockx_product_id,
                        )
                    else:
                        # No match found
                        await self._mark_product_not_found(product.id)
                        stats["not_found"] += 1
                        logger.debug(f"No match for product {i}/{len(products)}", ean=product.ean)

                except Exception as e:
                    stats["errors"] += 1
                    error_msg = f"Product {product.awin_product_id}: {str(e)}"
                    errors_log.append(error_msg)
                    logger.error(
                        "Product enrichment failed",
                        product_id=product.awin_product_id,
                        error=str(e),
                    )

                    await self._mark_product_error(product.id)

                stats["total_processed"] = i

                # Update job progress every 10 products
                if i % 10 == 0:
                    await self.update_job_progress(
                        job_id, stats["total_processed"], stats["matched"], stats["errors"]
                    )
                    logger.info(f"Progress: {i}/{len(products)} processed", **stats)

            # Final stats
            stats["completed_at"] = datetime.utcnow().isoformat()
            stats["match_rate_percentage"] = (
                round((stats["matched"] / stats["total_processed"] * 100), 2)
                if stats["total_processed"] > 0
                else 0
            )

            # Complete the job
            await self.complete_job(
                job_id,
                status="completed",
                results_summary=stats,
                error_log="\n".join(errors_log) if errors_log else None,
            )

            logger.info("Enrichment completed successfully", **stats)
            return stats

        except Exception as e:
            logger.error("Enrichment job failed", job_id=str(job_id), error=str(e), exc_info=True)
            stats["completed_at"] = datetime.utcnow().isoformat()
            stats["fatal_error"] = str(e)

            await self.complete_job(
                job_id, status="failed", results_summary=stats, error_log=str(e)
            )

            raise

    async def _update_product_match(
        self,
        awin_product_id: UUID,
        stockx_product_id: str,
        stockx_url_key: str,
        stockx_style_id: str,
        stockx_data: Dict,
        retail_price_cents: int,
    ):
        """Update Awin product with StockX match data"""
        # LEGACY: Update awin_products for backwards compatibility
        update_query = text(
            """
            UPDATE integration.awin_products
            SET stockx_product_id = CAST(:stockx_product_id AS uuid),
                stockx_url_key = :stockx_url_key,
                stockx_style_id = :stockx_style_id,
                enrichment_status = 'matched',
                last_enriched_at = NOW(),
                updated_at = NOW()
            WHERE id = :awin_product_id
        """
        )

        await self.session.execute(
            update_query,
            {
                "awin_product_id": str(awin_product_id),
                "stockx_product_id": stockx_product_id,
                "stockx_url_key": stockx_url_key,
                "stockx_style_id": stockx_style_id,
            },
        )

        # NEW: Also store in price_sources architecture
        await self._store_stockx_price_source(awin_product_id, stockx_product_id, stockx_data)

        await self.session.commit()

    async def _store_stockx_price_source(
        self, awin_product_id: UUID, stockx_product_id: str, stockx_data: Dict
    ):
        """Store StockX resale price in price_sources table"""
        import json

        # Get product_id from awin_product via EAN
        product_query = text(
            """
            SELECT p.id, ap.ean
            FROM integration.awin_products ap
            JOIN catalog.product p ON ap.ean = p.ean
            WHERE ap.id = :awin_product_id
        """
        )

        result = await self.session.execute(
            product_query, {"awin_product_id": str(awin_product_id)}
        )
        row = result.fetchone()

        if not row:
            logger.warning("Could not find product for StockX price", awin_id=str(awin_product_id))
            return

        product_id = row[0]

        # Extract lowest ask from stockx_data (if available)
        # Note: This may need adjustment based on actual StockX API response structure
        lowest_ask = stockx_data.get("market", {}).get("lowestAsk")
        if not lowest_ask:
            # Try alternate field names
            lowest_ask = stockx_data.get("lowestAsk") or stockx_data.get("lowest_ask")

        if not lowest_ask:
            logger.debug("No market data available for StockX product", stockx_id=stockx_product_id)
            return

        # Convert to cents if it's in euros/dollars
        if isinstance(lowest_ask, float):
            lowest_ask_cents = int(lowest_ask * 100)
        else:
            lowest_ask_cents = int(lowest_ask)

        metadata = {
            "url_key": stockx_data.get("urlKey"),
            "style_id": stockx_data.get("styleId"),
            "product_category": stockx_data.get("productCategory"),
            "price_type": "lowest_ask",
        }

        source_url = (
            f"https://stockx.com/{stockx_data.get('urlKey')}" if stockx_data.get("urlKey") else None
        )

        # Insert into price_sources
        insert_query = text(
            """
            INSERT INTO integration.price_sources (
                product_id, source_type, source_product_id, source_name,
                price_type, price_cents, currency, in_stock,
                source_url, metadata,
                last_updated, created_at, updated_at
            )
            VALUES (
                :product_id, 'stockx', :source_product_id, 'StockX',
                'resale', :price_cents, 'EUR', true,
                :source_url, CAST(:metadata AS jsonb),
                NOW(), NOW(), NOW()
            )
            ON CONFLICT (product_id, source_type, source_product_id)
            DO UPDATE SET
                price_cents = EXCLUDED.price_cents,
                last_updated = NOW(),
                updated_at = NOW()
        """
        )

        await self.session.execute(
            insert_query,
            {
                "product_id": str(product_id),
                "source_product_id": stockx_product_id,
                "price_cents": lowest_ask_cents,
                "source_url": source_url,
                "metadata": json.dumps(metadata),
            },
        )

        logger.debug(
            "Stored StockX price in price_sources",
            product_id=str(product_id),
            stockx_id=stockx_product_id,
            price_eur=lowest_ask_cents / 100.0,
        )

    async def _mark_product_not_found(self, awin_product_id: UUID):
        """Mark product as not found on StockX"""
        update_query = text(
            """
            UPDATE integration.awin_products
            SET enrichment_status = 'not_found',
                last_enriched_at = NOW(),
                updated_at = NOW()
            WHERE id = :awin_product_id
        """
        )

        await self.session.execute(update_query, {"awin_product_id": str(awin_product_id)})
        await self.session.commit()

    async def _mark_product_error(self, awin_product_id: UUID):
        """Mark product as having an error during enrichment"""
        update_query = text(
            """
            UPDATE integration.awin_products
            SET enrichment_status = 'error',
                last_enriched_at = NOW(),
                updated_at = NOW()
            WHERE id = :awin_product_id
        """
        )

        await self.session.execute(update_query, {"awin_product_id": str(awin_product_id)})
        await self.session.commit()

    async def get_enrichment_stats(self) -> Dict[str, Any]:
        """Get current enrichment statistics"""
        stats_query = text(
            """
            SELECT
                COUNT(*) as total_products,
                COUNT(CASE WHEN enrichment_status = 'matched' THEN 1 END) as matched,
                COUNT(CASE WHEN enrichment_status = 'not_found' THEN 1 END) as not_found,
                COUNT(CASE WHEN enrichment_status = 'error' THEN 1 END) as errors,
                COUNT(CASE WHEN enrichment_status = 'pending' OR enrichment_status IS NULL THEN 1 END) as pending
            FROM integration.awin_products
            WHERE ean IS NOT NULL AND in_stock = true
        """
        )

        result = await self.session.execute(stats_query)
        stats = result.fetchone()

        return {
            "total_products": stats.total_products,
            "matched": stats.matched,
            "not_found": stats.not_found,
            "errors": stats.errors,
            "pending": stats.pending,
            "match_rate_percentage": (
                round((stats.matched / stats.total_products * 100), 2)
                if stats.total_products > 0
                else 0
            ),
        }
