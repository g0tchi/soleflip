"""
SoleFlipper API - Main Application Entry Point
Production-ready FastAPI application with proper error handling,
logging, and monitoring.
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from contextlib import asynccontextmanager
import pandas as pd
import io
import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import database models and connection
def check_database_availability():
    """Check if database modules are available"""
    try:
        from shared.database.models import ImportBatch, ImportRecord
        from shared.database.connection import get_db_session, db_manager
        from domains.integration.services.import_processor import ImportProcessor, SourceType
        return True
    except ImportError as e:
        print(f"Database modules not available: {e}")
        return False

DATABASE_AVAILABLE = check_database_availability()

# Lifespan event handler (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events"""
    # Startup
    print("[STARTUP] SoleFlipper API starting up...")
    print(f"[INFO] DATABASE_AVAILABLE = {DATABASE_AVAILABLE}")
    print(f"[INFO] DATABASE_URL = {os.getenv('DATABASE_URL')}")
    if DATABASE_AVAILABLE:
        try:
            from shared.database.connection import db_manager
            await db_manager.initialize()
            # Also run migrations to create tables
            await db_manager.run_migrations()
            print("[SUCCESS] Database connection initialized and tables created")
        except Exception as e:
            print(f"Warning: Database initialization failed: {e}")
            print("Running in demo mode without database")
    else:
        print("Running in demo mode - database modules not available")
    
    yield  # Application runs here
    
    # Shutdown
    print("[SHUTDOWN] SoleFlipper API shutting down...")
    if DATABASE_AVAILABLE:
        try:
            from shared.database.connection import db_manager
            await db_manager.close()
            print("[SUCCESS] Database connections closed")
        except Exception as e:
            print(f"Warning: Database cleanup failed: {e}")
        except:
            pass

# Response models
class APIInfo(BaseModel):
    name: str
    version: str
    status: str
    docs: str
    health: str

class HealthResponse(BaseModel):
    status: str

class UploadResponse(BaseModel):
    filename: str
    total_records: int
    validation_errors: List[str]
    status: str
    message: str
    imported: Optional[bool] = None
    batch_id: Optional[str] = None

# Create FastAPI application with lifespan handler
app = FastAPI(
    title="SoleFlipper API",
    description="""
    ## Professional Sneaker Reselling Management System
    
    Upload and manage your sneaker inventory from various marketplaces with intelligent data processing.
    
    ### Supported Platforms
    * **StockX** ✅ - CSV exports with complete sales data and fee breakdown
    * **Alias (GOAT)** ✅ - GOAT's selling platform CSV reports with smart brand extraction
    * **Notion** 🚧 - Database integration (in development)
    * **eBay** 🔮 - Coming soon
    * **Manual CSV** ✅ - Custom CSV formats for other platforms
    
    ### Key Features  
    * **Smart Data Processing** - Automatic brand extraction from product names
    * **StockX Name Prioritization** - Prefers StockX product names for consistency
    * **Multi-Format Support** - Handles different date formats (DD/MM/YY) and currencies
    * **File Validation** - Comprehensive validation before importing
    * **Batch Processing** - Handle large datasets efficiently in background
    * **Error Reporting** - Detailed validation feedback with field-level errors
    * **Real-time Processing** - Instant upload and validation
    * **Audit Trail** - Complete import history with source data preservation
    
    ### Getting Started
    1. Choose your platform: **StockX Upload** or **Alias Upload** endpoints below
    2. Upload your CSV file
    3. Enable validation to check format first (recommended)
    4. Import your data when validation passes
    5. Monitor processing status via the import-status endpoints
    
    ### Recent Updates (v2.1.0)
    * ✅ Added full Alias platform support with intelligent CSV processing
    * ✅ Smart brand extraction from product names (50+ sneaker brands)
    * ✅ StockX name prioritization for consistent product matching
    * ✅ Enhanced size normalization (shoes vs. clothing detection)
    * ✅ Multi-format date handling (DD/MM/YY, MM/DD/YY, ISO)
    * ✅ Currency handling improvements (USD direct amounts)
    * ✅ Comprehensive error handling and validation feedback
    * ✅ Clean codebase organization and documentation
    """,
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,  # Modern lifespan handler
    contact={
        "name": "SoleFlipper Support", 
        "email": "support@soleflip.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
if DATABASE_AVAILABLE:
    try:
        from domains.integration.api.webhooks import webhook_router
        app.include_router(webhook_router, prefix="/api/v1/integration", tags=["Integration"])
        print("[SUCCESS] Integration webhooks loaded at top level.")
    except ImportError as e:
        print(f"Warning: Could not load webhook routers at top level: {e}")


@app.get("/", response_model=APIInfo, tags=["System"])
async def root():
    """
    **API Information**
    
    Returns basic information about the SoleFlipper API including version and available endpoints.
    """
    return APIInfo(
        name="SoleFlipper API",
        version="2.1.0",
        status="running",
        docs="/docs",
        health="/health"
    )


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """
    **Health Check**
    
    Returns the current health status of the API. Use this endpoint to monitor if the service is running properly.
    """
    return HealthResponse(status="healthy")

@app.get("/debug", tags=["System"])
async def debug_status():
    """Debug endpoint to check DATABASE_AVAILABLE status"""
    return {
        "DATABASE_AVAILABLE": DATABASE_AVAILABLE,
        "DATABASE_URL": os.getenv('DATABASE_URL', 'Not set'),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/upload", tags=["Upload"])
async def upload_page():
    """
    **Upload Test Page**
    
    Alternative upload interface for testing when SwaggerUI has issues.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SoleFlipper Upload</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
            .container { background: #f9f9f9; padding: 30px; border-radius: 10px; }
            h1 { color: #333; text-align: center; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; width: 100%; }
            button:hover { background: #0056b3; }
            .result { margin-top: 20px; padding: 10px; border-radius: 4px; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>SoleFlipper Upload</h1>
            <form id="uploadForm">
                <div class="form-group">
                    <label>CSV-Datei:</label>
                    <input type="file" id="file" accept=".csv" required>
                </div>
                <div class="form-group">
                    <label><input type="checkbox" id="validate_only"> Nur validieren</label>
                </div>
                <button type="submit">Upload</button>
            </form>
            <div id="result"></div>
        </div>
        <script>
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const file = document.getElementById('file').files[0];
                if (!file) return;
                
                const formData = new FormData();
                formData.append('file', file);
                formData.append('validate_only', document.getElementById('validate_only').checked);
                formData.append('batch_size', '1000');
                
                try {
                    const response = await fetch('/api/v1/integration/webhooks/stockx/upload', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    
                    if (response.ok) {
                        document.getElementById('result').innerHTML = 
                            `<div class="result success">✅ Erfolg!<br>
                            Datei: ${data.filename}<br>
                            Records: ${data.total_records}<br>
                            Status: ${data.status}<br>
                            Fehler: ${data.validation_errors.length}</div>`;
                    } else {
                        document.getElementById('result').innerHTML = 
                            `<div class="result error">❌ Fehler: ${data.detail}</div>`;
                    }
                } catch (error) {
                    document.getElementById('result').innerHTML = 
                        `<div class="result error">❌ Netzwerkfehler: ${error.message}</div>`;
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None  # Use our structured logging
    )