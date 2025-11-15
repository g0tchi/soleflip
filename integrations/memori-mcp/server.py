#!/usr/bin/env python3
"""
Memori MCP Server - Full Version with Semantic Search
Provides memory storage and retrieval with OpenAI embeddings via MCP Protocol.
"""
import asyncio
import json
import os
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

import asyncpg
import structlog
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger(__name__)


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    import math

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


class SimpleMemoriServer:
    """MCP Server for memory storage with semantic search."""

    def __init__(self):
        self.server = Server("memori-mcp-simple")
        self.db_pool: Optional[asyncpg.Pool] = None
        self.namespace = os.getenv("MEMORI_NAMESPACE", "soleflip")
        self.openai_api_key = os.getenv("MEMORI_OPENAI_API_KEY")
        self.openai_client = None

        # Initialize OpenAI client if API key is available
        if self.openai_api_key:
            try:
                from openai import AsyncOpenAI

                self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
                logger.info("openai_client_initialized", embeddings_enabled=True)
            except ImportError:
                logger.warning("openai_not_installed", embeddings_enabled=False)
        else:
            logger.info("openai_api_key_not_set", embeddings_enabled=False)

        self._setup_handlers()

    async def _generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate OpenAI embedding for text."""
        if not self.openai_client:
            return None

        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small", input=text
            )
            embedding = response.data[0].embedding
            logger.info(
                "embedding_generated", text_length=len(text), vector_dimension=len(embedding)
            )
            return embedding
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            return None

    def _setup_handlers(self):
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available memory tools."""
            return [
                Tool(
                    name="store_memory",
                    description="Store information in memory with semantic embeddings",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "Content to store"},
                            "namespace": {"type": "string", "description": "Optional namespace"},
                            "metadata": {"type": "object", "description": "Optional metadata"},
                        },
                        "required": ["content"],
                    },
                ),
                Tool(
                    name="search_memory",
                    description="Search stored memories using semantic similarity",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "namespace": {"type": "string", "description": "Optional namespace"},
                            "limit": {"type": "number", "description": "Max results", "default": 5},
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="list_memories",
                    description="List recent memories",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "namespace": {"type": "string", "description": "Optional namespace"},
                            "limit": {
                                "type": "number",
                                "description": "Max results",
                                "default": 10,
                            },
                        },
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "store_memory":
                    result = await self._store_memory(arguments)
                elif name == "search_memory":
                    result = await self._search_memory(arguments)
                elif name == "list_memories":
                    result = await self._list_memories(arguments)
                else:
                    result = {"error": f"Unknown tool: {name}"}

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except Exception as e:
                logger.error("tool_call_failed", tool=name, error=str(e))
                return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]

    async def _store_memory(self, args: dict[str, Any]) -> dict[str, Any]:
        """Store content in memory with embedding."""
        content = args["content"]
        namespace = args.get("namespace", self.namespace)
        metadata = args.get("metadata", {})
        memory_id = str(uuid4())

        # Generate embedding
        embedding = await self._generate_embedding(content)

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO memories (id, namespace, content, metadata, embedding, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                memory_id,
                namespace,
                content,
                json.dumps(metadata),
                json.dumps(embedding) if embedding else None,
                datetime.utcnow(),
            )

        logger.info(
            "memory_stored",
            memory_id=memory_id,
            namespace=namespace,
            content_length=len(content),
            has_embedding=embedding is not None,
        )

        return {
            "success": True,
            "memory_id": memory_id,
            "namespace": namespace,
            "has_embedding": embedding is not None,
            "message": "Memory stored successfully",
        }

    async def _search_memory(self, args: dict[str, Any]) -> dict[str, Any]:
        """Search memories using semantic similarity or fallback to text search."""
        query = args["query"]
        namespace = args.get("namespace", self.namespace)
        limit = args.get("limit", 5)

        # Generate embedding for query
        query_embedding = await self._generate_embedding(query)

        async with self.db_pool.acquire() as conn:
            if query_embedding:
                # Semantic search: fetch all memories with embeddings and rank by similarity
                rows = await conn.fetch(
                    """
                    SELECT id, content, metadata, embedding, created_at
                    FROM memories
                    WHERE namespace = $1
                    AND embedding IS NOT NULL
                    """,
                    namespace,
                )

                # Calculate similarity scores
                results_with_scores = []
                for row in rows:
                    if row["embedding"]:
                        stored_embedding = json.loads(row["embedding"])
                        similarity = cosine_similarity(query_embedding, stored_embedding)
                        results_with_scores.append((row, similarity))

                # Sort by similarity (highest first) and limit
                results_with_scores.sort(key=lambda x: x[1], reverse=True)
                top_results = results_with_scores[:limit]

                results = [
                    {
                        "id": str(row["id"]),
                        "content": row["content"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "created_at": row["created_at"].isoformat(),
                        "similarity_score": round(score, 4),
                    }
                    for row, score in top_results
                ]

                search_method = "semantic"
                logger.info(
                    "semantic_search",
                    query=query,
                    namespace=namespace,
                    results_count=len(results),
                    total_checked=len(rows),
                )
            else:
                # Fallback to text search
                rows = await conn.fetch(
                    """
                    SELECT id, content, metadata, created_at
                    FROM memories
                    WHERE namespace = $1
                    AND content ILIKE $2
                    ORDER BY created_at DESC
                    LIMIT $3
                    """,
                    namespace,
                    f"%{query}%",
                    limit,
                )

                results = [
                    {
                        "id": str(row["id"]),
                        "content": row["content"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "created_at": row["created_at"].isoformat(),
                    }
                    for row in rows
                ]

                search_method = "text"
                logger.info(
                    "text_search_fallback",
                    query=query,
                    namespace=namespace,
                    results_count=len(results),
                )

        return {
            "success": True,
            "query": query,
            "search_method": search_method,
            "results": results,
            "count": len(results),
        }

    async def _list_memories(self, args: dict[str, Any]) -> dict[str, Any]:
        """List recent memories."""
        namespace = args.get("namespace", self.namespace)
        limit = args.get("limit", 10)

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content, metadata, embedding, created_at
                FROM memories
                WHERE namespace = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                namespace,
                limit,
            )

        results = [
            {
                "id": str(row["id"]),
                "content": (
                    row["content"][:100] + "..." if len(row["content"]) > 100 else row["content"]
                ),
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "has_embedding": row["embedding"] is not None,
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]

        return {"success": True, "namespace": namespace, "memories": results, "count": len(results)}

    async def initialize(self):
        """Initialize database connection and create schema."""
        try:
            # Parse DATABASE_URL
            db_url = os.getenv(
                "MEMORI_DATABASE_URL", "postgresql://soleflip:password@postgres:5432/memori"
            )

            # Create connection pool
            self.db_pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)

            # Create schema if not exists
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memories (
                        id UUID PRIMARY KEY,
                        namespace VARCHAR(255) NOT NULL,
                        content TEXT NOT NULL,
                        metadata JSONB,
                        embedding JSONB,
                        created_at TIMESTAMP NOT NULL
                    )
                    """
                )

                # Create indexes
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_namespace ON memories (namespace)"
                )
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_created_at ON memories (created_at)"
                )
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_embedding ON memories ((embedding IS NOT NULL))"
                )

            logger.info(
                "memori_initialized",
                namespace=self.namespace,
                embeddings_enabled=self.openai_client is not None,
            )

        except Exception as e:
            logger.error("memori_initialization_failed", error=str(e))
            raise

    async def run(self):
        """Run the MCP server."""
        await self.initialize()

        async with stdio_server() as (read_stream, write_stream):
            logger.info("memori_mcp_server_started")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


async def main():
    """Entry point."""
    server = SimpleMemoriServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
