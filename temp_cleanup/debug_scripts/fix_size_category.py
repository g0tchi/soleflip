import asyncio
import asyncpg

async def fix_size_category():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Execute the update
        result = await conn.execute(
            "UPDATE core.sizes SET category_id = $1 WHERE id = $2",
            '7e476135-7bfa-43c6-9c7c-bddd4f9593f4',  # Apparel category
            '7aeaa0e4-a527-4c7f-8dc9-938a0f139924'   # Size 34W/32L
        )
        
        print(f"✅ Update executed: {result}")
        
        # Verify the change
        updated_size = await conn.fetchrow(
            """SELECT s.value, c.name as category_name
               FROM core.sizes s
               JOIN core.categories c ON s.category_id = c.id
               WHERE s.id = $1""",
            '7aeaa0e4-a527-4c7f-8dc9-938a0f139924'
        )
        
        if updated_size:
            print(f"✅ Verification: Size '{updated_size['value']}' is now in category '{updated_size['category_name']}'")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_size_category())