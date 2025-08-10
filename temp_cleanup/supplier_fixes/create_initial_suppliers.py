import asyncio
import asyncpg

async def create_initial_suppliers():
    """Create initial supplier data with comprehensive examples"""
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        print("Creating initial suppliers...")
        
        # Insert example suppliers
        suppliers = [
            # Brand Official Stores
            {
                'name': 'nike-store-munich',
                'slug': 'nike-store-munich', 
                'display_name': 'Nike Store München',
                'supplier_type': 'brand_official',
                'business_size': 'enterprise',
                'contact_person': 'Store Manager',
                'email': 'muenchen@nike.com',
                'phone': '+49 89 123456',
                'website': 'https://nike.com/stores/munich',
                'city': 'München',
                'country': 'Germany',
                'return_policy_days': 30,
                'return_policy_text': 'Full refund within 30 days with original receipt',
                'accepts_exchanges': True,
                'rating': 4.8,
                'preferred': True,
                'verified': True,
                'provides_authenticity_guarantee': True,
                'average_processing_days': 1,
                'discount_percent': 15.00
            },
            
            # Authorized Retailers
            {
                'name': 'footlocker-germany',
                'slug': 'footlocker-germany',
                'display_name': 'Foot Locker Deutschland', 
                'supplier_type': 'authorized_retailer',
                'business_size': 'enterprise',
                'contact_person': 'B2B Sales Team',
                'email': 'b2b@footlocker.de',
                'phone': '+49 30 987654',
                'website': 'https://footlocker.de',
                'city': 'Berlin',
                'country': 'Germany',
                'return_policy_days': 14,
                'return_policy_text': '14 days return policy, original packaging required',
                'accepts_exchanges': True,
                'rating': 4.5,
                'preferred': True,
                'verified': True,
                'provides_authenticity_guarantee': True,
                'average_processing_days': 2,
                'discount_percent': 10.00
            },
            
            # Resellers
            {
                'name': 'sneaker-district',
                'slug': 'sneaker-district',
                'display_name': 'Sneaker District',
                'supplier_type': 'reseller',
                'business_size': 'small_business',
                'contact_person': 'Max Müller',
                'email': 'info@sneakerdistrict.de',
                'phone': '+49 40 555123', 
                'website': 'https://sneakerdistrict.de',
                'city': 'Hamburg',
                'country': 'Germany',
                'return_policy_days': 7,
                'return_policy_text': 'No returns on limited editions, 7 days for regular items',
                'accepts_exchanges': False,
                'rating': 4.2,
                'preferred': False,
                'verified': True,
                'provides_authenticity_guarantee': False,
                'average_processing_days': 3,
                'discount_percent': 5.00
            },
            
            # Private Sellers
            {
                'name': 'private-seller-hans',
                'slug': 'private-seller-hans',
                'display_name': 'Hans Schmidt (Privat)',
                'supplier_type': 'private_seller',
                'business_size': 'individual',
                'contact_person': 'Hans Schmidt',
                'email': 'hans.schmidt@email.com',
                'phone': '+49 171 1234567',
                'website': None,
                'city': 'Berlin',
                'country': 'Germany',
                'return_policy_days': 3,
                'return_policy_text': 'Private sale - limited return options',
                'accepts_exchanges': False,
                'rating': 3.8,
                'preferred': False,
                'verified': False,
                'provides_authenticity_guarantee': False,
                'average_processing_days': 1,
                'discount_percent': 0.00
            },
            
            # Marketplaces
            {
                'name': 'stockx-marketplace',
                'slug': 'stockx-marketplace',
                'display_name': 'StockX Marketplace',
                'supplier_type': 'marketplace',
                'business_size': 'enterprise',
                'contact_person': 'Support Team',
                'email': 'support@stockx.com',
                'phone': None,
                'website': 'https://stockx.com',
                'city': 'Detroit',
                'country': 'USA',
                'return_policy_days': 3,
                'return_policy_text': 'Authentication service, 3 days for issues after delivery',
                'accepts_exchanges': False,
                'rating': 4.7,
                'preferred': True,
                'verified': True,
                'provides_authenticity_guarantee': True,
                'average_processing_days': 2,
                'ships_internationally': True,
                'discount_percent': 0.00
            }
        ]
        
        # Insert suppliers
        supplier_ids = {}
        for supplier_data in suppliers:
            supplier_id = await conn.fetchval(
                """INSERT INTO core.suppliers (
                    name, slug, display_name, supplier_type, business_size,
                    contact_person, email, phone, website, city, country,
                    return_policy_days, return_policy_text, accepts_exchanges,
                    rating, preferred, verified, provides_authenticity_guarantee,
                    average_processing_days, discount_percent, ships_internationally
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
                ) RETURNING id""",
                supplier_data['name'], supplier_data['slug'], supplier_data['display_name'],
                supplier_data['supplier_type'], supplier_data['business_size'],
                supplier_data['contact_person'], supplier_data['email'], supplier_data['phone'],
                supplier_data['website'], supplier_data['city'], supplier_data['country'],
                supplier_data['return_policy_days'], supplier_data['return_policy_text'],
                supplier_data['accepts_exchanges'], supplier_data['rating'],
                supplier_data['preferred'], supplier_data['verified'],
                supplier_data['provides_authenticity_guarantee'],
                supplier_data['average_processing_days'], supplier_data['discount_percent'],
                supplier_data.get('ships_internationally', False)
            )
            supplier_ids[supplier_data['name']] = supplier_id
            print(f"Created supplier: {supplier_data['display_name']}")
        
        # Create supplier-brand relationships
        print("\nCreating supplier-brand relationships...")
        
        # Get brand IDs
        brands = await conn.fetch("SELECT id, name FROM core.brands")
        brand_lookup = {brand['name']: brand['id'] for brand in brands}
        
        relationships = [
            # Nike Store -> Nike Brand (brand owned)
            {
                'supplier': 'nike-store-munich',
                'brand': 'Nike',
                'is_authorized_dealer': True,
                'is_brand_owned': True,
                'primary_supplier_for_brand': True,
                'brand_specific_discount': 15.00,
                'exclusive_access': True
            },
            
            # Footlocker -> Multiple brands  
            {
                'supplier': 'footlocker-germany',
                'brand': 'Nike',
                'is_authorized_dealer': True,
                'is_brand_owned': False,
                'primary_supplier_for_brand': False,
                'brand_specific_discount': 10.00,
                'exclusive_access': False
            },
            {
                'supplier': 'footlocker-germany', 
                'brand': 'Adidas',
                'is_authorized_dealer': True,
                'is_brand_owned': False,
                'primary_supplier_for_brand': False,
                'brand_specific_discount': 10.00,
                'exclusive_access': False
            },
            
            # Sneaker District -> Nike, Adidas
            {
                'supplier': 'sneaker-district',
                'brand': 'Nike',
                'is_authorized_dealer': False,
                'is_brand_owned': False,
                'primary_supplier_for_brand': False,
                'brand_specific_discount': 5.00,
                'exclusive_access': False
            },
            {
                'supplier': 'sneaker-district',
                'brand': 'Adidas', 
                'is_authorized_dealer': False,
                'is_brand_owned': False,
                'primary_supplier_for_brand': False,
                'brand_specific_discount': 5.00,
                'exclusive_access': False
            }
        ]
        
        for rel in relationships:
            if rel['brand'] in brand_lookup and rel['supplier'] in supplier_ids:
                await conn.execute(
                    """INSERT INTO core.supplier_brands (
                        supplier_id, brand_id, is_authorized_dealer, is_brand_owned,
                        primary_supplier_for_brand, brand_specific_discount, exclusive_access
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                    supplier_ids[rel['supplier']], brand_lookup[rel['brand']],
                    rel['is_authorized_dealer'], rel['is_brand_owned'],
                    rel['primary_supplier_for_brand'], rel['brand_specific_discount'],
                    rel['exclusive_access']
                )
                print(f"  {rel['supplier']} <-> {rel['brand']}")
        
        # Show summary
        supplier_count = await conn.fetchval("SELECT COUNT(*) FROM core.suppliers")
        relationship_count = await conn.fetchval("SELECT COUNT(*) FROM core.supplier_brands")
        
        print(f"\n[SUCCESS] Created {supplier_count} suppliers with {relationship_count} brand relationships")
        
    except Exception as e:
        print(f"[ERROR] Failed to create suppliers: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_initial_suppliers())