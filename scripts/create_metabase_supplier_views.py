"""
Create Metabase-optimized views for Supplier History visualization
Includes multiple view types for different chart types in Metabase
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import db_manager


VIEWS = {
    "supplier_timeline_view": """
        -- Timeline View: Perfect for Metabase Line Charts and Event Timeline
        -- Shows all events chronologically with metadata for visualization
        CREATE OR REPLACE VIEW analytics.supplier_timeline_view AS
        SELECT
            sh.id,
            sh.event_date,
            sh.event_title,
            sh.event_description,
            sh.event_type,
            sh.impact_level,
            sh.source_url,
            s.name as supplier_name,
            s.slug as supplier_slug,
            s.city,
            s.country,
            s.status as supplier_status,
            s.founded_year,
            s.instagram_handle,
            -- Color coding for Metabase conditional formatting
            CASE
                WHEN sh.impact_level = 'critical' THEN '#DC2626'
                WHEN sh.impact_level = 'high' THEN '#EA580C'
                WHEN sh.impact_level = 'medium' THEN '#CA8A04'
                ELSE '#65A30D'
            END as impact_color,
            -- Status indicator
            CASE
                WHEN s.status = 'closed' THEN '[X] Closed'
                WHEN s.status = 'active' THEN '[OK] Active'
                ELSE '[?] ' || s.status
            END as status_indicator,
            -- Years since founding
            EXTRACT(YEAR FROM sh.event_date) - s.founded_year as years_since_founding,
            -- Event number for this supplier
            ROW_NUMBER() OVER (PARTITION BY s.id ORDER BY sh.event_date) as event_sequence
        FROM core.supplier_history sh
        JOIN core.suppliers s ON sh.supplier_id = s.id
        ORDER BY sh.event_date, s.name
    """,

    "supplier_summary_stats": """
        -- Summary Statistics: Perfect for Metabase Number cards and KPI dashboard
        CREATE OR REPLACE VIEW analytics.supplier_summary_stats AS
        SELECT
            s.id,
            s.name,
            s.slug,
            s.display_name,
            s.city,
            s.country,
            s.status,
            s.founded_year,
            s.founder_name,
            s.instagram_handle,
            s.instagram_url,
            s.website,
            s.closure_date,
            -- Event statistics
            COUNT(sh.id) as total_events,
            COUNT(CASE WHEN sh.event_type = 'founded' THEN 1 END) as founding_events,
            COUNT(CASE WHEN sh.event_type = 'opened_store' THEN 1 END) as store_openings,
            COUNT(CASE WHEN sh.event_type = 'closed_store' THEN 1 END) as store_closures,
            COUNT(CASE WHEN sh.event_type = 'milestone' THEN 1 END) as milestones,
            COUNT(CASE WHEN sh.event_type = 'expansion' THEN 1 END) as expansions,
            COUNT(CASE WHEN sh.impact_level = 'critical' THEN 1 END) as critical_events,
            COUNT(CASE WHEN sh.impact_level = 'high' THEN 1 END) as high_impact_events,
            -- Timeline span
            MIN(sh.event_date) as first_event_date,
            MAX(sh.event_date) as last_event_date,
            MAX(sh.event_date) - MIN(sh.event_date) as timeline_duration_days,
            -- Age calculations
            EXTRACT(YEAR FROM CURRENT_DATE) - s.founded_year as years_active,
            CASE
                WHEN s.closure_date IS NOT NULL
                THEN EXTRACT(YEAR FROM s.closure_date) - s.founded_year
                ELSE EXTRACT(YEAR FROM CURRENT_DATE) - s.founded_year
            END as operational_years
        FROM core.suppliers s
        LEFT JOIN core.supplier_history sh ON s.id = sh.supplier_id
        WHERE s.founded_year IS NOT NULL
        GROUP BY s.id, s.name, s.slug, s.display_name, s.city, s.country,
                 s.status, s.founded_year, s.founder_name, s.instagram_handle,
                 s.instagram_url, s.website, s.closure_date
        ORDER BY s.founded_year, s.name
    """,

    "supplier_event_matrix": """
        -- Event Matrix: Perfect for Metabase Pivot Tables
        CREATE OR REPLACE VIEW analytics.supplier_event_matrix AS
        SELECT
            s.name as supplier_name,
            EXTRACT(YEAR FROM sh.event_date) as event_year,
            sh.event_type,
            sh.impact_level,
            COUNT(*) as event_count,
            STRING_AGG(sh.event_title, ' | ' ORDER BY sh.event_date) as events_summary
        FROM core.supplier_history sh
        JOIN core.suppliers s ON sh.supplier_id = s.id
        GROUP BY s.name, EXTRACT(YEAR FROM sh.event_date), sh.event_type, sh.impact_level
        ORDER BY event_year, s.name
    """,

    "supplier_geographic_overview": """
        -- Geographic Overview: Perfect for Metabase Maps
        CREATE OR REPLACE VIEW analytics.supplier_geographic_overview AS
        SELECT
            s.name,
            s.city,
            s.country,
            s.status,
            s.founded_year,
            COUNT(sh.id) as total_events,
            -- Coordinates for German cities (approximate)
            CASE s.city
                WHEN 'Berlin' THEN 52.5200
                WHEN 'München' THEN 48.1351
                WHEN 'Munich' THEN 48.1351
                WHEN 'Hamburg' THEN 53.5511
                WHEN 'Düsseldorf' THEN 51.2277
                WHEN 'Darmstadt' THEN 49.8728
                ELSE NULL
            END as latitude,
            CASE s.city
                WHEN 'Berlin' THEN 13.4050
                WHEN 'München' THEN 11.5820
                WHEN 'Munich' THEN 11.5820
                WHEN 'Hamburg' THEN 9.9937
                WHEN 'Düsseldorf' THEN 6.7735
                WHEN 'Darmstadt' THEN 8.6512
                ELSE NULL
            END as longitude
        FROM core.suppliers s
        LEFT JOIN core.supplier_history sh ON s.id = sh.supplier_id
        WHERE s.founded_year IS NOT NULL
        GROUP BY s.name, s.city, s.country, s.status, s.founded_year
        ORDER BY s.name
    """,

    "supplier_status_breakdown": """
        -- Status Breakdown: Perfect for Metabase Pie/Donut Charts
        CREATE OR REPLACE VIEW analytics.supplier_status_breakdown AS
        SELECT
            s.status,
            COUNT(*) as supplier_count,
            COUNT(sh.id) as total_events,
            ROUND(AVG(EXTRACT(YEAR FROM CURRENT_DATE) - s.founded_year), 1) as avg_age_years,
            STRING_AGG(s.name, ', ' ORDER BY s.name) as suppliers
        FROM core.suppliers s
        LEFT JOIN core.supplier_history sh ON s.id = sh.supplier_id
        WHERE s.founded_year IS NOT NULL
        GROUP BY s.status
        ORDER BY supplier_count DESC
    """,

    "supplier_detailed_table": """
        -- Detailed Table: Perfect for Metabase Tables with conditional formatting
        CREATE OR REPLACE VIEW analytics.supplier_detailed_table AS
        SELECT
            s.name,
            s.city,
            s.founded_year,
            s.founder_name,
            s.status,
            s.instagram_handle,
            s.website,
            -- Event counts
            COUNT(sh.id) as events,
            COUNT(CASE WHEN sh.event_type = 'opened_store' THEN 1 END) as stores_opened,
            COUNT(CASE WHEN sh.impact_level IN ('high', 'critical') THEN 1 END) as major_events,
            -- Timeline
            TO_CHAR(MIN(sh.event_date), 'YYYY') as first_event,
            TO_CHAR(MAX(sh.event_date), 'YYYY') as last_event,
            EXTRACT(YEAR FROM MAX(sh.event_date)) - EXTRACT(YEAR FROM MIN(sh.event_date)) + 1 as active_years,
            -- Status indicators
            CASE
                WHEN s.status = 'closed' THEN '[X]'
                WHEN s.status = 'active' THEN '[OK]'
                ELSE '[?]'
            END as status_emoji,
            CASE
                WHEN s.closure_date IS NOT NULL THEN TO_CHAR(s.closure_date, 'YYYY-MM-DD')
                ELSE NULL
            END as closed_date
        FROM core.suppliers s
        LEFT JOIN core.supplier_history sh ON s.id = sh.supplier_id
        WHERE s.founded_year IS NOT NULL
        GROUP BY s.id, s.name, s.city, s.founded_year, s.founder_name,
                 s.status, s.instagram_handle, s.website, s.closure_date
        ORDER BY s.founded_year, s.name
    """
}


async def main():
    print("=" * 100)
    print("CREATING METABASE-OPTIMIZED SUPPLIER HISTORY VIEWS")
    print("=" * 100)

    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # Create analytics schema if not exists
        print("\n[*] Creating analytics schema...")
        await session.execute(text("CREATE SCHEMA IF NOT EXISTS analytics"))
        print("[OK] Analytics schema ready")

        # Create all views
        for view_name, view_sql in VIEWS.items():
            print(f"\n[*] Creating view: {view_name}...")
            try:
                await session.execute(text(view_sql))
                print(f"[OK] View created: {view_name}")
            except Exception as e:
                print(f"[ERROR] Failed to create {view_name}: {e}")

        await session.commit()

        # Test views with sample queries
        print("\n" + "=" * 100)
        print("TESTING VIEWS - SAMPLE DATA")
        print("=" * 100)

        # Test 1: Timeline view
        print("\n1. TIMELINE VIEW (First 5 events):")
        result = await session.execute(
            text("""
                SELECT
                    event_date, supplier_name, event_title,
                    impact_level, status_indicator, years_since_founding
                FROM analytics.supplier_timeline_view
                LIMIT 5
            """)
        )
        for row in result:
            print(f"   {row[0]} | {row[1]:15s} | {row[2]:40s} | {row[3]:8s} | {row[4]:10s} | Year {row[5]}")

        # Test 2: Summary stats
        print("\n2. SUMMARY STATISTICS:")
        result = await session.execute(
            text("""
                SELECT
                    name, city, founded_year, total_events,
                    store_openings, milestones, operational_years, status
                FROM analytics.supplier_summary_stats
                ORDER BY founded_year
            """)
        )
        for row in result:
            years = int(row[6]) if row[6] is not None else 0
            print(f"   {row[0]:15s} | {row[1]:12s} | {row[2]} | Events: {row[3]:2d} | Stores: {row[4]:2d} | Milestones: {row[5]:2d} | {years:2d} years | {row[7]}")

        # Test 3: Geographic overview
        print("\n3. GEOGRAPHIC OVERVIEW:")
        result = await session.execute(
            text("""
                SELECT name, city, latitude, longitude, total_events, status
                FROM analytics.supplier_geographic_overview
                ORDER BY name
            """)
        )
        for row in result:
            coords = f"{row[2]:.4f}, {row[3]:.4f}" if row[2] and row[3] else "No coords"
            print(f"   {row[0]:15s} | {row[1]:12s} | {coords:20s} | {row[4]:2d} events | {row[5]}")

        # Test 4: Status breakdown
        print("\n4. STATUS BREAKDOWN:")
        result = await session.execute(
            text("""
                SELECT status, supplier_count, total_events, avg_age_years
                FROM analytics.supplier_status_breakdown
            """)
        )
        for row in result:
            print(f"   {row[0]:10s} | Count: {row[1]:2d} | Events: {row[2]:3d} | Avg Age: {row[3]:4.1f} years")

        print("\n" + "=" * 100)
        print("METABASE VISUALIZATION RECOMMENDATIONS")
        print("=" * 100)

        recommendations = """
1. SUPPLIER TIMELINE DASHBOARD
   [CHART] Line Chart with Events
   [VIEW] supplier_timeline_view
   [SETUP]
       - X-axis: event_date
       - Y-axis: event_sequence (or supplier_name for multi-line)
       - Series: supplier_name
       - Color by: impact_color
    Shows: Chronological progression of all supplier events

2. EVENT IMPACT ANALYSIS
    Chart Type: Stacked Bar Chart
    View: supplier_event_matrix
     Setup:
       - X-axis: event_year
       - Y-axis: event_count
       - Series: event_type
       - Color by: impact_level
    Shows: Event frequency and types over time

3. SUPPLIER KPI CARDS
    Chart Type: Number Cards / Gauges
    View: supplier_summary_stats
     Setup:
       - Metric: total_events, operational_years, store_openings
       - Filter by: supplier_name
    Shows: Key metrics for each supplier

4. GEOGRAPHIC DISTRIBUTION
    Chart Type: Pin Map
    View: supplier_geographic_overview
     Setup:
       - Latitude: latitude
       - Longitude: longitude
       - Size by: total_events
       - Color by: status
    Shows: Where suppliers are located in Germany

5. STATUS OVERVIEW
    Chart Type: Donut Chart
    View: supplier_status_breakdown
     Setup:
       - Dimension: status
       - Metric: supplier_count
    Shows: Active vs. closed suppliers

6. DETAILED SUPPLIER TABLE
    Chart Type: Table with Conditional Formatting
    View: supplier_detailed_table
     Setup:
       - Columns: All fields
       - Conditional Formatting:
         * status_emoji: Highlight closed suppliers in red
         * major_events: Bold if > 3
         * active_years: Color gradient by duration
    Shows: Complete supplier overview with metrics

7. EVENT TYPE BREAKDOWN
    Chart Type: Row Chart
    View: supplier_event_matrix
     Setup:
       - Y-axis: event_type
       - X-axis: SUM(event_count)
       - Series: supplier_name
    Shows: Which suppliers had which types of events
        """

        print(recommendations)

        print("\n" + "=" * 100)
        print("[OK] ALL METABASE VIEWS CREATED SUCCESSFULLY!")
        print("=" * 100)
        print("\nNext steps:")
        print("1. Open Metabase at http://localhost:6400")
        print("2. Create a new dashboard: 'Supplier History Analytics'")
        print("3. Add questions using the views in 'analytics' schema")
        print("4. Follow the recommendations above for chart types")


if __name__ == "__main__":
    asyncio.run(main())
