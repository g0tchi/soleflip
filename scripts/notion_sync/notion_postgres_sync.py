"""
Notion-PostgreSQL Data Synchronization Script
Matches historical Notion business data with current PostgreSQL records
using StockX Sale IDs and SKU matching strategies.
"""

import asyncio
import re
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import structlog

from shared.database.connection import get_db_session, db_manager
import sqlalchemy as sa

logger = structlog.get_logger(__name__)


class NotionPostgresSyncAnalyzer:
    """Analyzes and matches Notion historical data with PostgreSQL records"""

    def __init__(self):
        self.notion_data = []  # Would be loaded from Notion MCP
        self.postgres_data = []
        self.matches = []
        self.unmatched_notion = []
        self.unmatched_postgres = []

    async def load_postgres_data(self):
        """Load relevant PostgreSQL data for matching"""
        async with get_db_session() as session:
            session_gen = get_db_session()
            session = await session_gen.__anext__()

            try:
                # Load sales transactions with complete data
                result = await session.execute(sa.text('''
                    SELECT
                        t.id,
                        t.external_id,
                        t.sale_price,
                        t.transaction_date,
                        p.sku,
                        b.name as brand,
                        pr.name as product_name,
                        plat.name as platform,
                        i.purchase_price
                    FROM sales.transactions t
                    JOIN products.inventory i ON t.inventory_id = i.id
                    JOIN products.products pr ON i.product_id = pr.id
                    LEFT JOIN core.brands b ON pr.brand_id = b.id
                    JOIN core.platforms plat ON t.platform_id = plat.id
                    WHERE t.external_id IS NOT NULL
                    ORDER BY t.transaction_date DESC
                '''))

                self.postgres_data = [
                    {
                        'id': row[0],
                        'external_id': row[1],
                        'sale_price': float(row[2]) if row[2] else 0,
                        'transaction_date': row[3],
                        'sku': row[4],
                        'brand': row[5],
                        'product_name': row[6],
                        'platform': row[7],
                        'purchase_price': float(row[8]) if row[8] else 0
                    }
                    for row in result
                ]

                logger.info(f"Loaded {len(self.postgres_data)} PostgreSQL records for matching")

            finally:
                await session.close()

    def extract_stockx_id_from_postgres(self, external_id: str) -> Optional[str]:
        """
        Extract StockX ID from PostgreSQL external_id format
        Format: stockx_76551909-76451668 -> 76551909-76451668
        """
        if not external_id or not external_id.startswith('stockx_'):
            return None
        return external_id.replace('stockx_', '')

    def normalize_sku(self, sku: str) -> str:
        """Normalize SKU for matching (remove size suffixes, etc.)"""
        if not sku:
            return ""

        # Remove common size patterns
        sku = re.sub(r'-[A-Z]{2,3}\d+(\.\d+)?$', '', sku)  # -US10.5, -EU44
        sku = re.sub(r'-\d+(\.\d+)?$', '', sku)  # -10.5, -44

        return sku.strip()

    def match_by_stockx_id(self, notion_sale_id: str, postgres_external_id: str) -> bool:
        """
        Match Notion Sale ID with PostgreSQL external_id

        Notion format: 73560400-73460159
        PostgreSQL format: stockx_76551909-76451668
        """
        postgres_clean = self.extract_stockx_id_from_postgres(postgres_external_id)
        if not postgres_clean:
            return False

        # Direct match
        if notion_sale_id == postgres_clean:
            return True

        # Partial match (first part)
        notion_parts = notion_sale_id.split('-')
        postgres_parts = postgres_clean.split('-')

        if len(notion_parts) >= 1 and len(postgres_parts) >= 1:
            if notion_parts[0] == postgres_parts[0]:
                return True

        return False

    def match_by_sku(self, notion_sku: str, postgres_sku: str) -> bool:
        """Match SKUs with normalization"""
        if not notion_sku or not postgres_sku:
            return False

        # Direct match
        if notion_sku == postgres_sku:
            return True

        # Normalized match
        notion_norm = self.normalize_sku(notion_sku)
        postgres_norm = self.normalize_sku(postgres_sku)

        if notion_norm and postgres_norm and notion_norm == postgres_norm:
            return True

        return False

    def match_by_price_and_date(self, notion_item: dict, postgres_item: dict,
                               tolerance_percent: float = 5.0,
                               tolerance_days: int = 7) -> bool:
        """Match by price and date with tolerance"""

        # Price matching
        notion_price = float(notion_item.get('gross_sale', 0))
        postgres_price = postgres_item.get('sale_price', 0)

        if notion_price > 0 and postgres_price > 0:
            price_diff = abs(notion_price - postgres_price) / notion_price * 100
            if price_diff > tolerance_percent:
                return False

        # Date matching
        notion_date_str = notion_item.get('sale_date')
        postgres_date = postgres_item.get('transaction_date')

        if notion_date_str and postgres_date:
            try:
                if isinstance(notion_date_str, str):
                    notion_date = datetime.strptime(notion_date_str, '%Y-%m-%d').date()
                else:
                    notion_date = notion_date_str

                if isinstance(postgres_date, datetime):
                    postgres_date = postgres_date.date()

                date_diff = abs((notion_date - postgres_date).days)
                if date_diff > tolerance_days:
                    return False
            except (ValueError, AttributeError):
                pass

        return True

    def find_matches(self) -> Dict[str, List]:
        """
        Find matches between Notion and PostgreSQL data
        Returns categorized results
        """
        matches = []
        matched_postgres_ids = set()
        matched_notion_ids = set()

        logger.info("Starting Notion-PostgreSQL matching process...")

        # Example Notion data structure (would be loaded from MCP)
        example_notion_data = [
            {
                'sku': '476316',
                'sale_id': '73560400-73460159',
                'gross_sale': 36.86,
                'sale_date': '2025-03-22',
                'platform': 'StockX',
                'brand': 'Uniqlo',
                'size': 'L'
            }
        ]

        # For each Notion item, find PostgreSQL matches
        for notion_item in example_notion_data:
            best_match = None
            best_score = 0

            for postgres_item in self.postgres_data:
                score = 0
                match_reasons = []

                # StockX ID matching (highest priority)
                if self.match_by_stockx_id(
                    notion_item.get('sale_id', ''),
                    postgres_item.get('external_id', '')
                ):
                    score += 50
                    match_reasons.append('stockx_id_match')

                # SKU matching (high priority)
                if self.match_by_sku(
                    notion_item.get('sku', ''),
                    postgres_item.get('sku', '')
                ):
                    score += 30
                    match_reasons.append('sku_match')

                # Price and date matching (medium priority)
                if self.match_by_price_and_date(notion_item, postgres_item):
                    score += 20
                    match_reasons.append('price_date_match')

                # Brand matching (low priority)
                if (notion_item.get('brand', '').lower() ==
                    postgres_item.get('brand', '').lower()):
                    score += 10
                    match_reasons.append('brand_match')

                # Update best match if this score is higher
                if score > best_score and score >= 30:  # Minimum threshold
                    best_match = {
                        'notion': notion_item,
                        'postgres': postgres_item,
                        'score': score,
                        'match_reasons': match_reasons
                    }
                    best_score = score

            # Record the best match if found
            if best_match:
                matches.append(best_match)
                matched_postgres_ids.add(best_match['postgres']['id'])
                matched_notion_ids.add(notion_item.get('sku', ''))

        # Find unmatched records
        unmatched_postgres = [
            item for item in self.postgres_data
            if item['id'] not in matched_postgres_ids
        ]

        unmatched_notion = [
            item for item in example_notion_data
            if item.get('sku', '') not in matched_notion_ids
        ]

        return {
            'matches': matches,
            'unmatched_postgres': unmatched_postgres,
            'unmatched_notion': unmatched_notion,
            'match_rate': len(matches) / len(example_notion_data) * 100 if example_notion_data else 0
        }

    async def analyze_sync_potential(self):
        """Analyze the potential for Notion-PostgreSQL sync"""

        await self.load_postgres_data()
        results = self.find_matches()

        logger.info("=== NOTION-POSTGRESQL SYNC ANALYSIS ===")
        logger.info(f"PostgreSQL records: {len(self.postgres_data)}")
        logger.info(f"Matches found: {len(results['matches'])}")
        logger.info(f"Unmatched PostgreSQL: {len(results['unmatched_postgres'])}")
        logger.info(f"Match rate: {results['match_rate']:.1f}%")

        # Sample matches
        logger.info("\nSample matches:")
        for i, match in enumerate(results['matches'][:5]):
            notion = match['notion']
            postgres = match['postgres']
            logger.info(f"  {i+1}. Notion SKU: {notion.get('sku')} <-> PostgreSQL SKU: {postgres.get('sku')}")
            logger.info(f"     Price: EUR{notion.get('gross_sale')} <-> EUR{postgres.get('sale_price')}")
            logger.info(f"     Reasons: {', '.join(match['match_reasons'])}")
            logger.info(f"     Score: {match['score']}")

        return results

    async def sync_missing_business_intelligence(self, matches: List[Dict]):
        """
        Sync missing business intelligence from Notion to PostgreSQL
        This would add the missing ROI/PAS/Shelf Life calculations
        """

        logger.info("=== BUSINESS INTELLIGENCE SYNC SIMULATION ===")

        for match in matches[:3]:  # Sample first 3 matches
            notion = match['notion']
            postgres = match['postgres']

            # Calculate missing business metrics (Notion → PostgreSQL)
            purchase_price = postgres.get('purchase_price', 0)
            sale_price = postgres.get('sale_price', 0)

            if purchase_price > 0 and sale_price > 0:
                # ROI calculation (like Notion)
                roi = (sale_price - purchase_price) / purchase_price * 100

                # Shelf life calculation (would need purchase/sale dates)
                # shelf_life = (sale_date - purchase_date).days

                # Profit per shelf day (PAS)
                profit = sale_price - purchase_price
                # pas = profit / shelf_life if shelf_life > 0 else 0

                logger.info(f"SKU {postgres.get('sku')}: ROI = {roi:.1f}%")
                logger.info(f"  Profit: EUR{profit:.2f}")
                # logger.info(f"  PAS: EUR{pas:.2f}/day")


async def main():
    """Main execution function"""
    if not db_manager.engine:
        await db_manager.initialize()

    analyzer = NotionPostgresSyncAnalyzer()
    results = await analyzer.analyze_sync_potential()

    if results['matches']:
        await analyzer.sync_missing_business_intelligence(results['matches'])

    logger.info("Notion-PostgreSQL sync analysis complete")


if __name__ == "__main__":
    asyncio.run(main())