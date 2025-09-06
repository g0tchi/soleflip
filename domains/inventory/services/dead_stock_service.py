"""
Dead Stock Identification System
Intelligente Erkennung und Behandlung von schwer verkäuflichem Inventar
"""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from dataclasses import dataclass
from enum import Enum

import structlog
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import InventoryItem, Product

logger = structlog.get_logger(__name__)


class StockRiskLevel(Enum):
    """Stock risk categories"""
    HOT = "hot"           # 0-25% risk - schnell drehende Items
    WARM = "warm"         # 26-50% risk - normale Verkaufsgeschwindigkeit
    COLD = "cold"         # 51-75% risk - langsam drehend
    DEAD = "dead"         # 76-100% risk - praktisch unverkäuflich
    CRITICAL = "critical" # >100% - sofortige Aktion erforderlich


@dataclass
class DeadStockItem:
    """Dead stock item data structure"""
    item_id: UUID
    product_name: str
    brand_name: str
    size_value: str
    purchase_price: Decimal
    current_market_price: Optional[Decimal]
    days_in_inventory: int
    risk_score: float
    risk_level: StockRiskLevel
    locked_capital: Decimal
    potential_loss: Decimal
    last_price_check: Optional[datetime]
    recommended_actions: List[str]
    market_trend: str
    velocity_score: float
    

@dataclass
class DeadStockAnalysis:
    """Complete dead stock analysis"""
    total_items_analyzed: int
    dead_stock_items: List[DeadStockItem]
    risk_summary: Dict[str, int]
    financial_impact: Dict[str, float]
    recommendations: List[str]
    analysis_timestamp: datetime


class DeadStockService:
    """
    Dead Stock Identification and Management System
    
    Intelligente Algorithmen zur Erkennung von:
    - Langsamdrehern (slow movers)
    - Preisverfall-Kandidaten (price decline candidates)  
    - Trend-Verlierern (trend losers)
    - Saisonalen Auslaufern (seasonal end-of-life)
    - Überbestand-Positionen (overstock positions)
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.logger = logger.bind(service="dead_stock")
        
        # Konfigurierbare Schwellenwerte
        self.config = {
            "max_days_hot": 30,      # Items unter 30 Tagen = HOT
            "max_days_warm": 60,     # 31-60 Tage = WARM  
            "max_days_cold": 120,    # 61-120 Tage = COLD
            "max_days_dead": 180,    # 121-180 Tage = DEAD
            # Über 180 Tage = CRITICAL
            
            "price_decline_threshold": 0.15,  # 15% Preisrückgang
            "market_trend_weight": 0.3,       # 30% Gewichtung Markttrend
            "velocity_weight": 0.4,           # 40% Gewichtung Verkaufsgeschwindigkeit
            "age_weight": 0.3,                # 30% Gewichtung Alter
            
            "min_market_price_ratio": 0.8,   # Mindestens 80% des Einkaufspreises
        }

    async def analyze_dead_stock(
        self, 
        brand_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        min_risk_score: float = 0.5
    ) -> DeadStockAnalysis:
        """
        Vollständige Dead Stock Analyse des Inventars
        
        Args:
            brand_filter: Nur bestimmte Marke analysieren
            category_filter: Nur bestimmte Kategorie analysieren
            min_risk_score: Minimaler Risk Score (0.0 - 1.0)
        """
        self.logger.info(
            "Starting dead stock analysis",
            brand_filter=brand_filter,
            category_filter=category_filter,
            min_risk_score=min_risk_score
        )
        
        analysis_start = datetime.now(timezone.utc)
        
        try:
            # 1. Inventar Items für Analyse holen
            inventory_items = await self._get_inventory_for_analysis(
                brand_filter, category_filter
            )
            
            self.logger.info(f"Analyzing {len(inventory_items)} inventory items")
            
            # 2. Jeden Item analysieren
            dead_stock_items = []
            for item in inventory_items:
                risk_analysis = await self._analyze_item_risk(item)
                
                if risk_analysis.risk_score >= min_risk_score:
                    dead_stock_items.append(risk_analysis)
            
            # 3. Risk Summary erstellen
            risk_summary = self._calculate_risk_summary(dead_stock_items)
            
            # 4. Financial Impact berechnen
            financial_impact = self._calculate_financial_impact(dead_stock_items)
            
            # 5. Handlungsempfehlungen generieren
            recommendations = self._generate_recommendations(dead_stock_items, financial_impact)
            
            analysis = DeadStockAnalysis(
                total_items_analyzed=len(inventory_items),
                dead_stock_items=dead_stock_items,
                risk_summary=risk_summary,
                financial_impact=financial_impact,
                recommendations=recommendations,
                analysis_timestamp=analysis_start
            )
            
            self.logger.info(
                "Dead stock analysis completed",
                total_analyzed=analysis.total_items_analyzed,
                dead_stock_count=len(dead_stock_items),
                locked_capital=financial_impact.get("total_locked_capital", 0),
                potential_loss=financial_impact.get("total_potential_loss", 0)
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Dead stock analysis failed: {e}")
            raise

    async def _get_inventory_for_analysis(
        self, 
        brand_filter: Optional[str] = None,
        category_filter: Optional[str] = None
    ) -> List[InventoryItem]:
        """Inventar Items für Analyse holen"""
        try:
            # Base query - nur Items mit Einkaufspreis und in_stock
            stmt = (
                select(InventoryItem)
                .join(Product, InventoryItem.product_id == Product.id)
                .where(
                    and_(
                        InventoryItem.status.in_(["in_stock", "listed_stockx"]),
                        InventoryItem.purchase_price.isnot(None),
                        InventoryItem.purchase_date.isnot(None)
                    )
                )
            )
            
            # Brand Filter
            if brand_filter:
                from shared.database.models import Brand
                stmt = stmt.join(Brand, Product.brand_id == Brand.id).where(
                    Brand.name.ilike(f"%{brand_filter}%")
                )
            
            # Category Filter  
            if category_filter:
                from shared.database.models import Category
                stmt = stmt.join(Category, Product.category_id == Category.id).where(
                    Category.name.ilike(f"%{category_filter}%")
                )
            
            # Sortierung nach Alter (älteste zuerst)
            stmt = stmt.order_by(InventoryItem.purchase_date.asc())
            
            result = await self.db_session.execute(stmt)
            items = result.scalars().all()
            
            # Relationships laden
            for item in items:
                await self.db_session.refresh(
                    item, 
                    ["product", "product.brand", "product.category", "size"]
                )
            
            return list(items)
            
        except Exception as e:
            self.logger.error(f"Failed to get inventory for analysis: {e}")
            return []

    async def _analyze_item_risk(self, item: InventoryItem) -> DeadStockItem:
        """Einzelnen Item auf Dead Stock Risiko analysieren"""
        
        # Basis-Informationen
        product_name = item.product.name if item.product else "Unknown"
        brand_name = item.product.brand.name if item.product and item.product.brand else "Unknown"
        size_value = item.size.value if item.size else "N/A"
        
        # Alter berechnen
        purchase_date = item.purchase_date or item.created_at
        days_in_inventory = (datetime.now(timezone.utc) - purchase_date.replace(tzinfo=timezone.utc)).days
        
        # Marktpreis simulieren (später echte StockX Integration)
        current_market_price = await self._get_current_market_price(item)
        
        # Risk Score berechnen
        risk_components = await self._calculate_risk_components(
            item, days_in_inventory, current_market_price
        )
        
        risk_score = (
            risk_components["age_risk"] * self.config["age_weight"] +
            risk_components["market_risk"] * self.config["market_trend_weight"] +
            risk_components["velocity_risk"] * self.config["velocity_weight"]
        )
        
        # Risk Level bestimmen
        risk_level = self._determine_risk_level(days_in_inventory, risk_score)
        
        # Financial Impact
        locked_capital = item.purchase_price * item.quantity
        potential_loss = self._calculate_potential_loss(
            item.purchase_price, current_market_price, risk_score
        )
        
        # Handlungsempfehlungen
        recommendations = self._generate_item_recommendations(
            risk_level, days_in_inventory, risk_components
        )
        
        return DeadStockItem(
            item_id=item.id,
            product_name=product_name,
            brand_name=brand_name,
            size_value=size_value,
            purchase_price=item.purchase_price,
            current_market_price=current_market_price,
            days_in_inventory=days_in_inventory,
            risk_score=min(risk_score, 1.0),  # Cap at 1.0
            risk_level=risk_level,
            locked_capital=locked_capital,
            potential_loss=potential_loss,
            last_price_check=datetime.now(timezone.utc),
            recommended_actions=recommendations,
            market_trend=risk_components.get("trend_direction", "stable"),
            velocity_score=risk_components["velocity_risk"]
        )

    async def _get_current_market_price(self, item: InventoryItem) -> Optional[Decimal]:
        """Aktueller Marktpreis (simuliert - später echte StockX API Integration)"""
        if not item.purchase_price:
            return None
            
        # Simuliere Marktpreis basierend auf Alter und Zufall
        base_price = float(item.purchase_price)
        
        # Alter-basierte Preisanpassung
        age_days = (datetime.now(timezone.utc) - (item.purchase_date or item.created_at).replace(tzinfo=timezone.utc)).days
        
        if age_days < 30:
            # Neue Items: +10% bis +20%
            multiplier = 1.1 + (age_days / 300)  # 1.1 to 1.2
        elif age_days < 90:
            # Mittelalte Items: -5% bis +5%
            multiplier = 0.95 + ((90 - age_days) / 900)  # 0.95 to 1.05
        else:
            # Alte Items: -20% bis -5%
            multiplier = 0.8 + ((180 - min(age_days, 180)) / 600)  # 0.8 to 0.95
        
        # Brand-basierte Anpassung
        brand_name = item.product.brand.name if item.product and item.product.brand else ""
        if brand_name.lower() in ["nike", "jordan", "adidas"]:
            multiplier *= 1.1  # Premium Brands halten Wert besser
        
        market_price = base_price * multiplier
        return Decimal(str(round(market_price, 2)))

    async def _calculate_risk_components(
        self, 
        item: InventoryItem, 
        days_in_inventory: int,
        current_market_price: Optional[Decimal]
    ) -> Dict[str, Any]:
        """Risk-Komponenten für einen Item berechnen"""
        
        # 1. Age Risk (Alter-basiertes Risiko)
        if days_in_inventory <= self.config["max_days_hot"]:
            age_risk = 0.1
        elif days_in_inventory <= self.config["max_days_warm"]:
            age_risk = 0.3
        elif days_in_inventory <= self.config["max_days_cold"]:
            age_risk = 0.6
        elif days_in_inventory <= self.config["max_days_dead"]:
            age_risk = 0.8
        else:
            age_risk = 1.0
        
        # 2. Market Risk (Preis-basiertes Risiko)
        market_risk = 0.5  # Default
        trend_direction = "stable"
        
        if current_market_price and item.purchase_price:
            price_ratio = float(current_market_price) / float(item.purchase_price)
            
            if price_ratio < 0.8:
                market_risk = 0.9
                trend_direction = "declining"
            elif price_ratio < 0.9:
                market_risk = 0.7
                trend_direction = "declining"
            elif price_ratio > 1.2:
                market_risk = 0.2
                trend_direction = "rising"
            elif price_ratio > 1.1:
                market_risk = 0.3
                trend_direction = "rising"
            else:
                market_risk = 0.5
                trend_direction = "stable"
        
        # 3. Velocity Risk (Verkaufsgeschwindigkeits-Risiko)
        # Simuliere basierend auf Brand und Kategorie
        velocity_risk = 0.5  # Default
        
        if item.product and item.product.brand:
            brand_name = item.product.brand.name.lower()
            if brand_name in ["nike", "jordan"]:
                velocity_risk = 0.3  # Schnell drehende Brands
            elif brand_name in ["adidas", "puma"]:
                velocity_risk = 0.4
            else:
                velocity_risk = 0.6  # Langsamere Brands
        
        # Kategorie-Anpassung
        if item.product and item.product.category:
            category_name = item.product.category.name.lower()
            if "sneakers" in category_name:
                velocity_risk *= 0.8  # Sneakers drehen schneller
            elif "boots" in category_name:
                velocity_risk *= 1.2  # Boots drehen langsamer
        
        return {
            "age_risk": age_risk,
            "market_risk": market_risk,
            "velocity_risk": min(velocity_risk, 1.0),
            "trend_direction": trend_direction,
            "days_in_inventory": days_in_inventory
        }

    def _determine_risk_level(self, days_in_inventory: int, risk_score: float) -> StockRiskLevel:
        """Risk Level basierend auf Alter und Score bestimmen"""
        
        # Kritisch: Über 180 Tage oder sehr hoher Risk Score
        if days_in_inventory > 180 or risk_score > 0.9:
            return StockRiskLevel.CRITICAL
        
        # Dead: 121-180 Tage oder hoher Risk Score  
        elif days_in_inventory > 120 or risk_score > 0.75:
            return StockRiskLevel.DEAD
        
        # Cold: 61-120 Tage oder mittlerer Risk Score
        elif days_in_inventory > 60 or risk_score > 0.5:
            return StockRiskLevel.COLD
        
        # Warm: 31-60 Tage oder niedriger Risk Score
        elif days_in_inventory > 30 or risk_score > 0.25:
            return StockRiskLevel.WARM
        
        # Hot: Unter 30 Tage und niedriger Risk Score
        else:
            return StockRiskLevel.HOT

    def _calculate_potential_loss(
        self, 
        purchase_price: Decimal, 
        market_price: Optional[Decimal], 
        risk_score: float
    ) -> Decimal:
        """Potentiellen Verlust berechnen"""
        if not market_price:
            # Schätze Verlust basierend auf Risk Score
            estimated_loss = float(purchase_price) * risk_score * 0.3
            return Decimal(str(round(estimated_loss, 2)))
        
        # Direkter Vergleich Einkaufs- vs Marktpreis
        if market_price < purchase_price:
            loss = purchase_price - market_price
            # Verstärke Verlust basierend auf Risk Score
            adjusted_loss = float(loss) * (1 + risk_score)
            return Decimal(str(round(adjusted_loss, 2)))
        
        return Decimal("0.00")

    def _generate_item_recommendations(
        self, 
        risk_level: StockRiskLevel, 
        days_in_inventory: int,
        risk_components: Dict[str, Any]
    ) -> List[str]:
        """Handlungsempfehlungen für einzelnen Item"""
        
        recommendations = []
        
        if risk_level == StockRiskLevel.CRITICAL:
            recommendations.extend([
                "🚨 SOFORT-AKTION: Drastische Preisreduktion (-30% bis -50%)",
                "📦 Liquidation: Verkauf unter Einkaufspreis erwägen",
                "🎁 Bundle-Angebot: Mit beliebten Items kombinieren",
                "💸 Flash Sale: 24-48h Sonderaktion starten"
            ])
            
        elif risk_level == StockRiskLevel.DEAD:
            recommendations.extend([
                "📉 Aggressive Preissenkung: -20% bis -30%",
                "🏷️ Clearance Sale: Als Auslaufmodell bewerben",
                "📱 Social Media Push: Gezieltes Marketing",
                "🔄 Cross-Platform Listen: Auch auf anderen Plattformen"
            ])
            
        elif risk_level == StockRiskLevel.COLD:
            recommendations.extend([
                "💰 Preisanpassung: -10% bis -15%",
                "📊 Marktanalyse: Konkurrenzpreise prüfen",
                "🎯 Targeted Ads: Spezifische Zielgruppe ansprechen",
                "📈 Listing Optimierung: Bessere Fotos/Beschreibung"
            ])
            
        elif risk_level == StockRiskLevel.WARM:
            recommendations.extend([
                "👀 Monitoring: Wöchentliche Preis-/Marktanalyse",
                "📸 Content Update: Neue Fotos oder Videos",
                "🏪 Schaufenster: Prominente Platzierung im Shop",
                "💌 Newsletter: In nächstem Newsletter featuren"
            ])
            
        else:  # HOT
            recommendations.extend([
                "✅ Status Quo: Aktuelle Strategie beibehalten",
                "📈 Preis-Optimierung: Leichte Preiserhöhung testen",
                "🚀 Marketing Push: Momentum nutzen für mehr Verkäufe"
            ])
        
        # Trend-spezifische Empfehlungen
        if risk_components.get("trend_direction") == "declining":
            recommendations.append("📉 Markttrend beachten: Preis fallend - schnell handeln")
        elif risk_components.get("trend_direction") == "rising":
            recommendations.append("📈 Markttrend nutzen: Preis steigend - höheren Preis ansetzen")
            
        return recommendations

    def _calculate_risk_summary(self, dead_stock_items: List[DeadStockItem]) -> Dict[str, int]:
        """Risk Level Zusammenfassung berechnen"""
        summary = {
            "hot": 0,
            "warm": 0, 
            "cold": 0,
            "dead": 0,
            "critical": 0
        }
        
        for item in dead_stock_items:
            summary[item.risk_level.value] += 1
            
        return summary

    def _calculate_financial_impact(self, dead_stock_items: List[DeadStockItem]) -> Dict[str, float]:
        """Financial Impact berechnen"""
        total_locked_capital = sum(float(item.locked_capital) for item in dead_stock_items)
        total_potential_loss = sum(float(item.potential_loss) for item in dead_stock_items)
        
        # Risk Level aufschlüsseln
        locked_by_risk = {}
        loss_by_risk = {}
        
        for risk_level in StockRiskLevel:
            level_items = [item for item in dead_stock_items if item.risk_level == risk_level]
            locked_by_risk[risk_level.value] = sum(float(item.locked_capital) for item in level_items)
            loss_by_risk[risk_level.value] = sum(float(item.potential_loss) for item in level_items)
        
        return {
            "total_locked_capital": total_locked_capital,
            "total_potential_loss": total_potential_loss,
            "locked_capital_by_risk": locked_by_risk,
            "potential_loss_by_risk": loss_by_risk,
            "loss_percentage": (total_potential_loss / total_locked_capital * 100) if total_locked_capital > 0 else 0
        }

    def _generate_recommendations(
        self, 
        dead_stock_items: List[DeadStockItem],
        financial_impact: Dict[str, float]
    ) -> List[str]:
        """Globale Handlungsempfehlungen generieren"""
        
        recommendations = []
        
        critical_count = len([item for item in dead_stock_items if item.risk_level == StockRiskLevel.CRITICAL])
        dead_count = len([item for item in dead_stock_items if item.risk_level == StockRiskLevel.DEAD])
        total_locked = financial_impact["total_locked_capital"]
        total_loss = financial_impact["total_potential_loss"]
        
        # Prioritäts-Empfehlungen
        if critical_count > 0:
            recommendations.append(
                f"🚨 PRIORITÄT 1: {critical_count} kritische Items sofort liquidieren - "
                f"€{financial_impact['locked_capital_by_risk'].get('critical', 0):.2f} gebunden"
            )
        
        if dead_count > 0:
            recommendations.append(
                f"📉 PRIORITÄT 2: {dead_count} Dead Stock Items mit Clearance Sale abverkaufen"
            )
        
        # Financial Empfehlungen
        if total_loss > total_locked * 0.2:
            recommendations.append(
                f"💰 FINANZ-WARNUNG: {total_loss:.2f}€ potentieller Verlust "
                f"({financial_impact['loss_percentage']:.1f}% des gebundenen Kapitals)"
            )
        
        if total_locked > 10000:
            recommendations.append(
                f"🏦 KAPITAL-OPTIMIERUNG: {total_locked:.2f}€ gebundenes Kapital durch "
                "Liquidation für neue Investitionen freimachen"
            )
        
        # Strategische Empfehlungen
        recommendations.extend([
            "📊 ANALYTICS: Wöchentliche Dead Stock Analyse etablieren",
            "🔄 AUTOMATION: Auto-Repricing für Cold/Dead Stock aktivieren",
            "📱 MARKETING: Targeted Clearance Kampagnen starten",
            "📈 PREVENTION: Einkaufskriterien basierend auf Trends anpassen"
        ])
        
        return recommendations

    async def get_dead_stock_summary(self) -> Dict[str, Any]:
        """Schnelle Dead Stock Übersicht"""
        try:
            analysis = await self.analyze_dead_stock(min_risk_score=0.5)
            
            return {
                "total_items_at_risk": len(analysis.dead_stock_items),
                "risk_breakdown": analysis.risk_summary,
                "financial_impact": {
                    "locked_capital": analysis.financial_impact["total_locked_capital"],
                    "potential_loss": analysis.financial_impact["total_potential_loss"],
                    "loss_percentage": analysis.financial_impact["loss_percentage"]
                },
                "top_priorities": [
                    item for item in analysis.dead_stock_items 
                    if item.risk_level in [StockRiskLevel.CRITICAL, StockRiskLevel.DEAD]
                ][:5],
                "last_analysis": analysis.analysis_timestamp.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get dead stock summary: {e}")
            return {
                "error": str(e),
                "total_items_at_risk": 0,
                "risk_breakdown": {},
                "financial_impact": {}
            }

    async def execute_automated_clearance(
        self, 
        risk_levels: List[StockRiskLevel] = None,
        max_items: int = 50,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Automatische Clearance-Aktionen für Dead Stock
        
        Args:
            risk_levels: Welche Risk Levels behandeln (default: DEAD, CRITICAL)
            max_items: Maximale Anzahl Items
            dry_run: Test-Modus ohne echte Änderungen
        """
        if risk_levels is None:
            risk_levels = [StockRiskLevel.DEAD, StockRiskLevel.CRITICAL]
            
        self.logger.info(f"Starting automated clearance", risk_levels=risk_levels, dry_run=dry_run)
        
        try:
            # Dead Stock Analyse
            analysis = await self.analyze_dead_stock(min_risk_score=0.6)
            
            # Filter nach Risk Levels
            target_items = [
                item for item in analysis.dead_stock_items 
                if item.risk_level in risk_levels
            ][:max_items]
            
            actions_taken = []
            total_price_reductions = 0
            
            for item in target_items:
                # Clearance Preis berechnen
                clearance_discount = 0.3 if item.risk_level == StockRiskLevel.CRITICAL else 0.2
                new_price = item.purchase_price * (1 - Decimal(clearance_discount))
                
                action = {
                    "item_id": str(item.item_id),
                    "product_name": item.product_name,
                    "original_price": float(item.purchase_price),
                    "new_price": float(new_price),
                    "discount_percent": clearance_discount * 100,
                    "action_type": "clearance_pricing"
                }
                
                if not dry_run:
                    # Hier würde echte Preis-Update Logik stehen
                    # await self._update_item_price(item.item_id, new_price)
                    pass
                
                actions_taken.append(action)
                total_price_reductions += float(item.purchase_price - new_price)
            
            return {
                "success": True,
                "dry_run": dry_run,
                "items_processed": len(target_items),
                "actions_taken": actions_taken,
                "total_price_reductions": total_price_reductions,
                "estimated_capital_freed": sum(float(item.locked_capital) for item in target_items)
            }
            
        except Exception as e:
            self.logger.error(f"Automated clearance failed: {e}")
            return {"success": False, "error": str(e)}