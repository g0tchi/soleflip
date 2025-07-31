"""
API Tests for Webhook Endpoints
Tests API endpoints with realistic HTTP requests and responses
"""
import pytest
import json
import tempfile
from pathlib import Path
from httpx import AsyncClient
from fastapi import status

@pytest.mark.api
class TestWebhookEndpoints:
    """Test webhook API endpoints"""
    
    @pytest.fixture
    def stockx_csv_content(self, sample_stockx_csv_data):
        """Create CSV content for testing"""
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=sample_stockx_csv_data[0].keys())
        writer.writeheader()
        writer.writerows(sample_stockx_csv_data)
        
        return output.getvalue().encode('utf-8')
    
    @pytest.fixture  
    def notion_json_content(self, sample_notion_json_data):
        """Create JSON content for testing"""
        return {
            "results": sample_notion_json_data,
            "has_more": False,
            "next_cursor": None
        }
    
    async def test_stockx_upload_webhook_success(
        self,
        test_client: AsyncClient,
        stockx_csv_content,
        override_db_dependency
    ):
        """Test successful StockX file upload"""
        
        # Prepare multipart form data
        files = {
            "file": ("test_stockx.csv", stockx_csv_content, "text/csv")
        }
        data = {
            "batch_size": 1000,
            "validate_only": False
        }
        
        # Make request
        response = await test_client.post(
            "/api/v1/integration/webhooks/stockx/upload",
            files=files,
            data=data
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert response_data["status"] == "processing_started"
        assert "message" in response_data
        assert "filename" in response_data
        assert "check_status_url" in response_data
    
    async def test_stockx_upload_webhook_validation_only(
        self,
        test_client: AsyncClient,
        stockx_csv_content,
        override_db_dependency
    ):
        """Test StockX file upload with validation only"""
        
        files = {
            "file": ("test_stockx.csv", stockx_csv_content, "text/csv")
        }
        data = {
            "batch_size": 1000,
            "validate_only": True
        }
        
        response = await test_client.post(
            "/api/v1/integration/webhooks/stockx/upload",
            files=files,
            data=data
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert response_data["status"] == "validated"
        assert "valid" in response_data
        assert "errors" in response_data
        assert "warnings" in response_data
        assert "record_count" in response_data
    
    async def test_stockx_upload_webhook_invalid_file_type(
        self,
        test_client: AsyncClient,
        override_db_dependency
    ):
        """Test StockX upload with invalid file type"""
        
        files = {
            "file": ("test.txt", b"invalid content", "text/plain")
        }
        data = {
            "batch_size": 1000,
            "validate_only": False
        }
        
        response = await test_client.post(
            "/api/v1/integration/webhooks/stockx/upload",
            files=files,
            data=data
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        response_data = response.json()
        assert "error" in response_data
        assert "CSV and Excel files" in response_data["error"]["message"]
    
    async def test_notion_import_webhook_success(
        self,
        test_client: AsyncClient,
        notion_json_content,
        override_db_dependency
    ):
        """Test successful Notion import webhook"""
        
        response = await test_client.post(
            "/api/v1/integration/webhooks/notion/import",
            json=notion_json_content,
            params={"batch_size": 1000}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert response_data["status"] == "processing_started"
        assert response_data["record_count"] == 2
        assert "check_status_url" in response_data
    
    async def test_notion_import_webhook_empty_results(
        self,
        test_client: AsyncClient,
        override_db_dependency
    ):
        """Test Notion import with empty results"""
        
        empty_data = {
            "results": [],
            "has_more": False,
            "next_cursor": None
        }
        
        response = await test_client.post(
            "/api/v1/integration/webhooks/notion/import",
            json=empty_data,
            params={"batch_size": 1000}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert response_data["status"] == "completed"
        assert response_data["record_count"] == 0
    
    async def test_notion_import_webhook_invalid_payload(
        self,
        test_client: AsyncClient,
        override_db_dependency
    ):
        """Test Notion import with invalid payload"""
        
        invalid_data = {
            "invalid_field": "data"
            # Missing 'results' field
        }
        
        response = await test_client.post(
            "/api/v1/integration/webhooks/notion/import",
            json=invalid_data,
            params={"batch_size": 1000}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        response_data = response.json()
        assert "error" in response_data
        assert "missing 'results' field" in response_data["error"]["message"]
    
    async def test_manual_upload_webhook_success(
        self,
        test_client: AsyncClient,
        stockx_csv_content,
        override_db_dependency
    ):
        """Test manual upload webhook with auto-detection"""
        
        files = {
            "file": ("manual_upload.csv", stockx_csv_content, "text/csv")
        }
        data = {
            "source_type": "auto",
            "batch_size": 1000
        }
        
        response = await test_client.post(
            "/api/v1/integration/webhooks/manual/upload",
            files=files,
            data=data
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert response_data["status"] == "processing_started"
        assert response_data["source_type"] == "auto"
        assert "filename" in response_data
    
    async def test_manual_upload_webhook_explicit_source_type(
        self,
        test_client: AsyncClient,
        stockx_csv_content,
        override_db_dependency
    ):
        """Test manual upload with explicit source type"""
        
        files = {
            "file": ("stockx_manual.csv", stockx_csv_content, "text/csv")
        }
        data = {
            "source_type": "stockx",
            "batch_size": 500
        }
        
        response = await test_client.post(
            "/api/v1/integration/webhooks/manual/upload",
            files=files,
            data=data
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert response_data["status"] == "processing_started"
        assert response_data["source_type"] == "stockx"
    
    async def test_manual_upload_webhook_invalid_source_type(
        self,
        test_client: AsyncClient,
        stockx_csv_content,
        override_db_dependency
    ):
        """Test manual upload with invalid source type"""
        
        files = {
            "file": ("test.csv", stockx_csv_content, "text/csv")
        }
        data = {
            "source_type": "invalid_type",
            "batch_size": 1000
        }
        
        response = await test_client.post(
            "/api/v1/integration/webhooks/manual/upload",
            files=files,
            data=data
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        response_data = response.json()
        assert "error" in response_data
        assert "Invalid source type" in response_data["error"]["message"]
    
    async def test_get_import_status_webhook(
        self,
        test_client: AsyncClient,
        override_db_dependency
    ):
        """Test import status retrieval"""
        
        response = await test_client.get(
            "/api/v1/integration/webhooks/import-status"
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert "summary" in response_data
        assert "recent_imports" in response_data
        
        summary = response_data["summary"]
        assert "total_batches" in summary
        assert "completed" in summary
        assert "failed" in summary
        assert "processing" in summary
        assert "success_rate" in summary
        
        assert isinstance(response_data["recent_imports"], list)
    
    async def test_get_specific_batch_status_webhook(
        self,
        test_client: AsyncClient,
        override_db_dependency,
        sample_import_batch_data
    ):
        """Test specific batch status retrieval"""
        
        # First create a batch (this would normally be done by import process)
        from shared.database.models import ImportBatch
        from uuid import uuid4
        
        batch_id = str(uuid4())
        
        # Try to get status for non-existent batch
        response = await test_client.get(
            f"/api/v1/integration/webhooks/import-status/{batch_id}"
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        response_data = response.json()
        assert "error" in response_data
        assert "not found" in response_data["error"]["message"]

@pytest.mark.api
class TestWebhookErrorHandling:
    """Test error handling in webhook endpoints"""
    
    async def test_missing_file_parameter(
        self,
        test_client: AsyncClient,
        override_db_dependency
    ):
        """Test webhook with missing file parameter"""
        
        data = {
            "batch_size": 1000,
            "validate_only": False
        }
        
        response = await test_client.post(
            "/api/v1/integration/webhooks/stockx/upload",
            data=data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_invalid_batch_size(
        self,
        test_client: AsyncClient,
        override_db_dependency
    ):
        """Test webhook with invalid batch size"""
        
        files = {
            "file": ("test.csv", b"test,data\n1,2", "text/csv")
        }
        data = {
            "batch_size": -1,  # Invalid negative batch size
            "validate_only": False
        }
        
        response = await test_client.post(
            "/api/v1/integration/webhooks/stockx/upload",
            files=files,
            data=data
        )
        
        # FastAPI should handle validation automatically
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]
    
    async def test_large_file_upload(
        self,
        test_client: AsyncClient,
        override_db_dependency
    ):
        """Test handling of large file uploads"""
        
        # Create a large CSV content (simulate large file)
        large_content = "Order Number,Item,Size,Listing Price\n"
        for i in range(10000):  # 10k rows
            large_content += f"ORDER-{i:05d},Test Item {i},9,100.00\n"
        
        files = {
            "file": ("large_test.csv", large_content.encode('utf-8'), "text/csv")
        }
        data = {
            "batch_size": 1000,
            "validate_only": True  # Use validation only to avoid long processing
        }
        
        response = await test_client.post(
            "/api/v1/integration/webhooks/stockx/upload",
            files=files,
            data=data
        )
        
        # Should handle large files gracefully
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        ]
    
    async def test_malformed_json_notion_import(
        self,
        test_client: AsyncClient,
        override_db_dependency
    ):
        """Test Notion import with malformed JSON"""
        
        # Send invalid JSON
        response = await test_client.post(
            "/api/v1/integration/webhooks/notion/import",
            content="invalid json content",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_webhook_concurrent_requests(
        self,
        test_client: AsyncClient,
        override_db_dependency
    ):
        """Test concurrent webhook requests"""
        import asyncio
        
        csv_content = b"Order Number,Item,Size,Listing Price\nTEST-001,Test Item,9,100.00"
        
        async def make_request(i):
            files = {
                "file": (f"test_{i}.csv", csv_content, "text/csv")
            }
            data = {
                "batch_size": 10,
                "validate_only": True
            }
            
            return await test_client.post(
                "/api/v1/integration/webhooks/stockx/upload",
                files=files,
                data=data
            )
        
        # Make 5 concurrent requests
        tasks = [make_request(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["status"] == "validated"

@pytest.mark.api
class TestWebhookAuthentication:
    """Test authentication/authorization for webhooks"""
    
    async def test_webhook_without_auth(
        self,
        test_client: AsyncClient,
        override_db_dependency
    ):
        """Test webhook access without authentication"""
        
        # For now, webhooks are open (this might change based on requirements)
        csv_content = b"Order Number,Item,Size,Listing Price\nTEST-001,Test Item,9,100.00"
        files = {
            "file": ("test.csv", csv_content, "text/csv")  
        }
        data = {
            "batch_size": 10,
            "validate_only": True
        }
        
        response = await test_client.post(
            "/api/v1/integration/webhooks/stockx/upload",
            files=files,
            data=data
        )
        
        # Should work without authentication (adjust if auth is added)
        assert response.status_code == status.HTTP_200_OK
    
    async def test_webhook_rate_limiting(
        self,
        test_client: AsyncClient,
        override_db_dependency 
    ):
        """Test rate limiting on webhook endpoints"""
        
        # Make rapid requests to test rate limiting
        csv_content = b"Order Number,Item,Size,Listing Price\nTEST-001,Test Item,9,100.00"
        
        responses = []
        for i in range(20):  # Make 20 rapid requests
            files = {
                "file": (f"test_{i}.csv", csv_content, "text/csv")
            }
            data = {
                "batch_size": 1,
                "validate_only": True
            }
            
            response = await test_client.post(
                "/api/v1/integration/webhooks/stockx/upload",
                files=files,
                data=data
            )
            responses.append(response)
        
        # Most requests should succeed (rate limiting not implemented yet)
        success_count = sum(1 for r in responses if r.status_code == status.HTTP_200_OK)
        assert success_count > 0  # At least some should succeed
        
        # If rate limiting is implemented, some might return 429
        rate_limited_count = sum(1 for r in responses if r.status_code == status.HTTP_429_TOO_MANY_REQUESTS)
        # For now, expect no rate limiting
        assert rate_limited_count == 0