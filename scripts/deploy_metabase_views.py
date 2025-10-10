"""
Deploy updated Metabase analytics views (v2) to database
"""
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

async def deploy_views():
    engine = create_async_engine(os.getenv('DATABASE_URL'), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Read SQL file
    with open('metabase/views/core_analytics_views_v2.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Split into individual CREATE OR REPLACE VIEW statements
    statements = []
    current_statement = []
    in_view_definition = False

    for line in sql_content.split('\n'):
        stripped = line.strip()

        # Start of a new view
        if 'CREATE OR REPLACE VIEW' in line.upper():
            if current_statement and in_view_definition:
                statements.append('\n'.join(current_statement))
            current_statement = [line]
            in_view_definition = True
        # GRANT statements
        elif 'GRANT' in line.upper():
            if current_statement and in_view_definition:
                statements.append('\n'.join(current_statement))
                current_statement = []
                in_view_definition = False
            statements.append(line)
        # End of current statement (semicolon)
        elif ';' in line and in_view_definition:
            current_statement.append(line)
            statements.append('\n'.join(current_statement))
            current_statement = []
            in_view_definition = False
        # Regular line in view definition
        elif in_view_definition:
            current_statement.append(line)

    # Add last statement if exists
    if current_statement and in_view_definition:
        statements.append('\n'.join(current_statement))

    async with async_session() as session:
        print('Deploying Metabase Analytics Views v2.2.6')
        print('='*60)
        print('')

        view_count = 0
        for i, statement in enumerate(statements, 1):
            if not statement:
                continue

            # Skip GRANT statements for now (report them)
            if 'GRANT' in statement.upper():
                print(f'[SKIP] {i:2d}. GRANT statement (run manually if needed)')
                continue

            # Extract view name from CREATE OR REPLACE VIEW statement
            view_name = 'unknown'
            if 'CREATE OR REPLACE VIEW' in statement.upper():
                parts = statement.split()
                for j, part in enumerate(parts):
                    if part.upper() == 'VIEW' and j + 1 < len(parts):
                        view_name = parts[j + 1].replace('analytics.', '')
                        break

            try:
                await session.execute(text(statement))
                view_count += 1
                print(f'[OK] {view_count:2d}. Created/Updated view: {view_name}')
            except Exception as e:
                print(f'[ERROR] Failed to create {view_name}:')
                print(f'        {str(e)}')
                # Rollback to continue with other views
                await session.rollback()
                continue

        await session.commit()
        print('')
        print(f'[SUCCESS] {view_count} Metabase analytics views deployed!')
        print('')
        print('What Changed in v2.2.6:')
        print('-'*60)
        print('UPDATED (with ROI/VAT metrics):')
        print('  - daily_revenue, monthly_revenue, revenue_growth')
        print('  - top_products_revenue, brand_performance')
        print('  - platform_performance, sales_by_weekday')
        print('  - executive_dashboard')
        print('')
        print('NEW VIEWS:')
        print('  - product_size_analysis')
        print('  - platform_monthly_trends')
        print('  - roi_distribution (ROI bracket analysis)')
        print('  - purchase_vs_sale_analysis (VAT-aware)')
        print('  - supplier_profitability (with sell-through rate)')
        print('  - sales_by_hour')
        print('  - inventory_overview (with VAT)')
        print('  - product_velocity')

    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(deploy_views())
