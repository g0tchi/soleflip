"""
Integration Tests for Import Pipeline
Tests the complete import flow with real database interactions
"""
import pytest
import tempfile
import json
import csv
from pathlib import Path
from uuid import uuid4
from decimal import Decimal

from domains.integration.services.import_processor import (
    ImportProcessor,
    SourceType,
    ImportStatus
)
from shared.database.models import ImportBatch, ImportRecord
from sqlalchemy import select

@pytest.mark.integration
@pytest.mark.database
class TestImportPipelineIntegration:
    """Integration tests for the complete import pipeline"""
    
    @pytest.fixture
    def import_processor(self):
        """Create import processor instance"""
        return ImportProcessor()
    
    @pytest.fixture
    def temp_stockx_csv(self, sample_stockx_csv_data):
        """Create temporary StockX CSV file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=sample_stockx_csv_data[0].keys())
            writer.writeheader()
            writer.writerows(sample_stockx_csv_data)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def temp_notion_json(self, sample_notion_json_data):
        """Create temporary Notion JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_notion_json_data, f, indent=2)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def temp_invalid_csv(self):
        """Create temporary invalid CSV file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            # Write CSV with missing required fields
            writer = csv.DictWriter(f, fieldnames=['Invalid', 'Fields'])
            writer.writeheader()
            writer.writerow({'Invalid': 'data', 'Fields': 'here'})
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    async def test_stockx_import_success(
        self, 
        import_processor, 
        temp_stockx_csv, 
        db_session,
        override_db_dependency
    ):
        """Test successful StockX CSV import"""
        
        # Execute import
        result = await import_processor.process_file(
            file_path=temp_stockx_csv,
            source_type=SourceType.STOCKX,
            batch_size=10
        )
        
        # Assertions
        assert result.status == ImportStatus.COMPLETED
        assert result.source_type == SourceType.STOCKX.value
        assert result.total_records == 2
        assert result.processed_records == 2
        assert result.error_records == 0
        assert len(result.validation_errors) == 0
        assert result.processing_time_ms > 0
        
        # Verify database records
        batch_query = select(ImportBatch).where(ImportBatch.id == result.batch_id)
        batch_result = await db_session.execute(batch_query)
        batch = batch_result.scalar_one()
        
        assert batch.source_type == SourceType.STOCKX.value
        assert batch.status == ImportStatus.COMPLETED.value
        assert batch.total_records == 2
        assert batch.processed_records == 2
        assert batch.error_records == 0
        
        # Verify import records
        records_query = select(ImportRecord).where(ImportRecord.batch_id == result.batch_id)
        records_result = await db_session.execute(records_query)
        records = records_result.scalars().all()
        
        assert len(records) == 2
        for record in records:
            assert record.processed is True
            assert record.error_message is None
            assert record.raw_data is not None
            assert record.normalized_data is not None
    
    async def test_notion_import_success(
        self,
        import_processor,
        temp_notion_json,
        db_session,
        override_db_dependency
    ):
        """Test successful Notion JSON import"""
        
        # Execute import
        result = await import_processor.process_file(
            file_path=temp_notion_json,
            source_type=SourceType.NOTION,
            batch_size=10
        )
        
        # Assertions
        assert result.status == ImportStatus.COMPLETED
        assert result.source_type == SourceType.NOTION.value
        assert result.total_records == 2
        assert result.processed_records == 2
        assert result.error_records == 0
        
        # Verify database records
        records_query = select(ImportRecord).where(ImportRecord.batch_id == result.batch_id)
        records_result = await db_session.execute(records_query)
        records = records_result.scalars().all()
        
        assert len(records) == 2
        
        # Check Notion-specific data extraction
        for record in records:
            assert 'notion_page_id' in record.normalized_data
            assert 'item_name' in record.normalized_data
            assert record.normalized_data['source'] == 'notion'
    
    async def test_auto_detection_stockx(
        self,
        import_processor,
        temp_stockx_csv,
        db_session,
        override_db_dependency
    ):
        """Test automatic source type detection for StockX"""
        
        # Execute import without specifying source type
        result = await import_processor.process_file(
            file_path=temp_stockx_csv,
            source_type=None,  # Auto-detect
            batch_size=10
        )
        
        # Assertions - should auto-detect as StockX
        assert result.status == ImportStatus.COMPLETED
        assert result.source_type == SourceType.STOCKX.value
        assert result.processed_records == 2
    
    async def test_auto_detection_notion(
        self,
        import_processor,
        temp_notion_json,
        db_session,
        override_db_dependency
    ):
        """Test automatic source type detection for Notion"""
        
        # Execute import without specifying source type
        result = await import_processor.process_file(
            file_path=temp_notion_json,
            source_type=None,  # Auto-detect
            batch_size=10
        )
        
        # Assertions - should auto-detect as Notion
        assert result.status == ImportStatus.COMPLETED
        assert result.source_type == SourceType.NOTION.value
        assert result.processed_records == 2
    
    async def test_import_validation_errors(
        self,
        import_processor,
        temp_invalid_csv,
        db_session,
        override_db_dependency
    ):
        """Test import with validation errors"""
        
        # Execute import
        result = await import_processor.process_file(
            file_path=temp_invalid_csv,
            source_type=SourceType.MANUAL,  # Use manual for invalid data
            batch_size=10
        )
        
        # Should complete but with validation errors
        assert result.status == ImportStatus.COMPLETED
        assert result.total_records == 1
        # Record might still be processed but marked with validation errors
        assert result.processed_records >= 0
    
    async def test_batch_processing(
        self,
        import_processor,
        db_session,
        override_db_dependency
    ):
        """Test batch processing with different batch sizes"""
        
        # Create larger test dataset
        large_dataset = []
        for i in range(50):
            large_dataset.append({
                "Order Number": f"SX-{i:04d}",
                "Sale Date": "2024-01-15 10:30:00",
                "Item": f"Test Item {i}",
                "Size": "9",
                "Listing Price": "100.00"
            })
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=large_dataset[0].keys())
            writer.writeheader()
            writer.writerows(large_dataset)
            temp_path = f.name
        
        try:
            # Test with small batch size
            result = await import_processor.process_file(
                file_path=temp_path,
                source_type=SourceType.STOCKX,
                batch_size=10  # Small batch size
            )
            
            assert result.status == ImportStatus.COMPLETED
            assert result.total_records == 50
            assert result.processed_records == 50
            
            # Verify all records were processed in batches
            records_query = select(ImportRecord).where(ImportRecord.batch_id == result.batch_id)
            records_result = await db_session.execute(records_query)
            records = records_result.scalars().all()
            
            assert len(records) == 50
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    async def test_concurrent_imports(
        self,
        import_processor,
        sample_stockx_csv_data,
        db_session,
        override_db_dependency
    ):
        """Test concurrent import processing"""
        import asyncio
        
        # Create multiple temporary files
        temp_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                # Modify data slightly for each file
                data = [
                    {**record, 'Order Number': f"{record['Order Number']}-{i}"}
                    for record in sample_stockx_csv_data
                ]
                
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                temp_files.append(f.name)
        
        try:
            # Run imports concurrently
            tasks = [
                import_processor.process_file(
                    file_path=temp_file,
                    source_type=SourceType.STOCKX,
                    batch_size=10
                )
                for temp_file in temp_files
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All imports should succeed
            for result in results:
                assert result.status == ImportStatus.COMPLETED
                assert result.processed_records == 2
            
            # Verify all batches are in database
            batch_query = select(ImportBatch)
            batch_result = await db_session.execute(batch_query)
            batches = batch_result.scalars().all()
            
            assert len(batches) >= 3  # At least our 3 batches
            
            # Verify all records are processed
            records_query = select(ImportRecord)
            records_result = await db_session.execute(records_query)
            records = records_result.scalars().all()
            
            assert len(records) >= 6  # At least 2 records per batch * 3 batches
            
        finally:
            # Cleanup
            for temp_file in temp_files:
                Path(temp_file).unlink(missing_ok=True)
    
    async def test_import_error_handling(
        self,
        import_processor,
        db_session,
        override_db_dependency
    ):
        """Test import error handling for non-existent files"""
        
        # Try to import non-existent file
        result = await import_processor.process_file(
            file_path="/non/existent/file.csv",
            source_type=SourceType.STOCKX,
            batch_size=10
        )
        
        # Should fail gracefully
        assert result.status == ImportStatus.FAILED
        assert result.processed_records == 0
        assert result.error_records == 1
        assert len(result.validation_errors) > 0
    
    async def test_import_progress_tracking(
        self,
        import_processor,
        temp_stockx_csv,
        db_session,
        override_db_dependency
    ):
        """Test import progress tracking in database"""
        
        # Execute import
        result = await import_processor.process_file(
            file_path=temp_stockx_csv,
            source_type=SourceType.STOCKX,
            batch_size=1  # Process one at a time for better tracking
        )
        
        # Verify batch tracking
        batch_query = select(ImportBatch).where(ImportBatch.id == result.batch_id)
        batch_result = await db_session.execute(batch_query)
        batch = batch_result.scalar_one()
        
        assert batch.started_at is not None
        assert batch.completed_at is not None
        assert batch.completed_at >= batch.started_at
        assert batch.source_file == temp_stockx_csv
        
        # Verify individual record tracking
        records_query = select(ImportRecord).where(ImportRecord.batch_id == result.batch_id)
        records_result = await db_session.execute(records_query)
        records = records_result.scalars().all()
        
        for record in records:
            assert record.processing_started_at is not None
            assert record.processing_completed_at is not None
            assert record.processing_completed_at >= record.processing_started_at

@pytest.mark.integration 
@pytest.mark.slow
class TestImportPipelinePerformance:
    """Performance tests for import pipeline"""
    
    async def test_large_file_import_performance(
        self,
        db_session,
        override_db_dependency,
        performance_timer
    ):
        """Test performance with large datasets"""
        
        # Create large dataset (1000 records)
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                "Order Number": f"SX-{i:06d}",
                "Sale Date": "2024-01-15 10:30:00",
                "Item": f"Performance Test Item {i}",
                "Size": str((i % 12) + 6),  # Sizes 6-17
                "Listing Price": str(100 + (i % 100)),
                "SKU": f"PERF-{i:06d}",
                "Seller Fee": "10.00",
                "Payment Processing": "3.00", 
                "Shipping Fee": "12.00",
                "Total Payout": "75.00"
            })
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=large_dataset[0].keys())
            writer.writeheader()
            writer.writerows(large_dataset)
            temp_path = f.name
        
        try:
            import_processor = ImportProcessor()
            
            # Time the import
            performance_timer.start()
            result = await import_processor.process_file(
                file_path=temp_path,
                source_type=SourceType.STOCKX,
                batch_size=100  # Process in batches of 100
            )
            performance_timer.stop()
            
            # Performance assertions
            assert result.status == ImportStatus.COMPLETED
            assert result.total_records == 1000
            assert result.processed_records == 1000
            
            # Should complete within reasonable time (adjust threshold as needed)
            elapsed_ms = performance_timer.elapsed_ms
            assert elapsed_ms < 30000  # Less than 30 seconds
            
            # Calculate throughput
            throughput = result.processed_records / (elapsed_ms / 1000)  # records per second
            assert throughput > 10  # At least 10 records per second
            
            print(f"Performance: {result.processed_records} records in {elapsed_ms:.2f}ms")
            print(f"Throughput: {throughput:.2f} records/second")
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    async def test_memory_usage_large_import(
        self,
        db_session,
        override_db_dependency
    ):
        """Test memory usage with large imports"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create medium dataset
        dataset = []
        for i in range(500):
            dataset.append({
                "Order Number": f"MEM-{i:05d}",
                "Sale Date": "2024-01-15 10:30:00",
                "Item": f"Memory Test Item {i}" * 10,  # Longer strings
                "Size": "9",
                "Listing Price": "100.00"
            })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=dataset[0].keys())
            writer.writeheader()
            writer.writerows(dataset)
            temp_path = f.name
        
        try:
            import_processor = ImportProcessor()
            
            result = await import_processor.process_file(
                file_path=temp_path,
                source_type=SourceType.STOCKX,
                batch_size=50  # Smaller batches to test memory management
            )
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            assert result.status == ImportStatus.COMPLETED
            assert result.processed_records == 500
            
            # Memory increase should be reasonable (adjust threshold as needed)
            assert memory_increase < 100  # Less than 100MB increase
            
            print(f"Memory usage: {initial_memory:.2f}MB -> {final_memory:.2f}MB")
            print(f"Memory increase: {memory_increase:.2f}MB")
            
        finally:
            Path(temp_path).unlink(missing_ok=True)