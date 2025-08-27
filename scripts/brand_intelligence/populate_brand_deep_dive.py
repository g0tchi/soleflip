import asyncio
import asyncpg
from datetime import date

async def populate_brand_deep_dive():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    print("=== POPULATING BRAND DEEP DIVE DATA ===")
    
    # Comprehensive brand information
    brand_deep_data = {
        'Nike': {
            'founder_name': 'Phil Knight & Bill Bowerman',
            'headquarters_city': 'Beaverton',
            'headquarters_country': 'USA',
            'parent_company': 'Nike Inc.',
            'market_cap_usd': 196000000000,  # ~$196B
            'annual_revenue_usd': 51217000000,  # ~$51B FY2023
            'employee_count': 83700,
            'website_url': 'https://www.nike.com',
            'instagram_handle': '@nike',
            'brand_story': 'Founded in 1964 as Blue Ribbon Sports by track athlete Phil Knight and coach Bill Bowerman. Renamed Nike in 1971 after the Greek goddess of victory. Revolutionized athletic footwear with waffle sole technology and Air cushioning system.',
            'brand_mission': 'To bring inspiration and innovation to every athlete in the world. If you have a body, you are an athlete.',
            'brand_values': ['Innovation', 'Sustainability', 'Diversity', 'Community', 'Performance'],
            'sustainability_score': 7,
            'innovation_focus': ['Air Technology', 'Flyknit', 'React Foam', 'Sustainable Materials', 'Digital Fitness'],
            'key_technologies': ['Nike Air', 'Flyknit', 'ZoomX', 'React', 'Dri-FIT', 'Nike Adapt'],
            'authenticity_level': 'verified'
        },
        'Adidas': {
            'founder_name': 'Adolf "Adi" Dassler',
            'headquarters_city': 'Herzogenaurach',
            'headquarters_country': 'Germany',
            'parent_company': 'Adidas AG',
            'market_cap_usd': 45000000000,  # ~$45B
            'annual_revenue_usd': 22516000000,  # ~$22.5B 2023
            'employee_count': 59000,
            'website_url': 'https://www.adidas.com',
            'instagram_handle': '@adidas',
            'brand_story': 'Founded in 1949 by Adolf Dassler after splitting from his brother Rudolf (who founded Puma). Known for the three stripes logo and innovation in sports technology. Became global through football partnerships.',
            'brand_mission': 'Through sport, we have the power to change lives.',
            'brand_values': ['Performance', 'Passion', 'Integrity', 'Diversity', 'Sustainability'],
            'sustainability_score': 8,
            'innovation_focus': ['Boost Technology', 'Primeknit', 'Recycled Materials', '4D Printing', 'Parley Ocean Plastic'],
            'key_technologies': ['Boost', 'Primeknit', '4D', 'Climacool', 'Torsion System', 'Continental Rubber'],
            'authenticity_level': 'verified'
        },
        'ASICS': {
            'founder_name': 'Kihachiro Onitsuka',
            'headquarters_city': 'Kobe',
            'headquarters_country': 'Japan',
            'parent_company': 'ASICS Corporation',
            'annual_revenue_usd': 3800000000,  # ~$3.8B
            'employee_count': 9000,
            'website_url': 'https://www.asics.com',
            'instagram_handle': '@asics',
            'brand_story': 'Founded in 1949 as Onitsuka Tiger. ASICS stands for "Anima Sana In Corpore Sano" (Sound Mind in Sound Body). Pioneered gel cushioning technology and became leader in running shoes.',
            'brand_mission': 'Creating quality products to promote total health and fitness.',
            'brand_values': ['Japanese Craftsmanship', 'Innovation', 'Performance', 'Respect', 'Integrity'],
            'sustainability_score': 6,
            'innovation_focus': ['GEL Technology', 'FlyteFoam', 'Running Analytics', 'Biomechanics Research'],
            'key_technologies': ['GEL', 'FlyteFoam', 'Trusstic System', 'Impact Guidance System', 'Dynamic DuoMax'],
            'authenticity_level': 'verified'
        },
        'New Balance': {
            'founder_name': 'William J. Riley',
            'headquarters_city': 'Boston',
            'headquarters_country': 'USA',
            'parent_company': 'New Balance Athletics',
            'annual_revenue_usd': 4400000000,  # ~$4.4B
            'employee_count': 7000,
            'website_url': 'https://www.newbalance.com',
            'instagram_handle': '@newbalance',
            'brand_story': 'Founded in 1906 as arch support company. Known for "Made in USA/UK" manufacturing and wide width sizing. Popular in running and lifestyle segments.',
            'brand_mission': 'Demonstrating responsible leadership, we build global brands that athletes are proud to wear.',
            'brand_values': ['Integrity', 'Teamwork', 'Total Customer Satisfaction'],
            'sustainability_score': 7,
            'innovation_focus': ['Fresh Foam', 'FuelCell', 'Made in USA Manufacturing', 'Performance Analytics'],
            'key_technologies': ['Fresh Foam', 'FuelCell', 'REVlite', 'ABZORB', 'N-ergy'],
            'authenticity_level': 'verified'
        },
        'LEGO': {
            'founder_name': 'Ole Kirk Christiansen',
            'headquarters_city': 'Billund',
            'headquarters_country': 'Denmark',
            'parent_company': 'LEGO A/S',
            'annual_revenue_usd': 7800000000,  # ~$7.8B
            'employee_count': 26000,
            'website_url': 'https://www.lego.com',
            'instagram_handle': '@lego',
            'brand_story': 'Founded in 1932 by carpenter Ole Kirk Christiansen. Name comes from "leg godt" (play well in Danish). Invented the modern plastic brick in 1958, became global cultural phenomenon.',
            'brand_mission': 'Inspire and develop the builders of tomorrow through the power of play.',
            'brand_values': ['Imagination', 'Creativity', 'Fun', 'Learning', 'Caring', 'Quality'],
            'sustainability_score': 8,
            'innovation_focus': ['Sustainable Materials', 'Educational Technology', 'Digital Play Experiences'],
            'key_technologies': ['ABS Plastic Precision', 'Clutch Power', 'Digital Building Instructions'],
            'authenticity_level': 'verified'
        },
        'Crocs': {
            'founder_name': 'Scott Seamans, Lyndon Hanson, George Boedecker Jr.',
            'headquarters_city': 'Broomfield',
            'headquarters_country': 'USA',
            'parent_company': 'Crocs Inc.',
            'market_cap_usd': 6500000000,  # ~$6.5B
            'annual_revenue_usd': 3500000000,  # ~$3.5B
            'employee_count': 6000,
            'website_url': 'https://www.crocs.com',
            'instagram_handle': '@crocs',
            'brand_story': 'Founded in 2002, originally as boating shoe. Made from Croslite foam material. Became cultural phenomenon and fashion statement despite initial criticism.',
            'brand_mission': 'Come As You Are - encouraging people to be comfortable in their own shoes.',
            'brand_values': ['Comfort', 'Fun', 'Simplicity', 'Innovation'],
            'sustainability_score': 5,
            'innovation_focus': ['Croslite Material', 'Comfort Technology', 'Sustainable Materials'],
            'key_technologies': ['Croslite Foam', 'LiteRide Foam', 'Jibbitz Customization'],
            'authenticity_level': 'verified'
        },
        'Telfar': {
            'founder_name': 'Telfar Clemens',
            'headquarters_city': 'New York',
            'headquarters_country': 'USA',
            'parent_company': 'Telfar Global',
            'annual_revenue_usd': 50000000,  # ~$50M estimated
            'employee_count': 50,
            'website_url': 'https://telfar.net',
            'instagram_handle': '@telfarglobal',
            'brand_story': 'Founded in 2005 by Telfar Clemens. Known as "Bushwick Birkin" for accessible luxury bags. Pioneered gender-neutral fashion and inclusive luxury.',
            'brand_mission': 'Not for you — for everyone. Creating accessible luxury without exclusivity.',
            'brand_values': ['Inclusivity', 'Accessibility', 'Community', 'Innovation', 'Authenticity'],
            'sustainability_score': 6,
            'innovation_focus': ['Gender-Neutral Design', 'Community-First Commerce', 'Affordable Luxury'],
            'key_technologies': ['Vegan Leather', 'Direct-to-Consumer Model', 'Bag Security Program'],
            'authenticity_level': 'verified'
        }
    }
    
    print("1. Updating brands with deep dive information...")
    updated_count = 0
    
    for brand_name, data in brand_deep_data.items():
        try:
            result = await conn.execute("""
                UPDATE core.brands 
                SET 
                    founder_name = $1,
                    headquarters_city = $2,
                    headquarters_country = $3,
                    parent_company = $4,
                    market_cap_usd = $5,
                    annual_revenue_usd = $6,
                    employee_count = $7,
                    website_url = $8,
                    instagram_handle = $9,
                    brand_story = $10,
                    brand_mission = $11,
                    brand_values = $12,
                    sustainability_score = $13,
                    innovation_focus = $14,
                    key_technologies = $15,
                    authenticity_level = $16
                WHERE name = $17
            """, 
            data['founder_name'], data['headquarters_city'], data['headquarters_country'],
            data['parent_company'], data.get('market_cap_usd'), data['annual_revenue_usd'],
            data['employee_count'], data['website_url'], data['instagram_handle'],
            data['brand_story'], data['brand_mission'], data['brand_values'],
            data['sustainability_score'], data['innovation_focus'], data['key_technologies'],
            data['authenticity_level'], brand_name)
            
            if result == 'UPDATE 1':
                updated_count += 1
                print(f"  OK Updated {brand_name}")
                
        except Exception as e:
            print(f"  ERROR Failed to update {brand_name}: {e}")
    
    print(f"Updated {updated_count} brands with deep dive data")
    
    # Add historical events
    print("\n2. Adding brand historical events...")
    
    historical_events = [
        # Nike History
        ('Nike', date(1964, 1, 25), 'founded', 'Blue Ribbon Sports Founded', 'Phil Knight and Bill Bowerman start importing Onitsuka Tiger shoes', 'high'),
        ('Nike', date(1971, 5, 30), 'milestone', 'Nike Brand Launch', 'Company renamed to Nike, Swoosh logo introduced', 'critical'),
        ('Nike', date(1972, 6, 18), 'milestone', 'First Nike Shoe', 'Nike Cortez launched as first Nike-branded shoe', 'high'),
        ('Nike', date(1980, 12, 12), 'ipo', 'Nike IPO', 'Nike goes public on NASDAQ', 'high'),
        ('Nike', date(1985, 4, 1), 'collaboration', 'Michael Jordan Partnership', 'Air Jordan brand launched with Michael Jordan', 'critical'),
        ('Nike', date(1987, 3, 26), 'milestone', 'Air Max Revolution', 'Air Max 1 introduces visible Air technology', 'critical'),
        ('Nike', date(2012, 2, 22), 'milestone', 'Flyknit Technology', 'Revolutionary Flyknit material launched', 'high'),
        
        # Adidas History
        ('Adidas', date(1949, 8, 18), 'founded', 'Adidas Founded', 'Adolf Dassler founds Adidas after split with brother Rudolf', 'critical'),
        ('Adidas', date(1954, 7, 4), 'milestone', 'World Cup Victory', 'Germany wins World Cup wearing Adidas boots with screw-in studs', 'critical'),
        ('Adidas', date(1970, 6, 21), 'milestone', 'World Cup Ball', 'First official World Cup ball - Telstar by Adidas', 'high'),
        ('Adidas', date(1985, 10, 1), 'collaboration', 'Run-DMC Partnership', 'Hip-hop group Run-DMC popularizes Superstar', 'high'),
        ('Adidas', date(2013, 2, 27), 'milestone', 'Boost Technology', 'Revolutionary Boost midsole technology launched', 'critical'),
        ('Adidas', date(2015, 6, 15), 'collaboration', 'Kanye West Partnership', 'Yeezy collaboration begins', 'critical'),
        
        # ASICS History
        ('ASICS', date(1949, 9, 1), 'founded', 'Onitsuka Tiger Founded', 'Kihachiro Onitsuka starts Onitsuka Tiger', 'critical'),
        ('ASICS', date(1977, 7, 21), 'merger', 'ASICS Formation', 'Merger of Onitsuka Tiger, GTO, and JELENK creates ASICS', 'critical'),
        ('ASICS', date(1986, 3, 10), 'milestone', 'GEL Technology', 'Revolutionary GEL cushioning system introduced', 'critical'),
        
        # New Balance History  
        ('New Balance', date(1906, 1, 1), 'founded', 'New Balance Founded', 'William J. Riley founds New Balance Arch Support Company', 'critical'),
        ('New Balance', date(1972, 10, 28), 'milestone', 'Boston Marathon', 'First marathon victory in New Balance shoes', 'high'),
        ('New Balance', date(1982, 4, 19), 'milestone', 'Made in USA', 'Commits to US manufacturing', 'high'),
        
        # LEGO History
        ('LEGO', date(1932, 8, 10), 'founded', 'LEGO Founded', 'Ole Kirk Christiansen starts wooden toy company', 'critical'),
        ('LEGO', date(1947, 12, 1), 'milestone', 'First Plastic Toys', 'First plastic toys produced', 'high'),
        ('LEGO', date(1958, 1, 28), 'milestone', 'LEGO Brick Patent', 'Modern LEGO brick design patented', 'critical'),
        ('LEGO', date(1999, 2, 1), 'milestone', 'Mindstorms Launch', 'Programmable robotics sets launched', 'high'),
        
        # Crocs History
        ('Crocs', date(2002, 7, 1), 'founded', 'Crocs Founded', 'Founded by Scott Seamans, Lyndon Hanson, George Boedecker Jr.', 'critical'),
        ('Crocs', date(2004, 11, 17), 'milestone', 'Fashion Week Debut', 'Crocs debuts at fashion shows', 'medium'),
        ('Crocs', date(2006, 2, 8), 'ipo', 'Crocs IPO', 'Company goes public', 'high'),
        
        # Telfar History
        ('Telfar', date(2005, 6, 1), 'founded', 'Telfar Founded', 'Telfar Clemens starts gender-neutral fashion brand', 'medium'),
        ('Telfar', date(2014, 9, 15), 'milestone', 'Shopping Bag Launch', 'Iconic Telfar Shopping Bag introduced', 'critical'),
        ('Telfar', date(2019, 8, 19), 'milestone', 'Bushwick Birkin', 'Bag nicknamed "Bushwick Birkin" - viral cultural moment', 'critical'),
    ]
    
    events_added = 0
    for brand_name, event_date, event_type, title, description, impact in historical_events:
        try:
            # Get brand ID first
            brand_id = await conn.fetchval("SELECT id FROM core.brands WHERE name = $1", brand_name)
            if brand_id:
                await conn.execute("""
                    INSERT INTO core.brand_history 
                    (brand_id, event_date, event_type, event_title, event_description, impact_level)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT DO NOTHING
                """, brand_id, event_date, event_type, title, description, impact)
                events_added += 1
        except Exception as e:
            print(f"  ERROR adding event for {brand_name}: {e}")
    
    print(f"Added {events_added} historical events")
    
    print("\n3. Adding brand attributes...")
    
    # Brand personality attributes
    brand_attributes = [
        # Nike Attributes
        ('Nike', 'personality', 'brand_personality', 'Bold, Innovative, Inspiring'),
        ('Nike', 'target_audience', 'primary_demographic', 'Athletes and Sports Enthusiasts'),
        ('Nike', 'style', 'design_aesthetic', 'Performance-driven, Modern, Bold'),
        ('Nike', 'quality', 'build_quality', 'Premium'),
        ('Nike', 'price_perception', 'market_position', 'Premium but Accessible'),
        
        # Adidas Attributes  
        ('Adidas', 'personality', 'brand_personality', 'Authentic, Creative, Performance-focused'),
        ('Adidas', 'target_audience', 'primary_demographic', 'Football fans and Streetwear enthusiasts'),
        ('Adidas', 'style', 'design_aesthetic', 'Classic with Modern Innovation'),
        ('Adidas', 'heritage', 'cultural_significance', 'Football and Hip-Hop Culture'),
        
        # ASICS Attributes
        ('ASICS', 'personality', 'brand_personality', 'Technical, Serious, Japanese Precision'),
        ('ASICS', 'target_audience', 'primary_demographic', 'Serious Runners and Athletes'),
        ('ASICS', 'quality', 'craftsmanship', 'Japanese Engineering Excellence'),
        
        # Telfar Attributes
        ('Telfar', 'personality', 'brand_personality', 'Inclusive, Revolutionary, Community-first'),
        ('Telfar', 'target_audience', 'primary_demographic', 'Fashion-forward, Diverse Community'),
        ('Telfar', 'style', 'design_philosophy', 'Gender-neutral, Accessible Luxury'),
    ]
    
    attributes_added = 0
    for brand_name, category, attr_name, attr_value in brand_attributes:
        try:
            brand_id = await conn.fetchval("SELECT id FROM core.brands WHERE name = $1", brand_name)
            if brand_id:
                await conn.execute("""
                    INSERT INTO core.brand_attributes 
                    (brand_id, attribute_category, attribute_name, attribute_value, confidence_score, data_source)
                    VALUES ($1, $2, $3, $4, 0.95, 'manual')
                    ON CONFLICT (brand_id, attribute_category, attribute_name) 
                    DO UPDATE SET attribute_value = EXCLUDED.attribute_value
                """, brand_id, category, attr_name, attr_value)
                attributes_added += 1
        except Exception as e:
            print(f"  ERROR adding attribute for {brand_name}: {e}")
    
    print(f"Added {attributes_added} brand attributes")
    
    print("\n=== BRAND DEEP DIVE DATA POPULATED ===")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(populate_brand_deep_dive())