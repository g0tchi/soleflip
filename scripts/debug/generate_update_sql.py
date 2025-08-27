import os
import sys
import getpass
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from dotenv import load_dotenv
from cryptography.fernet import Fernet

def generate_sql():
    """
    Generates raw SQL UPDATE statements to manually fix the credentials in the database.
    """
    print("--- Manual SQL Update Generator ---")

    # 1. Load .env and get encryption key
    load_dotenv()
    encryption_key = os.getenv("FIELD_ENCRYPTION_KEY")
    if not encryption_key:
        print("FATAL: FIELD_ENCRYPTION_KEY not found in your .env file.")
        return

    try:
        cipher_suite = Fernet(encryption_key.encode())
    except Exception as e:
        print(f"FATAL: The FIELD_ENCRYPTION_KEY in your .env file is invalid. Error: {e}")
        return

    print("Encryption key loaded successfully.")

    # 2. Get credentials from user
    print("\nPlease enter the StockX credentials you want to save.")
    creds_to_encrypt = {
        "stockx_client_id": input("Enter your Client ID: ").strip(),
        "stockx_client_secret": getpass.getpass("Enter your Client Secret: ").strip(),
        "stockx_refresh_token": input("Enter your Refresh Token: ").strip(),
        "stockx_api_key": input("Enter your general API Key: ").strip(),
    }

    # 3. Generate SQL
    print("\n" + "="*60)
    print("Copy and run the following SQL statements in your database tool (e.g., Adminer).")
    print("Connect to the 'metabase' database and select the 'core' schema.")
    print("="*60 + "\n")

    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f%z')

    for key, value in creds_to_encrypt.items():
        if not value:
            print(f"-- Skipping {key} because no value was provided.")
            continue

        encrypted_value = cipher_suite.encrypt(value.encode()).decode()
        # Escape single quotes in the encrypted value for SQL
        sql_safe_encrypted_value = encrypted_value.replace("'", "''")

        sql = (
            f"UPDATE core.system_config "
            f"SET value_encrypted = '{sql_safe_encrypted_value}', updated_at = '{timestamp}' "
            f"WHERE key = '{key}';"
        )
        print(sql)

    print("\n" + "="*60)
    print("After running these commands, the main application should work correctly.")
    print("Don't forget to revert the DATABASE_URL in your .env file to use 'metabase-db:5432' for the main application.")

if __name__ == "__main__":
    generate_sql()
