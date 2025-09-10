"""
Streaming Response Utilities
High-performance streaming for large datasets and file downloads
"""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional
import structlog
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = structlog.get_logger(__name__)


class JSONStreamingResponse:
    """
    Efficient JSON streaming for large datasets
    - Streams data as JSON lines (JSONL format)
    - Memory efficient for large datasets
    - Supports chunked processing
    """
    
    @staticmethod
    async def stream_query_results(
        db_session: AsyncSession,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        chunk_size: int = 100
    ) -> AsyncGenerator[str, None]:
        """Stream database query results as JSON lines"""
        
        try:
            # Execute query with streaming cursor
            result = await db_session.execute(text(query), params or {})
            
            # Stream results in chunks
            chunk_count = 0
            total_rows = 0
            
            # Yield opening bracket for JSON array
            yield '{"data":['
            first_item = True
            
            while True:
                # Fetch chunk of results
                rows = result.fetchmany(chunk_size)
                if not rows:
                    break
                
                chunk_count += 1
                
                for row in rows:
                    # Convert row to dict
                    row_dict = {
                        column: (
                            str(value) if hasattr(value, '__str__') and 
                            not isinstance(value, (int, float, bool, type(None)))
                            else value
                        )
                        for column, value in row._mapping.items()
                    }
                    
                    # Add comma separator except for first item
                    if not first_item:
                        yield ","
                    first_item = False
                    
                    # Yield JSON-encoded row
                    yield json.dumps(row_dict, default=str, separators=(',', ':'))
                    total_rows += 1
                
                # Log progress for large datasets
                if chunk_count % 10 == 0:
                    logger.info(
                        "Streaming progress",
                        chunks_processed=chunk_count,
                        rows_streamed=total_rows
                    )
            
            # Yield closing bracket and metadata
            yield f'],"metadata":{{"total_rows":{total_rows},"chunks_processed":{chunk_count}}}}}'
            
            logger.info(
                "Streaming completed",
                total_rows=total_rows,
                chunks_processed=chunk_count
            )
            
        except Exception as e:
            logger.error("Streaming failed", error=str(e))
            yield f'{{"error":"Streaming failed: {str(e)}"}}'
        
        finally:
            await db_session.close()


class FileStreamingResponse:
    """
    Efficient file streaming for large file downloads
    - Supports resume/range requests
    - Memory efficient chunked reading
    - Progress tracking
    """
    
    @staticmethod
    async def stream_file(
        file_path: str,
        chunk_size: int = 8192,
        start_byte: int = 0,
        end_byte: Optional[int] = None
    ) -> AsyncGenerator[bytes, None]:
        """Stream file content in chunks"""
        
        import os
        import aiofiles
        
        try:
            file_size = os.path.getsize(file_path)
            end_byte = end_byte or file_size - 1
            
            logger.info(
                "Starting file stream",
                file_path=file_path,
                file_size=file_size,
                start_byte=start_byte,
                end_byte=end_byte
            )
            
            async with aiofiles.open(file_path, 'rb') as file:
                await file.seek(start_byte)
                bytes_read = start_byte
                
                while bytes_read <= end_byte:
                    # Calculate chunk size for this iteration
                    remaining = min(chunk_size, end_byte - bytes_read + 1)
                    
                    chunk = await file.read(remaining)
                    if not chunk:
                        break
                    
                    bytes_read += len(chunk)
                    yield chunk
                    
                    # Log progress for large files
                    if bytes_read % (1024 * 1024) == 0:  # Every 1MB
                        progress = (bytes_read / file_size) * 100
                        logger.debug(
                            "File streaming progress",
                            bytes_read=bytes_read,
                            progress_percent=f"{progress:.1f}%"
                        )
            
            logger.info("File streaming completed", bytes_streamed=bytes_read)
            
        except Exception as e:
            logger.error("File streaming failed", error=str(e), file_path=file_path)
            raise


class CSVStreamingResponse:
    """
    Efficient CSV streaming for data exports
    - Streams CSV data with headers
    - Memory efficient for large datasets
    - Supports custom formatting
    """
    
    @staticmethod
    async def stream_csv_data(
        data: List[Dict[str, Any]],
        headers: Optional[List[str]] = None,
        chunk_size: int = 50
    ) -> AsyncGenerator[str, None]:
        """Stream data as CSV format"""
        
        import csv
        import io
        
        try:
            if not data:
                yield ""
                return
            
            # Determine headers from first row if not provided
            headers = headers or list(data[0].keys())
            
            # Yield CSV headers
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            yield output.getvalue()
            
            # Stream data in chunks
            total_rows = 0
            
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                
                # Create CSV content for this chunk
                output = io.StringIO()
                writer = csv.writer(output)
                
                for row in chunk:
                    # Extract values in header order
                    values = [
                        str(row.get(header, "")) if row.get(header) is not None else ""
                        for header in headers
                    ]
                    writer.writerow(values)
                    total_rows += 1
                
                yield output.getvalue()
                
                # Log progress
                if total_rows % 1000 == 0:
                    logger.info("CSV streaming progress", rows_streamed=total_rows)
            
            logger.info("CSV streaming completed", total_rows=total_rows)
            
        except Exception as e:
            logger.error("CSV streaming failed", error=str(e))
            raise


def create_streaming_response(
    generator: AsyncGenerator,
    media_type: str = "application/json",
    filename: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None
) -> StreamingResponse:
    """Create a FastAPI StreamingResponse with appropriate headers"""
    
    response_headers = headers or {}
    
    # Add content disposition for file downloads
    if filename:
        response_headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    
    # Add cache control for streaming responses
    response_headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response_headers["Pragma"] = "no-cache"
    response_headers["Expires"] = "0"
    
    # Add streaming-specific headers
    response_headers["X-Content-Type-Options"] = "nosniff"
    response_headers["Transfer-Encoding"] = "chunked"
    
    return StreamingResponse(
        generator,
        media_type=media_type,
        headers=response_headers
    )


# Convenience functions for common use cases
async def stream_inventory_export(
    db_session: AsyncSession,
    export_format: str = "json",
    chunk_size: int = 100
) -> StreamingResponse:
    """Stream inventory data export"""
    
    query = """
        SELECT 
            i.id,
            i.product_id,
            p.name as product_name,
            b.name as brand_name,
            c.name as category_name,
            i.size,
            i.quantity,
            i.purchase_price,
            i.purchase_date,
            i.supplier,
            i.status,
            i.notes,
            i.created_at,
            i.updated_at
        FROM products.inventory i
        LEFT JOIN products.products p ON i.product_id = p.id
        LEFT JOIN core.brands b ON p.brand_id = b.id
        LEFT JOIN core.categories c ON p.category_id = c.id
        ORDER BY i.created_at DESC
    """
    
    if export_format.lower() == "csv":
        # For CSV, we need to fetch all data first
        result = await db_session.execute(text(query))
        rows = result.fetchall()
        data = [dict(row._mapping) for row in rows]
        
        generator = CSVStreamingResponse.stream_csv_data(data, chunk_size=chunk_size)
        return create_streaming_response(
            generator,
            media_type="text/csv",
            filename="inventory_export.csv"
        )
    
    else:  # JSON format
        generator = JSONStreamingResponse.stream_query_results(
            db_session, query, chunk_size=chunk_size
        )
        return create_streaming_response(
            generator,
            media_type="application/json",
            filename="inventory_export.json"
        )