#!/usr/bin/env python3
"""
Memori HTTP API Server - Powered by GibsonAI Memori
Provides memory storage and retrieval via HTTP REST API using official Memori library.
"""
import os
from typing import Optional

import structlog
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from memori import Memori
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
app = FastAPI(
    title="Memori Memory API",
    version="3.0.0",
    description="AI Memory API powered by GibsonAI Memori Library",
)


# Global state
class AppState:
    memori: Optional[Memori] = None
    namespace: str = os.getenv("MEMORI_NAMESPACE", "soleflip")
    conscious_ingest: bool = os.getenv("MEMORI_CONSCIOUS_INGEST", "true").lower() == "true"
    auto_ingest: bool = os.getenv("MEMORI_AUTO_INGEST", "true").lower() == "true"


state = AppState()


@app.on_event("startup")
async def startup():
    """Initialize Memori library on startup."""
    try:
        # Get database URL from environment (SQLAlchemy format with driver)
        db_url = os.getenv(
            "MEMORI_DATABASE_URL", "postgresql+psycopg2://soleflip:password@postgres:5432/memori"
        )

        # Get OpenAI API key
        openai_api_key = os.getenv("MEMORI_OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("openai_api_key_not_set", embeddings_disabled=True)

        # Initialize official Memori library
        state.memori = Memori(
            database_connect=db_url,  # Changed from connection_string
            openai_api_key=openai_api_key,
            namespace=state.namespace,
            conscious_ingest=state.conscious_ingest,
            auto_ingest=state.auto_ingest,
            verbose=os.getenv("MEMORI_VERBOSE", "false").lower() == "true",
        )
        state.memori.enable()  # Required to activate Memori

        logger.info(
            "memori_http_server_started",
            namespace=state.namespace,
            conscious_ingest=state.conscious_ingest,
            auto_ingest=state.auto_ingest,
            embeddings_enabled=openai_api_key is not None,
        )

    except Exception as e:
        logger.error("startup_failed", error=str(e))
        raise


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    if state.memori:
        state.memori.cleanup()
    logger.info("memori_http_server_stopped")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "namespace": state.namespace,
        "conscious_ingest": state.conscious_ingest,
        "auto_ingest": state.auto_ingest,
        "version": "3.0.0",
        "backend": "GibsonAI Memori",
    }


@app.post("/api/memory/store")
async def store_memory(request: StoreMemoryRequest):
    """Store content in memory using Memori library."""
    try:
        if not state.memori:
            raise HTTPException(status_code=500, detail="Memori not initialized")

        namespace = request.namespace or state.namespace
        metadata = request.metadata or {}

        # Use official Memori.add() - accepts text and optional metadata dict
        state.memori.add(text=request.content, metadata=metadata)

        logger.info(
            "memory_stored",
            namespace=namespace,
            content_length=len(request.content),
            metadata=metadata,
        )

        return {
            "success": True,
            "namespace": namespace,
            "metadata": metadata,
            "message": "Memory stored successfully via GibsonAI Memori",
        }

    except Exception as e:
        logger.error("store_memory_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/search")
async def search_memory(request: SearchMemoryRequest):
    """Search stored memories using Memori library's dual-mode retrieval."""
    try:
        if not state.memori:
            raise HTTPException(status_code=500, detail="Memori not initialized")

        namespace = request.namespace or state.namespace

        # Use official Memori.retrieve_context() with dual-mode retrieval
        context_results = state.memori.retrieve_context(request.query, limit=request.limit)

        # Format results for API response
        formatted_results = [
            {
                "content": result.get("content"),
                "category": result.get("category"),
                "importance_score": result.get("importance_score"),
                "created_at": result.get("created_at"),
            }
            for result in context_results
        ]

        logger.info(
            "search_completed",
            query=request.query,
            namespace=namespace,
            results_count=len(formatted_results),
        )

        return {
            "success": True,
            "query": request.query,
            "search_method": "dual-mode (conscious + auto)",
            "results": formatted_results,
            "count": len(formatted_results),
        }

    except Exception as e:
        logger.error("search_memory_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/list")
async def list_memories(request: ListMemoriesRequest):
    """List recent memories using Memori library."""
    try:
        if not state.memori:
            raise HTTPException(status_code=500, detail="Memori not initialized")

        namespace = request.namespace or state.namespace

        # Use Memori.get_memory_stats() to get overview
        stats = state.memori.get_memory_stats()

        # For actual listing, we'd need direct DB access or use retrieve_context with broad query
        # Return memory statistics instead of full list
        # (Memori SDK is optimized for context retrieval, not full listing)
        return {
            "success": True,
            "namespace": namespace,
            "stats": stats,
            "message": "Use /api/memory/search with broad query to retrieve specific memories",
        }

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
