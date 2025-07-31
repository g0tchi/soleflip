"""
Inventory Domain Service
Business logic layer for inventory management
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass
import structlog

from shared.database.connection import get_db_session
from ..repositories.product_repository import ProductRepository
from ..repositories.base_repository import BaseRepository
from shared.database.models import Product, InventoryItem, Brand, Category, Size

logger = structlog.get_logger(__name__)

@dataclass
class InventoryStats:
    """Inventory statistics"""
    total_items: int
    in_stock: int
    sold: int
    listed: int
    total_value: Decimal
    avg_purchase_price: Decimal

@dataclass
class ProductCreationRequest:
    """Request for creating a new product"""
    sku: str
    name: str
    brand_name: str
    category_name: str
    description: Optional[str] = None
    retail_price: Optional[Decimal] = None
    release_date: Optional[datetime] = None

@dataclass
class InventoryItemRequest:
    """Request for adding inventory item"""
    product_id: UUID
    size_value: str
    size_region: str
    quantity: int
    purchase_price: Optional[Decimal] = None
    purchase_date: Optional[datetime] = None
    supplier: Optional[str] = None

class InventoryService:
    """Domain service for inventory operations"""
    
    def __init__(self):
        self.logger = logger.bind(service="inventory")
    
    async def get_inventory_overview(self) -> InventoryStats:
        """Get overall inventory statistics"""
        async with get_db_session() as db:
            inventory_repo = BaseRepository(InventoryItem, db)
            
            # Get all inventory items
            all_items = await inventory_repo.get_all()
            
            total_items = len(all_items)
            in_stock = len([item for item in all_items if item.status == 'in_stock'])
            sold = len([item for item in all_items if item.status == 'sold'])
            listed = len([item for item in all_items if 'listed' in item.status])
            
            # Calculate total value
            total_value = sum(
                item.purchase_price or Decimal('0') 
                for item in all_items 
                if item.status == 'in_stock'
            )
            
            # Calculate average purchase price
            purchase_prices = [
                item.purchase_price 
                for item in all_items 
                if item.purchase_price is not None
            ]
            avg_purchase_price = (
                sum(purchase_prices) / len(purchase_prices) 
                if purchase_prices else Decimal('0')
            )
            
            self.logger.info(
                "Generated inventory overview",
                total_items=total_items,
                in_stock=in_stock,
                sold=sold,
                total_value=float(total_value)
            )
            
            return InventoryStats(
                total_items=total_items,
                in_stock=in_stock,
                sold=sold,
                listed=listed,
                total_value=total_value,
                avg_purchase_price=avg_purchase_price
            )
    
    async def create_product_with_inventory(
        self,
        product_request: ProductCreationRequest,
        inventory_requests: List[InventoryItemRequest]
    ) -> Dict[str, Any]:
        """Create a new product with initial inventory"""
        async with get_db_session() as db:
            product_repo = ProductRepository(db)
            brand_repo = BaseRepository(Brand, db)
            category_repo = BaseRepository(Category, db)
            size_repo = BaseRepository(Size, db)
            
            try:
                # Get or create brand
                brand = await brand_repo.find_one_by_field('name', product_request.brand_name)
                if not brand:
                    brand = await brand_repo.create(
                        name=product_request.brand_name,
                        slug=product_request.brand_name.lower().replace(' ', '-')
                    )
                
                # Get or create category
                category = await category_repo.find_one_by_field('name', product_request.category_name)
                if not category:
                    category = await category_repo.create(
                        name=product_request.category_name,
                        slug=product_request.category_name.lower().replace(' ', '-'),
                        path=product_request.category_name.lower()
                    )
                
                # Check if product already exists
                existing_product = await product_repo.find_by_sku(product_request.sku)
                if existing_product:
                    raise ValueError(f"Product with SKU {product_request.sku} already exists")
                
                # Create product
                product_data = {
                    'sku': product_request.sku,
                    'name': product_request.name,
                    'brand_id': brand.id,
                    'category_id': category.id,
                    'description': product_request.description,
                    'retail_price': product_request.retail_price,
                    'release_date': product_request.release_date
                }
                
                # Prepare inventory items
                inventory_items_data = []
                for inv_request in inventory_requests:
                    # Get or create size
                    size = await size_repo.find_one_by_field('value', inv_request.size_value)
                    if not size:
                        size = await size_repo.create(
                            category_id=category.id,
                            value=inv_request.size_value,
                            region=inv_request.size_region
                        )
                    
                    inventory_items_data.append({
                        'size_id': size.id,
                        'quantity': inv_request.quantity,
                        'purchase_price': inv_request.purchase_price,
                        'purchase_date': inv_request.purchase_date or datetime.now(timezone.utc),
                        'supplier': inv_request.supplier,
                        'status': 'in_stock'
                    })
                
                # Create product with inventory
                product = await product_repo.create_with_inventory(
                    product_data,
                    inventory_items_data
                )
                
                self.logger.info(
                    "Created product with inventory",
                    product_id=str(product.id),
                    sku=product.sku,
                    inventory_items=len(inventory_items_data)
                )
                
                return {
                    'product_id': str(product.id),
                    'sku': product.sku,
                    'name': product.name,
                    'brand': brand.name,
                    'category': category.name,
                    'inventory_items_created': len(inventory_items_data)
                }
                
            except Exception as e:
                self.logger.error(
                    "Failed to create product with inventory",
                    sku=product_request.sku,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
    
    async def update_inventory_status(
        self,
        inventory_id: UUID,
        new_status: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update inventory item status"""
        valid_statuses = ['in_stock', 'listed_stockx', 'listed_alias', 'sold', 'reserved', 'error']
        
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")
        
        async with get_db_session() as db:
            product_repo = ProductRepository(db)
            
            success = await product_repo.update_inventory_status(
                inventory_id, new_status, notes
            )
            
            if success:
                self.logger.info(
                    "Updated inventory status",
                    inventory_id=str(inventory_id),
                    new_status=new_status,
                    notes=notes
                )
            else:
                self.logger.warning(
                    "Failed to update inventory status - item not found",
                    inventory_id=str(inventory_id)
                )
            
            return success
    
    async def get_low_stock_alert(self, threshold: int = 5) -> List[Dict[str, Any]]:
        """Get products with low stock levels"""
        async with get_db_session() as db:
            product_repo = ProductRepository(db)
            
            low_stock_products = await product_repo.get_low_stock_products(threshold)
            
            self.logger.info(
                "Generated low stock alert",
                threshold=threshold,
                products_found=len(low_stock_products)
            )
            
            return low_stock_products
    
    async def search_products(
        self,
        search_term: Optional[str] = None,
        brand_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search products with filters"""
        async with get_db_session() as db:
            product_repo = ProductRepository(db)
            
            products = await product_repo.search(
                search_term=search_term,
                brand_filter=brand_filter,
                category_filter=category_filter,
                limit=limit,
                offset=offset
            )
            
            # Convert to dict format
            result = []
            for product in products:
                result.append({
                    'id': str(product.id),
                    'sku': product.sku,
                    'name': product.name,
                    'brand': product.brand.name if product.brand else None,
                    'category': product.category.name if product.category else None,
                    'retail_price': float(product.retail_price) if product.retail_price else None,
                    'release_date': product.release_date.isoformat() if product.release_date else None
                })
            
            self.logger.info(
                "Performed product search",
                search_term=search_term,
                brand_filter=brand_filter,
                category_filter=category_filter,
                results_found=len(result)
            )
            
            return result
    
    async def get_product_details(self, product_id: UUID) -> Optional[Dict[str, Any]]:
        """Get detailed product information with inventory"""
        async with get_db_session() as db:
            product_repo = ProductRepository(db)
            
            product = await product_repo.get_with_inventory(product_id)
            
            if not product:
                return None
            
            # Build detailed response
            inventory_items = []
            for item in product.inventory_items:
                inventory_items.append({
                    'id': str(item.id),
                    'size': item.size.value if item.size else None,
                    'region': item.size.region if item.size else None,
                    'quantity': item.quantity,
                    'status': item.status,
                    'purchase_price': float(item.purchase_price) if item.purchase_price else None,
                    'purchase_date': item.purchase_date.isoformat() if item.purchase_date else None,
                    'supplier': item.supplier,
                    'notes': item.notes
                })
            
            result = {
                'id': str(product.id),
                'sku': product.sku,
                'name': product.name,
                'description': product.description,
                'brand': product.brand.name if product.brand else None,
                'category': product.category.name if product.category else None,
                'retail_price': float(product.retail_price) if product.retail_price else None,
                'release_date': product.release_date.isoformat() if product.release_date else None,
                'inventory_items': inventory_items,
                'total_items': len(inventory_items),
                'in_stock_count': len([item for item in inventory_items if item['status'] == 'in_stock'])
            }
            
            self.logger.info(
                "Retrieved product details",
                product_id=str(product_id),
                inventory_items=len(inventory_items)
            )
            
            return result

# Singleton service instance
inventory_service = InventoryService()