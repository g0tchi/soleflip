"""
Database Utility Functions Module
=================================

This module provides utility functions for database schema management,
specifically handling differences between PostgreSQL (with schema support)
and SQLite (without schema support) for testing.

Key Features:
    - Runtime detection of database type (PostgreSQL vs SQLite)
    - Test environment detection (pytest)
    - Schema-qualified table name generation
    - Cross-database compatibility layer

Functions:
    - get_schema_ref: Constructs schema-qualified table names for ForeignKey references

Environment Variables:
    - DATABASE_URL: Database connection string (detects PostgreSQL prefix)

Testing Support:
    - Automatically disables schema references when running under pytest
    - Enables SQLite for fast test execution
    - Production uses PostgreSQL with multi-schema architecture

Example Usage:
    ```python
    from shared.database.utils import get_schema_ref

    # In production (PostgreSQL): returns "transactions.orders"
    # In tests (SQLite): returns "orders"
    table_ref = get_schema_ref("orders", "transactions")
    ```

Related Modules:
    - shared.database.connection: Database connection management
    - shared.database.models: ORM models using schema references
    - tests/conftest.py: Test database configuration

See Also:
    - docs/database-schema-complete-analysis.md: Schema documentation
    - CLAUDE.md: Database architecture section
"""

import os
import sys

# We are using PostgreSQL schemas in production, but SQLite for tests.
# SQLite does not support schemas. This logic determines when to apply the schema.
# It checks if we're running under pytest, or if the DATABASE_URL is for postgres.
IS_TESTING = "pytest" in sys.modules
IS_POSTGRES = os.getenv("DATABASE_URL", "").startswith("postgresql") and not IS_TESTING


def get_schema_ref(table_name: str, schema_name: str) -> str:
    """
    Constructs a schema-qualified table name for ForeignKey references,
    but only if using PostgreSQL (and not in a test environment).
    """
    if IS_POSTGRES:
        return f"{schema_name}.{table_name}"
    return table_name
