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
