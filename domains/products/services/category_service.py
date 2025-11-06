"""
Category Detection Service
Detects and creates product categories from product names
"""

from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from shared.database.models import Category

logger = structlog.get_logger(__name__)


class CategoryDetectionService:
    """
    Detects product categories from product names using keyword-based classification.
    Scalable: Can be enhanced with ML or DB-driven rules later.
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._category_cache = {}

    async def detect_category_from_name(
        self, product_name: str, create_if_not_found: bool = True
    ) -> Optional[Category]:
        """
        Detect category from product name using intelligent keyword matching.

        Args:
            product_name: Product name to analyze
            create_if_not_found: If True, creates category if not exists

        Returns:
            Category object or None
        """
        if not product_name:
            return None

        product_lower = product_name.lower()
        category_info = self._classify_product(product_lower)

        if category_info:
            category_name, category_slug = category_info
            if create_if_not_found:
                return await self._get_or_create_category(category_name, category_slug)

        return None

    def _classify_product(self, product_lower: str) -> Optional[tuple[str, str]]:
        """
        Classify product into category based on keywords.

        Returns:
            Tuple of (category_name, category_slug) or None
        """
        # Sneakers (high priority - specific keywords)
        sneaker_keywords = [
            "air force",
            "dunk",
            "jordan",
            "yeezy",
            "boost",
            "max",
            "runner",
            "trainer",
            "sneaker",
            "basketball",
            "running",
            "retro",
        ]
        if any(keyword in product_lower for keyword in sneaker_keywords):
            return ("Sneakers", "sneakers")

        # Footwear (broader category)
        footwear_keywords = [
            "clog",
            "sandal",
            "slide",
            "boot",
            "shoe",
            "slipper",
            "flip flop",
            "moccasin",
            "loafer",
            "heel",
            "pump",
        ]
        if any(keyword in product_lower for keyword in footwear_keywords):
            return ("Footwear", "footwear")

        # Collectibles
        collectible_keywords = [
            "book",
            "hardcover",
            "figure",
            "art",
            "print",
            "poster",
            "edition of",
            "collectible",
            "vinyl",
            "sculpture",
            "plush",
        ]
        if any(keyword in product_lower for keyword in collectible_keywords):
            return ("Collectibles", "collectibles")

        # Apparel
        apparel_keywords = [
            "hoodie",
            "shirt",
            "tee",
            "jacket",
            "pants",
            "shorts",
            "sweater",
            "sweatshirt",
            "jersey",
            "coat",
            "dress",
            "skirt",
            "jeans",
        ]
        if any(keyword in product_lower for keyword in apparel_keywords):
            return ("Apparel", "apparel")

        # Accessories
        accessory_keywords = [
            "bag",
            "hat",
            "cap",
            "backpack",
            "wallet",
            "belt",
            "scarf",
            "gloves",
            "sunglasses",
            "watch",
            "jewelry",
            "chain",
            "bracelet",
        ]
        if any(keyword in product_lower for keyword in accessory_keywords):
            return ("Accessories", "accessories")

        # Electronics/Tech
        tech_keywords = [
            "headphone",
            "airpods",
            "speaker",
            "console",
            "controller",
            "phone",
            "case",
            "charger",
        ]
        if any(keyword in product_lower for keyword in tech_keywords):
            return ("Electronics", "electronics")

        # Default fallback
        return ("Other", "other")

    async def _get_or_create_category(self, category_name: str, category_slug: str) -> Category:
        """
        Find or create a category in the database.

        Args:
            category_name: Category name
            category_slug: Category slug (unique)

        Returns:
            Category object
        """
        # Check cache first
        if category_slug in self._category_cache:
            logger.debug("Category cache hit", category=category_name)
            return self._category_cache[category_slug]

        # Try to find existing
        stmt = select(Category).where(Category.slug == category_slug)
        result = await self.db_session.execute(stmt)
        category = result.scalar_one_or_none()

        if category:
            self._category_cache[category_slug] = category
            logger.debug("Found existing category", category=category_name)
            return category

        # Create new
        category = Category(
            name=category_name,
            slug=category_slug,
        )
        self.db_session.add(category)
        await self.db_session.flush()

        self._category_cache[category_slug] = category
        logger.info("Created new category", category=category_name, category_id=str(category.id))
        return category
