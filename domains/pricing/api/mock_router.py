"""
Mock Pricing & Analytics API Router - Temporary endpoints with sample data
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter()


# Mock response models
class MockPricingInsights(BaseModel):
    timestamp: str
    summary: Dict[str, Any]
    recommendations: List[str]


class MockPredictiveInsights(BaseModel):
    timestamp: str
    business_metrics: Dict[str, Any]
    predictive_insights: List[str]
    growth_opportunities: List[str]
    risk_factors: List[str]
    recommendations: List[str]
    confidence_score: float


class MockMarketTrend(BaseModel):
    period: str
    trend_direction: str
    strength: float
    key_drivers: List[str]
    forecast_impact: str


@router.get("/insights", response_model=MockPricingInsights)
async def get_pricing_insights():
    """Mock pricing insights endpoint"""
    return MockPricingInsights(
        timestamp=datetime.utcnow().isoformat() + "Z",
        summary={
            "total_products_analyzed": 853,
            "average_price": 95.50,
            "average_margin_percent": 24.5,
            "total_price_updates": 127,
            "recent_updates_30d": 23,
        },
        recommendations=[
            "Consider dynamic pricing for high-demand items",
            "Review pricing strategy for low-margin products",
            "Optimize seasonal pricing adjustments",
        ],
    )


@router.get("/strategies")
async def get_pricing_strategies():
    """Mock pricing strategies endpoint"""
    return {
        "cost_plus": {
            "name": "Cost Plus",
            "description": "Add fixed margin to product cost",
            "use_case": "Simple, predictable pricing",
        },
        "market_based": {
            "name": "Market Based",
            "description": "Price based on current market conditions",
            "use_case": "Competitive positioning",
        },
        "dynamic": {
            "name": "Dynamic",
            "description": "AI-powered adaptive pricing",
            "use_case": "Maximum profit optimization",
        },
    }


# Smart Pricing Mock Endpoints
class MockAutoRepricingToggleRequest(BaseModel):
    enabled: bool


# Predictive Insights Models
class MockPredictiveInsight(BaseModel):
    insight_id: str
    insight_type: str
    priority: str
    title: str
    description: str
    product_id: str = None
    product_name: str = None
    confidence_score: float
    recommended_actions: List[Dict[str, Any]]
    supporting_data: Dict[str, Any]
    expires_at: str

class MockInventoryForecast(BaseModel):
    product_id: str
    product_name: str
    current_stock: int
    predicted_demand_30d: float
    predicted_demand_90d: float
    restock_recommendation: str
    optimal_restock_quantity: int
    days_until_stockout: int = None
    confidence_level: float
    seasonal_factors: Dict[str, Any]

class MockRestockRecommendation(BaseModel):
    product_id: str
    product_name: str
    current_stock: int
    recommended_quantity: int
    investment_required: float
    projected_revenue: float
    projected_profit: float
    roi_estimate: float
    optimal_timing: str
    risk_level: str
    supporting_insights: List[str]


@router.post("/smart/optimize-inventory")
async def optimize_inventory_pricing(strategy: str = "profit_maximization", limit: int = 50):
    """Mock Smart Pricing inventory optimization endpoint"""
    return {
        "total_items_analyzed": limit,
        "items_optimized": min(15, limit),
        "potential_profit_increase": 1247.50,
        "pricing_strategy": strategy,
        "market_conditions": "bullish",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "recommendations": [
            {
                "product_name": "Air Jordan 1 High OG",
                "current_price": 180.0,
                "recommended_price": 195.0,
                "profit_increase": 15.0,
                "confidence": 0.85
            },
            {
                "product_name": "Nike Dunk Low",
                "current_price": 90.0,
                "recommended_price": 98.0,
                "profit_increase": 8.0,
                "confidence": 0.72
            },
            {
                "product_name": "Yeezy Boost 350 V2",
                "current_price": 220.0,
                "recommended_price": 240.0,
                "profit_increase": 20.0,
                "confidence": 0.91
            }
        ]
    }


@router.get("/smart/auto-repricing/status")
async def get_auto_repricing_status():
    """Mock Auto-Repricing status endpoint"""
    return {
        "enabled": True,
        "last_run": "2025-09-05T12:30:00Z",
        "items_repriced": 23,
        "strategy": "profit_maximization",
        "next_run": "2025-09-05T18:30:00Z",
        "rules_applied": 5
    }


@router.post("/smart/auto-repricing/toggle")
async def toggle_auto_repricing(request: MockAutoRepricingToggleRequest):
    """Mock Auto-Repricing toggle endpoint"""
    return {
        "success": True,
        "enabled": request.enabled,
        "message": f"Auto-repricing {'enabled' if request.enabled else 'disabled'} successfully"
    }


@router.get("/smart/market-trends")
async def get_smart_market_trends():
    """Mock Smart Market trends endpoint"""
    return {
        "current_condition": "bullish",
        "trend_strength": 0.75,
        "volatility_level": "moderate",
        "price_momentum": "increasing",
        "recommended_action": "Increase prices by 5-8% for high-demand items",
        "confidence_score": 0.82,
        "key_insights": [
            "StockX sales volume up 15% this week",
            "Nike brand showing strong performance",
            "Retro releases gaining momentum"
        ]
    }


# Auto-Listing Rules Engine Mock Endpoints
class MockAutoListingRequest(BaseModel):
    max_items: int = 50
    dry_run: bool = True


class MockRuleToggleRequest(BaseModel):
    rule_name: str
    active: bool


@router.get("/auto-listing/status")
async def get_auto_listing_status():
    """Mock Auto-Listing status endpoint"""
    return {
        "enabled": True,
        "total_rules": 5,
        "active_rules": 4,
        "last_run": "2025-09-05T14:15:00Z",
        "next_scheduled_run": "2025-09-05T18:00:00Z",
        "items_processed_today": 23,
        "items_listed_today": 8,
        "success_rate_percent": 87.5,
        "rules": [
            {
                "name": "High Profit Margin Auto-List",
                "active": True,
                "priority": 10,
                "conditions_count": 4,
                "items_matched_today": 3
            },
            {
                "name": "Quick Turnover Items", 
                "active": True,
                "priority": 20,
                "conditions_count": 5,
                "items_matched_today": 5
            },
            {
                "name": "Premium Items Strategy",
                "active": True,
                "priority": 30,
                "conditions_count": 4,
                "items_matched_today": 0
            },
            {
                "name": "Dead Stock Prevention",
                "active": False,
                "priority": 5,
                "conditions_count": 3,
                "items_matched_today": 0
            },
            {
                "name": "Market Opportunity Capture",
                "active": True,
                "priority": 5,
                "conditions_count": 4,
                "items_matched_today": 0
            }
        ]
    }


@router.post("/auto-listing/execute")
async def execute_auto_listing(request: MockAutoListingRequest):
    """Mock Auto-Listing execution endpoint"""
    return {
        "execution_id": f"exec-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "max_items": request.max_items,
        "dry_run": request.dry_run,
        "items_evaluated": min(request.max_items, 15),
        "items_listed": 0 if request.dry_run else 6,
        "rules_matched": 8,
        "errors": 0,
        "skipped": 9,
        "execution_time": 2.34,
        "listings_created": [
            {
                "item_id": "item-001",
                "product_name": "Air Jordan 1 High OG Bred Toe",
                "rule_applied": "High Profit Margin Auto-List",
                "price": 285.00,
                "platform": "stockx",
                "dry_run": request.dry_run
            },
            {
                "item_id": "item-002", 
                "product_name": "Nike Dunk Low Panda",
                "rule_applied": "Quick Turnover Items",
                "price": 145.00,
                "platform": "stockx",
                "dry_run": request.dry_run
            },
            {
                "item_id": "item-003",
                "product_name": "Yeezy Boost 350 V2 Oreo",
                "rule_applied": "Market Opportunity Capture",
                "price": 320.00,
                "platform": "stockx", 
                "dry_run": request.dry_run
            }
        ] if not request.dry_run else [
            {
                "item_id": "item-001",
                "product_name": "Air Jordan 1 High OG Bred Toe",
                "rule_applied": "High Profit Margin Auto-List",
                "would_list": True,
                "estimated_price": 285.00,
                "dry_run": True
            },
            {
                "item_id": "item-002",
                "product_name": "Nike Dunk Low Panda", 
                "rule_applied": "Quick Turnover Items",
                "would_list": True,
                "estimated_price": 145.00,
                "dry_run": True
            }
        ]
    }


@router.post("/auto-listing/simulate")  
async def simulate_auto_listing(rule_name: str = None, max_items: int = 10):
    """Mock Auto-Listing simulation endpoint"""
    return {
        "simulation_complete": True,
        "rule_tested": rule_name or "All Rules",
        "items_evaluated": max_items,
        "items_that_would_be_listed": 3,
        "rules_matched": 4,
        "potential_revenue": 750.00,
        "average_markup_percent": 22.5,
        "execution_time": 0.85,
        "matched_items": [
            {
                "item_id": "sim-001",
                "product_name": "Air Force 1 Low White",
                "rule_matched": rule_name or "Quick Turnover Items",
                "current_status": "in_stock",
                "purchase_price": 85.00,
                "estimated_listing_price": 125.00,
                "profit_margin_percent": 47.1,
                "confidence": 0.89
            },
            {
                "item_id": "sim-002", 
                "product_name": "Jordan 4 Retro Black Cat",
                "rule_matched": rule_name or "High Profit Margin Auto-List",
                "current_status": "in_stock",
                "purchase_price": 180.00,
                "estimated_listing_price": 245.00,
                "profit_margin_percent": 36.1,
                "confidence": 0.92
            }
        ]
    }


@router.post("/auto-listing/toggle-rule")
async def toggle_listing_rule(request: MockRuleToggleRequest):
    """Mock Auto-Listing rule toggle endpoint"""
    return {
        "success": True,
        "rule_name": request.rule_name,
        "previous_state": not request.active,
        "new_state": request.active,
        "message": f"Rule '{request.rule_name}' {'enabled' if request.active else 'disabled'}",
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/auto-listing/rules/{rule_name}")
async def get_listing_rule_details(rule_name: str):
    """Mock endpoint to get detailed information about a specific listing rule"""
    rule_details = {
        "High Profit Margin Auto-List": {
            "name": "High Profit Margin Auto-List",
            "active": True,
            "priority": 10,
            "created_at": "2025-09-01T10:00:00Z",
            "conditions": {
                "min_profit_margin_percent": 25.0,
                "status": ["in_stock"],
                "purchase_age_days": 7,
                "market_condition": ["bullish", "stable"]
            },
            "actions": {
                "list_on_platform": "stockx",
                "pricing_strategy": "market_based", 
                "markup_percent": 20.0,
                "expires_in_days": 30
            },
            "stats": {
                "items_matched_7d": 12,
                "items_listed_7d": 8,
                "success_rate": 66.7,
                "avg_profit_margin": 28.4
            }
        },
        "Quick Turnover Items": {
            "name": "Quick Turnover Items",
            "active": True,
            "priority": 20,
            "created_at": "2025-09-01T10:00:00Z",
            "conditions": {
                "brand_names": ["Nike", "Adidas", "Jordan"],
                "status": ["in_stock"],
                "min_profit_margin_percent": 15.0,
                "category": "Sneakers",
                "purchase_price_range": [100, 500]
            },
            "actions": {
                "list_on_platform": "stockx",
                "pricing_strategy": "competitive",
                "markup_percent": 18.0,
                "expires_in_days": 14
            },
            "stats": {
                "items_matched_7d": 18,
                "items_listed_7d": 15,
                "success_rate": 83.3,
                "avg_profit_margin": 19.2
            }
        }
    }
    
    if rule_name not in rule_details:
        return {"error": f"Rule '{rule_name}' not found"}
    
    return rule_details[rule_name]


# Dead Stock Identification System Mock Endpoints
class MockDeadStockAnalysisRequest(BaseModel):
    brand_filter: Optional[str] = None
    category_filter: Optional[str] = None
    min_risk_score: float = 0.5


class MockClearanceRequest(BaseModel):
    risk_levels: List[str] = ["dead", "critical"]
    max_items: int = 50
    dry_run: bool = True


@router.get("/dead-stock/summary")
async def get_dead_stock_summary():
    """Mock Dead Stock summary endpoint"""
    return {
        "total_items_at_risk": 47,
        "risk_breakdown": {
            "hot": 156,
            "warm": 89,
            "cold": 32,
            "dead": 28,
            "critical": 19
        },
        "financial_impact": {
            "locked_capital": 18420.50,
            "potential_loss": 4230.75,
            "loss_percentage": 22.9
        },
        "top_priorities": [
            {
                "item_id": "dead-001",
                "product_name": "Air Jordan 4 Retro Lightning",
                "brand_name": "Jordan",
                "size_value": "9.5",
                "purchase_price": 180.00,
                "current_market_price": 135.00,
                "days_in_inventory": 195,
                "risk_score": 0.92,
                "risk_level": "critical",
                "locked_capital": 180.00,
                "potential_loss": 65.00,
                "recommended_actions": [
                    "🚨 SOFORT-AKTION: Drastische Preisreduktion (-30% bis -50%)",
                    "📦 Liquidation: Verkauf unter Einkaufspreis erwägen"
                ]
            },
            {
                "item_id": "dead-002", 
                "product_name": "Yeezy Boost 700 Wave Runner",
                "brand_name": "Adidas",
                "size_value": "10",
                "purchase_price": 350.00,
                "current_market_price": 280.00,
                "days_in_inventory": 167,
                "risk_score": 0.87,
                "risk_level": "critical", 
                "locked_capital": 350.00,
                "potential_loss": 90.00,
                "recommended_actions": [
                    "🚨 SOFORT-AKTION: Drastische Preisreduktion (-30% bis -50%)",
                    "🎁 Bundle-Angebot: Mit beliebten Items kombinieren"
                ]
            },
            {
                "item_id": "dead-003",
                "product_name": "New Balance 990v5 Grey",
                "brand_name": "New Balance", 
                "size_value": "8.5",
                "purchase_price": 175.00,
                "current_market_price": 145.00,
                "days_in_inventory": 142,
                "risk_score": 0.79,
                "risk_level": "dead",
                "locked_capital": 175.00,
                "potential_loss": 45.00,
                "recommended_actions": [
                    "📉 Aggressive Preissenkung: -20% bis -30%",
                    "🏷️ Clearance Sale: Als Auslaufmodell bewerben"
                ]
            }
        ],
        "last_analysis": datetime.utcnow().isoformat() + "Z"
    }


@router.post("/dead-stock/analyze")
async def analyze_dead_stock(request: MockDeadStockAnalysisRequest):
    """Mock Dead Stock analysis endpoint"""
    return {
        "analysis_id": f"analysis-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "total_items_analyzed": 324,
        "filters_applied": {
            "brand_filter": request.brand_filter,
            "category_filter": request.category_filter,
            "min_risk_score": request.min_risk_score
        },
        "dead_stock_items": [
            {
                "item_id": "item-ds-001",
                "product_name": "Nike Air Max 90 Triple Black",
                "brand_name": "Nike",
                "size_value": "11",
                "purchase_price": 120.00,
                "current_market_price": 95.00,
                "days_in_inventory": 156,
                "risk_score": 0.83,
                "risk_level": "dead",
                "locked_capital": 120.00,
                "potential_loss": 35.00,
                "market_trend": "declining",
                "velocity_score": 0.75,
                "recommended_actions": [
                    "📉 Aggressive Preissenkung: -20% bis -30%",
                    "📱 Social Media Push: Gezieltes Marketing",
                    "📉 Markttrend beachten: Preis fallend - schnell handeln"
                ]
            },
            {
                "item_id": "item-ds-002",
                "product_name": "Adidas Ultraboost 22 Core Black",
                "brand_name": "Adidas",
                "size_value": "9",
                "purchase_price": 180.00,
                "current_market_price": 160.00,
                "days_in_inventory": 98,
                "risk_score": 0.65,
                "risk_level": "cold",
                "locked_capital": 180.00,
                "potential_loss": 25.00,
                "market_trend": "stable",
                "velocity_score": 0.6,
                "recommended_actions": [
                    "💰 Preisanpassung: -10% bis -15%",
                    "📊 Marktanalyse: Konkurrenzpreise prüfen",
                    "📈 Listing Optimierung: Bessere Fotos/Beschreibung"
                ]
            }
        ],
        "risk_summary": {
            "hot": 89,
            "warm": 125,
            "cold": 67,
            "dead": 32,
            "critical": 11
        },
        "financial_impact": {
            "total_locked_capital": 15680.50,
            "total_potential_loss": 3420.25,
            "loss_percentage": 21.8,
            "locked_capital_by_risk": {
                "critical": 4250.00,
                "dead": 5890.50,
                "cold": 3840.00,
                "warm": 1700.00
            }
        },
        "recommendations": [
            "🚨 PRIORITÄT 1: 11 kritische Items sofort liquidieren - €4250.00 gebunden",
            "📉 PRIORITÄT 2: 32 Dead Stock Items mit Clearance Sale abverkaufen", 
            "💰 FINANZ-WARNUNG: 3420.25€ potentieller Verlust (21.8% des gebundenen Kapitals)",
            "📊 ANALYTICS: Wöchentliche Dead Stock Analyse etablieren",
            "🔄 AUTOMATION: Auto-Repricing für Cold/Dead Stock aktivieren"
        ],
        "analysis_timestamp": datetime.utcnow().isoformat() + "Z"
    }


@router.post("/dead-stock/clearance")
async def execute_automated_clearance(request: MockClearanceRequest):
    """Mock automated clearance execution endpoint"""
    return {
        "execution_id": f"clearance-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "success": True,
        "dry_run": request.dry_run,
        "risk_levels_targeted": request.risk_levels,
        "items_processed": min(request.max_items, 23),
        "actions_taken": [
            {
                "item_id": "clear-001",
                "product_name": "Nike Dunk High Retro White Black",
                "original_price": 110.00,
                "new_price": 77.00,
                "discount_percent": 30.0,
                "action_type": "clearance_pricing",
                "estimated_sale_probability": 0.85
            },
            {
                "item_id": "clear-002",
                "product_name": "Air Jordan 1 Mid Chicago",
                "original_price": 130.00,
                "new_price": 91.00,
                "discount_percent": 30.0, 
                "action_type": "clearance_pricing",
                "estimated_sale_probability": 0.92
            },
            {
                "item_id": "clear-003",
                "product_name": "Yeezy Slide Bone",
                "original_price": 60.00,
                "new_price": 48.00,
                "discount_percent": 20.0,
                "action_type": "clearance_pricing",
                "estimated_sale_probability": 0.78
            }
        ] if not request.dry_run else [
            {
                "item_id": "clear-001",
                "product_name": "Nike Dunk High Retro White Black", 
                "would_reduce_from": 110.00,
                "would_reduce_to": 77.00,
                "discount_percent": 30.0,
                "dry_run": True
            }
        ],
        "total_price_reductions": 0 if request.dry_run else 756.50,
        "estimated_capital_freed": 8920.00,
        "projected_outcomes": {
            "estimated_sales_within_30d": 18,
            "estimated_revenue": 6420.50,
            "capital_recovery_rate": 0.72
        },
        "execution_time": 1.87
    }


@router.get("/dead-stock/risk-levels")
async def get_risk_level_definitions():
    """Mock endpoint for risk level definitions and thresholds"""
    return {
        "risk_levels": {
            "hot": {
                "name": "Hot",
                "description": "Schnell drehende Items mit geringem Risiko",
                "risk_score_range": "0.0 - 0.25",
                "age_threshold_days": 30,
                "color": "#22c55e",
                "icon": "🔥",
                "action_priority": "low"
            },
            "warm": {
                "name": "Warm", 
                "description": "Normale Verkaufsgeschwindigkeit",
                "risk_score_range": "0.26 - 0.50",
                "age_threshold_days": 60,
                "color": "#eab308",
                "icon": "☀️",
                "action_priority": "monitor"
            },
            "cold": {
                "name": "Cold",
                "description": "Langsam drehende Items - Aufmerksamkeit erforderlich",
                "risk_score_range": "0.51 - 0.75", 
                "age_threshold_days": 120,
                "color": "#f97316",
                "icon": "🧊",
                "action_priority": "medium"
            },
            "dead": {
                "name": "Dead",
                "description": "Schwer verkäuflich - aggressive Maßnahmen nötig",
                "risk_score_range": "0.76 - 0.90",
                "age_threshold_days": 180,
                "color": "#ef4444", 
                "icon": "💀",
                "action_priority": "high"
            },
            "critical": {
                "name": "Critical",
                "description": "Praktisch unverkäuflich - sofortige Liquidation",
                "risk_score_range": "0.91 - 1.00",
                "age_threshold_days": 180,
                "color": "#991b1b",
                "icon": "🚨", 
                "action_priority": "urgent"
            }
        },
        "calculation_factors": {
            "age_weight": 0.3,
            "market_trend_weight": 0.3,
            "velocity_weight": 0.4,
            "price_decline_threshold": 0.15
        },
        "automation_triggers": {
            "auto_repricing_threshold": 0.6,
            "clearance_threshold": 0.75,
            "liquidation_threshold": 0.9
        }
    }


@router.get("/dead-stock/trends")
async def get_dead_stock_trends():
    """Mock dead stock trends and analytics endpoint"""
    return {
        "trend_period": "30_days",
        "trend_data": [
            {
                "date": "2025-08-07",
                "total_dead_stock_items": 42,
                "locked_capital": 16250.50,
                "items_liquidated": 8,
                "capital_freed": 1890.00
            },
            {
                "date": "2025-08-14", 
                "total_dead_stock_items": 39,
                "locked_capital": 15680.25,
                "items_liquidated": 12,
                "capital_freed": 2340.50
            },
            {
                "date": "2025-08-21",
                "total_dead_stock_items": 44,
                "locked_capital": 17120.75,
                "items_liquidated": 6,
                "capital_freed": 1250.00
            },
            {
                "date": "2025-08-28",
                "total_dead_stock_items": 47,
                "locked_capital": 18420.50,
                "items_liquidated": 15,
                "capital_freed": 3680.75
            }
        ],
        "insights": {
            "trend_direction": "increasing",
            "avg_liquidation_success_rate": 0.73,
            "most_problematic_category": "Lifestyle Sneakers",
            "most_problematic_brand": "New Balance",
            "seasonal_pattern": "Q4 typically shows 15% increase in dead stock"
        },
        "recommendations": [
            "🔍 Category Focus: Lifestyle Sneakers zeigen höchste Dead Stock Rate",
            "🏷️ Brand Strategy: New Balance Items früher mit Discount verkaufen",
            "📅 Seasonal Planning: Q4 Inventory besser steuern",
            "⚡ Automation: Auto-Clearance Rules für wiederkehrende Probleme"
        ]
    }


# =====================================================
# PREDICTIVE INSIGHTS ENDPOINTS
# =====================================================

@router.get("/predictive/insights", response_model=List[MockPredictiveInsight])
async def get_predictive_insights(
    insight_types: str = "all",
    days_ahead: int = 30,
    limit: int = 20
):
    """Mock endpoint for predictive inventory insights"""
    from uuid import uuid4
    
    base_insights = [
        {
            "insight_id": f"restock_{uuid4().hex[:8]}",
            "insight_type": "restock_opportunity",
            "priority": "high",
            "title": "Restock Opportunity: Nike Air Jordan 1 High OG",
            "description": "Predicted demand of 47 units in next 30 days exceeds current stock of 12 units",
            "product_id": "prod_001",
            "product_name": "Nike Air Jordan 1 High OG 'Chicago'",
            "confidence_score": 0.85,
            "recommended_actions": [
                {
                    "action": "restock",
                    "quantity": 45,
                    "priority": "high",
                    "timing": "within_7_days"
                }
            ],
            "supporting_data": {
                "forecast_model": "ensemble",
                "market_trend": "bullish",
                "days_until_stockout": 8,
                "potential_revenue": 4935.00
            },
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
        },
        {
            "insight_id": f"surge_{uuid4().hex[:8]}",
            "insight_type": "demand_surge",
            "priority": "critical",
            "title": "Demand Surge Predicted: Adidas Yeezy Boost 350",
            "description": "Predicted 73% increase in demand over next 30 days",
            "product_id": "prod_002", 
            "product_name": "Adidas Yeezy Boost 350 V2 'Zebra'",
            "confidence_score": 0.78,
            "recommended_actions": [
                {
                    "action": "restock",
                    "urgency": "immediate",
                    "reason": "surge_preparation"
                },
                {
                    "action": "increase_price",
                    "percentage": 12,
                    "timing": "before_surge"
                }
            ],
            "supporting_data": {
                "surge_factor": 1.73,
                "market_conditions": "volatile_bullish",
                "predicted_peak_demand": 28
            },
            "expires_at": (datetime.utcnow() + timedelta(days=3)).isoformat() + "Z"
        },
        {
            "insight_id": f"seasonal_{uuid4().hex[:8]}",
            "insight_type": "seasonal_trend", 
            "priority": "medium",
            "title": "Seasonal Trend: Back to School Season",
            "description": "Seasonal pattern indicates 40% increase in demand for Nike Dunk Low",
            "product_id": "prod_003",
            "product_name": "Nike Dunk Low 'Panda'",
            "confidence_score": 0.65,
            "recommended_actions": [
                {
                    "action": "restock",
                    "seasonal_factor": 1.4,
                    "timing": "before_peak_season"
                }
            ],
            "supporting_data": {
                "active_seasons": ["back_to_school"],
                "seasonal_multiplier": 1.4,
                "product_category": "basketball",
                "peak_months": [8, 9]
            },
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
        },
        {
            "insight_id": f"market_{uuid4().hex[:8]}",
            "insight_type": "market_shift",
            "priority": "high",
            "title": "Market Shift: Nike Air Force 1 Low",
            "description": "Strong bullish market with increasing volume",
            "product_id": "prod_004",
            "product_name": "Nike Air Force 1 Low '07",
            "confidence_score": 0.80,
            "recommended_actions": [
                {
                    "action": "hold_inventory",
                    "reason": "price_appreciation"
                },
                {
                    "action": "increase_price",
                    "percentage": 10
                }
            ],
            "supporting_data": {
                "price_trend": "bullish",
                "volume_trend": "increasing",
                "volatility": "moderate",
                "current_market_price": 120.00,
                "52w_high": 145.00,
                "52w_low": 89.00
            },
            "expires_at": (datetime.utcnow() + timedelta(days=5)).isoformat() + "Z"
        },
        {
            "insight_id": f"profit_{uuid4().hex[:8]}",
            "insight_type": "profit_optimization",
            "priority": "medium",
            "title": "Profit Optimization: Converse Chuck Taylor All Star",
            "description": "Price optimization could increase profit by 18% over next 30 days",
            "product_id": "prod_005",
            "product_name": "Converse Chuck Taylor All Star High Top",
            "confidence_score": 0.72,
            "recommended_actions": [
                {
                    "action": "increase_price",
                    "from_price": 65.00,
                    "to_price": 75.00,
                    "expected_profit_increase": 0.18
                }
            ],
            "supporting_data": {
                "current_price": 65.00,
                "optimal_price": 75.00,
                "profit_increase": 0.18,
                "predicted_sales": 22,
                "pricing_strategy": "dynamic"
            },
            "expires_at": (datetime.utcnow() + timedelta(days=14)).isoformat() + "Z"
        },
        {
            "insight_id": f"clearance_{uuid4().hex[:8]}",
            "insight_type": "clearance_alert",
            "priority": "medium",
            "title": "Clearance Alert: New Balance 990v3",
            "description": "Slow-moving inventory: 156 days to clear at current demand rate",
            "product_id": "prod_006",
            "product_name": "New Balance 990v3 'Grey'",
            "confidence_score": 0.75,
            "recommended_actions": [
                {
                    "action": "decrease_price",
                    "discount_percentage": 0.25,
                    "expected_velocity_increase": 3.5,
                    "timing": "within_30_days"
                },
                {
                    "action": "monitor",
                    "metric": "sales_velocity",
                    "frequency": "weekly"
                }
            ],
            "supporting_data": {
                "days_to_clear": 156,
                "current_velocity": 0.32,
                "market_trend": "stable"
            },
            "expires_at": (datetime.utcnow() + timedelta(days=21)).isoformat() + "Z"
        }
    ]
    
    # Filter by insight types if specified
    if insight_types != "all":
        requested_types = insight_types.split(",")
        base_insights = [
            insight for insight in base_insights
            if insight["insight_type"] in requested_types
        ]
    
    return base_insights[:limit]


@router.get("/predictive/forecasts", response_model=List[MockInventoryForecast])
async def get_inventory_forecasts(
    product_ids: str = None,
    horizon_days: int = 90
):
    """Mock endpoint for inventory forecasts"""
    from uuid import uuid4
    
    forecasts = [
        {
            "product_id": "prod_001",
            "product_name": "Nike Air Jordan 1 High OG 'Chicago'",
            "current_stock": 12,
            "predicted_demand_30d": 47.3,
            "predicted_demand_90d": 132.7,
            "restock_recommendation": "URGENT",
            "optimal_restock_quantity": 71,
            "days_until_stockout": 8,
            "confidence_level": 0.85,
            "seasonal_factors": {
                "current_month_factor": 1.2,
                "next_month_factor": 1.4,
                "quarter_trend": "increasing"
            }
        },
        {
            "product_id": "prod_002",
            "product_name": "Adidas Yeezy Boost 350 V2 'Zebra'",
            "current_stock": 35,
            "predicted_demand_30d": 28.9,
            "predicted_demand_90d": 89.4,
            "restock_recommendation": "RECOMMENDED",
            "optimal_restock_quantity": 43,
            "days_until_stockout": 36,
            "confidence_level": 0.78,
            "seasonal_factors": {
                "current_month_factor": 1.0,
                "next_month_factor": 1.1,
                "quarter_trend": "stable"
            }
        },
        {
            "product_id": "prod_003",
            "product_name": "Nike Dunk Low 'Panda'",
            "current_stock": 58,
            "predicted_demand_30d": 34.2,
            "predicted_demand_90d": 98.6,
            "restock_recommendation": "MONITOR",
            "optimal_restock_quantity": 51,
            "days_until_stockout": 51,
            "confidence_level": 0.72,
            "seasonal_factors": {
                "current_month_factor": 1.4,
                "next_month_factor": 1.3,
                "quarter_trend": "seasonal_peak"
            }
        },
        {
            "product_id": "prod_004",
            "product_name": "Nike Air Force 1 Low '07",
            "current_stock": 42,
            "predicted_demand_30d": 22.7,
            "predicted_demand_90d": 71.3,
            "restock_recommendation": "MONITOR",
            "optimal_restock_quantity": 34,
            "days_until_stockout": 56,
            "confidence_level": 0.80,
            "seasonal_factors": {
                "current_month_factor": 0.9,
                "next_month_factor": 1.0,
                "quarter_trend": "stable"
            }
        }
    ]
    
    # Filter by product_ids if specified
    if product_ids:
        requested_ids = product_ids.split(",")
        forecasts = [f for f in forecasts if f["product_id"] in requested_ids]
    
    return forecasts


@router.get("/predictive/restock-recommendations", response_model=List[MockRestockRecommendation])
async def get_restock_recommendations(
    investment_budget: float = None,
    min_roi: float = 0.15,
    max_products: int = 10
):
    """Mock endpoint for restock recommendations"""
    from datetime import date
    
    recommendations = [
        {
            "product_id": "prod_001",
            "product_name": "Nike Air Jordan 1 High OG 'Chicago'",
            "current_stock": 12,
            "recommended_quantity": 71,
            "investment_required": 5680.00,
            "projected_revenue": 8130.00,
            "projected_profit": 2450.00,
            "roi_estimate": 0.43,
            "optimal_timing": (date.today() + timedelta(days=1)).isoformat(),
            "risk_level": "LOW",
            "supporting_insights": [
                "Predicted demand: 47.3 units/month",
                "Days until stockout: 8",
                "Forecast confidence: 85.0%",
                "Market trend: bullish"
            ]
        },
        {
            "product_id": "prod_002",
            "product_name": "Adidas Yeezy Boost 350 V2 'Zebra'",
            "current_stock": 35,
            "recommended_quantity": 43,
            "investment_required": 8170.00,
            "projected_revenue": 11480.00,
            "projected_profit": 3310.00,
            "roi_estimate": 0.40,
            "optimal_timing": (date.today() + timedelta(days=7)).isoformat(),
            "risk_level": "MEDIUM",
            "supporting_insights": [
                "Predicted demand: 28.9 units/month",
                "Days until stockout: 36",
                "Forecast confidence: 78.0%",
                "Market trend: volatile_bullish"
            ]
        },
        {
            "product_id": "prod_005",
            "product_name": "Converse Chuck Taylor All Star High Top",
            "current_stock": 28,
            "recommended_quantity": 33,
            "investment_required": 1650.00,
            "projected_revenue": 2475.00,
            "projected_profit": 825.00,
            "roi_estimate": 0.50,
            "optimal_timing": (date.today() + timedelta(days=14)).isoformat(),
            "risk_level": "LOW",
            "supporting_insights": [
                "Predicted demand: 22.0 units/month",
                "Days until stockout: 38",
                "Forecast confidence: 72.0%",
                "Market trend: stable"
            ]
        }
    ]
    
    # Filter by budget if specified
    if investment_budget:
        filtered_recommendations = []
        total_investment = 0.0
        for rec in recommendations:
            if total_investment + rec["investment_required"] <= investment_budget:
                filtered_recommendations.append(rec)
                total_investment += rec["investment_required"]
            else:
                break
        recommendations = filtered_recommendations
    
    # Filter by min ROI
    recommendations = [r for r in recommendations if r["roi_estimate"] >= min_roi]
    
    return recommendations[:max_products]


@router.get("/predictive/summary")
async def get_predictive_insights_summary():
    """Mock endpoint for predictive insights summary"""
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "insights_generated": 47,
        "critical_insights": 3,
        "high_priority_insights": 12,
        "restock_opportunities": 8,
        "profit_optimizations": 6,
        "market_shifts_detected": 4,
        "seasonal_trends": 5,
        "clearance_alerts": 9,
        "total_potential_revenue": 28450.75,
        "total_potential_profit": 12380.25,
        "avg_forecast_confidence": 0.76,
        "categories": {
            "restock_opportunity": {
                "count": 8,
                "avg_confidence": 0.82,
                "total_potential_revenue": 15230.50
            },
            "demand_surge": {
                "count": 3,
                "avg_confidence": 0.78,
                "urgency": "immediate"
            },
            "seasonal_trend": {
                "count": 5,
                "avg_confidence": 0.65,
                "peak_season": "Q4"
            },
            "market_shift": {
                "count": 4,
                "avg_confidence": 0.80,
                "dominant_trend": "bullish"
            },
            "profit_optimization": {
                "count": 6,
                "avg_confidence": 0.72,
                "avg_profit_increase": 0.19
            },
            "clearance_alert": {
                "count": 9,
                "avg_confidence": 0.75,
                "total_locked_capital": 8940.25
            }
        },
        "recommendations": [
            "🚨 3 critical insights require immediate action",
            "📈 Strong bullish market conditions detected - consider price increases",
            "🔄 8 restock opportunities with high ROI potential",
            "⚡ Seasonal trends favor basketball shoes for Q4",
            "💰 Profit optimization potential: €12,380 additional profit"
        ],
        "next_analysis_at": (datetime.utcnow() + timedelta(hours=6)).isoformat() + "Z"
    }
