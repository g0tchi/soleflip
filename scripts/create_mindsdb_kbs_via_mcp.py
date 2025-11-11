#!/usr/bin/env python3
"""
MindsDB Knowledge Base Creator via MCP for SoleFlipper (v3.0)

This script creates domain-based knowledge bases in MindsDB using the MCP server.
It uses the local PostgreSQL database as a data source, which is more robust
than trying to pass content directly via SQL.

Strategy:
1. Create a PostgreSQL table for context documents
2. Populate it with markdown files from context/ folder
3. Connect MindsDB to PostgreSQL (if not already connected)
4. Create 5 domain-based knowledge bases from the PostgreSQL table

Requirements:
    pip install asyncpg python-dotenv

Usage:
    python scripts/create_mindsdb_kbs_via_mcp.py

Environment Variables (from .env):
    DATABASE_URL - PostgreSQL connection string
    OPENAI_API_KEY - OpenAI API key (optional, can be set in MindsDB)
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================
SCRIPT_DIR = Path(__file__).parent.parent
CONTEXT_DIR = SCRIPT_DIR / "context"
VERSION = "v3.0"

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not set in .env file")
    sys.exit(1)

# Convert SQLAlchemy asyncpg URL to asyncpg format
# postgresql+asyncpg://user:pass@host:port/db -> postgresql://user:pass@host:port/db
ASYNCPG_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Also create standard PostgreSQL URL for MindsDB
POSTGRES_URL = ASYNCPG_URL

# MindsDB Configuration
MINDSDB_PROJECT = "soleflipper"
EMBEDDING_MODEL = "text-embedding-3-small"
RERANKING_MODEL = "gpt-4o"

# ============================================================================
# Domain-Based Knowledge Base Definitions (matching v2.5.1)
# ============================================================================
KB_DEFINITIONS = {
    "kb_database_schema": {
        "title": "Database Schema & Migrations",
        "description": "Database schema, migrations, and data architecture",
        "categories": ["migrations", "database", "schema"],
        "paths": [
            CONTEXT_DIR / "migrations",
            CONTEXT_DIR / "database",
        ],
        "architecture_filters": ["database-*.md", "schema-*.md", "transactions-*.md"],
        "use_cases": [
            "How is the database structured?",
            "What migrations were performed?",
            "Multi-platform order system architecture",
        ],
    },
    "kb_integrations": {
        "title": "External Integrations & APIs",
        "description": "StockX, Metabase, Awin integrations and API documentation",
        "categories": ["integrations", "apis", "external"],
        "paths": [
            CONTEXT_DIR / "integrations",
        ],
        "exclude_patterns": ["*.pdf", "*.csv", "*.gz", "*.png", "*.jpg"],
        "use_cases": [
            "How does StockX integration work?",
            "What Metabase dashboards exist?",
            "How to import Awin feeds?",
        ],
    },
    "kb_architecture_design": {
        "title": "Architecture & Design Patterns",
        "description": "System architecture, design patterns, and business logic",
        "categories": ["architecture", "design", "patterns"],
        "paths": [
            CONTEXT_DIR / "architecture",
        ],
        "exclude_patterns": ["database-*.md", "schema-*.md"],
        "use_cases": [
            "How does the pricing engine work?",
            "What is the DDD structure?",
            "ROI calculation implementation",
        ],
    },
    "kb_code_quality_dev": {
        "title": "Code Quality & Development",
        "description": "Development standards, code quality, testing, and API documentation",
        "categories": ["development", "quality", "testing"],
        "paths": [
            CONTEXT_DIR / "refactoring",
            SCRIPT_DIR / "CLAUDE.md",
            SCRIPT_DIR / "README.md",
        ],
        "use_cases": [
            "What linting standards apply?",
            "How to run tests?",
            "What are the make commands?",
        ],
    },
    "kb_operations_history": {
        "title": "Operations & Historical Context",
        "description": "Notion integration, archived documentation, and historical decisions",
        "categories": ["operations", "notion", "history"],
        "paths": [
            CONTEXT_DIR / "notion",
            CONTEXT_DIR / "archived",
        ],
        "use_cases": [
            "How does Notion sync work?",
            "What happened in the refactoring sprint?",
            "Historical architectural decisions",
        ],
    },
}


# ============================================================================
# PostgreSQL Table Setup
# ============================================================================
async def create_context_documents_table(conn: asyncpg.Connection):
    """Create the context_documents table in PostgreSQL"""
    print("📊 Creating context_documents table...")

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS context_documents (
            id SERIAL PRIMARY KEY,
            kb_name VARCHAR(100) NOT NULL,
            file_path TEXT NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            category VARCHAR(50) NOT NULL,
            file_size_kb NUMERIC(10, 2),
            last_modified TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            version VARCHAR(20) DEFAULT 'v3.0',

            -- Indexes for faster queries
            CONSTRAINT unique_kb_file UNIQUE (kb_name, file_path)
        );

        CREATE INDEX IF NOT EXISTS idx_context_kb_name ON context_documents(kb_name);
        CREATE INDEX IF NOT EXISTS idx_context_category ON context_documents(category);
    """
    )

    print("✅ Table created/verified")


async def clear_context_documents(conn: asyncpg.Connection):
    """Clear existing data (optional)"""
    await conn.execute("TRUNCATE context_documents;")
    print("🗑️  Cleared existing context documents")


# ============================================================================
# Content Collection Functions
# ============================================================================
def should_include_file(file_path: Path, kb_def: Dict) -> bool:
    """Check if file should be included based on KB definition"""

    # Check exclude patterns
    exclude_patterns = kb_def.get("exclude_patterns", [])
    for pattern in exclude_patterns:
        if pattern.startswith("*"):
            # Extension pattern like "*.pdf"
            if file_path.suffix == pattern[1:]:
                return False
        else:
            # Filename pattern like "database-*.md"
            if file_path.match(pattern):
                return False

    # Check architecture filters (only for architecture KB)
    if "architecture_filters" in kb_def and "architecture" in str(file_path):
        filters = kb_def["architecture_filters"]
        matches = any(file_path.match(f) for f in filters)
        return matches

    return True


def read_file_safe(file_path: Path) -> Optional[str]:
    """Read file content safely"""
    try:
        # Skip binary files
        if file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".pdf", ".csv", ".gz"]:
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"⚠️  Could not read {file_path}: {e}")
        return None


def get_file_category(file_path: Path, kb_def: Dict) -> str:
    """Determine category from file path"""
    categories = kb_def.get("categories", [])

    # Check path components
    for category in categories:
        if category in str(file_path).lower():
            return category

    # Default to first category
    return categories[0] if categories else "general"


async def collect_and_insert_documents(conn: asyncpg.Connection, kb_name: str, kb_def: Dict) -> int:
    """Collect markdown files and insert into PostgreSQL"""
    print(f"\n{'='*60}")
    print(f"Processing: {kb_def['title']}")
    print(f"{'='*60}\n")

    documents = []

    for base_path in kb_def["paths"]:
        if not base_path.exists():
            print(f"⚠️  Path does not exist: {base_path}")
            continue

        # Handle single file
        if base_path.is_file():
            content = read_file_safe(base_path)
            if content:
                rel_path = base_path.relative_to(SCRIPT_DIR)
                documents.append(
                    {
                        "kb_name": kb_name,
                        "file_path": str(rel_path),
                        "file_name": base_path.name,
                        "content": content,
                        "category": get_file_category(base_path, kb_def),
                        "file_size_kb": len(content) / 1024,
                        "last_modified": datetime.fromtimestamp(base_path.stat().st_mtime),
                    }
                )
            continue

        # Handle directory
        for file_path in base_path.rglob("*.md"):
            if not should_include_file(file_path, kb_def):
                print(f"⏭️  Skipping: {file_path.name}")
                continue

            content = read_file_safe(file_path)
            if content:
                rel_path = file_path.relative_to(
                    CONTEXT_DIR if CONTEXT_DIR in file_path.parents else SCRIPT_DIR
                )
                documents.append(
                    {
                        "kb_name": kb_name,
                        "file_path": str(rel_path),
                        "file_name": file_path.name,
                        "content": content,
                        "category": get_file_category(file_path, kb_def),
                        "file_size_kb": len(content) / 1024,
                        "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime),
                    }
                )

    # Insert documents
    if documents:
        print(f"📄 Inserting {len(documents)} documents...")

        for doc in documents:
            await conn.execute(
                """
                INSERT INTO context_documents
                (kb_name, file_path, file_name, content, category, file_size_kb, last_modified, version)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (kb_name, file_path) DO UPDATE
                SET content = EXCLUDED.content,
                    file_size_kb = EXCLUDED.file_size_kb,
                    last_modified = EXCLUDED.last_modified,
                    version = EXCLUDED.version
            """,
                doc["kb_name"],
                doc["file_path"],
                doc["file_name"],
                doc["content"],
                doc["category"],
                doc["file_size_kb"],
                doc["last_modified"],
                VERSION,
            )

        total_size = sum(d["file_size_kb"] for d in documents)
        print(f"✅ Inserted {len(documents)} documents ({total_size:.1f} KB)")
    else:
        print(f"⚠️  No documents found for {kb_name}")

    return len(documents)


# ============================================================================
# MindsDB MCP Integration Instructions
# ============================================================================
def print_mcp_instructions():
    """Print instructions for using MCP to create Knowledge Bases"""
    print("\n" + "=" * 60)
    print("📋 MindsDB MCP Integration Instructions")
    print("=" * 60)
    print(
        """
Now that the PostgreSQL table is populated, you need to:

1. Connect MindsDB to PostgreSQL (if not already connected):

   Use the MCP tool mcp__mindsdb__query with this SQL:

   CREATE DATABASE soleflip_pg
   WITH ENGINE = 'postgres',
   PARAMETERS = {
       "host": "localhost",
       "port": 5432,
       "database": "soleflip",
       "user": "soleflip",
       "password": "SoleFlip2025SecureDB!"
   };

2. Verify the connection:

   SELECT * FROM soleflip_pg.context_documents LIMIT 5;

3. Create Knowledge Bases (one at a time):

   For kb_database_schema:
   """
    )

    for kb_name, kb_def in KB_DEFINITIONS.items():
        print(
            f"""
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
       FROM soleflip_pg.context_documents
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

   -- Test it:
   SELECT * FROM {MINDSDB_PROJECT}.{kb_name}
   WHERE question = '{kb_def["use_cases"][0]}'
   LIMIT 3;
   """
        )

    print(
        """
4. Alternative: Use the companion script to create all KBs automatically

   See create_kbs_mcp_automated.py for automated creation via MCP

"""
    )
    print("=" * 60)


# ============================================================================
# Main Execution
# ============================================================================
async def main():
    """Main execution function"""
    print("=" * 60)
    print("MindsDB Knowledge Base Creator via MCP")
    print(f"Version: {VERSION}")
    print("=" * 60)
    print()

    # Verify context directory exists
    if not CONTEXT_DIR.exists():
        print(f"❌ Context directory not found: {CONTEXT_DIR}")
        sys.exit(1)

    print(f"📂 Context directory: {CONTEXT_DIR}")
    print(f"🗄️  PostgreSQL URL: {POSTGRES_URL.split('@')[0]}@***")
    print()

    # Connect to PostgreSQL
    print("🔌 Connecting to PostgreSQL...")
    try:
        # Use ASYNCPG_URL (converted from SQLAlchemy format)
        conn = await asyncpg.connect(ASYNCPG_URL)
        print("✅ Connected to PostgreSQL")
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        sys.exit(1)

    try:
        # Create table
        await create_context_documents_table(conn)

        # Optional: clear existing data (add --clear flag to enable)
        if len(sys.argv) > 1 and sys.argv[1] == "--clear":
            print("\n🗑️  Clearing existing context_documents...")
            await clear_context_documents(conn)
        else:
            print("\n ℹ️  Keeping existing documents (use --clear flag to reset)")

        # Collect and insert documents
        print("\n📚 Collecting and inserting documents...")
        total_docs = 0
        stats = {}

        for kb_name, kb_def in KB_DEFINITIONS.items():
            count = await collect_and_insert_documents(conn, kb_name, kb_def)
            total_docs += count
            stats[kb_name] = count

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"✅ Total documents inserted: {total_docs}")
        print("📊 Documents per Knowledge Base:")
        for kb_name, count in stats.items():
            print(f"   - {kb_name}: {count} documents")

        # Verify data
        print("\n🔍 Verifying data...")
        result = await conn.fetch(
            """
            SELECT kb_name, COUNT(*) as doc_count,
                   SUM(file_size_kb) as total_size_kb
            FROM context_documents
            GROUP BY kb_name
            ORDER BY kb_name
        """
        )

        print("\n📊 Database Statistics:")
        for row in result:
            print(f"   - {row['kb_name']}: {row['doc_count']} docs, {row['total_size_kb']:.1f} KB")

        # Print MCP instructions
        print_mcp_instructions()

    finally:
        await conn.close()
        print("\n✅ PostgreSQL connection closed")

    print("\n" + "=" * 60)
    print("✅ Step 1 Complete: PostgreSQL table populated")
    print("📋 Next: Use MCP to create Knowledge Bases (see instructions above)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
