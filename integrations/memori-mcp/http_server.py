#!/usr/bin/env python3
"""
Memori HTTP API Server - Simplified Version
Provides memory storage and retrieval via HTTP REST API.
"""
import json
import os
from datetime import datetime
from typing import Optional
from uuid import uuid4

import asyncpg
import structlog
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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


# Pydantic models
class StoreMemoryRequest(BaseModel):
    content: str
    namespace: Optional[str] = None
    metadata: Optional[dict] = None


class SearchMemoryRequest(BaseModel):
    query: str
    namespace: Optional[str] = None
    limit: Optional[int] = 5


class ListMemoriesRequest(BaseModel):
    namespace: Optional[str] = None
    limit: Optional[int] = 10


# FastAPI app
app = FastAPI(title="Memori Memory API", version="1.0.0")


# Global state
class AppState:
    db_pool: Optional[asyncpg.Pool] = None
    namespace: str = os.getenv("MEMORI_NAMESPACE", "soleflip")


state = AppState()


@app.on_event("startup")
async def startup():
    """Initialize database connection on startup."""
    try:
        db_url = os.getenv(
            "MEMORI_DATABASE_URL", "postgresql://soleflip:password@postgres:5432/memori"
        )

        state.db_pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)

        # Create schema
        async with state.db_pool.acquire() as conn:
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

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_namespace ON memories (namespace)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON memories (created_at)")

        logger.info("memori_http_server_started", namespace=state.namespace)

    except Exception as e:
        logger.error("startup_failed", error=str(e))
        raise


@app.on_event("shutdown")
async def shutdown():
    """Close database connection on shutdown."""
    if state.db_pool:
        await state.db_pool.close()
    logger.info("memori_http_server_stopped")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "namespace": state.namespace}


@app.post("/api/memory/store")
async def store_memory(request: StoreMemoryRequest):
    """Store content in memory."""
    try:
        namespace = request.namespace or state.namespace
        metadata = request.metadata or {}
        memory_id = str(uuid4())

        async with state.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO memories (id, namespace, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                memory_id,
                namespace,
                request.content,
                json.dumps(metadata),
                datetime.utcnow(),
            )

        logger.info(
            "memory_stored",
            memory_id=memory_id,
            namespace=namespace,
            content_length=len(request.content),
        )

        return {
            "success": True,
            "memory_id": memory_id,
            "namespace": namespace,
            "message": "Memory stored successfully",
        }

    except Exception as e:
        logger.error("store_memory_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/search")
async def search_memory(request: SearchMemoryRequest):
    """Search stored memories."""
    try:
        namespace = request.namespace or state.namespace

        async with state.db_pool.acquire() as conn:
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
                f"%{request.query}%",
                request.limit,
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

        logger.info(
            "memory_search", query=request.query, namespace=namespace, results_count=len(results)
        )

        return {"success": True, "query": request.query, "results": results, "count": len(results)}

    except Exception as e:
        logger.error("search_memory_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/list")
async def list_memories(request: ListMemoriesRequest):
    """List recent memories."""
    try:
        namespace = request.namespace or state.namespace

        async with state.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content, metadata, created_at
                FROM memories
                WHERE namespace = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                namespace,
                request.limit,
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

    except Exception as e:
        logger.error("list_memories_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "http_server:app",
        host="0.0.0.0",
        port=8080,
        log_level=os.getenv("MEMORI_LOGGING_LEVEL", "info").lower(),
    )
