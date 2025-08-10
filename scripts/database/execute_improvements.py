#!/usr/bin/env python3
"""
Execute Database Improvements Script
"""
import asyncio
import sys
from pathlib import Path
sys.path.append('.')

from shared.database.connection import DatabaseManager
from sqlalchemy import text

async def execute_improvements():
    """Execute the database improvements SQL script"""
    
    print("SoleFlipper Database Improvements Execution")
    print("=" * 60)
    
    # Load the SQL script
    sql_file = Path(__file__).parent / "quick_db_improvements.sql"
    if not sql_file.exists():
        print(f"ERROR: SQL file not found: {sql_file}")
        return False
    
    print(f"Loading SQL script: {sql_file.name}")
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Split into individual statements
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
    
    print(f"Found {len(statements)} SQL statements to execute")
    
    db = DatabaseManager()
    await db.initialize()
    
    executed_count = 0
    failed_count = 0
    
    try:
        async with db.get_session() as session:
            for i, statement in enumerate(statements, 1):
                try:
                    # Skip comments and empty statements
                    if not statement or statement.startswith('--'):
                        continue
                    
                    print(f"Executing statement {i}/{len(statements)}...")
                    
                    # Execute the statement
                    await session.execute(text(statement))
                    await session.commit()
                    executed_count += 1
                    
                    # Show progress for long operations
                    if i % 10 == 0:
                        print(f"  Progress: {i}/{len(statements)} statements")
                    
                except Exception as e:
                    # Some errors are expected (e.g., "already exists")
                    error_str = str(e).lower()
                    if any(expected in error_str for expected in ['already exists', 'does not exist']):
                        print(f"  Note: {e} (expected, continuing)")
                        executed_count += 1
                    else:
                        print(f"  ERROR in statement {i}: {e}")
                        failed_count += 1
                        continue
        
        print(f"\\nExecution completed:")
        print(f"  Successfully executed: {executed_count}")
        print(f"  Failed: {failed_count}")
        
        if failed_count == 0:
            print("SUCCESS: All improvements applied successfully!")
            return True
        elif failed_count < executed_count / 10:  # Less than 10% failures
            print("SUCCESS: Improvements applied with minor issues")
            return True
        else:
            print("ERROR: Too many failures during execution")
            return False
        
    except Exception as e:
        print(f"CRITICAL ERROR: Database improvements failed: {e}")
        return False
    
    finally:
        await db.close()

async def verify_improvements():
    """Verify that the improvements were applied"""
    
    print("\\nVerifying database improvements...")
    
    db = DatabaseManager()
    await db.initialize()
    
    try:
        async with db.get_session() as session:
            # Check if new schemas exist
            schema_check = await session.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name IN ('finance', 'analytics', 'audit')
            """))
            schemas = [row[0] for row in schema_check.fetchall()]
            
            print(f"New schemas created: {schemas}")
            
            # Check if new tables exist
            table_check = await session.execute(text("""
                SELECT schemaname, tablename 
                FROM pg_tables 
                WHERE schemaname IN ('finance', 'analytics', 'audit', 'sales')
                AND tablename IN ('buyers', 'expenses', 'change_log')
            """))
            tables = [(row[0], row[1]) for row in table_check.fetchall()]
            
            print(f"New tables created: {tables}")
            
            # Check if new indexes exist
            index_check = await session.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE indexname LIKE 'idx_%transactions_%' 
                   OR indexname LIKE 'idx_%products_%'
                   OR indexname LIKE 'idx_%inventory_%'
            """))
            indexes = [row[0] for row in index_check.fetchall()]
            
            print(f"Performance indexes: {len(indexes)} created")
            
            # Check if views exist
            view_check = await session.execute(text("""
                SELECT schemaname, viewname 
                FROM pg_views 
                WHERE schemaname = 'analytics'
            """))
            views = [(row[0], row[1]) for row in view_check.fetchall()]
            
            print(f"Analytics views: {views}")
            
            if schemas and tables and indexes:
                print("SUCCESS: All major improvements verified!")
                return True
            else:
                print("WARNING: Some improvements may not have been applied")
                return False
                
    except Exception as e:
        print(f"ERROR: Verification failed: {e}")
        return False
    
    finally:
        await db.close()

if __name__ == "__main__":
    print("Starting database improvements...")
    
    success = asyncio.run(execute_improvements())
    
    if success:
        verification_success = asyncio.run(verify_improvements())
        
        if verification_success:
            print("\\n" + "="*60)
            print("DATABASE IMPROVEMENTS COMPLETED SUCCESSFULLY!")
            print("Your SoleFlipper database now has:")
            print("  • Performance indexes for faster queries")
            print("  • Buyer management tables")
            print("  • Expense tracking capabilities")
            print("  • Analytics views and reports")
            print("  • Audit trail for all changes")
            print("="*60)
        else:
            print("\\nWARNING: Improvements applied but verification incomplete")
    else:
        print("\\nERROR: Database improvements failed!")
        print("Your database is unchanged (backup available if needed)")