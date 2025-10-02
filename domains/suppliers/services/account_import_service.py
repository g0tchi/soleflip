"""
Supplier Account Import Service
Import and manage supplier accounts from CSV data with secure handling
"""

import csv
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError

from shared.database.models import Supplier, SupplierAccount, AccountPurchaseHistory
from shared.repositories.base_repository import BaseRepository
from shared.database.transaction_manager import TransactionMixin, transactional
from shared.security.api_security import InputSanitizer

logger = structlog.get_logger(__name__)


class AccountImportService(TransactionMixin):
    """Service for importing and managing supplier accounts from CSV"""

    def __init__(self, db: AsyncSession):
        super().__init__(db_session=db)
        self.supplier_repo = BaseRepository(Supplier, db)
        self.account_repo = BaseRepository(SupplierAccount, db)
        self.input_sanitizer = InputSanitizer()

    @transactional()
    async def import_accounts_from_csv(
        self,
        csv_file_path: str,
        supplier_mapping: Optional[Dict[str, UUID]] = None,
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Import accounts from CSV file with batch processing

        Args:
            csv_file_path: Path to the CSV file
            supplier_mapping: Optional mapping of list_name to supplier_id
            batch_size: Number of accounts to process in each batch

        Returns:
            Import statistics and results
        """
        try:
            if not Path(csv_file_path).exists():
                raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

            # If no supplier mapping provided, try to auto-map or create default suppliers
            if not supplier_mapping:
                supplier_mapping = await self._create_default_supplier_mapping()

            stats = {
                "total_rows": 0,
                "successful_imports": 0,
                "failed_imports": 0,
                "skipped_rows": 0,
                "duplicate_accounts": 0,
                "errors": []
            }

            # Read and validate CSV structure
            accounts_data = self._read_csv_file(csv_file_path)
            stats["total_rows"] = len(accounts_data)

            # Process in batches for better performance
            for i in range(0, len(accounts_data), batch_size):
                batch = accounts_data[i:i + batch_size]
                batch_stats = await self._process_account_batch(batch, supplier_mapping)

                # Aggregate stats
                stats["successful_imports"] += batch_stats["successful"]
                stats["failed_imports"] += batch_stats["failed"]
                stats["skipped_rows"] += batch_stats["skipped"]
                stats["duplicate_accounts"] += batch_stats["duplicates"]
                stats["errors"].extend(batch_stats["errors"])

                logger.info(
                    "Processed account batch",
                    batch_number=i // batch_size + 1,
                    batch_size=len(batch),
                    successful=batch_stats["successful"],
                    failed=batch_stats["failed"]
                )

            logger.info(
                "Account import completed",
                **{k: v for k, v in stats.items() if k != "errors"}
            )

            return stats

        except Exception as e:
            logger.error("Failed to import accounts from CSV", error=str(e))
            raise

    def _read_csv_file(self, csv_file_path: str) -> List[Dict[str, str]]:
        """Read and parse CSV file"""
        accounts = []

        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header
                    # Skip empty rows
                    if not any(row.values()):
                        continue

                    # Clean and validate required fields
                    email = row.get('EMAIL', '').strip()
                    if not email or '@' not in email:
                        logger.warning(f"Skipping row {row_num}: Invalid or missing email")
                        continue

                    accounts.append({
                        **row,
                        '_row_number': row_num
                    })

            return accounts

        except Exception as e:
            logger.error(f"Failed to read CSV file: {str(e)}")
            raise

    async def _create_default_supplier_mapping(self) -> Dict[str, UUID]:
        """Create default supplier mapping based on list names in CSV"""
        try:
            # Check if we have any suppliers
            suppliers = await self.supplier_repo.get_all()

            if not suppliers:
                # Create a default supplier
                default_supplier = Supplier(
                    name="Default Import Supplier",
                    slug="default-import-supplier",
                    display_name="Default Import Supplier",
                    supplier_type="online",
                    country="DE"
                )
                await self.supplier_repo.create(default_supplier)
                suppliers = [default_supplier]

            # Use the first supplier as default
            default_supplier_id = suppliers[0].id

            return {"default": default_supplier_id}

        except Exception as e:
            logger.error("Failed to create default supplier mapping", error=str(e))
            raise

    async def _process_account_batch(
        self,
        batch: List[Dict[str, str]],
        supplier_mapping: Dict[str, UUID]
    ) -> Dict[str, Any]:
        """Process a batch of account data"""
        stats = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "duplicates": 0,
            "errors": []
        }

        for account_data in batch:
            try:
                result = await self._process_single_account(account_data, supplier_mapping)
                stats[result["status"]] += 1

                if result["status"] == "failed":
                    stats["errors"].append({
                        "row": account_data.get('_row_number'),
                        "email": account_data.get('EMAIL'),
                        "error": result.get("error")
                    })

            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append({
                    "row": account_data.get('_row_number'),
                    "email": account_data.get('EMAIL'),
                    "error": str(e)
                })

        return stats

    async def _process_single_account(
        self,
        account_data: Dict[str, str],
        supplier_mapping: Dict[str, UUID]
    ) -> Dict[str, str]:
        """Process a single account record"""
        try:
            # Get supplier ID
            list_name = account_data.get('LISTNAME', 'default')
            supplier_id = supplier_mapping.get(list_name, supplier_mapping.get('default'))

            if not supplier_id:
                return {"status": "failed", "error": f"No supplier found for list: {list_name}"}

            # Sanitize and validate input data
            email = self.input_sanitizer.sanitize_string(account_data.get('EMAIL', ''))
            if not email or '@' not in email:
                return {"status": "failed", "error": "Invalid email address"}

            # Check for existing account
            existing_query = select(SupplierAccount).where(
                and_(
                    SupplierAccount.supplier_id == supplier_id,
                    SupplierAccount.email == email
                )
            )
            result = await self.db.execute(existing_query)
            existing_account = result.scalar_one_or_none()

            if existing_account:
                return {"status": "duplicates", "error": "Account already exists"}

            # Create new account
            account = SupplierAccount(
                supplier_id=supplier_id,
                email=email,
                first_name=self.input_sanitizer.sanitize_string(account_data.get('FIRST_NAME', '')),
                last_name=self.input_sanitizer.sanitize_string(account_data.get('LAST_NAME', '')),
                address_line_1=self.input_sanitizer.sanitize_string(account_data.get('ADDRESS_LINE_1', '')),
                address_line_2=self.input_sanitizer.sanitize_string(account_data.get('ADDRESS_LINE_2', '')),
                city=self.input_sanitizer.sanitize_string(account_data.get('CITY', '')),
                country_code=self.input_sanitizer.sanitize_string(account_data.get('COUNTRY_CODE', ''), 5),
                zip_code=self.input_sanitizer.sanitize_string(account_data.get('ZIP_CODE', '')),
                state_code=self.input_sanitizer.sanitize_string(account_data.get('STATE_CODE', '')),
                phone_number=self.input_sanitizer.sanitize_string(account_data.get('PHONE_NUMBER', '')),
                browser_preference=self.input_sanitizer.sanitize_string(account_data.get('BROWSER', '')),
                list_name=self.input_sanitizer.sanitize_string(account_data.get('LISTNAME', '')),
                account_status="active",
                proxy_config=account_data.get('PROXY', '') if account_data.get('PROXY') else None
            )

            # Handle encrypted fields securely
            password = account_data.get('PASSWORD', '')
            if password:
                account.set_encrypted_password(password)

            # REMOVED: Direct credit card storage - PCI compliance violation
            # Payment information must be tokenized through payment provider
            # cc_number = account_data.get('CC_NUMBER', '')  # SECURITY RISK - REMOVED
            # cvv = account_data.get('CVV', '')              # PCI VIOLATION - REMOVED

            # For existing data: Extract last 4 digits for display only (if needed)
            cc_number = account_data.get('CC_NUMBER', '')
            if cc_number and len(cc_number) >= 13:
                # Store only last 4 digits for display purposes
                last4 = cc_number[-4:] if len(cc_number) >= 4 else None
                # Set placeholder values until payment provider integration
                account.set_payment_method(
                    provider="manual_import",  # Temporary during migration
                    token=f"legacy_import_{uuid.uuid4().hex[:8]}",  # Temporary token
                    last4=last4,
                    brand="unknown"  # Will be determined by payment provider
                )

            # Handle expiry dates
            try:
                expiry_month = account_data.get('EXPIRY_MONTH', '')
                if expiry_month and expiry_month.isdigit():
                    month = int(expiry_month)
                    if 1 <= month <= 12:
                        account.expiry_month = month

                expiry_year = account_data.get('EXPIRY_YEAR', '')
                if expiry_year and expiry_year.isdigit():
                    year = int(expiry_year)
                    # Convert 2-digit year to 4-digit
                    if year < 100:
                        year += 2000
                    if year >= datetime.now().year:
                        account.expiry_year = year
            except ValueError:
                pass  # Skip invalid dates

            # Save account
            await self.account_repo.create(account)

            return {"status": "successful"}

        except IntegrityError:
            return {"status": "duplicates", "error": "Account already exists"}
        except Exception as e:
            logger.error(
                "Failed to process account",
                email=account_data.get('EMAIL'),
                error=str(e)
            )
            return {"status": "failed", "error": str(e)}

    async def get_import_summary(self, supplier_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get summary of imported accounts"""
        try:
            from sqlalchemy import func

            query = select(
                func.count(SupplierAccount.id).label('total_accounts'),
                func.sum(SupplierAccount.total_purchases).label('total_purchases'),
                func.sum(SupplierAccount.total_spent).label('total_revenue'),
                func.avg(SupplierAccount.success_rate).label('avg_success_rate'),
                func.count(SupplierAccount.id).filter(
                    SupplierAccount.account_status == 'active'
                ).label('active_accounts')
            )

            if supplier_id:
                query = query.where(SupplierAccount.supplier_id == supplier_id)

            result = await self.db.execute(query)
            row = result.first()

            return {
                "total_accounts": row.total_accounts or 0,
                "active_accounts": row.active_accounts or 0,
                "total_purchases": row.total_purchases or 0,
                "total_revenue": float(row.total_revenue or 0),
                "average_success_rate": float(row.avg_success_rate or 0)
            }

        except Exception as e:
            logger.error("Failed to get import summary", error=str(e))
            raise

    async def update_account_statistics(self, account_id: UUID) -> None:
        """Update statistics for a specific account"""
        try:
            # Get account
            account = await self.account_repo.get_by_id(account_id)
            if not account:
                raise ValueError(f"Account not found: {account_id}")

            # Calculate statistics from purchase history
            from sqlalchemy import func

            stats_query = select(
                func.count(AccountPurchaseHistory.id).label('total_purchases'),
                func.sum(AccountPurchaseHistory.purchase_amount).label('total_spent'),
                func.avg(AccountPurchaseHistory.purchase_amount).label('avg_order_value'),
                func.count(AccountPurchaseHistory.id).filter(
                    AccountPurchaseHistory.success
                ).label('successful_purchases')
            ).where(AccountPurchaseHistory.account_id == account_id)

            result = await self.db.execute(stats_query)
            stats = result.first()

            # Update account statistics
            account.total_purchases = stats.total_purchases or 0
            account.total_spent = stats.total_spent or Decimal('0.00')
            account.average_order_value = stats.avg_order_value or Decimal('0.00')

            # Calculate success rate
            if account.total_purchases > 0:
                success_rate = (stats.successful_purchases / account.total_purchases) * 100
                account.success_rate = Decimal(str(round(success_rate, 2)))

            await self.account_repo.update(account)

            logger.info(
                "Updated account statistics",
                account_id=str(account_id),
                total_purchases=account.total_purchases,
                success_rate=float(account.success_rate)
            )

        except Exception as e:
            logger.error(
                "Failed to update account statistics",
                account_id=str(account_id),
                error=str(e)
            )
            raise