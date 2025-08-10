import asyncio
import asyncpg

async def create_simple_suppliers():
    """Create basic supplier data to test the system"""
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        print("Creating basic suppliers...")
        
        # Insert Nike Store
        nike_id = await conn.fetchval(
            """INSERT INTO core.suppliers (
                name, slug, display_name, supplier_type, 
                city, country, return_policy_days, rating, preferred, status
            ) VALUES (
                'nike-store-munich', 'nike-store-munich', 'Nike Store München', 'brand_official',
                'München', 'Germany', 30, 4.8, true, 'active'
            ) RETURNING id"""
        )
        print(f"Created Nike Store: {nike_id}")
        
        # Insert Footlocker
        footlocker_id = await conn.fetchval(
            """INSERT INTO core.suppliers (
                name, slug, display_name, supplier_type,
                city, country, return_policy_days, rating, preferred, status
            ) VALUES (
                'footlocker-germany', 'footlocker-germany', 'Foot Locker Deutschland', 'authorized_retailer',
                'Berlin', 'Germany', 14, 4.5, true, 'active'
            ) RETURNING id"""
        )
        print(f"Created Footlocker: {footlocker_id}")
        
        # Insert StockX
        stockx_id = await conn.fetchval(
            """INSERT INTO core.suppliers (
                name, slug, display_name, supplier_type,
                city, country, return_policy_days, rating, preferred, ships_internationally, status
            ) VALUES (
                'stockx-marketplace', 'stockx-marketplace', 'StockX Marketplace', 'marketplace',
                'Detroit', 'USA', 3, 4.7, true, true, 'active'
            ) RETURNING id"""
        )
        print(f"Created StockX: {stockx_id}")
        
        # Create brand relationships if brands exist
        brands = await conn.fetch("SELECT id, name FROM core.brands WHERE name IN ('Nike', 'Adidas')")
        
        if brands:
            print("Creating brand relationships...")
            
            for brand in brands:
                if brand['name'] == 'Nike':
                    # Nike Store -> Nike Brand (brand owned)
                    await conn.execute(
                        """INSERT INTO core.supplier_brands (
                            supplier_id, brand_id, is_authorized_dealer, is_brand_owned
                        ) VALUES ($1, $2, true, true)""",
                        nike_id, brand['id']
                    )
                    print(f"  Nike Store <-> Nike Brand")
                    
                    # Footlocker -> Nike (authorized dealer)
                    await conn.execute(
                        """INSERT INTO core.supplier_brands (
                            supplier_id, brand_id, is_authorized_dealer, is_brand_owned
                        ) VALUES ($1, $2, true, false)""",
                        footlocker_id, brand['id']
                    )
                    print(f"  Footlocker <-> Nike Brand")
        
        # Show summary
        supplier_count = await conn.fetchval("SELECT COUNT(*) FROM core.suppliers")
        relationship_count = await conn.fetchval("SELECT COUNT(*) FROM core.supplier_brands")
        
        print(f"\n✅ Created {supplier_count} suppliers with {relationship_count} relationships")
        
        # Show all suppliers
        suppliers = await conn.fetch(
            "SELECT id, display_name, supplier_type, city, country, rating FROM core.suppliers"
        )
        
        print("\nSuppliers in database:")
        for supplier in suppliers:
            print(f"  - {supplier['display_name']} ({supplier['supplier_type']}) - {supplier['city']}, {supplier['country']} - Rating: {supplier['rating']}")
        
    except Exception as e:
        print(f"❌ Failed to create suppliers: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_simple_suppliers())