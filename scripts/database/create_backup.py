#!/usr/bin/env python3
"""
Create Database Backup before Schema Changes
"""
import asyncio
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

async def create_database_backup():
    """Create a full database backup using pg_dump"""
    
    # Database connection details
    db_config = {
        'host': '192.168.2.45',
        'port': '2665', 
        'database': 'soleflip',
        'username': 'metabaseuser',
        'password': 'metabasepass'
    }
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'soleflip_backup_before_improvements_{timestamp}.sql'
    backup_path = Path(__file__).parent / backup_filename
    
    print(f"Creating database backup...")
    print(f"Backup file: {backup_filename}")
    
    # Construct pg_dump command
    cmd = [
        'pg_dump',
        '-h', db_config['host'],
        '-p', db_config['port'],
        '-U', db_config['username'],
        '-d', db_config['database'],
        '--verbose',
        '--no-password',
        '--format=custom',
        '--compress=6',
        '--file', str(backup_path)
    ]
    
    # Set password via environment
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']
    
    try:
        print("Running pg_dump...")
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            backup_size = backup_path.stat().st_size / (1024 * 1024)  # MB
            print(f"SUCCESS: Backup created successfully!")
            print(f"Size: {backup_size:.1f} MB")
            print(f"Location: {backup_path}")
            
            # Also create a plain SQL backup for easier reading
            sql_backup_path = backup_path.with_suffix('.plain.sql')
            cmd_plain = cmd.copy()
            cmd_plain[cmd_plain.index('--format=custom')] = '--format=plain'
            cmd_plain[cmd_plain.index('--compress=6')] = '--no-owner'
            cmd_plain[cmd_plain.index('--file')] = '--file'
            cmd_plain[cmd_plain.index(str(backup_path))] = str(sql_backup_path)
            
            print("Creating plain SQL backup for readability...")
            subprocess.run(cmd_plain, env=env, capture_output=True)
            
            if sql_backup_path.exists():
                sql_size = sql_backup_path.stat().st_size / (1024 * 1024)
                print(f"Plain SQL backup: {sql_size:.1f} MB")
            
            return str(backup_path)
            
        else:
            print(f"ERROR: Backup failed!")
            print(f"Error: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("ERROR: Backup timed out after 5 minutes")
        return None
    except FileNotFoundError:
        print("ERROR: pg_dump not found. Make sure PostgreSQL client tools are installed.")
        return None
    except Exception as e:
        print(f"ERROR: Backup failed with error: {e}")
        return None

async def verify_backup(backup_path):
    """Verify the backup file is valid"""
    if not backup_path or not Path(backup_path).exists():
        return False
        
    try:
        # Check if pg_restore can read the backup
        cmd = ['pg_restore', '--list', backup_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            lines = result.stdout.count('\n')
            print(f"SUCCESS: Backup verification successful - {lines} objects found")
            return True
        else:
            print(f"ERROR: Backup verification failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"ERROR: Backup verification error: {e}")
        return False

if __name__ == "__main__":
    print("SoleFlipper Database Backup")
    print("=" * 50)
    
    backup_path = asyncio.run(create_database_backup())
    
    if backup_path:
        print("\nVerifying backup...")
        if asyncio.run(verify_backup(backup_path)):
            print("\nSUCCESS: Backup completed and verified successfully!")
            print("You can now proceed with the schema improvements.")
            
            # Create a restore script for emergencies
            restore_script = Path(__file__).parent / "restore_backup.sh"
            with open(restore_script, 'w') as f:
                f.write(f"""#!/bin/bash
# Emergency restore script
echo "WARNING: EMERGENCY RESTORE - This will OVERWRITE the current database!"
echo "Press Ctrl+C to cancel, or wait 10 seconds to proceed..."
sleep 10

export PGPASSWORD='metabasepass'
pg_restore \\
    -h 192.168.2.45 \\
    -p 2665 \\
    -U metabaseuser \\
    -d soleflip \\
    --clean --if-exists \\
    --verbose \\
    '{backup_path}'

echo "Restore completed"
""")
            
            restore_script.chmod(0o755)
            print(f"Emergency restore script created: {restore_script}")
            
        else:
            print("\nERROR: Backup verification failed - DO NOT proceed with changes!")
    else:
        print("\nERROR: Backup failed - DO NOT proceed with schema changes!")
        sys.exit(1)