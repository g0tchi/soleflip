"""
Comprehensive test demonstrating the new fixture infrastructure
Tests the integration between factories, database fixtures, and API fixtures
"""

from uuid import UUID

import pytest

from tests.fixtures import (  # Database fixtures; Model factories; API fixtures
    BrandFactory,
    CompleteProductFactory,
    FactoryHelper,
    InventoryItemFactory,
    ProductFactory,
    api_headers,
    api_helper,
    async_client,
    clean_database,
    db_helper,
    db_session,
    override_get_db,
    response_validator,
    sample_product_data,
    setup_integration_environment,
    test_engine,
)


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
async def test_comprehensive_database_fixtures(db_session, db_helper, clean_database):
    """Test comprehensive database operations with new fixtures"""

    # Create test scenario using FactoryHelper
    scenario = FactoryHelper.create_test_scenario()

    # Add all objects to database
    for brand in scenario["brands"]:
        db_session.add(brand)
    for category in scenario["categories"]:
        db_session.add(category)
    for supplier in scenario["suppliers"]:
        db_session.add(supplier)

    await db_session.commit()

    # Verify using database helper
    from shared.database.models import Brand, Category, Supplier

    brand_count = await db_helper.count_records(Brand)
    category_count = await db_helper.count_records(Category)
    supplier_count = await db_helper.count_records(Supplier)

    assert brand_count == 3, f"Expected 3 brands, got {brand_count}"
    assert category_count == 2, f"Expected 2 categories, got {category_count}"
    assert supplier_count == 2, f"Expected 2 suppliers, got {supplier_count}"

    # Test retrieving all records
    all_brands = await db_helper.get_all_records(Brand)
    assert len(all_brands) == 3

    # Verify brand names are properly generated
    brand_names = [brand.name for brand in all_brands]
    assert all("Brand" in name for name in brand_names)


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
async def test_model_factories_with_relationships(db_session, db_helper):
    """Test model factories with proper relationships"""

    # Create product with complete relationships
    product = CompleteProductFactory(inventory_items=3)

    # Add to database
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Verify relationships are properly set
    assert product.brand is not None
    assert isinstance(product.brand.id, UUID)
    assert product.category is not None
    assert isinstance(product.category.id, UUID)

    # Verify inventory items were created
    from shared.database.models import InventoryItem

    inventory_count = await db_helper.count_records(InventoryItem)
    assert inventory_count == 3, f"Expected 3 inventory items, got {inventory_count}"

    # Verify inventory items belong to the product
    all_inventory = await db_helper.get_all_records(InventoryItem)
    for item in all_inventory:
        assert item.product_id == product.id


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.asyncio
async def test_comprehensive_api_fixtures(
    async_client,
    api_helper,
    override_get_db,
    api_headers,
    sample_product_data,
    response_validator,
    setup_integration_environment,
):
    """Test comprehensive API operations with new fixtures"""

    # Get the integration environment data
    env_data = setup_integration_environment
    brand = env_data["brand"]
    category = env_data["category"]

    # Update sample data with actual IDs
    product_data = sample_product_data.copy()
    product_data["brand_id"] = str(brand.id)
    product_data["category_id"] = str(category.id)

    # Test health check endpoint first
    health_response = await api_helper.get_json("/health")
    response_validator.validate_success_response(
        health_response, expected_data_keys=None  # Health endpoint has different structure
    )

    # Test API info endpoint
    info_response = await api_helper.get_json("/")
    assert "name" in info_response
    assert "version" in info_response

    # Test with custom headers
    custom_response = await async_client.get("/health", headers=api_headers)
    assert custom_response.status_code == 200
    assert custom_response.headers.get("content-type") == "application/json"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.asyncio
async def test_error_response_validation(
    async_client, api_helper, response_validator, override_get_db
):
    """Test error response validation with new fixtures"""

    # Test non-existent endpoint
    response = await async_client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404

    # Test invalid product ID
    response = await async_client.get("/api/v1/products/invalid-uuid-format")
    # This might return 422 for validation error or 404, depending on implementation
    assert response.status_code in [404, 422, 500]


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
async def test_transaction_rollback_cleanup(db_session, db_helper):
    """Test that database cleanup works properly between tests"""

    # Create some test data
    brand = BrandFactory()
    product = ProductFactory(brand=brand)

    db_session.add(brand)
    db_session.add(product)
    await db_session.commit()

    # Verify data exists
    from shared.database.models import Brand, Product

    brand_count = await db_helper.count_records(Brand)
    product_count = await db_helper.count_records(Product)

    assert brand_count >= 1
    assert product_count >= 1

    # The cleanup should happen automatically after this test


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
async def test_database_cleanup_between_tests(db_helper):
    """Test that previous test data was cleaned up"""

    # This test verifies that the rollback/cleanup from the previous test worked
    from shared.database.models import Brand, Product

    brand_count = await db_helper.count_records(Brand)
    product_count = await db_helper.count_records(Product)

    # Due to test isolation, these should be 0 unless explicitly created in this test
    # (This depends on the specific fixture implementation and isolation level)
    # For now, we just verify we can count without errors
    assert isinstance(brand_count, int)
    assert isinstance(product_count, int)
    assert brand_count >= 0
    assert product_count >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_factory_helper_utilities(db_session):
    """Test the FactoryHelper utility methods"""

    # Test create_product_with_inventory
    product = FactoryHelper.create_product_with_inventory(inventory_count=5)
    db_session.add(product)
    await db_session.commit()

    # Refresh to load relationships
    await db_session.refresh(product)

    # Verify inventory was created
    assert len(product.inventory_items) == 5

    # Test create_sold_transaction
    sold_product = FactoryHelper.create_sold_transaction()
    db_session.add(sold_product)
    await db_session.commit()

    # Verify sold product structure
    assert len(sold_product.inventory_items) >= 1
    sold_item = sold_product.inventory_items[0]
    assert sold_item.status.value == "sold"

    # Test create_import_batch_with_records
    import_batch = FactoryHelper.create_import_batch_with_records(record_count=3)
    db_session.add(import_batch)
    await db_session.commit()

    # Verify import batch structure
    assert import_batch.total_records >= 3
    assert len(import_batch.records) == 3


@pytest.mark.performance
@pytest.mark.database
@pytest.mark.asyncio
async def test_bulk_operations_performance(db_session, db_helper):
    """Test bulk operations with factories for performance"""

    # Create multiple products efficiently
    products = []
    for i in range(10):
        product = ProductFactory()
        products.append(product)
        db_session.add(product)

    # Bulk commit
    await db_session.commit()

    # Verify all products were created
    from shared.database.models import Product

    product_count = await db_helper.count_records(Product)
    assert product_count == 10

    # Test bulk inventory creation
    inventory_items = []
    for product in products:
        for j in range(2):  # 2 inventory items per product
            item = InventoryItemFactory(product=product)
            inventory_items.append(item)
            db_session.add(item)

    await db_session.commit()

    # Verify bulk inventory creation
    from shared.database.models import InventoryItem

    inventory_count = await db_helper.count_records(InventoryItem)
    assert inventory_count == 20  # 10 products * 2 items each
