import asyncio
import asyncpg

async def fix_supplier_defaults():
    """Fix supplier table defaults"""
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        print("Fixing supplier table defaults...")
        
        # Fix ID default
        await conn.execute(
            "ALTER TABLE core.suppliers ALTER COLUMN id SET DEFAULT gen_random_uuid()"
        )
        print("✓ Set ID default to gen_random_uuid()")
        
        # Fix status default
        await conn.execute(
            "ALTER TABLE core.suppliers ALTER COLUMN status SET DEFAULT 'active'"
        )
        print("✓ Set status default to 'active'")
        
        # Fix boolean defaults
        await conn.execute(
            "ALTER TABLE core.suppliers ALTER COLUMN preferred SET DEFAULT false"
        )
        await conn.execute(
            "ALTER TABLE core.suppliers ALTER COLUMN verified SET DEFAULT false"
        )
        await conn.execute(
            "ALTER TABLE core.suppliers ALTER COLUMN ships_internationally SET DEFAULT false"
        )
        await conn.execute(
            "ALTER TABLE core.suppliers ALTER COLUMN accepts_returns_by_mail SET DEFAULT true"
        )
        await conn.execute(
            "ALTER TABLE core.suppliers ALTER COLUMN provides_authenticity_guarantee SET DEFAULT false"
        )
        await conn.execute(
            "ALTER TABLE core.suppliers ALTER COLUMN has_api SET DEFAULT false"
        )
        await conn.execute(
            "ALTER TABLE core.suppliers ALTER COLUMN accepts_exchanges SET DEFAULT true"
        )
        print("✓ Set boolean defaults")
        
        # Fix integer defaults
        await conn.execute(
            "ALTER TABLE core.suppliers ALTER COLUMN total_orders_count SET DEFAULT 0"
        )
        await conn.execute(
            "ALTER TABLE core.suppliers ALTER COLUMN total_order_value SET DEFAULT 0.00"
        )
        print("✓ Set numeric defaults")
        
        # Fix country default
        await conn.execute(
            "ALTER TABLE core.suppliers ALTER COLUMN country SET DEFAULT 'Germany'"
        )
        print("✓ Set country default")
        
        # Test insert now
        print("\nTesting insert with defaults...")
        test_id = await conn.fetchval(
            """INSERT INTO core.suppliers (
                name, slug, display_name, supplier_type
            ) VALUES (
                'test-supplier-2', 'test-supplier-2', 'Test Supplier 2', 'reseller'
            ) RETURNING id"""
        )
        print(f"✓ Test insert successful: {test_id}")
        
        # Clean up
        await conn.execute("DELETE FROM core.suppliers WHERE id = $1", test_id)
        print("✓ Test record cleaned up")
        
        print("\n🎉 Supplier table defaults fixed!")
        
    except Exception as e:
        print(f"❌ Failed to fix defaults: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_supplier_defaults())