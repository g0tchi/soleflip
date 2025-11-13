#!/usr/bin/env python3
"""
Memori MCP Server - Simplified Version
Provides basic memory storage and retrieval via MCP Protocol.
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


class SimpleMemoriServer:
    """Simplified MCP Server for memory storage."""

    def __init__(self):
        self.server = Server("memori-mcp-simple")
        self.db_pool: Optional[asyncpg.Pool] = None
        self.namespace = os.getenv("MEMORI_NAMESPACE", "soleflip")
        self._setup_handlers()

    def _setup_handlers(self):
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available memory tools."""
            return [
                Tool(
                    name="store_memory",
                    description="Store information in memory",
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
                    description="Search stored memories",
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
        """Store content in memory."""
        content = args["content"]
        namespace = args.get("namespace", self.namespace)
        metadata = args.get("metadata", {})
        memory_id = str(uuid4())

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO memories (id, namespace, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                memory_id,
                namespace,
                content,
                json.dumps(metadata),
                datetime.utcnow(),
            )

        logger.info(
            "memory_stored",
            memory_id=memory_id,
            namespace=namespace,
            content_length=len(content),
        )

        return {
            "success": True,
            "memory_id": memory_id,
            "namespace": namespace,
            "message": "Memory stored successfully",
        }

    async def _search_memory(self, args: dict[str, Any]) -> dict[str, Any]:
        """Search memories."""
        query = args["query"]
        namespace = args.get("namespace", self.namespace)
        limit = args.get("limit", 5)

        async with self.db_pool.acquire() as conn:
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

        logger.info("memory_search", query=query, namespace=namespace, results_count=len(results))

        return {"success": True, "query": query, "results": results, "count": len(results)}

    async def _list_memories(self, args: dict[str, Any]) -> dict[str, Any]:
        """List recent memories."""
        namespace = args.get("namespace", self.namespace)
        limit = args.get("limit", 10)

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content, metadata, created_at
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

            logger.info("memori_initialized", namespace=self.namespace)

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
