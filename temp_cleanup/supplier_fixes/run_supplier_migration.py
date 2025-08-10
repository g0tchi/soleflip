import asyncio
from shared.database.connection import db_manager

async def run_supplier_migration():
    """Run the supplier migration"""
    try:
        # Initialize database connection
        print("Initializing database connection...")
        await db_manager.initialize()
        
        # Run migrations
        print("Running database migrations...")
        await db_manager.run_migrations()
        
        print("✅ Supplier migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close connection
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(run_supplier_migration())