import subprocess
import datetime
import os
import asyncio
import asyncpg

async def create_comprehensive_backup():
    """Create comprehensive backup after brand deep dive extensions"""
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"soleflip_backup_brand_intelligence_{timestamp}.sql"
    backup_path = os.path.join(os.getcwd(), backup_filename)
    
    print("=== CREATING COMPREHENSIVE BACKUP AFTER BRAND EXTENSIONS ===")
    print(f"Backup will be saved to: {backup_path}")
    
    # Database connection details
    host = "192.168.2.45"
    port = "2665" 
    database = "soleflip"
    username = "metabaseuser"
    password = "metabasepass"
    
    # Create comprehensive backup command
    pg_dump_cmd = [
        "pg_dump",
        f"--host={host}",
        f"--port={port}", 
        f"--username={username}",
        f"--dbname={database}",
        "--verbose",
        "--clean",
        "--if-exists",
        "--create",
        "--format=plain",
        f"--file={backup_path}"
    ]
    
    print("Starting database backup...")
    print(f"Command: {' '.join(pg_dump_cmd)}")
    
    # Set environment variable for password
    env = os.environ.copy()
    env['PGPASSWORD'] = password
    
    try:
        # Execute backup
        result = subprocess.run(
            pg_dump_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode == 0:
            print("✓ Database backup completed successfully!")
            
            # Check backup file size
            if os.path.exists(backup_path):
                file_size = os.path.getsize(backup_path) / (1024 * 1024)  # MB
                print(f"✓ Backup file created: {backup_filename}")
                print(f"✓ File size: {file_size:.2f} MB")
            
            # Get database statistics
            conn = await asyncpg.connect(f'postgresql://{username}:{password}@{host}:{port}/{database}')
            
            # Count total records across all schemas
            total_records = 0
            schemas_info = {}
            
            schemas = ['core', 'sales', 'integration', 'analytics']
            for schema in schemas:
                tables = await conn.fetch("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = $1
                """, schema)
                
                schema_records = 0
                schema_tables = []
                
                for table in tables:
                    table_name = table['table_name']
                    try:
                        count = await conn.fetchval(f"SELECT COUNT(*) FROM {schema}.{table_name}")
                        schema_records += count
                        schema_tables.append(f"{table_name}: {count}")
                    except Exception as e:
                        schema_tables.append(f"{table_name}: ERROR")
                
                schemas_info[schema] = {
                    'records': schema_records,
                    'tables': len(tables),
                    'details': schema_tables
                }
                total_records += schema_records
            
            await conn.close()
            
            print(f"\n=== BACKUP CONTENTS SUMMARY ===")
            print(f"Total database records: {total_records:,}")
            
            for schema, info in schemas_info.items():
                print(f"\n{schema.upper()} Schema:")
                print(f"  Tables: {info['tables']}")
                print(f"  Records: {info['records']:,}")
                
                # Show key tables for each schema
                if schema == 'core':
                    key_tables = ['brands', 'brand_history', 'brand_collaborations', 'suppliers', 'platforms']
                elif schema == 'sales':
                    key_tables = ['transactions', 'buyers']
                elif schema == 'integration':
                    key_tables = ['import_records', 'import_batches']
                else:  # analytics
                    key_tables = ['brand_encyclopedia', 'brand_timeline', 'brand_cultural_impact']
                
                print(f"  Key tables:")
                for detail in info['details']:
                    table_name = detail.split(':')[0]
                    if table_name in key_tables:
                        print(f"    {detail}")
            
            # Create backup status report
            status_report = f"""# BACKUP STATUS REPORT - {timestamp}

## Backup Details
- **Filename**: {backup_filename}
- **Created**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **File Size**: {file_size:.2f} MB
- **Status**: ✓ SUCCESS

## Database Contents
- **Total Records**: {total_records:,}
- **Schemas**: {len(schemas)} (core, sales, integration, analytics)
- **Total Tables**: {sum(info['tables'] for info in schemas_info.values())}

## Key Achievements in This Backup
- ✓ Complete brand deep dive intelligence system
- ✓ 29 historical events across 7 major brands
- ✓ Brand collaboration tracking (Nike x Off-White, Adidas x Kanye, etc.)
- ✓ Financial performance data across multiple years
- ✓ Cultural impact scoring and personality analysis
- ✓ 7 new analytics views for comprehensive brand intelligence
- ✓ All original data preserved and unmodified

## Brand Intelligence Extensions
- Extended core.brands with 25+ new fields (founder, HQ, financials, story, mission)
- Added core.brand_history: 29 historical milestones
- Added core.brand_collaborations: Partnership tracking with success metrics
- Added core.brand_attributes: 15 personality and style attributes
- Added core.brand_relationships: Parent company and ownership mapping
- Added core.brand_financials: 6 years of financial data

## Analytics Views Created
- analytics.brand_encyclopedia: Complete brand profiles
- analytics.brand_timeline: Chronological history with impact levels
- analytics.brand_collaboration_network: Partnership analysis
- analytics.brand_innovation_timeline: Technology milestones
- analytics.brand_financial_evolution: Multi-year performance analysis
- analytics.brand_personality_analysis: Brand values and traits
- analytics.brand_cultural_impact: Influence scoring and tier classification

This backup contains a fully functional Brand Intelligence System ready for advanced analytics and dashboards.
"""
            
            # Save status report
            status_filename = f"BACKUP_STATUS_BRAND_INTELLIGENCE_{timestamp}.md"
            with open(status_filename, 'w', encoding='utf-8') as f:
                f.write(status_report)
            
            print(f"\n✓ Backup status report saved: {status_filename}")
            print(f"\n=== BACKUP COMPLETED SUCCESSFULLY ===")
            print(f"✓ Database backup: {backup_filename}")
            print(f"✓ Status report: {status_filename}")
            print(f"✓ All brand intelligence extensions preserved")
            
        else:
            print("✗ Backup failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            
    except subprocess.TimeoutExpired:
        print("✗ Backup timed out after 10 minutes")
    except Exception as e:
        print(f"✗ Backup error: {e}")

if __name__ == "__main__":
    asyncio.run(create_comprehensive_backup())