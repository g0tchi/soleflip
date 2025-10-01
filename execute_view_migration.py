"""
Execute analytics view migration SQL
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import DatabaseManager


async def execute_migration():
    db = DatabaseManager()
    await db.initialize()

    # Read SQL file
    with open('migrate_analytics_views_low.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Split into individual statements
    statements = []
    current_stmt = []

    for line in sql_content.split('\n'):
        # Skip empty lines and comments at start of line
        if not line.strip() or line.strip().startswith('--'):
            continue

        current_stmt.append(line)

        # Execute when we hit a semicolon
        if line.strip().endswith(';'):
            stmt = '\n'.join(current_stmt)
            if stmt.strip() and not stmt.strip().startswith('--'):
                statements.append(stmt)
            current_stmt = []

    print(f"Found {len(statements)} SQL statements to execute\n")

    async with db.get_session() as session:
        success_count = 0
        error_count = 0

        for idx, stmt in enumerate(statements, 1):
            try:
                # Get view name from CREATE OR REPLACE VIEW
                view_name = "unknown"
                if 'CREATE OR REPLACE VIEW' in stmt:
                    parts = stmt.split('CREATE OR REPLACE VIEW')[1].split('AS')[0]
                    view_name = parts.strip().split()[0]

                print(f"[{idx}/{len(statements)}] Executing: {view_name}...")

                await session.execute(text(stmt))
                await session.commit()

                success_count += 1
                print(f"    Success")

            except Exception as e:
                error_count += 1
                print(f"    ERROR: {str(e)}")
                if idx == 1:  # Show full error for first statement
                    import traceback
                    traceback.print_exc()

        print(f"\n{'='*80}")
        print(f"MIGRATION SUMMARY")
        print(f"{'='*80}")
        print(f"  Total statements: {len(statements)}")
        print(f"  Successful: {success_count}")
        print(f"  Errors: {error_count}")

    await db.close()


if __name__ == "__main__":
    asyncio.run(execute_migration())
