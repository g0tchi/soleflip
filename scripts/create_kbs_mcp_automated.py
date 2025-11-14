#!/usr/bin/env python3
"""
Automated MindsDB Knowledge Base Creator via MCP (v3.0)

This script generates SQL commands for creating Knowledge Bases in MindsDB.
Works with create_mindsdb_kbs_via_mcp.py

Prerequisites:
    1. Run create_mindsdb_kbs_via_mcp.py first to populate PostgreSQL
    2. Have MCP MindsDB server configured in Claude Code

Usage:
    python scripts/create_kbs_mcp_automated.py
"""

from pathlib import Path

# Configuration
MINDSDB_PROJECT = "soleflipper"
POSTGRES_DB_NAME = "soleflip_pg"
EMBEDDING_MODEL = "text-embedding-3-small"
RERANKING_MODEL = "gpt-4o"

# PostgreSQL connection
PG_HOST = "localhost"
PG_PORT = 5432
PG_DATABASE = "soleflip"
PG_USER = "soleflip"
PG_PASSWORD = "SoleFlip2025SecureDB!"

KB_DEFINITIONS = {
    "kb_database_schema": {
        "title": "Database Schema & Migrations",
        "test_question": "How is the database structured?",
    },
    "kb_integrations": {
        "title": "External Integrations & APIs",
        "test_question": "How does StockX integration work?",
    },
    "kb_architecture_design": {
        "title": "Architecture & Design Patterns",
        "test_question": "How does the pricing engine work?",
    },
    "kb_code_quality_dev": {
        "title": "Code Quality & Development",
        "test_question": "What linting standards apply?",
    },
    "kb_operations_history": {
        "title": "Operations & Historical Context",
        "test_question": "How does Notion sync work?",
    },
}


def generate_complete_script() -> str:
    """Generate complete SQL script"""
    script = f"""/*
================================================================================
MindsDB Knowledge Base Creation Script
Project: {MINDSDB_PROJECT}
Version: v3.0
================================================================================
*/

-- ============================================================================
-- Step 1: Connect MindsDB to PostgreSQL
-- ============================================================================

CREATE DATABASE {POSTGRES_DB_NAME}
WITH ENGINE = 'postgres',
PARAMETERS = {{
    "host": "{PG_HOST}",
    "port": {PG_PORT},
    "database": "{PG_DATABASE}",
    "user": "{PG_USER}",
    "password": "{PG_PASSWORD}"
}};

-- Verify connection
SELECT * FROM {POSTGRES_DB_NAME}.context_documents LIMIT 5;

"""

    # Add each KB creation
    for kb_name, kb_def in KB_DEFINITIONS.items():
        script += f"""
-- ============================================================================
-- {kb_def['title']}
-- ============================================================================

CREATE KNOWLEDGE_BASE {MINDSDB_PROJECT}.{kb_name}
FROM (
    SELECT
        id,
        file_path,
        file_name,
        content,
        category,
        file_size_kb,
        last_modified,
        version
    FROM {POSTGRES_DB_NAME}.context_documents
    WHERE kb_name = '{kb_name}'
)
USING
    embedding_model = {{
        "provider": "openai",
        "model_name": "{EMBEDDING_MODEL}",
    }},
    reranking_model = {{
        "provider": "openai",
        "model_name": "{RERANKING_MODEL}",
    }},
    metadata_columns = ['file_path', 'category', 'file_size_kb', 'last_modified', 'version'],
    content_columns = ['content'],
    id_column = 'id';

-- Test
SELECT file_path, category FROM {MINDSDB_PROJECT}.{kb_name}
WHERE question = '{kb_def['test_question']}'
LIMIT 3;

"""

    script += """
-- ============================================================================
-- Complete! 🎉
-- ============================================================================
"""
    return script


def main():
    """Main execution"""
    print("=" * 80)
    print("MindsDB Knowledge Base SQL Generator")
    print("=" * 80)

    # Generate and save
    script = generate_complete_script()
    output_file = Path(__file__).parent / "mindsdb_kb_creation.sql"

    with open(output_file, "w") as f:
        f.write(script)

    print(f"\n✅ Generated SQL script: {output_file}")
    print("\n📋 Next steps:")
    print("1. Run: python scripts/create_mindsdb_kbs_via_mcp.py")
    print("2. Use Claude Code MCP to execute SQL commands")
    print("3. Test Knowledge Bases with queries")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
