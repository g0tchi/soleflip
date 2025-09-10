#!/usr/bin/env python3
"""
Database Management for Retro CLI
SQLAlchemy models and database operations with security focus
"""

import csv
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from utils import clear_screen, colored_text, progress_bar

from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database operations manager with security focus"""

    def __init__(self, config: Config):
        self.config = config
        self.engine = None
        self.SessionLocal = None
        self._connect()

    def _connect(self):
        """Initialize database connection"""
        try:
            # Use test database if in test mode
            db_url = self.config.get_connection_string(use_test=self.config.system.is_test)

            self.engine = create_engine(
                db_url, echo=self.config.system.debug, pool_pre_ping=True, pool_recycle=3600
            )

            self.SessionLocal = sessionmaker(bind=self.engine)

            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            logger.info("Database connection established")

        except SQLAlchemyError as e:
            logger.error(f"Database connection failed: {e}")
            # Don't fail completely, just mark as unavailable
            self.engine = None
            self.SessionLocal = None

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with proper cleanup"""
        if not self.SessionLocal:
            raise RuntimeError("Database not connected")

        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def check_connection(self) -> bool:
        """Check if database is connected and accessible"""
        if not self.engine:
            return False

        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            return False

    def list_tables(self):
        """List all database tables"""
        if not self.check_connection():
            print(colored_text("[X] Database not connected!", "red"))
            print(colored_text("Check your DATABASE_URL configuration", "yellow"))
            print(
                colored_text(
                    f"Currently configured: {self.config.database.host}:{self.config.database.port}",
                    "dim",
                )
            )
            input(colored_text("\nPress Enter to continue...", "dim"))
            return

        try:
            clear_screen()
            print(colored_text("[DB] DATABASE TABLES", "bright_cyan"))
            print(colored_text("=" * 50, "cyan"))

            inspector = inspect(self.engine)
            tables = inspector.get_table_names()

            if not tables:
                print(colored_text("No tables found in database", "yellow"))
                return

            for i, table in enumerate(tables, 1):
                # Get table info
                try:
                    columns = inspector.get_columns(table)
                    column_count = len(columns)

                    # Get row count (safely)
                    with self.get_session() as session:
                        result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        row_count = result.scalar()

                    print(colored_text(f"{i:2d}. {table}", "bright_white"))
                    print(colored_text(f"    Columns: {column_count}, Rows: {row_count:,}", "dim"))

                except Exception as e:
                    print(colored_text(f"{i:2d}. {table}", "bright_white"))
                    print(colored_text(f"    Error: {str(e)}", "red"))

        except SQLAlchemyError as e:
            print(colored_text(f"Error listing tables: {e}", "red"))

        input(colored_text("\nPress Enter to continue...", "dim"))

    def interactive_query(self):
        """Interactive SQL query interface"""
        if not self.check_connection():
            print(colored_text("[X] Database not connected!", "red"))
            print(colored_text("Check your DATABASE_URL configuration", "yellow"))
            input(colored_text("\nPress Enter to continue...", "dim"))
            return

        clear_screen()
        print(colored_text("[SQL] INTERACTIVE QUERY INTERFACE", "bright_cyan"))
        print(colored_text("=" * 50, "cyan"))
        print(colored_text("Security Note: Only SELECT queries allowed", "yellow"))
        print(colored_text("Type 'exit' or 'quit' to return to menu\n", "dim"))

        while True:
            try:
                query = input(colored_text("SQL> ", "bright_green"))

                if query.lower() in ["exit", "quit", ""]:
                    break

                # Security check - only allow SELECT queries
                query_upper = query.strip().upper()
                if not query_upper.startswith("SELECT"):
                    print(colored_text("❌ Only SELECT queries are allowed for security", "red"))
                    continue

                # Execute query
                with self.get_session() as session:
                    result = session.execute(text(query))

                    if result.returns_rows:
                        rows = result.fetchall()
                        columns = result.keys()

                        if not rows:
                            print(colored_text("No results found", "yellow"))
                            continue

                        # Display results in table format
                        print(colored_text(f"\nResults: {len(rows)} rows", "bright_green"))
                        print(colored_text("-" * 60, "dim"))

                        # Header
                        header = " | ".join(f"{col:15}" for col in columns)
                        print(colored_text(header, "bright_white"))
                        print(colored_text("-" * len(header), "dim"))

                        # Rows (limit to 20 for display)
                        display_rows = rows[:20]
                        for row in display_rows:
                            row_str = " | ".join(f"{str(val)[:15]:15}" for val in row)
                            print(colored_text(row_str, "white"))

                        if len(rows) > 20:
                            print(colored_text(f"... and {len(rows) - 20} more rows", "dim"))
                    else:
                        print(colored_text("Query executed successfully", "bright_green"))

            except KeyboardInterrupt:
                print(colored_text("\nQuery cancelled", "yellow"))
                break
            except SQLAlchemyError as e:
                print(colored_text(f"❌ SQL Error: {e}", "red"))
            except Exception as e:
                print(colored_text(f"❌ Error: {e}", "red"))

    def export_data(self):
        """Export table data to CSV"""
        if not self.check_connection():
            print(colored_text("❌ Database not connected!", "red"))
            return

        try:
            # List tables for selection
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()

            if not tables:
                print(colored_text("No tables found", "yellow"))
                return

            clear_screen()
            print(colored_text("📤 EXPORT TABLE DATA", "bright_cyan"))
            print(colored_text("═" * 30, "cyan"))

            # Display table options
            for i, table in enumerate(tables, 1):
                print(colored_text(f"{i}. {table}", "white"))

            print(colored_text("0. Cancel", "dim"))

            choice = input(colored_text("\nSelect table to export: ", "bright_green"))

            try:
                choice_idx = int(choice) - 1
                if choice == "0":
                    return
                if choice_idx < 0 or choice_idx >= len(tables):
                    raise ValueError

                table_name = tables[choice_idx]

            except ValueError:
                print(colored_text("Invalid selection", "red"))
                return

            # Export table
            output_file = f"{table_name}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            with self.get_session() as session:
                # Get all data
                result = session.execute(text(f"SELECT * FROM {table_name}"))
                rows = result.fetchall()
                columns = result.keys()

                if not rows:
                    print(colored_text("Table is empty", "yellow"))
                    return

                # Write CSV
                with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                    writer = csv.writer(csvfile)

                    # Write header
                    writer.writerow(columns)

                    # Write rows with progress
                    progress_bar(f"Exporting {table_name}", len(rows), 0.001)
                    writer.writerows(rows)

                print(
                    colored_text(
                        f"✅ Exported {len(rows):,} rows to: {output_file}", "bright_green"
                    )
                )

        except SQLAlchemyError as e:
            print(colored_text(f"Export error: {e}", "red"))
        except Exception as e:
            print(colored_text(f"Error: {e}", "red"))

        input(colored_text("\nPress Enter to continue...", "dim"))

    def import_data(self):
        """Import CSV data to table"""
        if not self.check_connection():
            print(colored_text("❌ Database not connected!", "red"))
            return

        clear_screen()
        print(colored_text("📥 IMPORT CSV DATA", "bright_cyan"))
        print(colored_text("═" * 30, "cyan"))
        print(colored_text("⚠️  WARNING: Only use trusted CSV files!", "yellow"))
        print(colored_text("This will INSERT data into existing tables.", "yellow"))

        # List CSV files in current directory
        csv_files = [f for f in os.listdir(".") if f.endswith(".csv")]

        if not csv_files:
            print(colored_text("No CSV files found in current directory", "yellow"))
            return

        print(colored_text("\nAvailable CSV files:", "bright_white"))
        for i, file in enumerate(csv_files, 1):
            file_size = os.path.getsize(file) / 1024  # KB
            print(colored_text(f"{i}. {file} ({file_size:.1f} KB)", "white"))

        print(colored_text("0. Cancel", "dim"))

        choice = input(colored_text("\nSelect CSV file: ", "bright_green"))

        try:
            choice_idx = int(choice) - 1
            if choice == "0":
                return
            if choice_idx < 0 or choice_idx >= len(csv_files):
                raise ValueError

            csv_file = csv_files[choice_idx]

        except ValueError:
            print(colored_text("Invalid selection", "red"))
            return

        # Preview CSV
        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
                first_row = next(reader, None)

                print(colored_text(f"\nCSV Preview - {csv_file}:", "bright_white"))
                print(colored_text("Headers: " + ", ".join(headers), "cyan"))
                if first_row:
                    print(colored_text("Sample: " + ", ".join(first_row), "dim"))

        except Exception as e:
            print(colored_text(f"Error reading CSV: {e}", "red"))
            return

        # Confirm import
        confirm = input(colored_text("\nProceed with import? (y/N): ", "yellow"))
        if confirm.lower() != "y":
            print(colored_text("Import cancelled", "yellow"))
            return

        print(colored_text("❌ CSV import functionality requires table mapping", "red"))
        print(colored_text("This feature is not yet implemented for security", "yellow"))

        input(colored_text("\nPress Enter to continue...", "dim"))

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self.check_connection():
            return {"connected": False}

        try:
            with self.get_session() as session:
                # Get table count
                inspector = inspect(self.engine)
                tables = inspector.get_table_names()

                # Get database size (PostgreSQL specific)
                try:
                    size_result = session.execute(
                        text("SELECT pg_size_pretty(pg_database_size(current_database()))")
                    )
                    db_size = size_result.scalar()
                except:
                    db_size = "Unknown"

                return {
                    "connected": True,
                    "table_count": len(tables),
                    "database_size": db_size,
                    "environment": "TEST" if self.config.system.is_test else "PRODUCTION",
                }

        except SQLAlchemyError:
            return {"connected": False}

    def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        health_status = {
            "connection": False,
            "query_performance": None,
            "error_count": 0,
            "warnings": [],
        }

        try:
            # Test connection
            start_time = datetime.now()
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            end_time = datetime.now()

            health_status["connection"] = True
            health_status["query_performance"] = (end_time - start_time).total_seconds() * 1000

            # Check for potential issues
            if self.config.system.is_production and self.config.system.debug:
                health_status["warnings"].append("Debug mode enabled in production")

            if not self.config.system.encryption_key:
                health_status["warnings"].append("Encryption key not configured")

        except SQLAlchemyError as e:
            health_status["error_count"] = 1
            health_status["warnings"].append(f"Connection error: {str(e)}")

        return health_status


if __name__ == "__main__":
    # Demo database operations
    from config import get_config

    config = get_config()
    db_manager = DatabaseManager(config)

    if db_manager.check_connection():
        print("✅ Database connected successfully")
        stats = db_manager.get_database_stats()
        print(f"Tables: {stats.get('table_count', 0)}")
        print(f"Size: {stats.get('database_size', 'Unknown')}")
    else:
        print("❌ Database connection failed")
