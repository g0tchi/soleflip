"""
Metabase Integration Setup Script
=================================

Quick setup script for creating all materialized views and testing the integration.

Usage:
    python domains/integration/metabase/setup_metabase.py
"""

import asyncio
import sys
from datetime import datetime

from services.view_manager import MetabaseViewManager
from services.dashboard_service import MetabaseDashboardService
from services.sync_service import MetabaseSyncService


async def main():
    print("=" * 80)
    print("METABASE INTEGRATION SETUP")
    print("=" * 80)
    print(f"Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    # Initialize services
    view_manager = MetabaseViewManager()
    dashboard_service = MetabaseDashboardService()
    sync_service = MetabaseSyncService()

    # Step 1: Create all materialized views
    print("Step 1: Creating materialized views...")
    print("-" * 80)

    try:
        results = await view_manager.create_all_views(drop_existing=True)
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)

        print(f"\nCreated {success_count}/{total_count} views:")
        for view_name, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {view_name}")

        if success_count < total_count:
            print(f"\n⚠️  {total_count - success_count} views failed to create")
            print("    Check logs for details")

    except Exception as e:
        print(f"\n✗ Error creating views: {e}")
        sys.exit(1)

    # Step 2: Verify view creation
    print("\n" + "=" * 80)
    print("Step 2: Verifying view creation...")
    print("-" * 80)

    try:
        statuses = await view_manager.get_all_view_statuses()

        print(f"\nView Status Summary:")
        print(f"  Total views: {len(statuses)}")
        print(f"  Existing: {sum(1 for v in statuses if v.exists)}")
        print(f"  Missing: {sum(1 for v in statuses if not v.exists)}")
        print(f"  Total rows: {sum(v.row_count or 0 for v in statuses):,}")

        print(f"\nDetailed Status:")
        for status in statuses:
            if status.exists:
                print(f"  ✓ {status.view_name:40} | {status.row_count:>6,} rows | {len(status.indexes)} indexes")
            else:
                print(f"  ✗ {status.view_name:40} | NOT FOUND")

    except Exception as e:
        print(f"\n✗ Error verifying views: {e}")
        sys.exit(1)

    # Step 3: Generate dashboard templates
    print("\n" + "=" * 80)
    print("Step 3: Generating dashboard templates...")
    print("-" * 80)

    try:
        dashboards = dashboard_service.generate_all_dashboards()

        print(f"\nGenerated {len(dashboards)} dashboards:")
        for name, dashboard in dashboards.items():
            print(f"  ✓ {dashboard.name}")
            print(f"    - Cards: {len(dashboard.ordered_cards)}")
            print(f"    - Parameters: {len(dashboard.parameters)}")

    except Exception as e:
        print(f"\n✗ Error generating dashboards: {e}")
        sys.exit(1)

    # Step 4: Test sync functionality
    print("\n" + "=" * 80)
    print("Step 4: Testing sync functionality...")
    print("-" * 80)

    try:
        print("\nRefreshing all views (this may take 60-90 seconds)...")
        sync_results = await sync_service.sync_all()

        success_count = sum(1 for s in sync_results.values() if s.status == "completed")
        total_time = sum(s.duration_seconds or 0 for s in sync_results.values())

        print(f"\nSync Results:")
        print(f"  Successful: {success_count}/{len(sync_results)}")
        print(f"  Total time: {total_time:.1f}s")
        print(f"  Average: {total_time/len(sync_results):.1f}s per view")

        print(f"\nIndividual Refresh Times:")
        for view_name, status in sync_results.items():
            if status.status == "completed":
                print(f"  ✓ {view_name:40} | {status.duration_seconds:>5.1f}s")
            else:
                print(f"  ✗ {view_name:40} | FAILED: {status.error_message}")

    except Exception as e:
        print(f"\n✗ Error testing sync: {e}")
        sys.exit(1)

    # Step 5: Setup refresh schedule (optional)
    print("\n" + "=" * 80)
    print("Step 5: Setup automatic refresh schedule (optional)...")
    print("-" * 80)
    print("\nThis step requires:")
    print("  - PostgreSQL pg_cron extension installed")
    print("  - Superuser privileges")
    print("\nSkipping automatic setup. To enable later, run:")
    print("  curl -X POST http://localhost:8000/api/v1/metabase/setup/refresh-schedule")

    # Final summary
    print("\n" + "=" * 80)
    print("SETUP COMPLETE")
    print("=" * 80)
    print("\n✅ Metabase Integration Ready!")
    print("\nNext Steps:")
    print("  1. Open Metabase: http://localhost:6400")
    print("  2. Add PostgreSQL database connection:")
    print("     - Host: localhost (or postgres if using Docker)")
    print("     - Port: 5432")
    print("     - Database: soleflip")
    print("     - Schema: analytics (for materialized views)")
    print("  3. Create dashboards using the pre-built templates")
    print("  4. (Optional) Setup automated refresh:")
    print("     curl -X POST http://localhost:8000/api/v1/metabase/setup/refresh-schedule")
    print("\nAPI Endpoints:")
    print("  - View Status: GET /api/v1/metabase/views/status")
    print("  - Refresh All: POST /api/v1/metabase/sync/all")
    print("  - Dashboards: GET /api/v1/metabase/dashboards")
    print("\nDocumentation: domains/integration/metabase/README.md")
    print(f"\nCompleted: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        sys.exit(1)
