"""
Unified Supplier Service
Manages all supplier-related operations, from creation to analytics.
"""

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import and_, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Import the core analytics functions
from domains.suppliers.core import analytics
from shared.database.models import (
    AccountPurchaseHistory,
    Supplier,
    SupplierAccount,
)
from shared.database.transaction_manager import TransactionMixin, transactional
from shared.repositories.base_repository import BaseRepository
from shared.security.api_security import InputSanitizer

logger = structlog.get_logger(__name__)


class SupplierService(TransactionMixin):
    """Unified service for all supplier-related business logic."""

    def __init__(self, db: AsyncSession):
        super().__init__(db_session=db)
        self.supplier_repo = BaseRepository(Supplier, db)
        self.account_repo = BaseRepository(SupplierAccount, db)
        self.purchase_repo = BaseRepository(AccountPurchaseHistory, db)
        self.input_sanitizer = InputSanitizer()

    # Notion's 45+ Supplier Categories
    SUPPLIER_CATEGORIES = {
        "sneaker_retailers": ["BSTN", "Solebox", "Footlocker", "JD Sports"],
        "general_retail": ["Amazon", "MediaMarkt", "Zalando", "Otto"],
        "luxury_fashion": ["BestSecret", "Mytheresa", "Farfetch", "SSENSE"],
        "direct_brands": ["Nike", "Adidas", "Uniqlo", "Crocs"],
        "specialty_stores": ["Lego", "Apple Store", "Samsung", "Taschen"],
    }

    # region Supplier Management
    @transactional()
    async def create_supplier(self, supplier_data: Dict) -> Supplier:
        """Creates a new supplier with intelligent categorization."""
        category = self._determine_supplier_category(supplier_data.get("name", ""))
        slug = supplier_data["name"].lower().replace(" ", "-")

        # Extract additional fields excluding name and category to avoid duplicates
        extra_fields = {k: v for k, v in supplier_data.items() if k not in ["name", "category"]}

        # Determine supplier_type if not provided (required field)
        supplier_type = extra_fields.pop("supplier_type", "retail")  # Default to retail

        # Use repository's create method with kwargs
        supplier = await self.supplier_repo.create(
            name=supplier_data["name"],
            slug=slug,
            supplier_type=supplier_type,
            supplier_category=category,
            **extra_fields
        )
        logger.info("Supplier created", supplier_id=str(supplier.id), name=supplier.name)
        return supplier

    @transactional()
    async def bulk_create_notion_suppliers(self) -> List[UUID]:
        """Bulk creates suppliers from a predefined Notion-inspired list."""
        notion_suppliers = [
            {"name": "BSTN", "category": "sneaker_retailers"},
            {"name": "Amazon", "category": "general_retail"},
            {"name": "Nike", "category": "direct_brands"},
        ]
        created_ids = []
        for sup_data in notion_suppliers:
            existing = await self.supplier_repo.find_one(name=sup_data["name"])
            if not existing:
                supplier = await self.create_supplier(sup_data)
                created_ids.append(supplier.id)
        return created_ids

    def _determine_supplier_category(self, supplier_name: str) -> str:
        """Determines supplier category based on name."""
        for category, suppliers in self.SUPPLIER_CATEGORIES.items():
            if supplier_name in suppliers:
                return category
        return "general_retail"

    # endregion

    # region Account Management
    @transactional()
    async def import_accounts_from_csv(
        self, csv_file_path: str, supplier_mapping: Optional[Dict[str, UUID]], batch_size: int
    ) -> Dict[str, Any]:
        """Imports supplier accounts from a CSV file."""
        if not Path(csv_file_path).exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

        if not supplier_mapping:
            supplier_mapping = await self._create_default_supplier_mapping()

        accounts_data = self._read_csv_file(csv_file_path)
        stats = {
            "total_rows": len(accounts_data),
            "successful_imports": 0,
            "failed_imports": 0,
            "skipped_rows": 0,
            "duplicate_accounts": 0,
            "errors": [],
        }

        for i in range(0, len(accounts_data), batch_size):
            batch = accounts_data[i : i + batch_size]
            batch_stats = await self._process_account_batch(batch, supplier_mapping)
            stats["successful_imports"] += batch_stats["successful"]
            stats["failed_imports"] += batch_stats["failed"]
            stats["skipped_rows"] += batch_stats["skipped"]
            stats["duplicate_accounts"] += batch_stats["duplicates"]
            stats["errors"].extend(batch_stats["errors"])
        return stats

    def _read_csv_file(self, file_path: str) -> List[Dict[str, str]]:
        """Reads and validates a CSV file."""
        accounts = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("EMAIL") and "@" in row["EMAIL"]:
                    accounts.append(row)
        return accounts

    async def _create_default_supplier_mapping(self) -> Dict[str, UUID]:
        """Create default supplier mapping based on list names in CSV"""
        try:
            suppliers = await self.supplier_repo.get_all()
            if not suppliers:
                default_supplier = Supplier(
                    name="Default Import Supplier",
                    slug="default-import-supplier",
                    display_name="Default Import Supplier",
                    supplier_type="online",
                    country="DE",
                )
                await self.supplier_repo.create(default_supplier)
                suppliers = [default_supplier]
            default_supplier_id = suppliers[0].id
            return {"default": default_supplier_id}
        except Exception as e:
            logger.error("Failed to create default supplier mapping", error=str(e))
            raise

    async def _process_account_batch(
        self, batch: List[Dict[str, str]], supplier_mapping: Dict[str, UUID]
    ) -> Dict[str, Any]:
        """Process a batch of account data"""
        stats = {"successful": 0, "failed": 0, "skipped": 0, "duplicates": 0, "errors": []}

        for account_data in batch:
            try:
                result = await self._process_single_account(account_data, supplier_mapping)
                stats[result["status"]] += 1

                if result["status"] == "failed":
                    stats["errors"].append(
                        {
                            "row": account_data.get("_row_number"),
                            "email": account_data.get("EMAIL"),
                            "error": result.get("error"),
                        }
                    )

            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append(
                    {
                        "row": account_data.get("_row_number"),
                        "email": account_data.get("EMAIL"),
                        "error": str(e),
                    }
                )

        return stats

    async def _process_single_account(
        self, account_data: Dict[str, str], supplier_mapping: Dict[str, UUID]
    ) -> Dict[str, str]:
        """Process a single account record"""
        try:
            list_name = account_data.get("LISTNAME", "default")
            supplier_id = supplier_mapping.get(list_name, supplier_mapping.get("default"))

            if not supplier_id:
                return {"status": "failed", "error": f"No supplier found for list: {list_name}"}

            email = self.input_sanitizer.sanitize_string(account_data.get("EMAIL", ""))
            if not email or "@" not in email:
                return {"status": "failed", "error": "Invalid email address"}

            existing_query = select(SupplierAccount).where(
                and_(SupplierAccount.supplier_id == supplier_id, SupplierAccount.email == email)
            )
            result = await self.db.execute(existing_query)
            existing_account = result.scalar_one_or_none()

            if existing_account:
                return {"status": "duplicates", "error": "Account already exists"}

            account = SupplierAccount(
                supplier_id=supplier_id,
                email=email,
                first_name=self.input_sanitizer.sanitize_string(account_data.get("FIRST_NAME", "")),
                last_name=self.input_sanitizer.sanitize_string(account_data.get("LAST_NAME", "")),
                address_line_1=self.input_sanitizer.sanitize_string(
                    account_data.get("ADDRESS_LINE_1", "")
                ),
                city=self.input_sanitizer.sanitize_string(account_data.get("CITY", "")),
                country_code=self.input_sanitizer.sanitize_string(
                    account_data.get("COUNTRY_CODE", ""), 5
                ),
            )
            await self.account_repo.create(account)
            return {"status": "successful"}
        except IntegrityError:
            return {"status": "duplicates", "error": "Account already exists"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def list_supplier_accounts(
        self, supplier_id: UUID, status: Optional[str], verified_only: bool, limit: int, offset: int
    ) -> List[SupplierAccount]:
        """Lists accounts for a specific supplier."""
        query = select(SupplierAccount).where(SupplierAccount.supplier_id == supplier_id)
        if status:
            query = query.where(SupplierAccount.account_status == status)
        if verified_only:
            query = query.where(SupplierAccount.is_verified)
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    @transactional()
    async def record_account_purchase(
        self, account_id: UUID, purchase_data: Dict
    ) -> AccountPurchaseHistory:
        """Records a purchase for an account and updates statistics."""
        purchase = AccountPurchaseHistory(
            account_id=account_id,
            purchase_amount=Decimal(str(purchase_data["purchase_amount"])),
            purchase_date=datetime.utcnow(),
            success=purchase_data.get("success", True),
        )
        await self.purchase_repo.create(purchase)
        await self.update_account_statistics(account_id)
        return purchase

    # endregion

    # region Statistics
    @transactional()
    async def update_account_statistics(self, account_id: UUID) -> None:
        """Updates statistics for a single account."""
        account = await self.account_repo.get_by_id(account_id)
        if not account:
            raise ValueError("Account not found")

        stats_query = select(
            func.count(AccountPurchaseHistory.id),
            func.sum(AccountPurchaseHistory.purchase_amount),
            func.avg(AccountPurchaseHistory.purchase_amount),
            func.count(AccountPurchaseHistory.id).filter(AccountPurchaseHistory.success),
        ).where(AccountPurchaseHistory.account_id == account_id)

        result = await self.db.execute(stats_query)
        stats = result.first()

        total_purchases, total_spent, avg_order_value, successful_purchases = stats
        account.total_purchases = total_purchases or 0
        account.total_spent = total_spent or Decimal("0.0")
        account.average_order_value = avg_order_value or Decimal("0.0")
        if total_purchases > 0:
            account.success_rate = (successful_purchases / total_purchases) * 100

        await self.account_repo.update(account)
        logger.info("Updated account statistics", account_id=str(account_id))

    @transactional()
    async def recalculate_all_account_statistics(
        self, supplier_id: Optional[UUID] = None
    ) -> Dict[str, int]:
        """Recalculates statistics for all accounts or a specific supplier."""
        query = select(SupplierAccount.id)
        if supplier_id:
            query = query.where(SupplierAccount.supplier_id == supplier_id)

        result = await self.db.execute(query)
        account_ids = [row[0] for row in result.all()]

        updated_count = 0
        for account_id in account_ids:
            try:
                await self.update_account_statistics(account_id)
                updated_count += 1
            except Exception as e:
                logger.error(
                    "Failed to update stats for account", account_id=str(account_id), error=str(e)
                )

        return {
            "total_accounts": len(account_ids),
            "updated_count": updated_count,
            "failed_count": len(account_ids) - updated_count,
        }

    async def get_supplier_account_overview(self, supplier_id: UUID) -> Dict[str, Any]:
        """Gets a comprehensive overview of supplier accounts."""
        stats_query = select(
            func.count(SupplierAccount.id).label("total_accounts"),
            func.sum(SupplierAccount.total_spent).label("total_revenue"),
        ).where(SupplierAccount.supplier_id == supplier_id)
        result = await self.db.execute(stats_query)
        stats = result.first()

        top_accounts = await self._get_top_performing_accounts(supplier_id)

        return {
            "overview": {
                "total_accounts": stats.total_accounts or 0,
                "total_revenue": float(stats.total_revenue or 0),
            },
            "top_performing_accounts": top_accounts,
        }

    async def _get_top_performing_accounts(
        self, supplier_id: UUID, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get top performing accounts by total spent."""
        query = (
            select(SupplierAccount)
            .where(SupplierAccount.supplier_id == supplier_id)
            .order_by(desc("total_spent"))
            .limit(limit)
        )
        result = await self.db.execute(query)
        accounts = result.scalars().all()
        return [acc.to_dict() for acc in accounts]

    async def get_account_detailed_statistics(self, account_id: UUID) -> Dict[str, Any]:
        """Gets detailed statistics for a specific account."""
        account = await self.account_repo.get_by_id(account_id)
        if not account:
            raise ValueError("Account not found")

        purchase_stats = await self._calculate_account_purchase_stats(account_id)

        return {"account_info": account.to_dict(), "purchase_statistics": purchase_stats}

    async def _calculate_account_purchase_stats(self, account_id: UUID) -> Dict[str, Any]:
        """Calculate detailed purchase statistics for an account"""
        stats_query = select(
            func.count(AccountPurchaseHistory.id).label("total_purchases"),
            func.sum(AccountPurchaseHistory.purchase_amount).label("total_spent"),
        ).where(AccountPurchaseHistory.account_id == account_id)
        result = await self.db.execute(stats_query)
        stats = result.first()
        return {
            "total_purchases": stats.total_purchases or 0,
            "total_spent": float(stats.total_spent or 0),
        }

    # endregion

    # region Intelligence
    async def get_supplier_intelligence_dashboard(self) -> Dict:
        """Generates a dashboard with supplier intelligence by calling core analytics."""
        return await analytics.get_supplier_intelligence_dashboard(self.db)

    async def get_supplier_recommendations(self, category: Optional[str] = None) -> List[Dict]:
        """Gets supplier recommendations by calling core analytics."""
        return await analytics.get_supplier_recommendations(self.db, category)

    async def get_category_analytics(self, category: str) -> Dict[str, Any]:
        """Gets analytics for a specific supplier category."""
        return await analytics.get_category_analytics(self.db, category)

    # endregion
