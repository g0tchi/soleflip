"""
Model factories for testing using Factory Boy
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import factory
from factory import LazyAttribute, Sequence, SubFactory

from shared.database.models import (
    Brand,
    Category,
    ImportBatch,
    ImportRecord,
    InventoryItem,
    Platform,
    Product,
    Size,
    Supplier,
    Transaction,
)
from shared.types.domain_types import (
    BusinessSize,
    ImportSourceType,
    ImportStatus,
    InventoryStatus,
    PlatformType,
    ProductStatus,
    SizeRegion,
    SupplierStatus,
    SupplierType,
    TransactionStatus,
)


class BrandFactory(factory.Factory):
    """Factory for Brand model"""

    class Meta:
        model = Brand

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Brand {n}")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class CategoryFactory(factory.Factory):
    """Factory for Category model"""

    class Meta:
        model = Category

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    path = factory.LazyAttribute(lambda obj: obj.name.lower())
    parent_id = None
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class SizeFactory(factory.Factory):
    """Factory for Size model"""

    class Meta:
        model = Size

    id = factory.LazyFunction(uuid.uuid4)
    value = factory.Sequence(lambda n: f"{n + 8}")
    standardized_value = factory.LazyAttribute(lambda obj: Decimal(obj.value))
    region = factory.Iterator([SizeRegion.US, SizeRegion.EU, SizeRegion.UK])
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class ProductFactory(factory.Factory):
    """Factory for Product model"""

    class Meta:
        model = Product

    id = factory.LazyFunction(uuid.uuid4)
    sku = factory.Sequence(lambda n: f"PROD-{n:04d}")
    name = factory.Sequence(lambda n: f"Test Product {n}")
    description = factory.Faker("text", max_nb_chars=200)
    retail_price = factory.LazyFunction(
        lambda: Decimal(str(factory.Faker("random_int", min=50, max=500).generate()))
    )
    avg_resale_price = factory.LazyAttribute(
        lambda obj: obj.retail_price * Decimal("1.2") if obj.retail_price else None
    )
    release_date = factory.Faker("date_time_this_year", tzinfo=timezone.utc)
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    # Foreign keys
    brand = factory.SubFactory(BrandFactory)
    category = factory.SubFactory(CategoryFactory)


class SupplierFactory(factory.Factory):
    """Factory for Supplier model"""

    class Meta:
        model = Supplier

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Supplier {n}")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    display_name = factory.LazyAttribute(lambda obj: f"{obj.name} Corp")
    supplier_type = factory.Iterator(
        [
            SupplierType.RETAILER,
            SupplierType.WHOLESALER,
            SupplierType.MANUFACTURER,
            SupplierType.INDIVIDUAL,
        ]
    )
    business_size = factory.Iterator([BusinessSize.SMALL, BusinessSize.MEDIUM, BusinessSize.LARGE])

    # Contact information
    contact_person = factory.Faker("name")
    email = factory.Faker("email")
    phone = factory.Faker("phone_number")
    website = factory.Faker("url")

    # Address
    address_line1 = factory.Faker("street_address")
    city = factory.Faker("city")
    state_province = factory.Faker("state")
    postal_code = factory.Faker("postcode")
    country = "Germany"

    # Business details
    payment_terms = "Net 30"
    return_policy_days = factory.Faker("random_int", min=7, max=30)
    accepts_exchanges = True
    minimum_order_amount = factory.LazyFunction(lambda: Decimal("100.00"))

    # Status and ratings
    status = SupplierStatus.ACTIVE
    preferred = False
    verified = True
    rating = factory.LazyFunction(
        lambda: Decimal(str(factory.Faker("random_int", min=3, max=5).generate()))
    )

    # Statistics
    total_orders_count = factory.Faker("random_int", min=0, max=100)
    total_order_value = factory.LazyFunction(
        lambda: Decimal(str(factory.Faker("random_int", min=1000, max=50000).generate()))
    )

    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class InventoryItemFactory(factory.Factory):
    """Factory for InventoryItem model"""

    class Meta:
        model = InventoryItem

    id = factory.LazyFunction(uuid.uuid4)
    quantity = factory.Faker("random_int", min=1, max=10)
    purchase_price = factory.LazyFunction(
        lambda: Decimal(str(factory.Faker("random_int", min=100, max=400).generate()))
    )
    purchase_date = factory.Faker("date_time_this_year", tzinfo=timezone.utc)
    supplier = factory.Faker("company")
    status = factory.Iterator(
        [
            InventoryStatus.IN_STOCK,
            InventoryStatus.LISTED_STOCKX,
            InventoryStatus.SOLD,
            InventoryStatus.RESERVED,
        ]
    )
    notes = factory.Faker("text", max_nb_chars=100)
    external_ids = factory.LazyFunction(lambda: {"stockx": str(uuid.uuid4())})
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    # Foreign keys
    product = factory.SubFactory(ProductFactory)
    size = factory.SubFactory(SizeFactory)
    supplier_obj = factory.SubFactory(SupplierFactory)


class PlatformFactory(factory.Factory):
    """Factory for Platform model"""

    class Meta:
        model = Platform

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Platform {n}")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    fee_percentage = factory.LazyFunction(lambda: Decimal("8.5"))
    supports_fees = True
    active = True
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class TransactionFactory(factory.Factory):
    """Factory for Transaction model"""

    class Meta:
        model = Transaction

    id = factory.LazyFunction(uuid.uuid4)
    transaction_date = factory.Faker("date_time_this_year", tzinfo=timezone.utc)
    sale_price = factory.LazyFunction(
        lambda: Decimal(str(factory.Faker("random_int", min=200, max=800).generate()))
    )
    platform_fee = factory.LazyAttribute(
        lambda obj: obj.sale_price * Decimal("0.085") if obj.sale_price else Decimal("0")
    )
    shipping_cost = factory.LazyFunction(
        lambda: Decimal(str(factory.Faker("random_int", min=10, max=50).generate()))
    )
    net_profit = factory.LazyAttribute(
        lambda obj: obj.sale_price - obj.platform_fee - obj.shipping_cost
    )
    status = factory.Iterator(
        [TransactionStatus.PENDING, TransactionStatus.COMPLETED, TransactionStatus.CANCELLED]
    )
    external_id = factory.LazyFunction(lambda: f"EXT-{uuid.uuid4().hex[:8]}")
    buyer_destination_country = factory.Faker("country")
    buyer_destination_city = factory.Faker("city")
    notes = factory.Faker("text", max_nb_chars=100)
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    # Foreign keys
    inventory_item = factory.SubFactory(InventoryItemFactory)
    platform = factory.SubFactory(PlatformFactory)


class ImportBatchFactory(factory.Factory):
    """Factory for ImportBatch model"""

    class Meta:
        model = ImportBatch

    id = factory.LazyFunction(uuid.uuid4)
    source_type = factory.Iterator(
        [ImportSourceType.CSV_UPLOAD, ImportSourceType.STOCKX_API, ImportSourceType.MANUAL_ENTRY]
    )
    source_file = factory.Faker("file_path", extension="csv")
    total_records = factory.Faker("random_int", min=10, max=1000)
    processed_records = factory.LazyAttribute(
        lambda obj: min(
            obj.total_records, factory.Faker("random_int", min=0, max=obj.total_records).generate()
        )
    )
    error_records = factory.LazyAttribute(lambda obj: obj.total_records - obj.processed_records)
    status = factory.Iterator(
        [ImportStatus.PENDING, ImportStatus.PROCESSING, ImportStatus.COMPLETED, ImportStatus.FAILED]
    )
    started_at = factory.Faker("date_time_this_year", tzinfo=timezone.utc)
    completed_at = factory.LazyAttribute(
        lambda obj: (
            obj.started_at + factory.Faker("time_delta", hours=1).generate()
            if obj.status == ImportStatus.COMPLETED
            else None
        )
    )
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class ImportRecordFactory(factory.Factory):
    """Factory for ImportRecord model"""

    class Meta:
        model = ImportRecord

    id = factory.LazyFunction(uuid.uuid4)
    source_data = factory.LazyFunction(
        lambda: {
            "sku": f"IMPORT-{uuid.uuid4().hex[:8]}",
            "name": factory.Faker("catch_phrase").generate(),
            "price": str(factory.Faker("random_int", min=100, max=500).generate()),
        }
    )
    processed_data = factory.LazyAttribute(lambda obj: obj.source_data)
    validation_errors = factory.LazyFunction(lambda: [])
    status = factory.Iterator([ImportStatus.PENDING, ImportStatus.COMPLETED, ImportStatus.FAILED])
    processing_started_at = factory.Faker("date_time_this_year", tzinfo=timezone.utc)
    processing_completed_at = factory.LazyAttribute(
        lambda obj: (
            obj.processing_started_at + factory.Faker("time_delta", minutes=1).generate()
            if obj.status == ImportStatus.COMPLETED
            else None
        )
    )
    error_message = None
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    # Foreign keys
    batch = factory.SubFactory(ImportBatchFactory)


# Specialized factories for testing scenarios
class CompleteProductFactory(ProductFactory):
    """Factory for product with complete data"""

    @factory.post_generation
    def inventory_items(self, create, extracted, **kwargs):
        """Create inventory items for the product"""
        if not create:
            return

        if extracted:
            # If a number was passed, create that many inventory items
            for _ in range(extracted):
                InventoryItemFactory(product=self)
        else:
            # Default: create 2 inventory items
            for _ in range(2):
                InventoryItemFactory(product=self)


class SoldProductFactory(ProductFactory):
    """Factory for product with sold inventory"""

    @factory.post_generation
    def sold_items(self, create, extracted, **kwargs):
        """Create sold inventory items"""
        if not create:
            return

        count = extracted if extracted else 1
        for _ in range(count):
            inventory_item = InventoryItemFactory(product=self, status=InventoryStatus.SOLD)
            TransactionFactory(inventory_item=inventory_item)


class StockXImportBatchFactory(ImportBatchFactory):
    """Factory for StockX import batch"""

    source_type = ImportSourceType.STOCKX_API
    source_file = None

    @factory.post_generation
    def records(self, create, extracted, **kwargs):
        """Create import records"""
        if not create:
            return

        count = extracted if extracted else 5
        for _ in range(count):
            ImportRecordFactory(batch=self)


# Factory utilities
class FactoryHelper:
    """Helper class for factory operations"""

    @staticmethod
    def create_product_with_inventory(inventory_count: int = 3):
        """Create product with specified inventory count"""
        return CompleteProductFactory(inventory_items=inventory_count)

    @staticmethod
    def create_sold_transaction():
        """Create a complete sold transaction"""
        return SoldProductFactory(sold_items=1)

    @staticmethod
    def create_import_batch_with_records(record_count: int = 10):
        """Create import batch with records"""
        return StockXImportBatchFactory(records=record_count)

    @staticmethod
    def create_test_scenario():
        """Create a complete test scenario with all related objects"""
        # Create brands and categories
        brands = [BrandFactory() for _ in range(3)]
        categories = [CategoryFactory() for _ in range(2)]

        # Create suppliers
        suppliers = [SupplierFactory() for _ in range(2)]

        # Create platforms
        platforms = [PlatformFactory() for _ in range(2)]

        # Create products with inventory
        products = []
        for brand in brands:
            for category in categories:
                product = ProductFactory(brand=brand, category=category)

                # Create inventory for each product
                for supplier in suppliers:
                    InventoryItemFactory(product=product, supplier_obj=supplier)

                products.append(product)

        # Create some transactions
        transactions = []
        for product in products[:2]:  # Only first 2 products
            for inventory_item in product.inventory_items:
                if len(transactions) < 5:  # Limit transactions
                    transaction = TransactionFactory(
                        inventory_item=inventory_item, platform=platforms[0]
                    )
                    transactions.append(transaction)

        return {
            "brands": brands,
            "categories": categories,
            "suppliers": suppliers,
            "platforms": platforms,
            "products": products,
            "transactions": transactions,
        }
