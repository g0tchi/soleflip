import pytest
from unittest.mock import AsyncMock
from domains.integration.services.import_processor import (
    ImportProcessor,
    SourceType,
    ImportStatus
)

# Mark all tests in this file as integration tests requiring a database
pytestmark = [pytest.mark.integration, pytest.mark.database]

@pytest.fixture
def mock_product_processor():
    """Fixture for a mocked ProductProcessor."""
    return AsyncMock()

@pytest.fixture
def mock_transaction_processor():
    """Fixture for a mocked TransactionProcessor."""
    return AsyncMock()

@pytest.fixture
def import_processor(db_session, mock_product_processor, mock_transaction_processor):
    """Fixture for ImportProcessor with mocked dependencies."""
    return ImportProcessor(
        db_session=db_session,
        product_processor=mock_product_processor,
        transaction_processor=mock_transaction_processor
    )

class TestImportPipelineIntegration:
    
    async def test_stockx_import_success(self, import_processor, mock_product_processor, mock_transaction_processor, sample_stockx_csv_data):
        result = await import_processor.process_import(
            source_type=SourceType.STOCKX,
            data=sample_stockx_csv_data,
            raw_data=sample_stockx_csv_data,
            metadata={'filename': 'test.csv'}
        )
        assert result.status == ImportStatus.COMPLETED
        assert result.processed_records == 2
        mock_product_processor.extract_products_from_batch.assert_awaited_once()
        mock_transaction_processor.create_transactions_from_batch.assert_awaited_once()

    async def test_notion_import_success(self, import_processor, mock_product_processor, mock_transaction_processor, sample_notion_json_data):
        result = await import_processor.process_import(
            source_type=SourceType.NOTION,
            data=sample_notion_json_data,
            raw_data=sample_notion_json_data,
            metadata={'filename': 'test.json'}
        )
        assert result.status == ImportStatus.COMPLETED
        assert result.processed_records == 2
    
    async def test_import_validation_errors(self, import_processor):
        # This validator (SALES) is simple and good for this test
        invalid_data = [{'SKU': '123', 'Sale Date': '2024-01-01'}] # Missing 'Status'
        result = await import_processor.process_import(
            source_type=SourceType.SALES,
            data=invalid_data,
            raw_data=invalid_data,
            metadata={'filename': 'invalid.csv'}
        )
        assert result.status == ImportStatus.FAILED
        assert len(result.validation_errors) > 0
        assert "Missing required field: Status" in result.validation_errors[0]


@pytest.mark.slow
class TestImportPipelinePerformance:
    
    async def test_large_file_import_performance(self, import_processor, performance_timer):
        large_dataset = [{"Order Number": f"SX-{i:06d}", "Sale Date": "2024-01-15 10:30:00", "Item": f"Perf Test {i}", "Size": "9", "Listing Price": "100"} for i in range(100)]
        
        performance_timer.start()
        result = await import_processor.process_import(
            source_type=SourceType.STOCKX,
            data=large_dataset,
            raw_data=large_dataset,
            metadata={'filename': 'large.csv'}
        )
        performance_timer.stop()

        assert result.status == ImportStatus.COMPLETED
        assert result.processed_records == 100
        assert performance_timer.elapsed_ms < 10000

    async def test_memory_usage_large_import(self, import_processor):
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        dataset = [{"Item": f"Mem Test {i}"*10, "Order Number": f"MEM-{i}", "Sale Date": "2024-01-15", "Listing Price": "100"} for i in range(100)]
        
        await import_processor.process_import(
            source_type=SourceType.STOCKX,
            data=dataset,
            raw_data=dataset,
            metadata={'filename': 'memory.csv'}
        )
        
        final_memory = process.memory_info().rss
        memory_increase_mb = (final_memory - initial_memory) / 1024 / 1024
        
        assert memory_increase_mb < 50