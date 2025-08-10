#!/usr/bin/env python3
"""
Metabase Dashboard Validation Script
Testet alle Analytics Views und gibt Performance-Statistiken aus
"""

import asyncio
import asyncpg
import time
from datetime import datetime

async def validate_metabase_views():
    """Validiert alle Analytics Views für Metabase Dashboards"""
    db_url = 'postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip'
    
    # Liste aller Views die getestet werden sollen
    views_to_test = [
        'analytics.daily_revenue',
        'analytics.monthly_revenue', 
        'analytics.revenue_growth',
        'analytics.top_products_revenue',
        'analytics.brand_performance',
        'analytics.platform_performance',
        'analytics.sales_by_country',
        'analytics.sales_by_weekday',
        'analytics.executive_dashboard',
        'analytics.recent_transactions',
        'analytics.brand_deep_dive_overview',
        'analytics.nike_product_breakdown',
        'analytics.brand_monthly_performance'
    ]
    
    print("METABASE DASHBOARD VALIDATION")
    print("=" * 50)
    print(f"Zeitpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Views zu testen: {len(views_to_test)}")
    print()
    
    conn = await asyncpg.connect(db_url)
    
    try:
        results = []
        total_start = time.time()
        
        for view_name in views_to_test:
            print(f"Testing {view_name}...")
            
            # Performance Test
            start_time = time.time()
            try:
                # Test basic SELECT
                result = await conn.fetch(f"SELECT * FROM {view_name} LIMIT 5")
                query_time = time.time() - start_time
                
                # Count total rows
                count_start = time.time()
                count_result = await conn.fetchval(f"SELECT COUNT(*) FROM {view_name}")
                count_time = time.time() - count_start
                
                # Get column info
                columns = list(result[0].keys()) if result else []
                
                status = "SUCCESS"
                error = None
                
            except Exception as e:
                query_time = time.time() - start_time
                count_time = 0
                count_result = 0
                columns = []
                status = "ERROR"
                error = str(e)
                
            results.append({
                'view': view_name,
                'status': status,
                'rows': count_result,
                'columns': len(columns),
                'query_time': round(query_time * 1000, 2),  # ms
                'count_time': round(count_time * 1000, 2),  # ms
                'error': error,
                'column_names': columns[:5]  # First 5 columns
            })
            
            print(f"   Status: {status}")
            print(f"   Rows: {count_result:,}")
            print(f"   Query Time: {round(query_time * 1000, 2)}ms")
            if error:
                print(f"   Error: {error}")
            print()
        
        total_time = time.time() - total_start
        
        # Summary Report
        print("📈 VALIDATION SUMMARY")
        print("=" * 50)
        
        successful_views = [r for r in results if r['status'] == '✅ SUCCESS']
        failed_views = [r for r in results if r['status'] == '❌ ERROR']
        
        print(f"✅ Successful Views: {len(successful_views)}/{len(views_to_test)}")
        print(f"❌ Failed Views: {len(failed_views)}")
        print(f"⏱️  Total Validation Time: {round(total_time, 2)}s")
        print()
        
        # Performance Stats
        if successful_views:
            avg_query_time = sum(r['query_time'] for r in successful_views) / len(successful_views)
            max_query_time = max(r['query_time'] for r in successful_views)
            min_query_time = min(r['query_time'] for r in successful_views)
            
            print("⚡ PERFORMANCE STATS")
            print("-" * 30)
            print(f"Average Query Time: {round(avg_query_time, 2)}ms")
            print(f"Fastest Query: {round(min_query_time, 2)}ms")
            print(f"Slowest Query: {round(max_query_time, 2)}ms")
            print()
        
        # Data Quality Check
        print("🔍 DATA QUALITY CHECK")
        print("-" * 30)
        
        total_rows = sum(r['rows'] for r in successful_views if 'revenue' in r['view'])
        print(f"Revenue Views Total Rows: {total_rows:,}")
        
        # Check for empty views
        empty_views = [r['view'] for r in successful_views if r['rows'] == 0]
        if empty_views:
            print(f"⚠️  Empty Views: {', '.join(empty_views)}")
        else:
            print("✅ All views contain data")
        
        print()
        
        # Detailed Results Table
        print("📋 DETAILED RESULTS")
        print("-" * 80)
        print(f"{'View Name':<35} {'Status':<10} {'Rows':<8} {'Time':<8} {'Cols':<5}")
        print("-" * 80)
        
        for result in results:
            view_short = result['view'].replace('analytics.', '')
            print(f"{view_short:<35} {result['status']:<10} {result['rows']:<8,} {result['query_time']:<8.1f} {result['columns']:<5}")
        
        print("-" * 80)
        
        # Failed Views Details
        if failed_views:
            print("\n❌ FAILED VIEWS DETAILS")
            print("-" * 50)
            for result in failed_views:
                print(f"View: {result['view']}")
                print(f"Error: {result['error']}")
                print()
        
        # Recommendations
        print("💡 RECOMMENDATIONS")
        print("-" * 30)
        
        slow_views = [r for r in successful_views if r['query_time'] > 1000]  # > 1 second
        if slow_views:
            print("⚠️  Consider optimizing these slow views:")
            for view in slow_views:
                print(f"   - {view['view']}: {view['query_time']}ms")
        else:
            print("✅ All views perform well (< 1 second)")
        
        print()
        print("🎯 METABASE DASHBOARD READINESS")
        print("-" * 40)
        
        if len(successful_views) == len(views_to_test):
            print("🚀 ALL SYSTEMS GO! Ready for Metabase dashboard creation.")
            print("   Next steps:")
            print("   1. Open Metabase (http://192.168.2.45:3000)")
            print("   2. Use SQL queries from metabase_sql_queries.sql")
            print("   3. Follow metabase_dashboard_import_guide.md")
        else:
            print("⚠️  Some views need attention before dashboard creation.")
            print("   Fix failed views first, then re-run validation.")
        
        print()
        print("=" * 50)
        print("✨ Validation Complete!")
        
    except Exception as e:
        print(f"💥 Database connection error: {e}")
    finally:
        await conn.close()

async def run_sample_queries():
    """Führt Sample Queries für Dashboard-Test aus"""
    db_url = 'postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip'
    
    sample_queries = [
        ("Executive KPIs", "SELECT total_revenue, total_transactions, avg_order_value FROM analytics.executive_dashboard"),
        ("Top 5 Brands", "SELECT extracted_brand, total_revenue FROM analytics.brand_deep_dive_overview ORDER BY total_revenue DESC LIMIT 5"),
        ("Recent Transactions", "SELECT transaction_date, product_name, sale_price FROM analytics.recent_transactions LIMIT 5"),
        ("Monthly Trends", "SELECT month, gross_revenue FROM analytics.monthly_revenue ORDER BY month DESC LIMIT 6")
    ]
    
    print("\n🧪 SAMPLE QUERY TESTS")
    print("=" * 50)
    
    conn = await asyncpg.connect(db_url)
    
    try:
        for query_name, query in sample_queries:
            print(f"\n📊 {query_name}")
            print("-" * 30)
            
            try:
                result = await conn.fetch(query)
                
                if result:
                    # Print column headers
                    columns = list(result[0].keys())
                    header = " | ".join(f"{col:<15}" for col in columns)
                    print(header)
                    print("-" * len(header))
                    
                    # Print first few rows
                    for row in result[:3]:
                        row_str = " | ".join(f"{str(val):<15}" for val in row.values())
                        print(row_str)
                    
                    if len(result) > 3:
                        print(f"... and {len(result) - 3} more rows")
                else:
                    print("No data returned")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
    except Exception as e:
        print(f"💥 Database connection error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    print("Starting Metabase Dashboard Validation...")
    print()
    
    # Run main validation
    asyncio.run(validate_metabase_views())
    
    # Run sample queries
    asyncio.run(run_sample_queries())
    
    print("\nAll done! Check the results above.")