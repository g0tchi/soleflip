import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import re

from shared.database.models import Brand, BrandPattern

logger = structlog.get_logger(__name__)

class BrandExtractorService:
    """
    A service to extract brand information from product names using
    database-driven patterns.
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._patterns: List[BrandPattern] = []

    async def load_patterns(self):
        """
        Load all brand patterns from the database, ordered by priority.
        """
        if self._patterns:
            return

        logger.info("Loading brand patterns from database...")
        stmt = select(BrandPattern).order_by(BrandPattern.priority.asc(), BrandPattern.created_at.asc())
        result = await self.db_session.execute(stmt)
        self._patterns = result.scalars().all()
        logger.info(f"Loaded {len(self._patterns)} brand patterns.")

    async def extract_brand_from_name(self, product_name: str) -> Optional[Brand]:
        """
        Tries to find a matching brand for a given product name using the loaded patterns.
        """
        if not self._patterns:
            await self.load_patterns()

        if not product_name:
            return None

        for p in self._patterns:
            try:
                if p.pattern_type == 'regex':
                    if re.search(p.pattern, product_name, re.IGNORECASE):
                        logger.debug("Found brand match", brand=p.brand.name, pattern=p.pattern, product=product_name)
                        return p.brand
                elif p.pattern_type == 'keyword':
                    if p.pattern.lower() in product_name.lower():
                        logger.debug("Found brand match", brand=p.brand.name, pattern=p.pattern, product=product_name)
                        return p.brand
            except re.error as e:
                logger.warning("Invalid regex pattern in database", pattern=p.pattern, error=str(e))
                continue

        logger.debug("No brand match found for product", product_name=product_name)
        return None
