import re
from typing import List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from slugify import slugify

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

        from sqlalchemy.orm import selectinload

        logger.info("Loading brand patterns from database...")
        stmt = (
            select(BrandPattern)
            .options(selectinload(BrandPattern.brand))  # Eagerly load brand relationship
            .order_by(BrandPattern.priority.asc(), BrandPattern.created_at.asc())
        )
        result = await self.db_session.execute(stmt)
        self._patterns = result.scalars().all()
        logger.info(f"Loaded {len(self._patterns)} brand patterns.")

    async def extract_brand_from_name(
        self, product_name: str, create_if_not_found: bool = False
    ) -> Optional[Brand]:
        """
        Tries to find a matching brand for a given product name using the loaded patterns.

        Args:
            product_name: The product name to extract brand from
            create_if_not_found: If True, creates a new brand from intelligent fallback

        Returns:
            Brand object or None
        """
        if not self._patterns:
            await self.load_patterns()

        if not product_name:
            return None

        # First try: Pattern matching (DB-driven)
        for p in self._patterns:
            try:
                if p.pattern_type == "regex":
                    if re.search(p.pattern, product_name, re.IGNORECASE):
                        logger.debug(
                            "Found brand match via pattern",
                            brand=p.brand.name,
                            pattern=p.pattern,
                            product=product_name,
                        )
                        return p.brand
                elif p.pattern_type == "keyword":
                    if p.pattern.lower() in product_name.lower():
                        logger.debug(
                            "Found brand match via keyword",
                            brand=p.brand.name,
                            pattern=p.pattern,
                            product=product_name,
                        )
                        return p.brand
            except re.error as e:
                logger.warning("Invalid regex pattern in database", pattern=p.pattern, error=str(e))
                continue

        # Second try: Intelligent fallback
        if create_if_not_found:
            brand_name = self._intelligent_brand_extraction(product_name)
            if brand_name:
                brand = await self._get_or_create_brand(brand_name)
                logger.info(
                    "Created brand via intelligent fallback",
                    brand_name=brand_name,
                    product=product_name
                )
                return brand

        logger.debug("No brand match found for product", product_name=product_name)
        return None

    def _intelligent_brand_extraction(self, product_name: str) -> Optional[str]:
        """
        Intelligently extract brand from product name when no pattern matches.

        Rules:
        1. First two capitalized words might be a brand (e.g., "Daniel Arsham")
        2. First capitalized word might be brand (e.g., "Crocs")
        3. Ignore common keywords like "The", "A", etc.
        """
        words = product_name.split()
        if not words:
            return None

        # Skip common articles/prepositions
        skip_words = {"the", "a", "an", "of", "for", "in", "on", "at"}

        # Clean words (remove special chars but keep capitalization)
        clean_words = [
            re.sub(r'[^\w\s-]', '', word)
            for word in words
            if word.lower() not in skip_words
        ]

        if not clean_words:
            return None

        # Try first two capitalized words (e.g., "Daniel Arsham", "New Balance")
        if len(clean_words) >= 2:
            first_word = clean_words[0]
            second_word = clean_words[1]

            if first_word and first_word[0].isupper() and second_word and second_word[0].isupper():
                # Check if second word looks like part of brand (not a product type)
                if len(second_word) > 2 and second_word.lower() not in ["air", "max", "pro", "ultra"]:
                    return f"{first_word} {second_word}"

        # Fallback: Use first capitalized word
        first_word = clean_words[0]
        if first_word and first_word[0].isupper():
            return first_word

        return None

    async def _get_or_create_brand(self, brand_name: str) -> Brand:
        """
        Find or create a brand in the database.

        Args:
            brand_name: Brand name to find or create

        Returns:
            Brand object
        """
        brand_slug = slugify(brand_name)

        # Try to find existing
        stmt = select(Brand).where(Brand.slug == brand_slug)
        result = await self.db_session.execute(stmt)
        brand = result.scalar_one_or_none()

        if brand:
            return brand

        # Create new
        brand = Brand(
            name=brand_name,
            slug=brand_slug,
        )
        self.db_session.add(brand)
        await self.db_session.flush()

        logger.info("Created new brand", brand_name=brand_name, brand_id=str(brand.id))
        return brand
