"""
OpenAPI/Swagger Documentation Generator
Generates comprehensive API documentation with examples and schemas
"""

import json
import os
import sys
from typing import Any, Dict

from fastapi.openapi.utils import get_openapi

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from main import app


def generate_openapi_schema() -> Dict[str, Any]:
    """Generate comprehensive OpenAPI schema with custom descriptions"""
    return get_openapi(
        title="SoleFlipper API",
        version="2.0.0",
        description="""
# SoleFlipper API Documentation

## Overview
Professional sneaker reselling management system with inventory tracking, 
automated imports, and analytics integration.

## Architecture
- **FastAPI**: Modern async Python framework
- **PostgreSQL**: Primary database with schema separation
- **n8n Integration**: Webhook-based automation
- **Metabase**: Analytics and reporting
- **Domain-Driven Design**: Clean architecture patterns

## Authentication
Currently, most endpoints are open. Authentication will be added in future versions.

## Rate Limiting
Rate limiting is planned but not yet implemented.

## Data Import Sources
- **StockX**: Sales and transaction data
- **Notion**: Inventory management database
- **Manual**: CSV/Excel file uploads with auto-detection

## Error Handling
All endpoints return structured error responses with:
- `error.type`: Error category
- `error.message`: Human-readable description
- `error.details`: Additional context (optional)

## Pagination
List endpoints support query parameters:
- `limit`: Number of items (default: 50, max: 1000)
- `offset`: Number of items to skip (default: 0)
        """,
        routes=app.routes,
        servers=[
            {"url": "http://localhost:8000", "description": "Development server"},
            {"url": "https://api.soleflip.com", "description": "Production server"},
        ],
    )


def add_custom_schemas(openapi_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Add custom schemas and examples to OpenAPI specification"""

    # Add custom schemas
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}

    # Import status schema
    openapi_schema["components"]["schemas"]["ImportStatus"] = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["processing_started", "validated", "completed", "failed"],
                "description": "Current status of the import operation",
            },
            "batch_id": {
                "type": "string",
                "format": "uuid",
                "description": "Unique identifier for the import batch",
            },
            "message": {"type": "string", "description": "Human-readable status message"},
            "filename": {"type": "string", "description": "Original filename of uploaded file"},
            "record_count": {"type": "integer", "description": "Number of records processed"},
            "check_status_url": {
                "type": "string",
                "format": "uri",
                "description": "URL to check import progress",
            },
        },
        "required": ["status", "message"],
    }

    # Validation result schema
    openapi_schema["components"]["schemas"]["ValidationResult"] = {
        "type": "object",
        "properties": {
            "valid": {"type": "boolean", "description": "Whether validation passed"},
            "errors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of validation errors",
            },
            "warnings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of validation warnings",
            },
            "record_count": {"type": "integer", "description": "Total number of records validated"},
        },
    }

    # Import batch summary schema
    openapi_schema["components"]["schemas"]["ImportBatchSummary"] = {
        "type": "object",
        "properties": {
            "summary": {
                "type": "object",
                "properties": {
                    "total_batches": {"type": "integer"},
                    "completed": {"type": "integer"},
                    "failed": {"type": "integer"},
                    "processing": {"type": "integer"},
                    "success_rate": {"type": "number", "format": "float"},
                },
            },
            "recent_imports": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "source_type": {"type": "string"},
                        "source_file": {"type": "string"},
                        "status": {"type": "string"},
                        "created_at": {"type": "string", "format": "date-time"},
                        "total_records": {"type": "integer"},
                        "processed_records": {"type": "integer"},
                    },
                },
            },
        },
    }

    # Error response schema
    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "error": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "description": "Error category"},
                    "message": {"type": "string", "description": "Human-readable error message"},
                    "details": {"type": "object", "description": "Additional error context"},
                },
                "required": ["type", "message"],
            }
        },
        "required": ["error"],
    }

    return openapi_schema


def add_examples_to_paths(openapi_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Add request/response examples to API paths"""

    if "paths" not in openapi_schema:
        return openapi_schema

    # StockX upload examples
    stockx_upload_path = "/api/v1/integration/webhooks/stockx/upload"
    if stockx_upload_path in openapi_schema["paths"]:
        post_operation = openapi_schema["paths"][stockx_upload_path].get("post", {})

        # Add request example
        if "requestBody" in post_operation:
            post_operation["requestBody"]["content"]["multipart/form-data"]["example"] = {
                "file": "stockx_sales_report.csv",
                "batch_size": 1000,
                "validate_only": False,
            }

        # Add response examples
        if "responses" in post_operation:
            if "200" in post_operation["responses"]:
                post_operation["responses"]["200"]["content"]["application/json"]["examples"] = {
                    "processing_started": {
                        "summary": "Import processing started",
                        "value": {
                            "status": "processing_started",
                            "message": "File uploaded successfully. Processing started in background.",
                            "batch_id": "123e4567-e89b-12d3-a456-426614174000",
                            "filename": "stockx_sales_report.csv",
                            "record_count": 150,
                            "check_status_url": "/api/v1/integration/webhooks/import-status/123e4567-e89b-12d3-a456-426614174000",
                        },
                    },
                    "validation_only": {
                        "summary": "Validation only result",
                        "value": {
                            "status": "validated",
                            "valid": True,
                            "errors": [],
                            "warnings": ["Some items missing optional fields"],
                            "record_count": 150,
                        },
                    },
                }

    # Notion import examples
    notion_import_path = "/api/v1/integration/webhooks/notion/import"
    if notion_import_path in openapi_schema["paths"]:
        post_operation = openapi_schema["paths"][notion_import_path].get("post", {})

        if "requestBody" in post_operation:
            post_operation["requestBody"]["content"]["application/json"]["example"] = {
                "results": [
                    {
                        "id": "page-123",
                        "name": "Nike Air Jordan 1",
                        "properties": {
                            "brand": {"rich_text": [{"text": {"content": "Nike"}}]},
                            "size": {"rich_text": [{"text": {"content": "US 9"}}]},
                            "purchase_price": {"number": 120.00},
                            "status": {"select": {"name": "In Stock"}},
                        },
                    }
                ],
                "has_more": False,
                "next_cursor": None,
            }

    return openapi_schema


def generate_postman_collection() -> Dict[str, Any]:
    """Generate Postman collection for API testing"""
    return {
        "info": {
            "name": "SoleFlipper API",
            "description": "Complete API collection for SoleFlipper sneaker management system",
            "version": "2.0.0",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [{"key": "baseUrl", "value": "http://localhost:8000", "type": "string"}],
        "item": [
            {
                "name": "Integration",
                "item": [
                    {
                        "name": "StockX Upload",
                        "request": {
                            "method": "POST",
                            "header": [{"key": "Content-Type", "value": "multipart/form-data"}],
                            "body": {
                                "mode": "formdata",
                                "formdata": [
                                    {
                                        "key": "file",
                                        "type": "file",
                                        "src": "stockx_sales_report.csv",
                                    },
                                    {"key": "batch_size", "value": "1000", "type": "text"},
                                    {"key": "validate_only", "value": "false", "type": "text"},
                                ],
                            },
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/integration/webhooks/stockx/upload",
                                "host": ["{{baseUrl}}"],
                                "path": [
                                    "api",
                                    "v1",
                                    "integration",
                                    "webhooks",
                                    "stockx",
                                    "upload",
                                ],
                            },
                        },
                    },
                    {
                        "name": "Notion Import",
                        "request": {
                            "method": "POST",
                            "header": [{"key": "Content-Type", "value": "application/json"}],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps(
                                    {
                                        "results": [
                                            {
                                                "id": "page-123",
                                                "name": "Nike Air Jordan 1",
                                                "properties": {
                                                    "brand": {
                                                        "rich_text": [{"text": {"content": "Nike"}}]
                                                    },
                                                    "size": {
                                                        "rich_text": [{"text": {"content": "US 9"}}]
                                                    },
                                                },
                                            }
                                        ],
                                        "has_more": False,
                                    },
                                    indent=2,
                                ),
                            },
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/integration/webhooks/notion/import?batch_size=1000",
                                "host": ["{{baseUrl}}"],
                                "path": [
                                    "api",
                                    "v1",
                                    "integration",
                                    "webhooks",
                                    "notion",
                                    "import",
                                ],
                                "query": [{"key": "batch_size", "value": "1000"}],
                            },
                        },
                    },
                    {
                        "name": "Import Status Overview",
                        "request": {
                            "method": "GET",
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/integration/webhooks/import-status",
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "integration", "webhooks", "import-status"],
                            },
                        },
                    },
                ],
            },
            {
                "name": "Health Check",
                "request": {
                    "method": "GET",
                    "url": {
                        "raw": "{{baseUrl}}/health",
                        "host": ["{{baseUrl}}"],
                        "path": ["health"],
                    },
                },
            },
        ],
    }


def main():
    """Generate all API documentation files"""

    # Generate OpenAPI schema
    openapi_schema = generate_openapi_schema()
    openapi_schema = add_custom_schemas(openapi_schema)
    openapi_schema = add_examples_to_paths(openapi_schema)

    # Save OpenAPI schema
    output_dir = os.path.dirname(__file__)
    openapi_path = os.path.join(output_dir, "openapi.json")
    postman_path = os.path.join(output_dir, "postman_collection.json")

    with open(openapi_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)

    # Generate Postman collection
    postman_collection = generate_postman_collection()
    with open(postman_path, "w", encoding="utf-8") as f:
        json.dump(postman_collection, f, indent=2, ensure_ascii=False)

    print(f"✅ OpenAPI documentation generated: {openapi_path}")
    print(f"✅ Postman collection generated: {postman_path}")
    print("📖 View docs at: http://localhost:8000/docs")
    print("📖 ReDoc at: http://localhost:8000/redoc")


if __name__ == "__main__":
    main()
