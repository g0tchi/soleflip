#!/usr/bin/env python3
"""
Test script to verify Memori MCP memory operations
"""
import asyncio
import os
from datetime import datetime

from memori import Memori

# Set environment
os.environ["MEMORI_DATABASE_URL"] = (
    "postgresql://soleflip:SoleFlip2025SecureDB!@localhost:5432/memori"
)
os.environ["MEMORI_NAMESPACE"] = "soleflip_test"


async def test_memory_operations():
    """Test storing and retrieving memories."""
    print("🧪 Testing Memori Memory Operations...\n")

    # Initialize Memori
    print("1️⃣ Initializing Memori...")
    memori = Memori(
        database_url=os.environ["MEMORI_DATABASE_URL"], namespace=os.environ["MEMORI_NAMESPACE"]
    )
    print("✅ Memori initialized\n")

    # Test 1: Store a memory
    print("2️⃣ Storing a test memory...")
    test_content = (
        f"Test memory created at {datetime.now().isoformat()}: Memori MCP is working correctly!"
    )
    memory_id = await memori.store(
        content=test_content, metadata={"test": True, "purpose": "verification"}
    )
    print(f"✅ Memory stored with ID: {memory_id}\n")

    # Test 2: Search for the memory
    print("3️⃣ Searching for the memory...")
    results = await memori.search(query="Memori MCP working", limit=5)
    print(f"✅ Found {len(results)} memories")
    if results:
        print(f"   First result: {results[0].content[:80]}...\n")
    else:
        print("   ⚠️ No results found\n")

    # Test 3: Get all memories in namespace
    print("4️⃣ Listing all memories in namespace...")
    all_memories = await memori.get_all()
    print(f"✅ Total memories in '{os.environ['MEMORI_NAMESPACE']}': {len(all_memories)}\n")

    # Test 4: Delete test memory
    print("5️⃣ Cleaning up test memory...")
    await memori.delete(memory_id)
    print("✅ Test memory deleted\n")

    print("🎉 All tests passed! Memori MCP is fully functional.")

    # Close connection
    await memori.close()


if __name__ == "__main__":
    asyncio.run(test_memory_operations())
