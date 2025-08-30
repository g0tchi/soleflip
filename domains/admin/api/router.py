"""
Admin API Router
Provides administrative functions like database queries and system management
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

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
    request: QueryRequest, db: AsyncSession = Depends(get_db_session)
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

        # Execute the query
        import time

        start_time = time.time()

        result = await db.execute(text(request.query))
        rows = result.fetchall()

        execution_time = (time.time() - start_time) * 1000

        # Convert rows to list of dictionaries
        if rows:
            columns = result.keys()
            results = []
            for row in rows:
                row_dict = {}
                for i, column in enumerate(columns):
                    value = row[i]
                    # Convert datetime and other objects to strings for JSON serialization
                    if hasattr(value, "isoformat"):
                        value = value.isoformat()
                    elif value is None:
                        value = None
                    else:
                        value = str(value) if not isinstance(value, (int, float, bool)) else value
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
