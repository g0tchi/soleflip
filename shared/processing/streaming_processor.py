"""
Streaming Data Processor for Large-Scale Retailer Imports
Handles streaming data processing with memory-efficient chunking,
backpressure control, and parallel processing.
"""

import asyncio
import csv
import io
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID

import aiofiles
import structlog

from shared.processing.async_pipeline import ProcessingContext, get_async_pipeline

logger = structlog.get_logger(__name__)


@dataclass
class StreamingConfig:
    """Configuration for streaming processor"""
    chunk_size: int = 10000  # Records per chunk for large imports
    max_memory_mb: int = 500  # Maximum memory usage in MB
    max_concurrent_chunks: int = 3  # Reduced for large imports
    buffer_size: int = 8192  # Buffer size for file reading
    enable_backpressure: bool = True
    progress_interval: int = 1000  # Report progress every N records


class DataStreamProcessor:
    """
    High-performance streaming processor for large retailer imports.
    Designed to handle millions of products efficiently.
    """
    
    def __init__(self, config: Optional[StreamingConfig] = None):
        self.config = config or StreamingConfig()
        self.pipeline = get_async_pipeline()
        
        # Configure pipeline for large imports
        self.pipeline.max_concurrent_chunks = self.config.max_concurrent_chunks
        self.pipeline.chunk_size = self.config.chunk_size
        
        # Memory monitoring
        self._current_memory_mb = 0
        self._processed_records = 0
        
        # Backpressure control
        self._processing_semaphore = asyncio.Semaphore(self.config.max_concurrent_chunks)
        self._backpressure_active = False
    
    async def process_csv_stream(
        self,
        file_path: str,
        batch_id: UUID,
        source_type: str,
        encoding: str = 'utf-8-sig'
    ) -> ProcessingContext:
        """
        Process a large CSV file using streaming approach.
        Memory-efficient for files of any size.
        """
        logger.info(
            "Starting streaming CSV processing",
            file_path=file_path,
            batch_id=str(batch_id),
            source_type=source_type,
            chunk_size=self.config.chunk_size
        )
        
        try:
            # Estimate total records for progress tracking
            total_records = await self._estimate_csv_records(file_path)
            
            # Create async generator for CSV data
            data_stream = self._create_csv_stream(file_path, encoding)
            
            # Process using the async pipeline
            context = await self.pipeline.process_large_dataset(
                batch_id=batch_id,
                data_stream=data_stream,
                source_type=source_type,
                total_records=total_records
            )
            
            return context
            
        except Exception as e:
            logger.error(
                "Streaming CSV processing failed",
                file_path=file_path,
                batch_id=str(batch_id),
                error=str(e),
                exc_info=True
            )
            raise
    
    async def process_json_stream(
        self,
        file_path: str,
        batch_id: UUID,
        source_type: str
    ) -> ProcessingContext:
        """
        Process a large JSON file using streaming approach.
        Handles JSON arrays and newline-delimited JSON.
        """
        logger.info(
            "Starting streaming JSON processing",
            file_path=file_path,
            batch_id=str(batch_id),
            source_type=source_type
        )
        
        try:
            # Detect JSON format
            is_jsonl = await self._is_jsonlines_format(file_path)
            
            if is_jsonl:
                data_stream = self._create_jsonl_stream(file_path)
                total_records = await self._estimate_jsonl_records(file_path)
            else:
                data_stream = self._create_json_array_stream(file_path)
                total_records = None  # Harder to estimate for JSON arrays
            
            context = await self.pipeline.process_large_dataset(
                batch_id=batch_id,
                data_stream=data_stream,
                source_type=source_type,
                total_records=total_records
            )
            
            return context
            
        except Exception as e:
            logger.error(
                "Streaming JSON processing failed",
                file_path=file_path,
                batch_id=str(batch_id),
                error=str(e),
                exc_info=True
            )
            raise
    
    async def process_api_stream(
        self,
        api_generator: AsyncGenerator[Dict[str, Any], None],
        batch_id: UUID,
        source_type: str,
        estimated_records: Optional[int] = None
    ) -> ProcessingContext:
        """
        Process data from an API using streaming approach.
        Handles paginated API responses efficiently.
        """
        logger.info(
            "Starting streaming API processing",
            batch_id=str(batch_id),
            source_type=source_type,
            estimated_records=estimated_records
        )
        
        try:
            # Chunk the API data
            data_stream = self._chunk_api_stream(api_generator)
            
            context = await self.pipeline.process_large_dataset(
                batch_id=batch_id,
                data_stream=data_stream,
                source_type=source_type,
                total_records=estimated_records
            )
            
            return context
            
        except Exception as e:
            logger.error(
                "Streaming API processing failed",
                batch_id=str(batch_id),
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _create_csv_stream(self, file_path: str, encoding: str) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Create async generator for CSV data"""
        current_chunk = []
        record_count = 0
        
        async with aiofiles.open(file_path, mode='r', encoding=encoding, buffering=self.config.buffer_size) as file:
            # Read header
            header_line = await file.readline()
            if not header_line:
                return
                
            # Parse header
            reader = csv.DictReader(io.StringIO(header_line))
            fieldnames = reader.fieldnames
            
            async for line in file:
                if not line.strip():
                    continue
                
                try:
                    # Parse CSV row
                    row_reader = csv.DictReader(io.StringIO(line), fieldnames=fieldnames)
                    row_data = next(row_reader)
                    
                    # Clean the data
                    clean_data = {k: (v.strip() if v else None) for k, v in row_data.items()}
                    current_chunk.append(clean_data)
                    record_count += 1
                    
                    # Check if chunk is full
                    if len(current_chunk) >= self.config.chunk_size:
                        # Apply backpressure if needed
                        if self.config.enable_backpressure:
                            await self._apply_backpressure()
                        
                        yield current_chunk.copy()
                        current_chunk.clear()
                        
                        # Report progress
                        if record_count % self.config.progress_interval == 0:
                            logger.debug(
                                "CSV streaming progress",
                                records_processed=record_count,
                                memory_mb=self._current_memory_mb
                            )
                
                except Exception as e:
                    logger.warning(
                        "Failed to parse CSV row",
                        line_number=record_count + 1,
                        error=str(e)
                    )
                    continue
            
            # Yield remaining records
            if current_chunk:
                yield current_chunk
    
    async def _create_jsonl_stream(self, file_path: str) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Create async generator for JSON Lines data"""
        import json
        
        current_chunk = []
        record_count = 0
        
        async with aiofiles.open(file_path, mode='r', encoding='utf-8', buffering=self.config.buffer_size) as file:
            async for line in file:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    record = json.loads(line)
                    current_chunk.append(record)
                    record_count += 1
                    
                    if len(current_chunk) >= self.config.chunk_size:
                        if self.config.enable_backpressure:
                            await self._apply_backpressure()
                        
                        yield current_chunk.copy()
                        current_chunk.clear()
                        
                        if record_count % self.config.progress_interval == 0:
                            logger.debug(
                                "JSONL streaming progress",
                                records_processed=record_count
                            )
                
                except json.JSONDecodeError as e:
                    logger.warning(
                        "Failed to parse JSON line",
                        line_number=record_count + 1,
                        error=str(e)
                    )
                    continue
            
            if current_chunk:
                yield current_chunk
    
    async def _create_json_array_stream(self, file_path: str) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Create async generator for JSON array data (more complex)"""
        import json
        
        # For very large JSON arrays, we'd need a streaming JSON parser
        # For now, load in chunks if possible
        logger.warning(
            "JSON array streaming not fully implemented - consider using JSONL format for large files",
            file_path=file_path
        )
        
        # Simple implementation for smaller arrays
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as file:
            content = await file.read()
            data = json.loads(content)
            
            if isinstance(data, list):
                current_chunk = []
                for record in data:
                    current_chunk.append(record)
                    
                    if len(current_chunk) >= self.config.chunk_size:
                        yield current_chunk.copy()
                        current_chunk.clear()
                
                if current_chunk:
                    yield current_chunk
    
    async def _chunk_api_stream(
        self, 
        api_generator: AsyncGenerator[Dict[str, Any], None]
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Chunk API data stream"""
        current_chunk = []
        record_count = 0
        
        async for record in api_generator:
            current_chunk.append(record)
            record_count += 1
            
            if len(current_chunk) >= self.config.chunk_size:
                if self.config.enable_backpressure:
                    await self._apply_backpressure()
                
                yield current_chunk.copy()
                current_chunk.clear()
                
                if record_count % self.config.progress_interval == 0:
                    logger.debug(
                        "API streaming progress",
                        records_processed=record_count
                    )
        
        if current_chunk:
            yield current_chunk
    
    async def _apply_backpressure(self):
        """Apply backpressure control to manage memory usage"""
        async with self._processing_semaphore:
            # Monitor memory usage
            await self._check_memory_usage()
            
            # Small delay to allow processing to catch up
            if self._backpressure_active:
                await asyncio.sleep(0.1)
    
    async def _check_memory_usage(self):
        """Monitor and control memory usage"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self._current_memory_mb = memory_mb
            
            if memory_mb > self.config.max_memory_mb:
                if not self._backpressure_active:
                    logger.warning(
                        "Memory threshold exceeded, activating backpressure",
                        current_memory_mb=memory_mb,
                        threshold_mb=self.config.max_memory_mb
                    )
                    self._backpressure_active = True
                
                # Force garbage collection
                import gc
                gc.collect()
                
                # Wait for memory to reduce
                await asyncio.sleep(0.5)
            else:
                if self._backpressure_active:
                    logger.info(
                        "Memory usage normalized, deactivating backpressure",
                        current_memory_mb=memory_mb
                    )
                    self._backpressure_active = False
                    
        except ImportError:
            # psutil not available, skip memory monitoring
            pass
    
    async def _estimate_csv_records(self, file_path: str) -> Optional[int]:
        """Estimate number of records in CSV file"""
        try:
            async with aiofiles.open(file_path, mode='r', encoding='utf-8-sig') as file:
                line_count = 0
                async for line in file:
                    line_count += 1
                    if line_count > 100000:  # Don't count too long for very large files
                        break
                
                if line_count <= 100000:
                    return max(0, line_count - 1)  # Subtract header
                else:
                    # Estimate based on file size
                    import os
                    file_size = os.path.getsize(file_path)
                    avg_line_size = file_size / line_count
                    estimated_lines = int(file_size / avg_line_size)
                    return max(0, estimated_lines - 1)
        
        except Exception as e:
            logger.warning(
                "Failed to estimate CSV record count",
                file_path=file_path,
                error=str(e)
            )
            return None
    
    async def _estimate_jsonl_records(self, file_path: str) -> Optional[int]:
        """Estimate number of records in JSONL file"""
        try:
            line_count = 0
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as file:
                async for line in file:
                    if line.strip():
                        line_count += 1
            return line_count
        
        except Exception as e:
            logger.warning(
                "Failed to estimate JSONL record count",
                file_path=file_path,
                error=str(e)
            )
            return None
    
    async def _is_jsonlines_format(self, file_path: str) -> bool:
        """Detect if file is JSON Lines format"""
        try:
            import json
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as file:
                first_line = await file.readline()
                if not first_line.strip():
                    return False
                
                # Try to parse first line as JSON
                json.loads(first_line.strip())
                
                # Check if it starts with '[' (JSON array) or '{' (JSONL)
                return first_line.strip().startswith('{')
        
        except Exception:
            return False


# Global streaming processor instance
_streaming_processor: Optional[DataStreamProcessor] = None


def get_streaming_processor(config: Optional[StreamingConfig] = None) -> DataStreamProcessor:
    """Get the global streaming processor instance"""
    global _streaming_processor
    if _streaming_processor is None:
        _streaming_processor = DataStreamProcessor(config)
    return _streaming_processor