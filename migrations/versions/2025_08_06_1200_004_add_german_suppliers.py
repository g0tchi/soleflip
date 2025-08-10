"""Add German sneaker suppliers

Revision ID: 004_add_german_suppliers
Revises: 003_add_suppliers  
Create Date: 2025-08-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_german_suppliers'
down_revision = '003_add_suppliers'
branch_labels = None
depends_on = None

def upgrade():
    """Add common German sneaker suppliers"""
    
    # Insert German sneaker suppliers
    suppliers_data = [
        {
            'id': 'gen_random_uuid()',
            'name': 'Solebox',
            'slug': 'solebox',
            'display_name': 'Solebox Berlin',
            'supplier_type': 'authorized_retailer',
            'business_size': 'enterprise',
            'email': 'info@solebox.com',
            'website': 'https://www.solebox.com',
            'city': 'Berlin',
            'country': 'Germany',
            'return_policy_days': 14,
            'accepts_exchanges': True,
            'rating': 4.5,
            'reliability_score': 9,
            'quality_score': 9,
            'preferred': True,
            'verified': True,
            'ships_internationally': True,
            'provides_authenticity_guarantee': True,
            'notes': 'Premium sneaker store with exclusive releases'
        },
        {
            'id': 'gen_random_uuid()',
            'name': 'Overkill',
            'slug': 'overkill',
            'display_name': 'Overkill Berlin',
            'supplier_type': 'authorized_retailer',
            'business_size': 'enterprise',
            'email': 'info@overkillshop.com',
            'website': 'https://www.overkillshop.com',
            'city': 'Berlin',
            'country': 'Germany',
            'return_policy_days': 14,
            'accepts_exchanges': True,
            'rating': 4.6,
            'reliability_score': 9,
            'quality_score': 9,
            'preferred': True,
            'verified': True,
            'ships_internationally': True,
            'provides_authenticity_guarantee': True,
            'notes': 'Established Berlin sneaker boutique with limited releases'
        },
        {
            'id': 'gen_random_uuid()',
            'name': 'BSTN',
            'slug': 'bstn',
            'display_name': 'BSTN Store',
            'supplier_type': 'authorized_retailer',
            'business_size': 'enterprise',
            'email': 'info@bstn.com',
            'website': 'https://www.bstn.com',
            'city': 'Munich',
            'country': 'Germany',
            'return_policy_days': 14,
            'accepts_exchanges': True,
            'rating': 4.4,
            'reliability_score': 8,
            'quality_score': 8,
            'preferred': True,
            'verified': True,
            'ships_internationally': True,
            'provides_authenticity_guarantee': True,
            'notes': 'Munich-based streetwear and sneaker retailer'
        },
        {
            'id': 'gen_random_uuid()',
            'name': 'Afew Store',
            'slug': 'afew-store',
            'display_name': 'AFEW Store',
            'supplier_type': 'authorized_retailer',
            'business_size': 'small_business',
            'email': 'info@afew-store.com',
            'website': 'https://www.afew-store.com',
            'city': 'Düsseldorf',
            'country': 'Germany',
            'return_policy_days': 14,
            'accepts_exchanges': True,
            'rating': 4.3,
            'reliability_score': 8,
            'quality_score': 8,
            'preferred': True,
            'verified': True,
            'ships_internationally': True,
            'provides_authenticity_guarantee': True,
            'notes': 'Düsseldorf sneaker boutique with curated selection'
        },
        {
            'id': 'gen_random_uuid()',
            'name': 'Snipes',
            'slug': 'snipes',
            'display_name': 'SNIPES',
            'supplier_type': 'authorized_retailer',
            'business_size': 'enterprise',
            'email': 'service@snipes.com',
            'website': 'https://www.snipes.com',
            'city': 'Cologne',
            'country': 'Germany',
            'return_policy_days': 30,
            'accepts_exchanges': True,
            'rating': 4.2,
            'reliability_score': 8,
            'quality_score': 7,
            'preferred': False,
            'verified': True,
            'ships_internationally': True,
            'provides_authenticity_guarantee': True,
            'notes': 'Large European sneaker chain'
        },
        {
            'id': 'gen_random_uuid()',
            'name': 'Footlocker DE',
            'slug': 'footlocker-de',
            'display_name': 'Foot Locker Germany',
            'supplier_type': 'authorized_retailer',
            'business_size': 'enterprise',
            'email': 'kundenservice@footlocker.de',
            'website': 'https://www.footlocker.de',
            'city': 'Düsseldorf',
            'country': 'Germany',
            'return_policy_days': 30,
            'accepts_exchanges': True,
            'rating': 4.1,
            'reliability_score': 8,
            'quality_score': 7,
            'preferred': False,
            'verified': True,
            'ships_internationally': True,
            'provides_authenticity_guarantee': True,
            'notes': 'Major international sneaker retailer'
        },
        {
            'id': 'gen_random_uuid()',
            'name': 'JD Sports DE',
            'slug': 'jd-sports-de',
            'display_name': 'JD Sports Germany',
            'supplier_type': 'authorized_retailer',
            'business_size': 'enterprise',
            'email': 'kundenservice@jdsports.de',
            'website': 'https://www.jdsports.de',
            'city': 'Düsseldorf',
            'country': 'Germany',
            'return_policy_days': 30,
            'accepts_exchanges': True,
            'rating': 4.0,
            'reliability_score': 7,
            'quality_score': 7,
            'preferred': False,
            'verified': True,
            'ships_internationally': True,
            'provides_authenticity_guarantee': True,
            'notes': 'UK-based sports retailer with German operations'
        },
        {
            'id': 'gen_random_uuid()',
            'name': 'Zalando',
            'slug': 'zalando',
            'display_name': 'Zalando',
            'supplier_type': 'authorized_retailer',
            'business_size': 'enterprise',
            'email': 'service@zalando.de',
            'website': 'https://www.zalando.de',
            'city': 'Berlin',
            'country': 'Germany',
            'return_policy_days': 100,
            'accepts_exchanges': True,
            'rating': 4.2,
            'reliability_score': 8,
            'quality_score': 7,
            'preferred': False,
            'verified': True,
            'ships_internationally': True,
            'provides_authenticity_guarantee': True,
            'notes': 'Major European fashion and sneaker e-commerce platform'
        },
        {
            'id': 'gen_random_uuid()',
            'name': 'About You',
            'slug': 'about-you',
            'display_name': 'About You',
            'supplier_type': 'authorized_retailer',
            'business_size': 'enterprise',
            'email': 'service@aboutyou.de',
            'website': 'https://www.aboutyou.de',
            'city': 'Hamburg',
            'country': 'Germany',
            'return_policy_days': 30,
            'accepts_exchanges': True,
            'rating': 4.1,
            'reliability_score': 7,
            'quality_score': 7,
            'preferred': False,
            'verified': True,
            'ships_internationally': True,
            'provides_authenticity_guarantee': False,
            'notes': 'Hamburg-based fashion e-commerce with sneaker selection'
        },
        {
            'id': 'gen_random_uuid()',
            'name': 'Size?',
            'slug': 'size',
            'display_name': 'size?',
            'supplier_type': 'authorized_retailer',
            'business_size': 'enterprise',
            'email': 'customercare@size.de',
            'website': 'https://www.size.de',
            'city': 'Düsseldorf',
            'country': 'Germany',
            'return_policy_days': 28,
            'accepts_exchanges': True,
            'rating': 4.3,
            'reliability_score': 8,
            'quality_score': 8,
            'preferred': True,
            'verified': True,
            'ships_internationally': True,
            'provides_authenticity_guarantee': True,
            'notes': 'UK premium sneaker retailer with German operations'
        }
    ]
    
    # Build INSERT statement
    insert_sql = """
    INSERT INTO core.suppliers (
        id, name, slug, display_name, supplier_type, business_size, email, website, 
        city, country, return_policy_days, accepts_exchanges, rating, reliability_score, 
        quality_score, preferred, verified, ships_internationally, provides_authenticity_guarantee, 
        notes, status, created_at, updated_at
    ) VALUES 
    """
    
    values = []
    for supplier in suppliers_data:
        values.append(f"""(
            {supplier['id']}, 
            '{supplier['name']}', 
            '{supplier['slug']}', 
            '{supplier['display_name']}', 
            '{supplier['supplier_type']}', 
            '{supplier['business_size']}', 
            '{supplier['email']}', 
            '{supplier['website']}', 
            '{supplier['city']}', 
            '{supplier['country']}', 
            {supplier['return_policy_days']}, 
            {supplier['accepts_exchanges']}, 
            {supplier['rating']}, 
            {supplier['reliability_score']}, 
            {supplier['quality_score']}, 
            {supplier['preferred']}, 
            {supplier['verified']}, 
            {supplier['ships_internationally']}, 
            {supplier['provides_authenticity_guarantee']}, 
            '{supplier['notes']}', 
            'active',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )""")
    
    op.execute(insert_sql + ',\n'.join(values))


def downgrade():
    """Remove German sneaker suppliers"""
    
    suppliers_to_remove = [
        'solebox', 'overkill', 'bstn', 'afew-store', 'snipes',
        'footlocker-de', 'jd-sports-de', 'zalando', 'about-you', 'size'
    ]
    
    for slug in suppliers_to_remove:
        op.execute(f"DELETE FROM core.suppliers WHERE slug = '{slug}'")