"""
Supplier Intelligence Service
45+ Supplier Management with Performance Analytics (from Notion Analysis)
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Supplier, SupplierPerformance, InventoryItem, Product

logger = structlog.get_logger(__name__)


class SupplierIntelligenceService:
    """Advanced supplier management with Notion feature parity"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Notion's 45+ Supplier Categories
    SUPPLIER_CATEGORIES = {
        "sneaker_retailers": [
            "BSTN", "Solebox", "Footlocker", "JD Sports", "Afew", "Sneakersnstuff",
            "Size?", "Office", "Footpatrol", "END Clothing", "Caliroots"
        ],
        "general_retail": [
            "Amazon", "MediaMarkt", "Zalando", "AboutYou", "Otto", "Kaufland",
            "Real", "Saturn", "Conrad", "Alternate"
        ],
        "luxury_fashion": [
            "BestSecret", "Highsnobiety", "Engelhorn", "Breuninger", "Mytheresa",
            "Net-a-Porter", "Farfetch", "SSENSE", "Mr Porter"
        ],
        "direct_brands": [
            "Nike", "Adidas", "Uniqlo", "Crocs", "New Balance", "Asics",
            "Vans", "Converse", "Puma", "Under Armour"
        ],
        "specialty_stores": [
            "Lego", "MEGA Construx", "HotWheels", "Taschen", "Apple Store",
            "Samsung", "Sony", "Nintendo", "Microsoft"
        ]
    }

    async def create_supplier_from_notion_data(self, supplier_data: Dict) -> UUID:
        """
        Create supplier with Notion intelligence data
        Includes category, VAT rate, return policy, and default email
        """

        # Determine category
        category = self._determine_supplier_category(supplier_data.get("name", ""))

        # Generate slug from name
        slug = supplier_data["name"].lower().replace(" ", "-").replace("?", "").replace("&", "and")

        supplier = Supplier(
            name=supplier_data["name"],
            slug=slug,
            supplier_type="online",  # Default type
            supplier_category=category,
            vat_rate=supplier_data.get("vat_rate", Decimal("19.0")),  # Default German VAT
            return_policy=supplier_data.get("return_policy", "Standard return policy"),
            default_email=supplier_data.get("email", f"orders@{supplier_data['name'].lower().replace(' ', '')}.com"),

            # Standard fields
            contact_person=supplier_data.get("contact_person"),
            phone=supplier_data.get("phone"),
            email=supplier_data.get("email"),
            website=supplier_data.get("website"),
            address_line1=supplier_data.get("address"),
            city=supplier_data.get("city", "Unknown"),
            country=supplier_data.get("country", "Germany"),

            # Business intelligence fields
            return_policy_days=supplier_data.get("return_days", 14),
            payment_terms=supplier_data.get("payment_terms", "Net 30"),
            minimum_order_amount=supplier_data.get("min_order", Decimal("50.0")),
            status="active"
        )

        self.db.add(supplier)
        await self.db.commit()
        await self.db.refresh(supplier)

        logger.info("Supplier created from Notion data",
                   supplier_id=str(supplier.id),
                   name=supplier.name,
                   category=category)

        return supplier.id

    def _determine_supplier_category(self, supplier_name: str) -> str:
        """Determine supplier category based on name (Notion logic)"""
        name_lower = supplier_name.lower()

        for category, suppliers in self.SUPPLIER_CATEGORIES.items():
            for supplier in suppliers:
                if supplier.lower() in name_lower:
                    return category

        # Default categorization logic
        if any(keyword in name_lower for keyword in ["sneaker", "shoe", "foot"]):
            return "sneaker_retailers"
        elif any(keyword in name_lower for keyword in ["luxury", "fashion", "designer"]):
            return "luxury_fashion"
        elif any(keyword in name_lower for keyword in ["nike", "adidas", "brand"]):
            return "direct_brands"
        else:
            return "general_retail"

    async def bulk_create_notion_suppliers(self) -> List[UUID]:
        """
        Bulk create all 45+ suppliers from Notion analysis
        Recreates the comprehensive supplier network
        """

        notion_suppliers = [
            # Sneaker Retailers
            {"name": "BSTN", "category": "sneaker_retailers", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Solebox", "category": "sneaker_retailers", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Footlocker", "category": "sneaker_retailers", "vat_rate": "19.0", "country": "Germany"},
            {"name": "JD Sports", "category": "sneaker_retailers", "vat_rate": "19.0", "country": "UK"},
            {"name": "Afew", "category": "sneaker_retailers", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Sneakersnstuff", "category": "sneaker_retailers", "vat_rate": "25.0", "country": "Sweden"},
            {"name": "Size?", "category": "sneaker_retailers", "vat_rate": "20.0", "country": "UK"},
            {"name": "Office", "category": "sneaker_retailers", "vat_rate": "20.0", "country": "UK"},
            {"name": "Footpatrol", "category": "sneaker_retailers", "vat_rate": "20.0", "country": "UK"},
            {"name": "END Clothing", "category": "sneaker_retailers", "vat_rate": "20.0", "country": "UK"},

            # General Retail
            {"name": "Amazon", "category": "general_retail", "vat_rate": "19.0", "country": "Germany"},
            {"name": "MediaMarkt", "category": "general_retail", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Zalando", "category": "general_retail", "vat_rate": "19.0", "country": "Germany"},
            {"name": "AboutYou", "category": "general_retail", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Otto", "category": "general_retail", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Saturn", "category": "general_retail", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Conrad", "category": "general_retail", "vat_rate": "19.0", "country": "Germany"},

            # Luxury/Fashion
            {"name": "BestSecret", "category": "luxury_fashion", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Highsnobiety", "category": "luxury_fashion", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Engelhorn", "category": "luxury_fashion", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Breuninger", "category": "luxury_fashion", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Mytheresa", "category": "luxury_fashion", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Farfetch", "category": "luxury_fashion", "vat_rate": "20.0", "country": "UK"},
            {"name": "SSENSE", "category": "luxury_fashion", "vat_rate": "0.0", "country": "Canada"},

            # Direct Brands
            {"name": "Nike", "category": "direct_brands", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Adidas", "category": "direct_brands", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Uniqlo", "category": "direct_brands", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Crocs", "category": "direct_brands", "vat_rate": "19.0", "country": "Germany"},
            {"name": "New Balance", "category": "direct_brands", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Asics", "category": "direct_brands", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Vans", "category": "direct_brands", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Converse", "category": "direct_brands", "vat_rate": "19.0", "country": "Germany"},

            # Specialty Stores
            {"name": "Lego", "category": "specialty_stores", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Apple Store", "category": "specialty_stores", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Samsung", "category": "specialty_stores", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Sony", "category": "specialty_stores", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Nintendo", "category": "specialty_stores", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Microsoft", "category": "specialty_stores", "vat_rate": "19.0", "country": "Germany"},

            # Additional suppliers from Notion analysis
            {"name": "Kaufland", "category": "general_retail", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Real", "category": "general_retail", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Alternate", "category": "general_retail", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Caliroots", "category": "sneaker_retailers", "vat_rate": "25.0", "country": "Sweden"},
            {"name": "Net-a-Porter", "category": "luxury_fashion", "vat_rate": "20.0", "country": "UK"},
            {"name": "Mr Porter", "category": "luxury_fashion", "vat_rate": "20.0", "country": "UK"},
            {"name": "Puma", "category": "direct_brands", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Under Armour", "category": "direct_brands", "vat_rate": "19.0", "country": "Germany"},
            {"name": "MEGA Construx", "category": "specialty_stores", "vat_rate": "19.0", "country": "Germany"},
            {"name": "HotWheels", "category": "specialty_stores", "vat_rate": "19.0", "country": "Germany"},
            {"name": "Taschen", "category": "specialty_stores", "vat_rate": "19.0", "country": "Germany"}
        ]

        created_suppliers = []

        for supplier_data in notion_suppliers:
            # Check if supplier already exists
            existing_query = select(Supplier).where(Supplier.name == supplier_data["name"])
            result = await self.db.execute(existing_query)
            existing = result.scalar_one_or_none()

            if existing:
                logger.info("Supplier already exists", name=supplier_data["name"])
                created_suppliers.append(existing.id)
                continue

            # Create new supplier
            supplier_id = await self.create_supplier_from_notion_data(supplier_data)
            created_suppliers.append(supplier_id)

        logger.info("Bulk supplier creation completed",
                   total_suppliers=len(notion_suppliers),
                   created_count=len(created_suppliers))

        return created_suppliers

    async def calculate_supplier_performance(self, supplier_id: UUID, month_year: date) -> Dict:
        """
        Calculate monthly supplier performance metrics (Notion intelligence)
        """

        # Get inventory items from this supplier
        query = select(InventoryItem, Product).join(Product).where(
            and_(
                InventoryItem.supplier_obj.has(id=supplier_id),
                InventoryItem.purchase_date >= month_year,
                InventoryItem.purchase_date < date(month_year.year, month_year.month + 1, 1)
            )
        )

        result = await self.db.execute(query)
        items = result.fetchall()

        if not items:
            return {
                "total_orders": 0,
                "avg_delivery_time": 0,
                "return_rate": 0,
                "avg_roi": 0
            }

        total_orders = len(items)
        total_roi = sum(float(item.roi_percentage or 0) for item, _ in items)
        avg_roi = total_roi / total_orders if total_orders > 0 else 0

        # Estimate delivery time based on shelf life (simplified)
        avg_delivery_time = sum(
            min(float(item.shelf_life_days or 7), 7) for item, _ in items
        ) / total_orders if total_orders > 0 else 7

        # Estimate return rate (simplified - based on items without sales)
        unsold_items = sum(1 for item, _ in items if item.status == "in_stock")
        return_rate = (unsold_items / total_orders * 100) if total_orders > 0 else 0

        performance_data = {
            "total_orders": total_orders,
            "avg_delivery_time": avg_delivery_time,
            "return_rate": return_rate,
            "avg_roi": avg_roi
        }

        # Store performance record
        performance = SupplierPerformance(
            supplier_id=supplier_id,
            month_year=month_year,
            total_orders=total_orders,
            avg_delivery_time=Decimal(str(avg_delivery_time)),
            return_rate=Decimal(str(return_rate)),
            avg_roi=Decimal(str(avg_roi))
        )

        self.db.add(performance)
        await self.db.commit()

        logger.info("Supplier performance calculated",
                   supplier_id=str(supplier_id),
                   month_year=month_year.isoformat(),
                   performance=performance_data)

        return performance_data

    async def get_supplier_intelligence_dashboard(self) -> Dict:
        """
        Get comprehensive supplier intelligence dashboard
        45+ supplier analytics with performance insights
        """

        # Get supplier category distribution
        category_query = select(
            Supplier.supplier_category,
            func.count(Supplier.id).label('count')
        ).group_by(Supplier.supplier_category)

        category_result = await self.db.execute(category_query)
        category_distribution = {row.supplier_category: row.count for row in category_result.fetchall()}

        # Get top performing suppliers
        top_performers_query = select(SupplierPerformance, Supplier).join(Supplier).where(
            SupplierPerformance.avg_roi > 0
        ).order_by(desc(SupplierPerformance.avg_roi)).limit(10)

        top_result = await self.db.execute(top_performers_query)
        top_performers = []

        for perf, supplier in top_result.fetchall():
            top_performers.append({
                "supplier_name": supplier.name,
                "category": supplier.supplier_category,
                "avg_roi": float(perf.avg_roi or 0),
                "total_orders": perf.total_orders,
                "avg_delivery_time": float(perf.avg_delivery_time or 0)
            })

        # Get supplier count by country
        country_query = select(
            Supplier.country,
            func.count(Supplier.id).label('count')
        ).group_by(Supplier.country)

        country_result = await self.db.execute(country_query)
        country_distribution = {row.country: row.count for row in country_result.fetchall()}

        # Overall statistics
        total_suppliers_query = select(func.count(Supplier.id))
        total_suppliers_result = await self.db.execute(total_suppliers_query)
        total_suppliers = total_suppliers_result.scalar() or 0

        dashboard = {
            "summary": {
                "total_suppliers": total_suppliers,
                "total_categories": len(category_distribution),
                "notion_target": 45,
                "completion_percentage": (total_suppliers / 45 * 100) if total_suppliers <= 45 else 100
            },
            "category_distribution": category_distribution,
            "country_distribution": country_distribution,
            "top_performers": top_performers,
            "analysis_date": datetime.now().isoformat()
        }

        logger.info("Supplier intelligence dashboard generated", summary=dashboard["summary"])

        return dashboard

    async def get_supplier_recommendations(self, category: Optional[str] = None) -> List[Dict]:
        """
        Get supplier recommendations based on performance data
        """

        query = select(Supplier, SupplierPerformance).outerjoin(SupplierPerformance)

        if category:
            query = query.where(Supplier.supplier_category == category)

        query = query.order_by(desc(SupplierPerformance.avg_roi))

        result = await self.db.execute(query)
        recommendations = []

        for supplier, performance in result.fetchall():
            score = self._calculate_supplier_score(supplier, performance)

            recommendation = {
                "supplier_id": str(supplier.id),
                "name": supplier.name,
                "category": supplier.supplier_category,
                "country": supplier.country,
                "vat_rate": float(supplier.vat_rate or 0),
                "performance_score": score,
                "avg_roi": float(performance.avg_roi or 0) if performance else 0,
                "recommendation_reason": self._generate_recommendation_reason(supplier, performance, score)
            }

            recommendations.append(recommendation)

        return recommendations[:20]  # Top 20 recommendations

    def _calculate_supplier_score(self, supplier: Supplier, performance: Optional[SupplierPerformance]) -> float:
        """Calculate supplier recommendation score (0-100)"""
        score = 50  # Base score

        if performance:
            # ROI contribution (max 30 points)
            roi_score = min(float(performance.avg_roi or 0) / 50 * 30, 30)
            score += roi_score

            # Delivery time contribution (max 10 points)
            delivery_score = max(10 - float(performance.avg_delivery_time or 7), 0)
            score += delivery_score

            # Return rate contribution (max 10 points)
            return_score = max(10 - float(performance.return_rate or 0) / 10, 0)
            score += return_score

        # Category bonus
        if supplier.supplier_category in ["direct_brands", "sneaker_retailers"]:
            score += 5

        return min(score, 100)

    def _generate_recommendation_reason(self, supplier: Supplier, performance: Optional[SupplierPerformance], score: float) -> str:
        """Generate human-readable recommendation reason"""
        if score >= 80:
            return "Excellent performer with high ROI and reliable delivery"
        elif score >= 60:
            return "Good supplier with decent performance metrics"
        elif score >= 40:
            return "Average supplier, suitable for diversification"
        else:
            return "Consider for specific products only"