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
        # Arrange
        batch = await import_processor.create_initial_batch(SourceType.STOCKX, "test.csv")

        # Act
        await import_processor.process_import(
            batch_id=batch.id,
            source_type=SourceType.STOCKX,
            data=sample_stockx_csv_data,
            raw_data=sample_stockx_csv_data
        )

        # Assert
        # Re-fetch batch from DB to check final status
        updated_batch = await import_processor.db_session.get(type(batch), batch.id)
        assert updated_batch.status == ImportStatus.COMPLETED.value
        assert updated_batch.processed_records == 2
        mock_product_processor.extract_products_from_batch.assert_awaited_once()
        mock_transaction_processor.create_transactions_from_batch.assert_awaited_once()

    async def test_notion_import_success(self, import_processor, mock_product_processor, mock_transaction_processor, sample_notion_json_data):
        # Arrange
        batch = await import_processor.create_initial_batch(SourceType.NOTION, "test.json")

        # Act
        await import_processor.process_import(
            batch_id=batch.id,
            source_type=SourceType.NOTION,
            data=sample_notion_json_data,
            raw_data=sample_notion_json_data
        )

        # Assert
        updated_batch = await import_processor.db_session.get(type(batch), batch.id)
        assert updated_batch.status == ImportStatus.COMPLETED.value
        assert updated_batch.processed_records == 2
    
    async def test_import_validation_errors(self, import_processor):
        # Arrange
        batch = await import_processor.create_initial_batch(SourceType.SALES, "invalid.csv")
        invalid_data = [{'SKU': '123', 'Sale Date': '2024-01-01'}] # Missing 'Status'

        # Act
        await import_processor.process_import(
            batch_id=batch.id,
            source_type=SourceType.SALES,
            data=invalid_data,
            raw_data=invalid_data
        )

        # Assert
        updated_batch = await import_processor.db_session.get(type(batch), batch.id)
        assert updated_batch.status == ImportStatus.FAILED.value
        assert updated_batch.error_records == 1


@pytest.mark.slow
class TestImportPipelinePerformance:
    
    async def test_large_file_import_performance(self, import_processor, performance_timer):
        # Arrange
        batch = await import_processor.create_initial_batch(SourceType.STOCKX, "large.csv")
        large_dataset = [{"Order Number": f"SX-{i:06d}", "Sale Date": "2024-01-15 10:30:00", "Item": f"Perf Test {i}", "Size": "9", "Listing Price": "100"} for i in range(100)]
        
        # Act
        performance_timer.start()
        await import_processor.process_import(
            batch_id=batch.id,
            source_type=SourceType.STOCKX,
            data=large_dataset,
            raw_data=large_dataset
        )
        performance_timer.stop()

        # Assert
        updated_batch = await import_processor.db_session.get(type(batch), batch.id)
        assert updated_batch.status == ImportStatus.COMPLETED.value
        assert updated_batch.processed_records == 100
        assert performance_timer.elapsed_ms < 10000

    async def test_memory_usage_large_import(self, import_processor):
        # Arrange
        batch = await import_processor.create_initial_batch(SourceType.STOCKX, "memory.csv")
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        dataset = [{"Item": f"Mem Test {i}"*10, "Order Number": f"MEM-{i}", "Sale Date": "2024-01-15", "Listing Price": "100"} for i in range(100)]
        
        # Act
        await import_processor.process_import(
            batch_id=batch.id,
            source_type=SourceType.STOCKX,
            data=dataset,
            raw_data=dataset
        )
        
        # Assert
        final_memory = process.memory_info().rss
        memory_increase_mb = (final_memory - initial_memory) / 1024 / 1024
        
        assert memory_increase_mb < 50