import os
import shutil
import json
from datetime import datetime

def create_directory_structure():
    """Create organized directory structure for SoleFlipper"""
    
    print("=== SOLEFLIPER CODEBASE CLEANUP & ORGANIZATION ===")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Define new directory structure
    directories = [
        'scripts/database',
        'scripts/brand_intelligence', 
        'scripts/transactions',
        'data/backups',
        'data/samples',
        'data/dev',
        'config/n8n',
        'sql/improvements',
        'sql/dashboards',
        'docs/setup',
        'docs/guides/n8n_integration',
        'docs/guides/metabase_setup',
        'docs/guides/backup_restore'
    ]
    
    # Create directories
    print("\n1. Creating organized directory structure...")
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  OK Created: {directory}")
    
    # File organization mappings
    file_moves = {
        # Brand Intelligence Scripts
        'scripts/brand_intelligence': [
            'brand_deep_dive_schema.py',
            'brand_deep_dive_summary.py', 
            'brand_deep_dive_views.py',
            'brand_relationships_collaborations.py',
            'populate_brand_deep_dive.py'
        ],
        
        # Database Scripts
        'scripts/database': [
            'create_backup.py',
            'create_app_backup.py',
            'create_backup_after_brand_extensions.py',
            'create_manual_backup.py',
            'check_database_integrity.py',
            'execute_improvements.py',
            'execute_simple_improvements.py'
        ],
        
        # Transaction Scripts
        'scripts/transactions': [
            'check_alias_transactions.py',
            'create_alias_transactions.py'
        ],
        
        # Data Files
        'data/backups': [
            'soleflip_backup_before_improvements_20250806_073936.sql',
            'backup_metadata_20250807_133519.json'
        ],
        
        'data/samples': [
            'sales report for total.csv',
            'stockx_historical_seller_sales_report_ab3c4afb-7b84-11eb-a20e-124738b50e12_1751996312862.csv'
        ],
        
        'data/dev': [
            'soleflip_demo.db'
        ],
        
        # Configuration Files
        'config/n8n': [
            'n8n_direct_db_inventory_status.json',
            'n8n_direct_db_supplier_update.json',
            'n8n_direct_db_transaction_updates.json',
            'n8n_notion_supplier_sync_workflow.json'
        ],
        
        # SQL Files
        'sql/improvements': [
            'quick_db_improvements.sql',
            'shopify_inspired_improvements.sql'
        ],
        
        'sql/dashboards': [
            'brand_dashboard_queries.sql',
            'brand_dashboard_sql_queries.sql'
        ],
        
        # Documentation
        'docs/setup': [
            'QUICKSTART.md',
            'SCHEMA_MIGRATION_GUIDE.md',
            'RESTORE_INSTRUCTIONS.md'
        ],
        
        'docs/guides/n8n_integration': [
            'N8N_DIRECT_DB_SETUP_GUIDE.md',
            'N8N_NOTION_INTEGRATION_STATUS.md',
            'N8N_SUPPLIER_SYNC_SETUP.md'
        ],
        
        'docs/guides/backup_restore': [
            'BACKUP_INFO.md',
            'BACKUP_STATUS_2025-08-01.md',
            'BACKUP_STATUS_2025-08-03.md',
            'BACKUP_STATUS_2025-08-05.md',
            'BACKUP_STATUS_BRAND_INTELLIGENCE_20250807_133519.md'
        ]
    }
    
    # Move files
    print("\n2. Moving files to organized locations...")
    total_moved = 0
    errors = []
    
    for target_dir, files in file_moves.items():
        print(f"\n  Moving to {target_dir}:")
        for file in files:
            try:
                if os.path.exists(file):
                    shutil.move(file, os.path.join(target_dir, os.path.basename(file)))
                    print(f"    OK Moved: {file}")
                    total_moved += 1
                else:
                    print(f"    - Skip: {file} (not found)")
            except Exception as e:
                error_msg = f"Error moving {file}: {e}"
                print(f"    ERROR {error_msg}")
                errors.append(error_msg)
    
    # Clean up files to delete
    print("\n3. Cleaning up files...")
    files_to_delete = [
        'soleflip_backup_20250805_080106.sql',  # Empty backup file
    ]
    
    for file in files_to_delete:
        try:
            if os.path.exists(file):
                # Check file size before deleting
                size = os.path.getsize(file)
                if size == 0:
                    os.remove(file)
                    print(f"    OK Deleted empty file: {file}")
                else:
                    print(f"    - Kept: {file} (not empty: {size} bytes)")
            else:
                print(f"    - Skip: {file} (not found)")
        except Exception as e:
            print(f"    ERROR deleting {file}: {e}")
    
    # Rename files with spaces
    print("\n4. Renaming files for consistency...")
    if os.path.exists('data/samples/sales report for total.csv'):
        try:
            shutil.move('data/samples/sales report for total.csv', 'data/samples/sales_report_for_total.csv')
            print("    OK Renamed: sales report for total.csv -> sales_report_for_total.csv")
        except Exception as e:
            print(f"    ERROR renaming file: {e}")
    
    # Create README files for new directories
    print("\n5. Creating directory README files...")
    readme_content = {
        'scripts': "# Scripts Directory\n\nUtility scripts organized by purpose:\n- `database/` - Backup and database management scripts\n- `brand_intelligence/` - Brand analytics and deep dive scripts\n- `transactions/` - Transaction processing utilities\n",
        
        'data': "# Data Directory\n\nData files organized by type:\n- `backups/` - Database backup files\n- `samples/` - Sample data files for testing\n- `dev/` - Development databases and test data\n",
        
        'config': "# Configuration Directory\n\nConfiguration files for external services:\n- `n8n/` - N8N workflow configurations and setups\n",
        
        'sql': "# SQL Directory\n\nSQL queries and scripts organized by purpose:\n- `improvements/` - Database improvement and optimization scripts\n- `dashboards/` - Dashboard and analytics query collections\n"
    }
    
    for dir_name, content in readme_content.items():
        readme_path = os.path.join(dir_name, 'README.md')
        try:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"    OK Created: {readme_path}")
        except Exception as e:
            print(f"    ERROR creating {readme_path}: {e}")
    
    # Generate cleanup report
    print("\n6. Generating cleanup report...")
    cleanup_report = {
        'cleanup_completed': datetime.now().isoformat(),
        'directories_created': len(directories),
        'files_moved': total_moved,
        'errors': errors,
        'new_structure': {
            'scripts': {
                'database': len(file_moves.get('scripts/database', [])),
                'brand_intelligence': len(file_moves.get('scripts/brand_intelligence', [])),
                'transactions': len(file_moves.get('scripts/transactions', []))
            },
            'data': {
                'backups': len(file_moves.get('data/backups', [])),
                'samples': len(file_moves.get('data/samples', [])),
                'dev': len(file_moves.get('data/dev', []))
            },
            'config': {
                'n8n': len(file_moves.get('config/n8n', []))
            },
            'sql': {
                'improvements': len(file_moves.get('sql/improvements', [])),
                'dashboards': len(file_moves.get('sql/dashboards', []))
            }
        }
    }
    
    with open('CLEANUP_REPORT.json', 'w', encoding='utf-8') as f:
        json.dump(cleanup_report, f, indent=2)
    
    print(f"    OK Created: CLEANUP_REPORT.json")
    
    print(f"\n=== CLEANUP COMPLETED ===")
    print(f"OK Directories created: {len(directories)}")
    print(f"OK Files moved: {total_moved}")
    print(f"OK Errors: {len(errors)}")
    
    if errors:
        print("\nErrors encountered:")
        for error in errors:
            print(f"  - {error}")
    
    print(f"\nSoleFlipper codebase is now professionally organized!")
    return cleanup_report

if __name__ == "__main__":
    create_directory_structure()