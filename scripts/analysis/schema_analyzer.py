import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine


def get_schema_markdown(sync_conn: Connection) -> str:
    """
    Inspects the database schema using a synchronous connection and returns a Markdown string.
    """
    print("Executing inspection...")
    inspector = inspect(sync_conn)
    markdown_output = ["# Database Schema Analysis"]

    schema_names = inspector.get_schema_names()
    schemas_to_document = [
        s for s in schema_names if not s.startswith("pg_") and s not in ("information_schema",)
    ]
    print(f"Found schemas to document: {schemas_to_document}")

    for schema in sorted(schemas_to_document):
        markdown_output.append(f"\n## Schema: `{schema}`")
        table_names = inspector.get_table_names(schema=schema)

        if not table_names:
            markdown_output.append("\n*No tables found in this schema.*")
            continue

        for table_name in sorted(table_names):
            markdown_output.append(f"\n### Table: `{schema}.{table_name}`")

            # Columns
            markdown_output.append("\n| Column Name | Data Type | Nullable | Default |")
            markdown_output.append("|-------------|-----------|----------|---------|")
            columns = inspector.get_columns(table_name, schema=schema)
            for column in columns:
                col_name = column["name"]
                col_type = repr(column["type"])
                col_nullable = column["nullable"]
                col_default = column.get("default", "N/A")
                markdown_output.append(
                    f"| `{col_name}` | `{col_type}` | {col_nullable} | `{col_default}` |"
                )

            # Foreign Keys
            fks = inspector.get_foreign_keys(table_name, schema=schema)
            if fks:
                markdown_output.append("\n**Foreign Keys:**\n")
                markdown_output.append(
                    "| Constrained Columns | Points To Table | Points To Columns |"
                )
                markdown_output.append(
                    "|---------------------|-----------------|-------------------|"
                )
                for fk in fks:
                    constrained_cols = ", ".join(fk["constrained_columns"])
                    referred_table = f"{fk['referred_schema']}.{fk['referred_table']}"
                    referred_cols = ", ".join(fk["referred_columns"])
                    markdown_output.append(
                        f"| `{constrained_cols}` | `{referred_table}` | `{referred_cols}` |"
                    )

            # Indexes
            indexes = inspector.get_indexes(table_name, schema=schema)
            if indexes:
                markdown_output.append("\n**Indexes:**\n")
                markdown_output.append("| Name | Columns | Unique |")
                markdown_output.append("|------|---------|--------|")
                for index in indexes:
                    name = index["name"]
                    cols = ", ".join(index["column_names"])
                    unique = index["unique"]
                    markdown_output.append(f"| `{name}` | `{cols}` | {unique} |")

    return "\n".join(markdown_output)


async def analyze_schema():
    """
    Connects to the database asynchronously and runs the synchronous inspection.
    """
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL environment variable not set.")
        return

    print("Connecting to database...")
    engine = create_async_engine(db_url)

    try:
        async with engine.connect() as conn:
            markdown_content = await conn.run_sync(get_schema_markdown)

        # Ensure the output directory exists
        output_dir = Path("docs/generated")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "db_schema_analysis.md"

        print(f"Writing analysis to {output_file}...")
        with open(output_file, "w") as f:
            f.write(markdown_content)

        print("Schema analysis complete.")

    except Exception as e:
        print(f"An error occurred: {e}")
        return


if __name__ == "__main__":
    asyncio.run(analyze_schema())
