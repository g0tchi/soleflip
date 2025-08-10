import asyncio
import asyncpg

async def fix_supplier_brands_defaults():
    """Fix supplier_brands table defaults"""
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        print("Fixing supplier_brands table defaults...")
        
        # Fix ID default for supplier_brands
        await conn.execute(
            "ALTER TABLE core.supplier_brands ALTER COLUMN id SET DEFAULT gen_random_uuid()"
        )
        print("Set ID default for supplier_brands")
        
        # Fix boolean defaults for supplier_brands
        await conn.execute(
            "ALTER TABLE core.supplier_brands ALTER COLUMN is_authorized_dealer SET DEFAULT false"
        )
        await conn.execute(
            "ALTER TABLE core.supplier_brands ALTER COLUMN is_brand_owned SET DEFAULT false"
        )
        await conn.execute(
            "ALTER TABLE core.supplier_brands ALTER COLUMN primary_supplier_for_brand SET DEFAULT false"
        )
        await conn.execute(
            "ALTER TABLE core.supplier_brands ALTER COLUMN exclusive_access SET DEFAULT false"
        )
        await conn.execute(
            "ALTER TABLE core.supplier_brands ALTER COLUMN relationship_status SET DEFAULT 'active'"
        )
        print("Set boolean and status defaults for supplier_brands")
        
        # Now test the complete supplier creation
        print("\nTesting complete supplier + relationship creation...")
        
        # Create a test supplier
        test_supplier_id = await conn.fetchval(
            """INSERT INTO core.suppliers (
                name, slug, display_name, supplier_type, status
            ) VALUES (
                'test-complete', 'test-complete', 'Test Complete Supplier', 'reseller', 'active'
            ) RETURNING id"""
        )
        print(f"Created test supplier: {test_supplier_id}")
        
        # Get a brand to test with
        brand = await conn.fetchrow("SELECT id, name FROM core.brands LIMIT 1")
        
        if brand:
            # Create relationship
            relationship_id = await conn.fetchval(
                """INSERT INTO core.supplier_brands (
                    supplier_id, brand_id, is_authorized_dealer
                ) VALUES ($1, $2, false) RETURNING id""",
                test_supplier_id, brand['id']
            )
            print(f"Created relationship: {relationship_id}")
        
        # Clean up test data
        await conn.execute("DELETE FROM core.supplier_brands WHERE supplier_id = $1", test_supplier_id)
        await conn.execute("DELETE FROM core.suppliers WHERE id = $1", test_supplier_id)
        print("Cleaned up test data")
        
        print("\nSupplier system is now ready!")
        
    except Exception as e:
        print(f"Failed to fix supplier_brands defaults: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_supplier_brands_defaults())