import os

IS_POSTGRES = bool(os.getenv('DATABASE_URL'))

def get_schema_ref(table_name: str, schema_name: str) -> str:
    """
    Constructs a schema-qualified table name for ForeignKey references,
    but only if a database schema is actually in use (i.e., not SQLite).
    """
    if IS_POSTGRES:
        return f"{schema_name}.{table_name}"
    return table_name
