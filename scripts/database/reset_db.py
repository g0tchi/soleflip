import os
import subprocess
import sys

# Set a valid key for this script to run without a .env file
os.environ["FIELD_ENCRYPTION_KEY"] = "HXfzzwhvSyuNwcvmWhG3rYixL0TiuSkHiJJ0EI4sG7U="


def main():
    db_path = "./soleflip_demo.db"
    print(f"--- Running Database Reset Script ---")

    # 1. Delete existing DB file
    if os.path.exists(db_path):
        print(f"Found old database at {db_path}. Deleting it.")
        os.remove(db_path)
        print("Old database file deleted.")
    else:
        print("No old database file found. Starting fresh.")

    # 2. Create schema directly from models
    print("\nCreating schema directly from models for a clean slate...")
    import asyncio

    from shared.database.connection import DatabaseManager
    from shared.database.models import Base

    async def create_schema():
        db_manager_local = DatabaseManager()
        db_manager_local.database_url = f"sqlite+aiosqlite:///{db_path}"
        await db_manager_local.initialize()
        async with db_manager_local.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await db_manager_local.close()
        print("Schema created successfully.")

    try:
        asyncio.run(create_schema())
        print("Database reset successful.")
    except Exception as e:
        print(f"\nDatabase schema creation failed: {e}")


if __name__ == "__main__":
    main()
