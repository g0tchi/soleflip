#!/usr/bin/env python3
"""
Safe database migration script with automatic backup and rollback capability.
Used in CI/CD pipeline for automated deployments.
"""

import asyncio
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
import structlog
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logger = structlog.get_logger(__name__)


class SafeMigrationManager:
    """Safe database migration with backup and rollback capabilities"""

    def __init__(self, dry_run: bool = False):
        self.db_url = os.getenv("DATABASE_URL", "").replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        self.dry_run = dry_run
        self.connection = None
        self.backup_file = None

        # Parse database connection details
        self.db_config = self._parse_db_url()

    def _parse_db_url(self) -> dict:
        """Parse database URL into connection components"""
        from urllib.parse import urlparse

        parsed = urlparse(self.db_url)
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "database": parsed.path.lstrip("/"),
            "user": parsed.username,
            "password": parsed.password,
        }

    async def connect(self):
        """Connect to database"""
        try:
            self.connection = await asyncpg.connect(self.db_url)
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error("Failed to connect to database", error=str(e))
            raise

    async def disconnect(self):
        """Disconnect from database"""
        if self.connection:
            await self.connection.close()
            logger.info("Disconnected from database")

    def create_backup(self) -> str:
        """Create database backup using pg_dump"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)

        backup_file = backup_dir / f"migration_backup_{timestamp}.sql"

        logger.info("Creating database backup", backup_file=str(backup_file))

        if self.dry_run:
            logger.info("DRY RUN: Would create backup", backup_file=str(backup_file))
            return str(backup_file)

        try:
            # Build pg_dump command
            cmd = [
                "pg_dump",
                "--host",
                self.db_config["host"],
                "--port",
                str(self.db_config["port"]),
                "--username",
                self.db_config["user"],
                "--dbname",
                self.db_config["database"],
                "--verbose",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                "--file",
                str(backup_file),
            ]

            # Set password via environment variable
            env = os.environ.copy()
            if self.db_config["password"]:
                env["PGPASSWORD"] = self.db_config["password"]

            # Execute pg_dump
            subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)

            logger.info(
                "Database backup created successfully",
                backup_file=str(backup_file),
                size_bytes=backup_file.stat().st_size,
            )

            self.backup_file = str(backup_file)
            return str(backup_file)

        except subprocess.CalledProcessError as e:
            logger.error("Backup failed", error=e.stderr)
            raise RuntimeError(f"Database backup failed: {e.stderr}")

    async def get_current_migration(self) -> str:
        """Get current migration version"""
        try:
            result = await self.connection.fetch("SELECT version_num FROM alembic_version")
            if result:
                return result[0]["version_num"]
            return "no_migration"
        except Exception as e:
            logger.warning("Could not get current migration", error=str(e))
            return "unknown"

    def run_migration(self, target: str = "head") -> bool:
        """Run Alembic migration"""
        logger.info("Running database migration", target=target, dry_run=self.dry_run)

        if self.dry_run:
            logger.info("DRY RUN: Would run migration", target=target)
            return True

        try:
            # Run Alembic upgrade
            cmd = ["python", "-m", "alembic", "upgrade", target]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            logger.info("Migration completed successfully", target=target, output=result.stdout)

            return True

        except subprocess.CalledProcessError as e:
            logger.error("Migration failed", target=target, error=e.stderr, output=e.stdout)
            return False

    def rollback_migration(self, target_version: str) -> bool:
        """Rollback to specific migration version"""
        logger.warning("Rolling back migration", target_version=target_version)

        if self.dry_run:
            logger.info("DRY RUN: Would rollback to", target_version=target_version)
            return True

        try:
            cmd = ["python", "-m", "alembic", "downgrade", target_version]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            logger.info(
                "Rollback completed successfully",
                target_version=target_version,
                output=result.stdout,
            )

            return True

        except subprocess.CalledProcessError as e:
            logger.error("Rollback failed", target_version=target_version, error=e.stderr)
            return False

    def restore_from_backup(self, backup_file: str) -> bool:
        """Restore database from backup file"""
        logger.warning("Restoring database from backup", backup_file=backup_file)

        if self.dry_run:
            logger.info("DRY RUN: Would restore from backup", backup_file=backup_file)
            return True

        try:
            # Build psql command
            cmd = [
                "psql",
                "--host",
                self.db_config["host"],
                "--port",
                str(self.db_config["port"]),
                "--username",
                self.db_config["user"],
                "--dbname",
                self.db_config["database"],
                "--file",
                backup_file,
                "--quiet",
            ]

            # Set password via environment variable
            env = os.environ.copy()
            if self.db_config["password"]:
                env["PGPASSWORD"] = self.db_config["password"]

            # Execute psql
            subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)

            logger.info("Database restored from backup successfully", backup_file=backup_file)

            return True

        except subprocess.CalledProcessError as e:
            logger.error("Database restore failed", backup_file=backup_file, error=e.stderr)
            return False

    async def verify_migration(self) -> bool:
        """Verify migration was successful"""
        logger.info("Verifying migration")

        try:
            # Check if we can connect and query basic tables
            await self.connect()

            # Simple verification - just check that we can query alembic_version
            result = await self.connection.fetch("SELECT version_num FROM alembic_version")
            if result:
                logger.info(
                    "Migration verification passed", current_version=result[0]["version_num"]
                )
                return True
            else:
                logger.error("Migration verification failed - no version found")
                return False

        except Exception as e:
            logger.error("Migration verification failed with exception", error=str(e))
            return False
        finally:
            await self.disconnect()

    async def safe_migrate(self, target: str = "head") -> bool:
        """Perform safe migration with backup and rollback capability"""
        logger.info("Starting safe database migration", target=target, dry_run=self.dry_run)
        start_time = datetime.now()

        # Connect to get current state
        await self.connect()
        current_migration = await self.get_current_migration()
        await self.disconnect()

        logger.info("Current migration state", current_migration=current_migration)

        try:
            # Step 1: Create backup
            backup_file = self.create_backup()

            # Step 2: Run migration
            migration_success = self.run_migration(target)

            if not migration_success:
                logger.error("Migration failed, attempting rollback")

                # Try to rollback to previous version
                if current_migration != "no_migration" and current_migration != "unknown":
                    rollback_success = self.rollback_migration(current_migration)
                    if rollback_success:
                        logger.info("Successfully rolled back to previous version")
                        return False

                # If rollback fails, try to restore from backup
                logger.warning("Rollback failed, attempting restore from backup")
                restore_success = self.restore_from_backup(backup_file)

                if restore_success:
                    logger.info("Successfully restored from backup")
                else:
                    logger.critical("CRITICAL: Both rollback and restore failed!")

                return False

            # Step 3: Verify migration
            verification_success = await self.verify_migration()

            if not verification_success:
                logger.error("Migration verification failed, rolling back")

                # Rollback due to verification failure
                rollback_success = self.rollback_migration(current_migration)
                if not rollback_success:
                    # Try restore from backup
                    self.restore_from_backup(backup_file)

                return False

            # Success!
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                "Safe migration completed successfully",
                target=target,
                duration_seconds=duration,
                backup_file=backup_file,
            )

            return True

        except Exception as e:
            logger.error("Safe migration failed with exception", error=str(e))

            # Emergency restore
            if self.backup_file:
                logger.warning("Attempting emergency restore from backup")
                self.restore_from_backup(self.backup_file)

            return False


def main():
    """CLI interface for safe migration"""
    import argparse

    parser = argparse.ArgumentParser(description="Safe database migration with backup")
    parser.add_argument("--target", "-t", default="head", help="Migration target (default: head)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Perform dry run without actual changes"
    )

    args = parser.parse_args()

    migration_manager = SafeMigrationManager(dry_run=args.dry_run)

    async def run_migration():
        success = await migration_manager.safe_migrate(args.target)
        return success

    try:
        success = asyncio.run(run_migration())

        if success:
            print("Migration completed successfully")
            sys.exit(0)
        else:
            print("Migration failed")
            sys.exit(1)

    except KeyboardInterrupt:
        print("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Migration failed with exception: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
