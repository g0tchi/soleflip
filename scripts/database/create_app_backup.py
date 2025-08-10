#!/usr/bin/env python3
"""
Create Database Backup using App Database Connection
"""
import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
sys.path.append('.')

from shared.database.connection import DatabaseManager
from sqlalchemy import text

async def create_app_backup():
    """Create backup using app database connection"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'soleflip_backup_before_improvements_{timestamp}.sql'
    backup_path = Path(__file__).parent / backup_filename
    
    print(f"SoleFlipper Database Backup via App Connection")
    print("=" * 60)
    print(f"Creating backup: {backup_filename}")
    
    db = DatabaseManager()
    await db.initialize()
    
    try:
        with open(backup_path, 'w', encoding='utf-8') as backup_file:
            backup_file.write(f"-- SoleFlipper Database Backup\n")
            backup_file.write(f"-- Created: {datetime.now()}\n")
            backup_file.write(f"-- Before Schema Improvements\n\n")
            
            # Get all tables to backup
            tables_to_backup = [
                ('core', 'brands'),
                ('core', 'categories'), 
                ('core', 'sizes'),
                ('core', 'suppliers'),
                ('core', 'supplier_brands'),
                ('core', 'platforms'),
                ('products', 'products'),
                ('products', 'inventory'),
                ('sales', 'transactions'),
                ('integration', 'import_batches'),
                ('integration', 'import_records')
            ]
            
            async with db.get_session() as session:
                total_rows = 0
                
                for schema, table in tables_to_backup:
                    try:
                        print(f"Backing up {schema}.{table}...")
                        
                        # Get table structure
                        structure_query = text(f"""
                            SELECT column_name, data_type, is_nullable, column_default
                            FROM information_schema.columns
                            WHERE table_schema = '{schema}' AND table_name = '{table}'
                            ORDER BY ordinal_position
                        """)
                        
                        structure_result = await session.execute(structure_query)
                        columns = structure_result.fetchall()
                        
                        if not columns:
                            print(f"  Warning: Table {schema}.{table} not found, skipping...")
                            continue
                        
                        backup_file.write(f"\\n-- Table: {schema}.{table}\\n")
                        
                        # Get all data
                        data_query = text(f"SELECT * FROM {schema}.{table}")
                        data_result = await session.execute(data_query)
                        rows = data_result.fetchall()
                        
                        if rows:
                            # Write column names
                            column_names = [col.column_name for col in columns]
                            
                            # Create INSERT statements
                            backup_file.write(f"-- Data for {schema}.{table} ({len(rows)} rows)\\n")
                            
                            for row in rows:
                                values = []
                                for i, value in enumerate(row):
                                    if value is None:
                                        values.append('NULL')
                                    elif isinstance(value, str):
                                        # Escape single quotes
                                        escaped_value = value.replace("'", "''")
                                        values.append(f"'{escaped_value}'")
                                    elif isinstance(value, datetime):
                                        values.append(f"'{value.isoformat()}'")
                                    else:
                                        values.append(str(value))
                                
                                insert_sql = f"INSERT INTO {schema}.{table} ({', '.join(column_names)}) VALUES ({', '.join(values)});\\n"
                                backup_file.write(insert_sql)
                            
                            total_rows += len(rows)
                            print(f"  {len(rows)} rows backed up")
                        else:
                            print(f"  No data found")
                            
                    except Exception as e:
                        print(f"  Error backing up {schema}.{table}: {e}")
                        backup_file.write(f"-- ERROR backing up {schema}.{table}: {e}\\n")
                        continue
                
                # Add metadata
                backup_file.write(f"\\n-- Backup completed\\n")
                backup_file.write(f"-- Total rows backed up: {total_rows}\\n")
                
        backup_size = backup_path.stat().st_size / (1024 * 1024)  # MB
        print(f"\\nSUCCESS: Backup completed!")
        print(f"File: {backup_path}")
        print(f"Size: {backup_size:.1f} MB")
        print(f"Total rows: {total_rows}")
        
        return str(backup_path)
        
    except Exception as e:
        print(f"ERROR: Backup failed: {e}")
        if backup_path.exists():
            backup_path.unlink()  # Clean up partial backup
        return None
    
    finally:
        await db.close()

async def verify_app_backup(backup_path):
    """Verify backup file exists and has content"""
    if not backup_path or not Path(backup_path).exists():
        return False
    
    try:
        with open(backup_path, 'r', encoding='utf-8') as f:
            content = f.read()
            insert_count = content.count('INSERT INTO')
            
        if insert_count > 0:
            print(f"SUCCESS: Backup verified - {insert_count} INSERT statements found")
            return True
        else:
            print("ERROR: Backup verification failed - no INSERT statements found")
            return False
            
    except Exception as e:
        print(f"ERROR: Backup verification error: {e}")
        return False

if __name__ == "__main__":
    backup_path = asyncio.run(create_app_backup())
    
    if backup_path:
        print("\\nVerifying backup...")
        if asyncio.run(verify_app_backup(backup_path)):
            print("\\nSUCCESS: Backup completed and verified!")
            print("You can now proceed with schema improvements.")
            
            # Create simple restore note
            restore_note = Path(__file__).parent / "RESTORE_INSTRUCTIONS.md"
            with open(restore_note, 'w') as f:
                f.write(f"""# Emergency Restore Instructions

If you need to restore the database:

1. **Connect to PostgreSQL:**
   ```
   psql -h 192.168.2.45 -p 2665 -U metabaseuser -d soleflip
   ```

2. **Clean existing data:**
   ```sql
   TRUNCATE sales.transactions CASCADE;
   TRUNCATE products.inventory CASCADE;  
   TRUNCATE products.products CASCADE;
   TRUNCATE core.brands CASCADE;
   TRUNCATE core.categories CASCADE;
   TRUNCATE core.sizes CASCADE;
   TRUNCATE core.suppliers CASCADE;
   TRUNCATE core.platforms CASCADE;
   ```

3. **Restore from backup:**
   ```
   \\i {backup_path}
   ```

Backup created: {datetime.now()}
""")
            print(f"Restore instructions: {restore_note}")
        else:
            print("\\nERROR: Backup verification failed!")
    else:
        print("\\nERROR: Backup creation failed!")