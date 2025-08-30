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
from urllib.parse import urlparse
from dotenv import load_dotenv


async def create_database_backup():
    """Create a full database backup using pg_dump, loading config from .env"""

    load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not found.")
        print("Please ensure it is set in your .env file or environment.")
        return None, None

    try:
        parsed_url = urlparse(database_url)
        db_config = {
            "username": parsed_url.username,
            "password": parsed_url.password,
            "host": parsed_url.hostname,
            "port": str(parsed_url.port or 5432),
            "database": parsed_url.path.lstrip("/"),
        }
    except Exception as e:
        print(f"ERROR: Could not parse DATABASE_URL. Please check its format. Error: {e}")
        return None, None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"soleflip_backup_{timestamp}.sql"
    backup_path = Path(__file__).parent.parent.parent / "data" / "backups" / backup_filename
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Creating database backup...")
    print(f"Host: {db_config['host']}, DB: {db_config['database']}")
    print(f"Backup file: {backup_path}")

    cmd = [
        "pg_dump",
        "-h",
        db_config["host"],
        "-p",
        db_config["port"],
        "-U",
        db_config["username"],
        "-d",
        db_config["database"],
        "--verbose",
        "--no-password",
        "--format=custom",
        "--compress=6",
        "--file",
        str(backup_path),
    ]

    env = os.environ.copy()
    env["PGPASSWORD"] = db_config["password"]

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            backup_size = backup_path.stat().st_size / (1024 * 1024)
            print(f"SUCCESS: Backup created successfully!")
            print(f"Size: {backup_size:.2f} MB")
            print(f"Location: {backup_path}")
            return str(backup_path), db_config
        else:
            print(f"ERROR: Backup failed!")
            print(f"Error: {result.stderr}")
            return None, None

    except FileNotFoundError:
        print(
            "ERROR: pg_dump not found. Make sure PostgreSQL client tools are installed and in your PATH."
        )
        return None, None
    except Exception as e:
        print(f"ERROR: Backup failed with an unexpected error: {e}")
        return None, None


async def verify_backup(backup_path):
    """Verify the backup file is valid using pg_restore."""
    if not backup_path or not Path(backup_path).exists():
        return False

    try:
        cmd = ["pg_restore", "--list", backup_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            lines = result.stdout.count("\n")
            print(f"SUCCESS: Backup verification successful - {lines} objects found.")
            return True
        else:
            print(f"ERROR: Backup verification failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"ERROR: Backup verification error: {e}")
        return False


if __name__ == "__main__":
    print("SoleFlipper Database Backup Utility")
    print("=" * 50)

    backup_path, db_config = asyncio.run(create_database_backup())

    if backup_path and db_config:
        print("\nVerifying backup...")
        if asyncio.run(verify_backup(backup_path)):
            print("\nSUCCESS: Backup completed and verified successfully!")

            restore_script_path = Path(backup_path).parent / f"restore_{Path(backup_path).stem}.sh"
            with open(restore_script_path, "w") as f:
                f.write(
                    f"""#!/bin/bash
# Emergency restore script for backup '{Path(backup_path).name}'
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

echo "WARNING: This script will OVERWRITE the database '{db_config['database']}' on host '{db_config['host']}'!"
echo "Press Ctrl+C to cancel, or Enter to continue in 10 seconds..."
sleep 10

# Set the password for the pg_restore command
export PGPASSWORD='{db_config['password']}'

echo "Starting restore..."
pg_restore \\
    -h {db_config['host']} \\
    -p {db_config['port']} \\
    -U {db_config['username']} \\
    -d {db_config['database']} \\
    --clean \\
    --if-exists \\
    --verbose \\
    "{backup_path}"

# Unset the password
unset PGPASSWORD

echo "Restore completed."
"""
                )

            restore_script_path.chmod(0o755)
            print(f"\nTo restore this backup, run the following command:")
            print(f"  {restore_script_path}")

        else:
            print("\nERROR: Backup verification failed! The backup file may be corrupt.")
    else:
        print("\nERROR: Backup creation failed! No changes were made.")
        sys.exit(1)
