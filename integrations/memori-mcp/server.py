#!/usr/bin/env python3
"""
Memori MCP Server - Powered by GibsonAI Memori
Provides memory tools for Claude Code via Model Context Protocol.
"""
import os
from typing import Optional

import structlog
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from memori import Memori

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


class MemoriMCPServer:
    """MCP Server for Memori memory operations."""

    def __init__(self):
        self.server = Server("memori-mcp")
        self.memori: Optional[Memori] = None
        # Use user_id instead of deprecated namespace
        self.user_id = os.getenv("MEMORI_USER_ID", os.getenv("MEMORI_NAMESPACE", "soleflip"))
        self.conscious_ingest = os.getenv("MEMORI_CONSCIOUS_INGEST", "true").lower() == "true"
        self.auto_ingest = os.getenv("MEMORI_AUTO_INGEST", "true").lower() == "true"

        # Register MCP tools
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tools."""

        @self.server.list_tools()
        async def list_tools():
            """List available memory tools."""
            return [
                {
                    "name": "store_memory",
                    "description": "Store information in memory with semantic embeddings",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Content to store in memory",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Optional metadata to attach",
                            },
                            "namespace": {
                                "type": "string",
                                "description": f"Optional namespace (default: {self.user_id})",
                            },
                        },
                        "required": ["content"],
                    },
                },
                {
                    "name": "search_memory",
                    "description": "Search stored memories using dual-mode retrieval (conscious + auto)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query",
                            },
                            "limit": {
                                "type": "number",
                                "description": "Maximum number of results (default: 5)",
                            },
                            "namespace": {
                                "type": "string",
                                "description": f"Optional namespace (default: {self.user_id})",
                            },
                        },
                        "required": ["query"],
                    },
                },
                {
                    "name": "list_memories",
                    "description": "List recent memories from a namespace",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "number",
                                "description": "Maximum number of memories to return (default: 10)",
                            },
                            "namespace": {
                                "type": "string",
                                "description": f"Optional namespace (default: {self.user_id})",
                            },
                        },
                    },
                },
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            """Handle tool calls."""
            if not self.memori:
                return [
                    {
                        "type": "text",
                        "text": "Error: Memori not initialized. Please check configuration.",
                    }
                ]

            try:
                if name == "store_memory":
                    return await self._store_memory(arguments)
                elif name == "search_memory":
                    return await self._search_memory(arguments)
                elif name == "list_memories":
                    return await self._list_memories(arguments)
                else:
                    return [{"type": "text", "text": f"Unknown tool: {name}"}]

            except Exception as e:
                logger.error("tool_call_failed", tool=name, error=str(e))
                return [{"type": "text", "text": f"Error: {str(e)}"}]

    async def _store_memory(self, args: dict):
        """Store memory using Memori library."""
        content = args.get("content")
        metadata = args.get("metadata", {})
        namespace = args.get("namespace", self.user_id)

        # Use official Memori.add() - accepts text and optional metadata dict
        self.memori.add(text=content, metadata=metadata)

        logger.info(
            "memory_stored_via_mcp",
            namespace=namespace,
            content_length=len(content),
            metadata=metadata,
        )

        return [
            {
                "type": "text",
                "text": f"✓ Memory stored successfully\n"
                f"Namespace: {namespace}\n"
                f"Metadata: {metadata}\n"
                f"Content length: {len(content)} chars\n"
                f"Mode: conscious_ingest={self.conscious_ingest}, auto_ingest={self.auto_ingest}",
            }
        ]

    async def _search_memory(self, args: dict):
        """Search memories using Memori library's dual-mode retrieval."""
        query = args.get("query")
        limit = args.get("limit", 5)
        namespace = args.get("namespace", self.user_id)

        # Use official Memori.retrieve_context() with dual-mode
        results = self.memori.retrieve_context(query, limit=limit)

        logger.info(
            "memory_search_via_mcp",
            query=query,
            namespace=namespace,
            results_count=len(results),
        )

        if not results:
            return [{"type": "text", "text": f"No memories found for query: '{query}'"}]

        # Format results for Claude Code
        output = [f"Found {len(results)} memories for query: '{query}'\n"]
        output.append("=" * 60 + "\n\n")

        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            category = result.get("category", "")
            importance = result.get("importance_score")
            created_at = result.get("created_at", "")

            output.append(f"**Memory {i}**\n")
            output.append(f"Category: {category}\n")
            if importance:
                output.append(f"Importance: {importance:.2f}\n")
            output.append(f"Created: {created_at}\n")
            output.append(f"\nContent:\n{content}\n")
            output.append("-" * 60 + "\n\n")

        return [{"type": "text", "text": "".join(output)}]

    async def _list_memories(self, args: dict):
        """List memory statistics using Memori library."""
        namespace = args.get("namespace", self.user_id)

        # Use Memori.get_memory_stats()
        stats = self.memori.get_memory_stats()

        logger.info(
            "memory_stats_via_mcp",
            namespace=namespace,
            stats=stats,
        )

        # Format output
        output = [f"Memory Statistics for '{namespace}' namespace:\n"]
        output.append("=" * 60 + "\n\n")

        for key, value in stats.items():
            output.append(f"{key}: {value}\n")

        output.append(
            "\n💡 Tip: Use search_memory with a broad query to retrieve specific memories\n"
        )

        return [{"type": "text", "text": "".join(output)}]

    async def initialize(self):
        """Initialize Memori library."""
        try:
            # Get configuration from environment (SQLAlchemy format with driver)
            db_url = os.getenv(
                "MEMORI_DATABASE_URL",
                "postgresql+psycopg2://soleflip:password@localhost:5432/memori",
            )
            openai_api_key = os.getenv("MEMORI_OPENAI_API_KEY")

            if not openai_api_key:
                logger.warning("openai_api_key_not_set", embeddings_disabled=True)

            # Initialize official Memori library
            self.memori = Memori(
                database_connect=db_url,  # Changed from connection_string
                openai_api_key=openai_api_key,
                user_id=self.user_id,  # Use user_id instead of deprecated namespace
                conscious_ingest=self.conscious_ingest,
                auto_ingest=self.auto_ingest,
                verbose=os.getenv("MEMORI_VERBOSE", "false").lower() == "true",
            )
            self.memori.enable()  # Required to activate Memori

            logger.info(
                "memori_mcp_server_initialized",
                user_id=self.user_id,
                conscious_ingest=self.conscious_ingest,
                auto_ingest=self.auto_ingest,
                embeddings_enabled=openai_api_key is not None,
            )

        except Exception as e:
            logger.error("initialization_failed", error=str(e))
            raise

    async def cleanup(self):
        """Cleanup resources."""
        if self.memori:
            self.memori.cleanup()
        logger.info("memori_mcp_server_stopped")


async def main():
    """Run MCP server."""
    mcp_server = MemoriMCPServer()
    await mcp_server.initialize()

    try:
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.server.run(
                read_stream,
                write_stream,
                mcp_server.server.create_initialization_options(),
            )
    finally:
        await mcp_server.cleanup()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
