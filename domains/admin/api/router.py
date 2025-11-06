"""
Admin API Router
Provides administrative functions like database queries and system management
"""

from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db_session

logger = structlog.get_logger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    results: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float


@router.post(
    "/query",
    summary="Execute Database Query",
    description="Execute a read-only database query for administrative purposes",
)
async def execute_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """Execute a database query"""
    logger.info("Executing admin query", query=request.query[:100])

    try:
        # Security check - only allow SELECT queries
        query_trimmed = request.query.strip().lower()
        if not query_trimmed.startswith("select"):
            raise HTTPException(
                status_code=400, detail="Only SELECT queries are allowed for security reasons"
            )

        # SECURITY: Use predefined queries to prevent SQL injection
        # Map query identifiers to actual SQL queries
        allowed_queries = {
            "count_products": "SELECT COUNT(*) FROM products",
            "count_import_batches": "SELECT COUNT(*) FROM import_batches",
            "import_batch_status": "SELECT status, COUNT(*) FROM import_batches GROUP BY status",
            "count_inventory": "SELECT COUNT(*) FROM inventory_items",
            "recent_logs": "SELECT * FROM system_logs ORDER BY created_at DESC LIMIT 100",
        }

        # Check if query is in allowed list (exact match)
        sql_query = allowed_queries.get(request.query)
        if not sql_query:
            # For backward compatibility, also check if the query itself matches
            if request.query not in allowed_queries.values():
                raise HTTPException(
                    status_code=403,
                    detail=f"Query not allowed. Allowed query IDs: {', '.join(allowed_queries.keys())}",
                )
            sql_query = request.query

        # Execute the whitelisted query
        import time

        start_time = time.time()

        result = await db.execute(text(sql_query))

        # STREAMING OPTIMIZATION: Use fetchmany() for memory-efficient processing
        execution_time = (time.time() - start_time) * 1000

        # Process results in chunks to avoid memory exhaustion
        columns = result.keys() if result.returns_rows else []
        results = []
        chunk_size = 10000  # Process 10k rows at a time

        if result.returns_rows:
            while True:
                chunk = result.fetchmany(chunk_size)
                if not chunk:
                    break

                # Process chunk
                for row in chunk:
                    row_dict = {}
                    for i, column in enumerate(columns):
                        value = row[i]
                        # Convert datetime and other objects to strings for JSON serialization
                        if hasattr(value, "isoformat"):
                            value = value.isoformat()
                        elif value is None:
                            value = None
                        else:
                            value = (
                                str(value) if not isinstance(value, (int, float, bool)) else value
                            )
                        row_dict[column] = value
                results.append(row_dict)
        else:
            results = []

        logger.info(
            "Query executed successfully", row_count=len(results), execution_time_ms=execution_time
        )

        return results

    except Exception as e:
        logger.error("Failed to execute query", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@router.get(
    "/tables", summary="List Database Tables", description="Get list of available database tables"
)
async def list_tables(db: AsyncSession = Depends(get_db_session)) -> List[Dict[str, str]]:
    """Get list of database tables"""
    logger.info("Listing database tables")

    try:
        # Query to get all tables
        query = """
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
        """

        result = await db.execute(text(query))
        rows = result.fetchall()

        tables = []
        for row in rows:
            tables.append({"name": row[0], "type": row[1]})

        logger.info("Tables listed successfully", table_count=len(tables))
        return tables

    except Exception as e:
        logger.error("Failed to list tables", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list tables: {str(e)}")
