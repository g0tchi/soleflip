"""
List all analytics views that depend on transactions.transactions table
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import DatabaseManager


async def list_views():
    db = DatabaseManager()
    await db.initialize()

    async with db.get_session() as session:
        print("=" * 80)
        print("ANALYTICS VIEWS USING transactions.transactions")
        print("=" * 80)

        # Get all views in analytics schema
        result = await session.execute(text("""
            SELECT
                schemaname,
                viewname,
                definition
            FROM pg_views
            WHERE schemaname = 'analytics'
            ORDER BY viewname
        """))

        views = list(result)
        print(f"\nTotal views in analytics schema: {len(views)}\n")

        # Check which ones use transactions.transactions
        dependent_views = []
        independent_views = []

        for view in views:
            if 'transactions.transactions' in view.definition:
                dependent_views.append(view)
            else:
                independent_views.append(view)

        print(f"Views using transactions.transactions: {len(dependent_views)}")
        print(f"Views NOT using transactions.transactions: {len(independent_views)}\n")

        if dependent_views:
            print("=" * 80)
            print("DEPENDENT VIEWS (NEED MIGRATION)")
            print("=" * 80)

            for idx, view in enumerate(dependent_views, 1):
                print(f"\n[{idx}] {view.viewname}")

                # Count approximate complexity by definition length
                lines = view.definition.count('\n')
                if lines < 20:
                    complexity = "LOW"
                elif lines < 50:
                    complexity = "MEDIUM"
                else:
                    complexity = "HIGH"

                print(f"    Complexity: {complexity} ({lines} lines)")

                # Show first 200 chars of definition
                preview = view.definition[:200].replace('\n', ' ')
                print(f"    Preview: {preview}...")

        if independent_views:
            print("\n" + "=" * 80)
            print("INDEPENDENT VIEWS (ALREADY USING orders OR OTHER TABLES)")
            print("=" * 80)

            for idx, view in enumerate(independent_views, 1):
                print(f"\n[{idx}] {view.viewname}")
                if 'transactions.orders' in view.definition:
                    print("    Status: Already uses orders table")
                else:
                    print("    Status: Uses other tables")

    await db.close()


if __name__ == "__main__":
    asyncio.run(list_views())
