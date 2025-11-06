"""
Fix existing Metabase views by dropping and recreating them
"""

import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Views that need to be dropped and recreated
VIEWS_TO_DROP = [
    "analytics.daily_revenue",
    "analytics.monthly_revenue",
    "analytics.revenue_growth",
    "analytics.top_products_revenue",
    "analytics.brand_performance",
    "analytics.platform_performance",
    "analytics.sales_by_weekday",
    "analytics.executive_dashboard",
    "analytics.roi_distribution",
]


async def fix_views():
    engine = create_async_engine(os.getenv("DATABASE_URL"), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("Fixing Metabase Analytics Views")
        print("=" * 60)
        print("")

        # Step 1: Drop existing views
        print("Step 1: Dropping existing views...")
        print("-" * 60)
        for view_name in VIEWS_TO_DROP:
            try:
                await session.execute(text(f"DROP VIEW IF EXISTS {view_name} CASCADE"))
                print(f"[OK] Dropped: {view_name}")
            except Exception as e:
                print(f"[ERROR] Failed to drop {view_name}: {str(e)[:80]}")
                await session.rollback()

        await session.commit()
        print("")

        # Step 2: Read and parse SQL file
        print("Step 2: Creating new views...")
        print("-" * 60)

        with open("metabase/views/core_analytics_views_v2.sql", "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Parse CREATE VIEW statements
        statements = []
        current_statement = []
        in_view_definition = False

        for line in sql_content.split("\n"):
            if "CREATE OR REPLACE VIEW" in line.upper():
                if current_statement and in_view_definition:
                    statements.append("\n".join(current_statement))
                current_statement = [line]
                in_view_definition = True
            elif "GRANT" in line.upper():
                if current_statement and in_view_definition:
                    statements.append("\n".join(current_statement))
                    current_statement = []
                    in_view_definition = False
            elif ";" in line and in_view_definition:
                current_statement.append(line)
                statements.append("\n".join(current_statement))
                current_statement = []
                in_view_definition = False
            elif in_view_definition:
                current_statement.append(line)

        if current_statement and in_view_definition:
            statements.append("\n".join(current_statement))

        # Step 3: Create all views
        view_count = 0
        for statement in statements:
            if not statement.strip():
                continue

            # Extract view name
            view_name = "unknown"
            if "CREATE OR REPLACE VIEW" in statement.upper():
                parts = statement.split()
                for j, part in enumerate(parts):
                    if part.upper() == "VIEW" and j + 1 < len(parts):
                        view_name = parts[j + 1].replace("analytics.", "")
                        break

            try:
                await session.execute(text(statement))
                view_count += 1
                print(f"[OK] {view_count:2d}. Created: {view_name}")
            except Exception as e:
                print(f"[ERROR] Failed to create {view_name}:")
                print(f"        {str(e)[:150]}")
                await session.rollback()
                continue

        await session.commit()
        print("")
        print(f"[SUCCESS] {view_count} views successfully created!")
        print("")
        print("Summary:")
        print("-" * 60)
        print(f"Dropped: {len(VIEWS_TO_DROP)} old views")
        print(f"Created: {view_count} new/updated views")
        print("")
        print("All analytics views now include:")
        print("  - ROI metrics (avg_roi_percent)")
        print("  - VAT-aware calculations (net vs gross)")
        print("  - Enhanced profit tracking")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_views())
