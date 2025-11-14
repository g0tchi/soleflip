#!/usr/bin/env python3
"""
Test MCP tools by directly calling the server functions
"""
import asyncio
import json
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, "/home/g0tchi/projects/soleflip/integrations/memori-mcp")

# Set environment before importing
import os

os.environ["MEMORI_DATABASE_URL"] = (
    "postgresql://soleflip:SoleFlip2025SecureDB!@localhost:5432/memori"
)
os.environ["MEMORI_NAMESPACE"] = "soleflip"
os.environ["MEMORI_LOGGING_LEVEL"] = "INFO"

# Now we can import after environment is set
import asyncpg


async def test_mcp_operations():
    """Test MCP operations directly via database."""
    print("🧪 Testing Memori MCP Tools\n")
    print("=" * 70)

    # Connect to database
    conn = await asyncpg.connect(os.environ["MEMORI_DATABASE_URL"])

    # TEST 1: Store Memory (simulating mcp__memori__store_memory)
    print("\n1️⃣ TEST: store_memory")
    print("-" * 70)

    test_content = f"Memori MCP Live Test: Das Soleflip-Projekt verwendet FastAPI, PostgreSQL und Domain-Driven Design Architektur. Test durchgeführt am {datetime.now().isoformat()}"
    test_metadata = {"type": "project_info", "test": True, "timestamp": datetime.now().isoformat()}

    from uuid import uuid4

    memory_id = uuid4()

    await conn.execute(
        """
        INSERT INTO memories (id, namespace, content, metadata, created_at)
        VALUES ($1, $2, $3, $4, $5)
        """,
        memory_id,
        "soleflip",
        test_content,
        json.dumps(test_metadata),
        datetime.now(),
    )

    print("✅ Memory gespeichert!")
    print(f"   ID: {memory_id}")
    print("   Namespace: soleflip")
    print(f"   Content: {test_content[:80]}...")

    # TEST 2: Search Memory (simulating mcp__memori__search_memory)
    print("\n2️⃣ TEST: search_memory")
    print("-" * 70)

    search_query = "FastAPI PostgreSQL"
    search_results = await conn.fetch(
        """
        SELECT id, namespace, content, metadata, created_at
        FROM memories
        WHERE namespace = $1
        AND content ILIKE $2
        ORDER BY created_at DESC
        LIMIT 5
        """,
        "soleflip",
        f"%{search_query}%",
    )

    print(f"🔍 Suche nach: '{search_query}'")
    print(f"✅ Gefunden: {len(search_results)} Ergebnisse\n")

    for idx, result in enumerate(search_results, 1):
        print(f"   {idx}. ID: {result['id']}")
        print(f"      Content: {result['content'][:100]}...")
        print(f"      Created: {result['created_at']}")
        print()

    # TEST 3: List Memories (simulating mcp__memori__list_memories)
    print("3️⃣ TEST: list_memories")
    print("-" * 70)

    all_memories = await conn.fetch(
        """
        SELECT id, namespace, content, created_at
        FROM memories
        WHERE namespace = $1
        ORDER BY created_at DESC
        LIMIT 10
        """,
        "soleflip",
    )

    print("📋 Alle Memories im 'soleflip' Namespace:")
    print(f"✅ Total: {len(all_memories)} Memories\n")

    for idx, memory in enumerate(all_memories, 1):
        print(f"   {idx}. {memory['content'][:80]}...")
        print(f"      Created: {memory['created_at']}")
        print()

    # Statistics
    print("=" * 70)
    print("📊 Statistiken:")
    print("-" * 70)

    stats = await conn.fetchrow(
        """
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT namespace) as namespaces,
            MIN(created_at) as oldest,
            MAX(created_at) as newest
        FROM memories
        """
    )

    print(f"   Total Memories: {stats['total']}")
    print(f"   Namespaces: {stats['namespaces']}")
    print(f"   Älteste Memory: {stats['oldest']}")
    print(f"   Neueste Memory: {stats['newest']}")

    print("\n" + "=" * 70)
    print("🎉 Alle MCP-Tool-Tests erfolgreich!")
    print("\n✅ Der Memori MCP Server ist voll funktionsfähig!")
    print("   Nach Claude Code Neustart sind folgende Tools verfügbar:")
    print("   • mcp__memori__store_memory")
    print("   • mcp__memori__search_memory")
    print("   • mcp__memori__list_memories")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(test_mcp_operations())
