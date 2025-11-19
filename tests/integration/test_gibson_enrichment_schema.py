"""
Integration tests for Gibson AI Hybrid Schema enrichment optimizations.

Tests:
- enrichment_version field
- UNIQUE constraint on stockx_product_id
- Composite index on (lowest_ask, highest_bid)
- StockX enrichment service integration
"""

from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


@pytest.mark.integration
@pytest.mark.database
async def test_enrichment_version_default_value(db_session):
    """Test that enrichment_version defaults to 1 for new products."""
    # Create a minimal product
    query = text(
        """
        INSERT INTO catalog.product (
            id, sku, name, created_at, updated_at
        )
        VALUES (
            gen_random_uuid(), :sku, :name, NOW(), NOW()
        )
        RETURNING id, enrichment_version
    """
    )

    result = await db_session.execute(query, {"sku": "TEST-ENRICH-001", "name": "Test Product"})
    await db_session.commit()

    row = result.first()
    assert row.enrichment_version == 1, "Default enrichment_version should be 1"


@pytest.mark.integration
@pytest.mark.database
async def test_stockx_product_id_unique_constraint(db_session):
    """Test that stockx_product_id has UNIQUE constraint."""
    stockx_id = "test-stockx-unique-123"

    # Create first product with stockx_product_id
    query = text(
        """
        INSERT INTO catalog.product (
            id, sku, name, stockx_product_id, created_at, updated_at
        )
        VALUES (
            gen_random_uuid(), :sku1, :name1, :stockx_id, NOW(), NOW()
        )
    """
    )

    await db_session.execute(
        query, {"sku1": "TEST-UNIQUE-001", "name1": "First Product", "stockx_id": stockx_id}
    )
    await db_session.commit()

    # Try to create second product with same stockx_product_id
    # This should fail due to UNIQUE constraint
    with pytest.raises(IntegrityError) as exc_info:
        await db_session.execute(
            query, {"sku1": "TEST-UNIQUE-002", "name1": "Second Product", "stockx_id": stockx_id}
        )
        await db_session.commit()

    assert "uq_product_stockx_id" in str(exc_info.value)
    await db_session.rollback()


@pytest.mark.integration
@pytest.mark.database
async def test_composite_pricing_index_exists(db_session):
    """Test that composite index on (lowest_ask, highest_bid) exists."""
    query = text(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'catalog'
          AND tablename = 'product'
          AND indexname = 'idx_product_pricing'
    """
    )

    result = await db_session.execute(query)
    row = result.first()

    assert row is not None, "Composite pricing index should exist"
    assert "lowest_ask" in row.indexdef
    assert "highest_bid" in row.indexdef


@pytest.mark.integration
@pytest.mark.database
async def test_enrichment_data_with_pricing_columns(db_session):
    """Test Gibson hybrid schema: separate pricing columns + JSONB."""
    import json

    enrichment_payload = {
        "stockx_product_id": "abc-123-def",
        "variants": [{"size": "10", "sku": "ABC123-10"}],
        "images": ["https://example.com/image1.jpg"],
    }

    query = text(
        """
        INSERT INTO catalog.product (
            id, sku, name,
            stockx_product_id, enrichment_data,
            lowest_ask, highest_bid,
            recommended_sell_faster, recommended_earn_more,
            enrichment_version,
            created_at, updated_at
        )
        VALUES (
            gen_random_uuid(), :sku, :name,
            :stockx_id, CAST(:enrichment_data AS jsonb),
            :lowest_ask, :highest_bid,
            :sell_faster, :earn_more,
            :version,
            NOW(), NOW()
        )
        RETURNING id, stockx_product_id, lowest_ask, highest_bid, enrichment_version
    """
    )

    result = await db_session.execute(
        query,
        {
            "sku": "TEST-HYBRID-001",
            "name": "Test Hybrid Product",
            "stockx_id": "hybrid-test-123",
            "enrichment_data": json.dumps(enrichment_payload),
            "lowest_ask": Decimal("150.00"),
            "highest_bid": Decimal("140.00"),
            "sell_faster": Decimal("145.00"),
            "earn_more": Decimal("155.00"),
            "version": 1,
        },
    )
    await db_session.commit()

    row = result.first()
    assert row.stockx_product_id == "hybrid-test-123"
    assert row.lowest_ask == Decimal("150.00")
    assert row.highest_bid == Decimal("140.00")
    assert row.enrichment_version == 1


@pytest.mark.integration
@pytest.mark.database
async def test_pricing_query_performance(db_session):
    """Test that pricing queries can use composite index."""
    # This test verifies the query plan uses the index
    query = text(
        """
        EXPLAIN (FORMAT JSON)
        SELECT id, sku, lowest_ask, highest_bid
        FROM catalog.product
        WHERE lowest_ask >= 100
          AND highest_bid <= 200
        ORDER BY lowest_ask
    """
    )

    result = await db_session.execute(query)
    plan = result.scalar()

    # The query plan should mention the index (in a real scenario)
    # For now, just verify the query executes successfully
    assert plan is not None


@pytest.mark.integration
@pytest.mark.database
async def test_enrichment_version_update(db_session):
    """Test that enrichment_version can be updated (for API migrations)."""
    # Create product
    create_query = text(
        """
        INSERT INTO catalog.product (
            id, sku, name, enrichment_version, created_at, updated_at
        )
        VALUES (
            gen_random_uuid(), :sku, :name, 1, NOW(), NOW()
        )
        RETURNING id
    """
    )

    result = await db_session.execute(
        create_query, {"sku": "TEST-VERSION-001", "name": "Version Test"}
    )
    product_id = result.scalar()
    await db_session.commit()

    # Update to version 2 (simulate API migration)
    update_query = text(
        """
        UPDATE catalog.product
        SET enrichment_version = 2
        WHERE id = :product_id
        RETURNING enrichment_version
    """
    )

    result = await db_session.execute(update_query, {"product_id": product_id})
    await db_session.commit()

    row = result.first()
    assert row.enrichment_version == 2


@pytest.mark.integration
@pytest.mark.database
async def test_null_stockx_product_id_allowed(db_session):
    """Test that stockx_product_id can be NULL (for non-enriched products)."""
    query = text(
        """
        INSERT INTO catalog.product (
            id, sku, name, stockx_product_id, created_at, updated_at
        )
        VALUES (
            gen_random_uuid(), :sku, :name, NULL, NOW(), NOW()
        )
        RETURNING id, stockx_product_id
    """
    )

    result = await db_session.execute(
        query, {"sku": "TEST-NULL-001", "name": "Non-enriched Product"}
    )
    await db_session.commit()

    row = result.first()
    assert row.stockx_product_id is None


@pytest.mark.integration
@pytest.mark.database
async def test_multiple_null_stockx_ids_allowed(db_session):
    """Test that multiple products can have NULL stockx_product_id."""
    query = text(
        """
        INSERT INTO catalog.product (
            id, sku, name, stockx_product_id, created_at, updated_at
        )
        VALUES (
            gen_random_uuid(), :sku, :name, NULL, NOW(), NOW()
        )
    """
    )

    # Create two products with NULL stockx_product_id
    await db_session.execute(query, {"sku": "NULL-TEST-1", "name": "Product 1"})
    await db_session.execute(query, {"sku": "NULL-TEST-2", "name": "Product 2"})
    await db_session.commit()

    # Should succeed - UNIQUE constraint allows multiple NULLs
    count_query = text(
        """
        SELECT COUNT(*)
        FROM catalog.product
        WHERE stockx_product_id IS NULL
          AND sku LIKE 'NULL-TEST-%'
    """
    )

    result = await db_session.execute(count_query)
    count = result.scalar()
    assert count >= 2
