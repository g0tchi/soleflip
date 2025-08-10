import asyncio
import asyncpg

async def verify_supplier_system():
    """Verify the supplier system is working correctly"""
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        print("=== Supplier System Verification ===")
        
        # Check suppliers
        suppliers = await conn.fetch(
            """SELECT id, name, display_name, supplier_type, city, country, 
                      return_policy_days, rating, preferred, status
               FROM core.suppliers 
               ORDER BY display_name"""
        )
        
        print(f"\\nSuppliers ({len(suppliers)}):")
        for supplier in suppliers:
            print(f"  • {supplier['display_name']} ({supplier['supplier_type']})")
            print(f"    Location: {supplier['city']}, {supplier['country']}")
            print(f"    Return Policy: {supplier['return_policy_days']} days")
            print(f"    Rating: {supplier['rating']}/5.0 | Preferred: {supplier['preferred']} | Status: {supplier['status']}")
            print()
        
        # Check supplier-brand relationships
        relationships = await conn.fetch(
            """SELECT s.display_name as supplier_name, b.name as brand_name,
                      sb.is_authorized_dealer, sb.is_brand_owned, sb.primary_supplier_for_brand,
                      sb.exclusive_access, sb.relationship_status
               FROM core.supplier_brands sb
               JOIN core.suppliers s ON sb.supplier_id = s.id
               JOIN core.brands b ON sb.brand_id = b.id
               ORDER BY s.display_name, b.name"""
        )
        
        print(f"Supplier-Brand Relationships ({len(relationships)}):")
        for rel in relationships:
            auth_status = "Authorized" if rel['is_authorized_dealer'] else "Reseller"
            owned_status = " (Brand Owned)" if rel['is_brand_owned'] else ""
            primary_status = " [PRIMARY]" if rel['primary_supplier_for_brand'] else ""
            exclusive_status = " Exclusive" if rel['exclusive_access'] else ""
            
            print(f"  • {rel['supplier_name']} <-> {rel['brand_name']}")
            print(f"    {auth_status}{owned_status}{primary_status}{exclusive_status}")
            print(f"    Status: {rel['relationship_status']}")
            print()
        
        # Check inventory integration
        inventory_with_suppliers = await conn.fetchval(
            "SELECT COUNT(*) FROM products.inventory WHERE supplier_id IS NOT NULL"
        )
        total_inventory = await conn.fetchval("SELECT COUNT(*) FROM products.inventory")
        
        print(f"Inventory Integration:")
        print(f"  • Total Inventory Items: {total_inventory}")
        print(f"  • Items with Supplier Link: {inventory_with_suppliers}")
        print(f"  • Coverage: {(inventory_with_suppliers/total_inventory*100):.1f}%")
        
        # Test advanced supplier queries
        print(f"\\nAdvanced Queries:")
        
        # Preferred suppliers
        preferred = await conn.fetchval(
            "SELECT COUNT(*) FROM core.suppliers WHERE preferred = true"
        )
        print(f"  • Preferred Suppliers: {preferred}")
        
        # Suppliers by type
        by_type = await conn.fetch(
            """SELECT supplier_type, COUNT(*) as count
               FROM core.suppliers 
               GROUP BY supplier_type 
               ORDER BY count DESC"""
        )
        print(f"  • By Type:")
        for type_info in by_type:
            print(f"    - {type_info['supplier_type']}: {type_info['count']}")
        
        # Suppliers by country
        by_country = await conn.fetch(
            """SELECT country, COUNT(*) as count
               FROM core.suppliers 
               WHERE country IS NOT NULL
               GROUP BY country 
               ORDER BY count DESC"""
        )
        print(f"  • By Country:")
        for country_info in by_country:
            print(f"    - {country_info['country']}: {country_info['count']}")
        
        # Test return policy analysis
        avg_return_days = await conn.fetchval(
            "SELECT AVG(return_policy_days) FROM core.suppliers WHERE return_policy_days IS NOT NULL"
        )
        print(f"  • Average Return Policy: {avg_return_days:.1f} days")
        
        print(f"\\nSupplier System Verification Complete!")
        print(f"Ready for:")
        print(f"   - Supplier Performance Analytics")
        print(f"   - Return Policy Management") 
        print(f"   - Brand Relationship Tracking")
        print(f"   - Geographic Supplier Analysis")
        print(f"   - Contact Management")
        
    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(verify_supplier_system())