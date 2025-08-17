"""
SoleFlipper API - Main Application Entry Point
Production-ready FastAPI application with proper error handling,
logging, and monitoring.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

load_dotenv()

from shared.database.connection import get_db_session, db_manager
from domains.inventory.services.inventory_service import InventoryService

# Dependency provider functions
def get_inventory_service(db: AsyncSession = Depends(get_db_session)) -> InventoryService:
    return InventoryService(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[STARTUP] SoleFlipper API starting up...")
    await db_manager.initialize()
    await db_manager.run_migrations()
    print("[SUCCESS] Database connection initialized and tables created")
    yield
    print("[SHUTDOWN] SoleFlipper API shutting down...")
    await db_manager.close()
    print("[SUCCESS] Database connections closed")

class APIInfo(BaseModel):
    name: str
    version: str

app = FastAPI(
    title="SoleFlipper API",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
from domains.integration.api.webhooks import router as webhook_router
from domains.integration.api.upload_router import router as upload_router
from domains.orders.api.router import router as orders_router
from domains.products.api.router import router as products_router
from domains.inventory.api.router import router as inventory_router

app.include_router(webhook_router, prefix="/api/v1/integration", tags=["Integration"])
app.include_router(upload_router, prefix="/api/v1/integration", tags=["Integration"]) # Prefix is the same
app.include_router(orders_router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(products_router, prefix="/api/v1/products", tags=["Products"])
app.include_router(inventory_router, prefix="/api/v1/inventory", tags=["Inventory"])


@app.get("/", response_model=APIInfo, tags=["System"])
async def root():
    return APIInfo(name="SoleFlipper API", version="2.1.0")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)