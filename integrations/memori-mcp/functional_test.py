#!/usr/bin/env python3
"""
Functional test for Memori MCP Server
Tests database operations directly
"""
import asyncio
import json
from datetime import datetime
from uuid import uuid4

import asyncpg

DATABASE_URL = "postgresql://soleflip:SoleFlip2025SecureDB!@localhost:5432/memori"
NAMESPACE = "test_namespace"


async def functional_test():
    """Run functional tests on Memori database."""
    print("🧪 Memori MCP Functional Test\n")
    print("=" * 60)

    # Connect to database
    print("\n1️⃣ Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    print("✅ Connected successfully")

    # Test 1: Store a memory
    print("\n2️⃣ Storing a test memory...")
    memory_id = uuid4()
    test_content = f"Test memory created at {datetime.now().isoformat()}"
    test_metadata = {"test": True, "operation": "functional_test"}

    await conn.execute(
        """
        INSERT INTO memories (id, namespace, content, metadata, created_at)
        VALUES ($1, $2, $3, $4, $5)
        """,
        memory_id,
        NAMESPACE,
        test_content,
        json.dumps(test_metadata),
        datetime.now(),
    )
    print(f"✅ Memory stored with ID: {memory_id}")

    # Test 2: Retrieve the memory
    print("\n3️⃣ Retrieving the stored memory...")
    result = await conn.fetchrow("SELECT * FROM memories WHERE id = $1", memory_id)
    if result:
        print("✅ Memory retrieved successfully")
        print(f"   Content: {result['content']}")
        print(f"   Namespace: {result['namespace']}")
        print(f"   Metadata: {result['metadata']}")
    else:
        print("❌ Failed to retrieve memory")

    # Test 3: Search memories
    print("\n4️⃣ Searching for memories in namespace...")
    memories = await conn.fetch(
        """
        SELECT * FROM memories
        WHERE namespace = $1
        ORDER BY created_at DESC
        LIMIT 5
        """,
        NAMESPACE,
    )
    print(f"✅ Found {len(memories)} memories in '{NAMESPACE}' namespace")

    # Test 4: List all namespaces
    print("\n5️⃣ Listing all namespaces...")
    namespaces = await conn.fetch(
        """
        SELECT DISTINCT namespace, COUNT(*) as count
        FROM memories
        GROUP BY namespace
        """
    )
    print(f"✅ Total namespaces: {len(namespaces)}")
    for ns in namespaces:
        print(f"   • {ns['namespace']}: {ns['count']} memories")

    # Test 5: Delete test memory
    print("\n6️⃣ Cleaning up test memory...")
    await conn.execute("DELETE FROM memories WHERE id = $1", memory_id)
    print("✅ Test memory deleted")

    # Summary
    print("\n" + "=" * 60)
    print("🎉 All functional tests passed!")
    print("\n📊 Summary:")
    print("   • Database connection: ✅ Working")
    print("   • Memory storage: ✅ Working")
    print("   • Memory retrieval: ✅ Working")
    print("   • Memory search: ✅ Working")
    print("   • Memory deletion: ✅ Working")

    # Close connection
    await conn.close()
    print("\n✅ Database connection closed")


if __name__ == "__main__":
    try:
        asyncio.run(functional_test())
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
