"""
Simple script to import Nike accounts from CSV using direct SQL
"""

import asyncio
import csv
import os
from uuid import uuid4
from datetime import datetime

from shared.database.connection import db_manager
from sqlalchemy import text
from cryptography.fernet import Fernet

# Get encryption key
ENCRYPTION_KEY = os.getenv("FIELD_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("FIELD_ENCRYPTION_KEY not set")

fernet = Fernet(ENCRYPTION_KEY.encode())


def encrypt_field(value):
    """Encrypt a field value"""
    if not value:
        return None
    return fernet.encrypt(value.encode()).decode()


async def import_nike_accounts():
    """Import Nike accounts using direct SQL"""

    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # Check if Nike supplier exists
        result = await session.execute(text(
            "SELECT id, name FROM core.suppliers WHERE LOWER(name) LIKE '%nike%'"
        ))
        nike_supplier = result.first()

        if not nike_supplier:
            print("Creating Nike supplier...")
            nike_id = str(uuid4())
            await session.execute(text("""
                INSERT INTO core.suppliers
                (id, name, slug, display_name, supplier_type, business_size, website, country, status, created_at, updated_at)
                VALUES
                (:id, 'Nike', 'nike', 'Nike Inc.', 'brand', 'large', 'https://www.nike.com', 'US', 'active', :created_at, :updated_at)
            """), {
                'id': nike_id,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })
            await session.commit()
            print(f"Created Nike supplier with ID: {nike_id}")
        else:
            nike_id = str(nike_supplier.id)
            print(f"Found existing Nike supplier: {nike_supplier.name} (ID: {nike_id})")

        # Read CSV file
        csv_path = "C:\\nth_dev\\soleflip\\src\\data\\accounts.csv"
        if not os.path.exists(csv_path):
            print(f"CSV file not found: {csv_path}")
            return

        print(f"Reading accounts from {csv_path}...")

        total_rows = 0
        successful_imports = 0
        failed_imports = 0
        skipped_rows = 0
        errors = []

        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row_num, row in enumerate(reader, start=2):
                total_rows += 1

                # Skip empty rows
                if not any(row.values()):
                    skipped_rows += 1
                    continue

                # Validate email
                email = row.get('EMAIL', '').strip()
                if not email or '@' not in email:
                    skipped_rows += 1
                    continue

                try:
                    # Check if account already exists
                    existing = await session.execute(text("""
                        SELECT id FROM core.supplier_accounts
                        WHERE supplier_id = :supplier_id AND email = :email
                    """), {'supplier_id': nike_id, 'email': email})

                    if existing.first():
                        skipped_rows += 1
                        continue

                    # Prepare account data
                    account_id = str(uuid4())
                    password = row.get('PASSWORD', '')
                    cc_number = row.get('CC_NUMBER', '')
                    cvv = row.get('CVV', '')

                    # Handle dates
                    expiry_month = None
                    expiry_year = None
                    try:
                        if row.get('EXPIRY_MONTH') and row.get('EXPIRY_MONTH').isdigit():
                            expiry_month = int(row.get('EXPIRY_MONTH'))
                            if not (1 <= expiry_month <= 12):
                                expiry_month = None
                    except:
                        pass

                    try:
                        if row.get('EXPIRY_YEAR') and row.get('EXPIRY_YEAR').isdigit():
                            expiry_year = int(row.get('EXPIRY_YEAR'))
                            if expiry_year < 100:
                                expiry_year += 2000
                            if expiry_year < datetime.now().year:
                                expiry_year = None
                    except:
                        pass

                    # Insert account
                    await session.execute(text("""
                        INSERT INTO core.supplier_accounts (
                            id, supplier_id, email, password_hash, proxy_config,
                            first_name, last_name, address_line_1, address_line_2,
                            city, country_code, zip_code, state_code, phone_number,
                            cc_number_encrypted, expiry_month, expiry_year, cvv_encrypted,
                            browser_preference, list_name, account_status, is_verified,
                            total_purchases, total_spent, success_rate, average_order_value,
                            created_at, updated_at
                        ) VALUES (
                            :id, :supplier_id, :email, :password_hash, :proxy_config,
                            :first_name, :last_name, :address_line_1, :address_line_2,
                            :city, :country_code, :zip_code, :state_code, :phone_number,
                            :cc_number_encrypted, :expiry_month, :expiry_year, :cvv_encrypted,
                            :browser_preference, :list_name, 'active', false,
                            0, 0.00, 0.00, 0.00,
                            :created_at, :updated_at
                        )
                    """), {
                        'id': account_id,
                        'supplier_id': nike_id,
                        'email': email,
                        'password_hash': encrypt_field(password) if password else None,
                        'proxy_config': row.get('PROXY') if row.get('PROXY') else None,
                        'first_name': row.get('FIRST_NAME', '')[:100] if row.get('FIRST_NAME') else None,
                        'last_name': row.get('LAST_NAME', '')[:100] if row.get('LAST_NAME') else None,
                        'address_line_1': row.get('ADDRESS_LINE_1', '')[:200] if row.get('ADDRESS_LINE_1') else None,
                        'address_line_2': row.get('ADDRESS_LINE_2', '')[:200] if row.get('ADDRESS_LINE_2') else None,
                        'city': row.get('CITY', '')[:100] if row.get('CITY') else None,
                        'country_code': row.get('COUNTRY_CODE', '')[:5] if row.get('COUNTRY_CODE') else None,
                        'zip_code': row.get('ZIP_CODE', '')[:20] if row.get('ZIP_CODE') else None,
                        'state_code': row.get('STATE_CODE', '')[:10] if row.get('STATE_CODE') else None,
                        'phone_number': row.get('PHONE_NUMBER', '')[:50] if row.get('PHONE_NUMBER') else None,
                        'cc_number_encrypted': encrypt_field(cc_number) if cc_number and len(cc_number) >= 13 else None,
                        'expiry_month': expiry_month,
                        'expiry_year': expiry_year,
                        'cvv_encrypted': encrypt_field(cvv) if cvv and cvv.isdigit() else None,
                        'browser_preference': row.get('BROWSER', '')[:50] if row.get('BROWSER') else None,
                        'list_name': row.get('LISTNAME', '')[:100] if row.get('LISTNAME') else None,
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    })

                    successful_imports += 1

                    # Commit every 10 records
                    if successful_imports % 10 == 0:
                        await session.commit()
                        print(f"Imported {successful_imports} accounts...")

                except Exception as e:
                    failed_imports += 1
                    errors.append({
                        'row': row_num,
                        'email': email,
                        'error': str(e)
                    })

        # Final commit
        await session.commit()

        # Get final count
        result = await session.execute(text("""
            SELECT COUNT(*) as count FROM core.supplier_accounts WHERE supplier_id = :supplier_id
        """), {'supplier_id': nike_id})
        total_accounts = result.scalar()

        print("\n=== IMPORT RESULTS ===")
        print(f"Total rows processed: {total_rows}")
        print(f"Successful imports: {successful_imports}")
        print(f"Failed imports: {failed_imports}")
        print(f"Skipped rows: {skipped_rows}")
        print(f"Total Nike accounts in database: {total_accounts}")

        if errors:
            print(f"\n=== ERRORS (showing first 5) ===")
            for error in errors[:5]:
                print(f"Row {error['row']} ({error['email']}): {error['error']}")


if __name__ == "__main__":
    asyncio.run(import_nike_accounts())