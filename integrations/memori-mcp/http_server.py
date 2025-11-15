#!/usr/bin/env python3
"""
Memori HTTP API Server - Full Version with Semantic Search
Provides memory storage and retrieval via HTTP REST API with OpenAI embeddings.
"""
import json
import math
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


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


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
app = FastAPI(
    title="Memori Memory API", version="2.0.0", description="AI Memory API with Semantic Search"
)


# Global state
class AppState:
    db_pool: Optional[asyncpg.Pool] = None
    namespace: str = os.getenv("MEMORI_NAMESPACE", "soleflip")
    openai_client = None
    embeddings_enabled: bool = False


state = AppState()


async def generate_embedding(text: str) -> Optional[list[float]]:
    """Generate OpenAI embedding for text."""
    if not state.openai_client:
        return None

    try:
        response = await state.openai_client.embeddings.create(
            model="text-embedding-3-small", input=text
        )
        embedding = response.data[0].embedding
        logger.info("embedding_generated", text_length=len(text), vector_dimension=len(embedding))
        return embedding
    except Exception as e:
        logger.error("embedding_generation_failed", error=str(e))
        return None


@app.on_event("startup")
async def startup():
    """Initialize database connection and OpenAI client on startup."""
    try:
        # Initialize OpenAI client if API key is available
        openai_api_key = os.getenv("MEMORI_OPENAI_API_KEY")
        if openai_api_key:
            try:
                from openai import AsyncOpenAI

                state.openai_client = AsyncOpenAI(api_key=openai_api_key)
                state.embeddings_enabled = True
                logger.info("openai_client_initialized", embeddings_enabled=True)
            except ImportError:
                logger.warning("openai_not_installed", embeddings_enabled=False)
        else:
            logger.info("openai_api_key_not_set", embeddings_enabled=False)

        # Initialize database
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
                    embedding JSONB,
                    created_at TIMESTAMP NOT NULL
                )
                """
            )

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_namespace ON memories (namespace)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON memories (created_at)")
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_embedding ON memories ((embedding IS NOT NULL))"
            )

        logger.info(
            "memori_http_server_started",
            namespace=state.namespace,
            embeddings_enabled=state.embeddings_enabled,
        )

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
    return {
        "status": "healthy",
        "namespace": state.namespace,
        "embeddings_enabled": state.embeddings_enabled,
    }


@app.post("/api/memory/store")
async def store_memory(request: StoreMemoryRequest):
    """Store content in memory with optional embedding."""
    try:
        namespace = request.namespace or state.namespace
        metadata = request.metadata or {}
        memory_id = str(uuid4())

        # Generate embedding
        embedding = await generate_embedding(request.content)

        async with state.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO memories (id, namespace, content, metadata, embedding, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                memory_id,
                namespace,
                request.content,
                json.dumps(metadata),
                json.dumps(embedding) if embedding else None,
                datetime.utcnow(),
            )

        logger.info(
            "memory_stored",
            memory_id=memory_id,
            namespace=namespace,
            content_length=len(request.content),
            has_embedding=embedding is not None,
        )

        return {
            "success": True,
            "memory_id": memory_id,
            "namespace": namespace,
            "has_embedding": embedding is not None,
            "message": "Memory stored successfully",
        }

    except Exception as e:
        logger.error("store_memory_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/search")
async def search_memory(request: SearchMemoryRequest):
    """Search stored memories using semantic similarity or text fallback."""
    try:
        namespace = request.namespace or state.namespace

        # Generate embedding for query
        query_embedding = await generate_embedding(request.query)

        async with state.db_pool.acquire() as conn:
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
                top_results = results_with_scores[: request.limit]

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
                    query=request.query,
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

                search_method = "text"
                logger.info(
                    "text_search_fallback",
                    query=request.query,
                    namespace=namespace,
                    results_count=len(results),
                )

        return {
            "success": True,
            "query": request.query,
            "search_method": search_method,
            "results": results,
            "count": len(results),
        }

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
                SELECT id, content, metadata, embedding, created_at
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
                "has_embedding": row["embedding"] is not None,
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
