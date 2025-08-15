"""
API Router for Inventory-related endpoints
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import structlog

from shared.database.connection import get_db_session
from domains.inventory.services.inventory_service import InventoryService

logger = structlog.get_logger(__name__)

router = APIRouter()

def get_inventory_service(db: AsyncSession = Depends(get_db_session)) -> InventoryService:
    return InventoryService(db)
