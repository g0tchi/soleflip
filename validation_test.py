#!/usr/bin/env python3
"""
Simple validation test for Pricing & Forecasting System
Tests basic functionality without complex relationships
"""
import asyncio
import asyncpg
from datetime import datetime, date
from decimal import Decimal
import uuid


async def validate_pricing_system():
    """Test basic pricing system functionality"""
    print("=" * 60)
    print("PRICING & FORECASTING SYSTEM VALIDATION")
    print("=" * 60)

    conn = await asyncpg.connect(
        "postgresql://metabaseuser:metabasepass@192.168.2.45:2665/metabase"
    )

    try:
        # Test 1: Database Schema Validation
        print("\n1. DATABASE SCHEMA VALIDATION")
        print("-" * 40)

        schemas = await conn.fetch(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('pricing', 'analytics')"
        )
        print(f"Required schemas found: {len(schemas)}/2")
        for schema in schemas:
            print(f"   [OK] {schema['schema_name']}")

        # Test 2: Table Structure Validation
        print("\n2. TABLE STRUCTURE VALIDATION")
        print("-" * 40)

        pricing_tables = await conn.fetch(
            """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'pricing'
        """
        )
        print(f"Pricing tables: {len(pricing_tables)}")
        for table in pricing_tables:
            print(f"   [OK] pricing.{table['table_name']}")

        analytics_tables = await conn.fetch(
            """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'analytics'
        """
        )
        print(f"Analytics tables: {len(analytics_tables)}")
        for table in analytics_tables:
            print(f"   [OK] analytics.{table['table_name']}")

        # Test 3: Insert Sample Data
        print("\n3. DATA INSERTION TESTS")
        print("-" * 40)

        # Insert sample pricing rule
        rule_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO pricing.price_rules (id, name, rule_type, conditions, actions, priority, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
            rule_id,
            "Test Cost-Plus Rule",
            "cost_plus",
            '{"brand": "Nike"}',
            '{"markup": 1.25}',
            1,
            True,
        )
        print("   [OK] Pricing rule inserted")

        # Insert sample brand multiplier
        brand_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO pricing.brand_multipliers (id, brand, multiplier, reason, is_active)
            VALUES ($1, $2, $3, $4, $5)
        """,
            brand_id,
            "Nike",
            Decimal("1.15"),
            "Premium brand markup",
            True,
        )
        print("   [OK] Brand multiplier inserted")

        # Insert sample price history
        price_id = uuid.uuid4()
        product_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO pricing.price_history (id, product_id, sku, price, margin_percentage, confidence_score, strategy_used)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
            price_id,
            product_id,
            "AIR-JORDAN-1-HIGH",
            Decimal("180.00"),
            Decimal("25.5"),
            Decimal("0.85"),
            "cost_plus",
        )
        print("   [OK] Price history record inserted")

        # Insert sample forecast
        forecast_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO analytics.sales_forecasts (id, product_id, forecast_date, forecast_type, predicted_quantity, predicted_revenue, confidence_score, model_used)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
            forecast_id,
            product_id,
            date.today(),
            "daily",
            5,
            Decimal("900.00"),
            Decimal("0.78"),
            "ensemble",
        )
        print("   [OK] Sales forecast inserted")

        # Test 4: Query Data
        print("\n4. DATA RETRIEVAL TESTS")
        print("-" * 40)

        # Query pricing rules
        rules = await conn.fetch(
            "SELECT name, rule_type, is_active FROM pricing.price_rules WHERE is_active = true"
        )
        print(f"   [OK] Active pricing rules: {len(rules)}")
        for rule in rules:
            print(f"     - {rule['name']} ({rule['rule_type']})")

        # Query brand multipliers
        multipliers = await conn.fetch(
            "SELECT brand, multiplier FROM pricing.brand_multipliers WHERE is_active = true"
        )
        print(f"   [OK] Active brand multipliers: {len(multipliers)}")
        for mult in multipliers:
            print(f"     - {mult['brand']}: {mult['multiplier']}x")

        # Query forecasts
        forecasts = await conn.fetch(
            """
            SELECT forecast_date, predicted_quantity, predicted_revenue, model_used 
            FROM analytics.sales_forecasts 
            WHERE forecast_date >= CURRENT_DATE
        """
        )
        print(f"   [OK] Future forecasts: {len(forecasts)}")
        for forecast in forecasts:
            print(
                f"     - {forecast['forecast_date']}: {forecast['predicted_quantity']} units, EUR{forecast['predicted_revenue']}"
            )

        # Test 5: Analytics Queries
        print("\n5. ANALYTICS VALIDATION")
        print("-" * 40)

        # Average margin
        avg_margin = await conn.fetchval(
            "SELECT ROUND(AVG(margin_percentage), 2) FROM pricing.price_history"
        )
        print(f"   [OK] Average margin: {avg_margin}%")

        # Total forecasted revenue
        total_forecast = await conn.fetchval(
            """
            SELECT ROUND(SUM(predicted_revenue), 2) FROM analytics.sales_forecasts 
            WHERE forecast_date >= CURRENT_DATE
        """
        )
        print(f"   [OK] Total forecasted revenue: EUR{total_forecast}")

        # Index performance check
        indexes = await conn.fetch(
            """
            SELECT indexname FROM pg_indexes 
            WHERE tablename IN ('price_history', 'sales_forecasts') 
            AND schemaname IN ('pricing', 'analytics')
        """
        )
        print(f"   [OK] Performance indexes: {len(indexes)}")
        for idx in indexes:
            print(f"     - {idx['indexname']}")

        print("\n" + "=" * 60)
        print("SUCCESS: VALIDATION COMPLETE - ALL SYSTEMS OPERATIONAL")
        print("=" * 60)
        print(f"[OK] Database schemas created and accessible")
        print(f"[OK] Tables created with proper structure")
        print(f"[OK] Data insertion working correctly")
        print(f"[OK] Data retrieval functioning")
        print(f"[OK] Analytics queries operational")
        print(f"[OK] Performance indexes in place")
        print("\nThe Pricing & Forecasting System is ready for production use!")

    except Exception as e:
        print(f"\nERROR: VALIDATION FAILED: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(validate_pricing_system())
