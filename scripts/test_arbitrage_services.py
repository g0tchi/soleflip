#!/usr/bin/env python
"""
Test script for new Arbitrage Services

Tests:
1. Demand Score Calculator
2. Risk Scorer
3. Enhanced Opportunity Service
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession

from domains.arbitrage.services import (
    DemandScoreCalculator,
    EnhancedOpportunityService,
    RiskScorer,
)
from shared.database.connection import get_async_session_maker


async def test_demand_score_calculator() -> None:
    """Test Demand Score Calculator"""
    print("\n" + "=" * 60)
    print("TEST 1: Demand Score Calculator")
    print("=" * 60)

    async_session = get_async_session_maker()

    async with async_session() as session:
        calculator = DemandScoreCalculator(session)

        # Get a sample product from the database
        from shared.database.models import Product
        from sqlalchemy import select

        query = select(Product.id, Product.name, Product.sku).limit(5)
        result = await session.execute(query)
        products = result.all()

        if not products:
            print("❌ No products found in database")
            return

        print(f"\n✅ Found {len(products)} products to test\n")

        for product_id, product_name, product_sku in products:
            print(f"\n📊 Calculating demand score for: {product_name} ({product_sku})")

            try:
                demand_score, breakdown = await calculator.calculate_product_demand_score(
                    product_id, days_back=90
                )

                print(f"   💯 Demand Score: {demand_score}/100")
                print(f"   📈 Sales Frequency: {breakdown['sales_frequency_score']:.1f} "
                      f"({breakdown['sales_per_day']:.3f} sales/day)")
                print(f"   📊 Price Trend: {breakdown['price_trend_score']:.1f} "
                      f"({breakdown['trend_direction']})")
                print(f"   ⚡ Stock Turnover: {breakdown['stock_turnover_score']:.1f}")
                if breakdown['avg_turnover_days']:
                    print(f"      → Avg: {breakdown['avg_turnover_days']:.1f} days")
                print(f"   🗓️  Seasonal: {breakdown['seasonal_score']:.1f}")
                print(f"   🏷️  Brand: {breakdown['brand_score']:.1f}")

            except Exception as e:
                print(f"   ❌ Error: {str(e)}")


async def test_risk_scorer() -> None:
    """Test Risk Scorer"""
    print("\n" + "=" * 60)
    print("TEST 2: Risk Scorer")
    print("=" * 60)

    async_session = get_async_session_maker()

    async with async_session() as session:
        # First get some opportunities
        from domains.integration.services.quickflip_detection_service import (
            QuickFlipDetectionService,
        )

        quickflip = QuickFlipDetectionService(session)
        opportunities = await quickflip.find_opportunities(
            min_profit_margin=10.0, min_gross_profit=20.0, limit=5
        )

        if not opportunities:
            print("\n❌ No opportunities found")
            return

        print(f"\n✅ Found {len(opportunities)} opportunities to test\n")

        risk_scorer = RiskScorer(session)

        for opp in opportunities:
            print(f"\n🎯 Assessing risk for: {opp.product_name}")
            print(f"   💰 Profit: €{opp.gross_profit} ({opp.profit_margin}% margin)")
            print(f"   📦 Stock: {opp.buy_stock_qty or 0} units")

            try:
                assessment = await risk_scorer.assess_opportunity_risk(opp)

                # Risk level with emoji
                risk_emoji = {
                    "LOW": "🟢",
                    "MEDIUM": "🟡",
                    "HIGH": "🔴",
                }
                emoji = risk_emoji.get(assessment.risk_level.value, "⚪")

                print(f"\n   {emoji} Risk Level: {assessment.risk_level.value}")
                print(f"   📊 Risk Score: {assessment.risk_score}/100")
                print(f"   🎯 Confidence: {assessment.confidence_score}%")

                print(f"\n   📋 Risk Factors:")
                for factor, description in assessment.risk_factors.items():
                    print(f"      • {factor.capitalize()}: {description}")

                print(f"\n   💡 Recommendations:")
                for rec in assessment.recommendations:
                    print(f"      {rec}")

            except Exception as e:
                print(f"   ❌ Error: {str(e)}")


async def test_enhanced_opportunity_service() -> None:
    """Test Enhanced Opportunity Service"""
    print("\n" + "=" * 60)
    print("TEST 3: Enhanced Opportunity Service")
    print("=" * 60)

    async_session = get_async_session_maker()

    async with async_session() as session:
        service = EnhancedOpportunityService(session)

        print("\n🔍 Finding top enhanced opportunities...")

        try:
            opportunities = await service.get_top_opportunities(
                limit=5, min_feasibility=50
            )

            if not opportunities:
                print("\n❌ No opportunities found")
                return

            print(f"\n✅ Found {len(opportunities)} enhanced opportunities\n")

            # Get summary
            summary = await service.get_opportunity_summary(opportunities)

            print("📊 SUMMARY STATISTICS")
            print(f"   Total Opportunities: {summary['total_opportunities']}")
            print(f"   Avg Feasibility Score: {summary['avg_feasibility_score']}/100")
            print(f"   Avg Demand Score: {summary['avg_demand_score']}/100")
            print(f"   Avg Risk Score: {summary['avg_risk_score']}/100")
            print(f"   Total Potential Profit: €{summary['total_potential_profit']:.2f}")
            print(f"   Estimated Avg Days to Sell: {summary['estimated_avg_days_to_sell']:.1f}")

            print(f"\n   Risk Distribution:")
            for risk_level, count in summary['risk_distribution'].items():
                print(f"      • {risk_level}: {count}")

            print("\n\n🏆 TOP OPPORTUNITIES")
            print("-" * 60)

            for i, enh in enumerate(opportunities, 1):
                opp = enh.opportunity

                # Risk emoji
                risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
                emoji = risk_emoji.get(enh.risk_level_str, "⚪")

                print(f"\n#{i}. {opp.product_name} ({opp.product_sku})")
                print(f"   💰 Buy: €{opp.buy_price} → Sell: €{opp.sell_price}")
                print(f"   📈 Profit: €{opp.gross_profit} ({opp.profit_margin}% margin)")
                print(f"   📦 Stock: {opp.buy_stock_qty or 0} @ {opp.buy_supplier}")
                print(f"\n   🎯 Feasibility Score: {enh.feasibility_score}/100")
                print(f"   💯 Demand Score: {enh.demand_score:.1f}/100")
                print(f"   {emoji} Risk: {enh.risk_level_str} "
                      f"({enh.risk_assessment.risk_score if enh.risk_assessment else 'N/A'})")
                print(f"   ⏱️  Est. Days to Sell: {enh.estimated_days_to_sell or 'Unknown'}")

                if enh.risk_assessment and enh.risk_assessment.recommendations:
                    print(f"\n   💡 Top Recommendation:")
                    print(f"      {enh.risk_assessment.recommendations[0]}")

        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback

            traceback.print_exc()


async def main() -> None:
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🚀 ARBITRAGE SERVICES TEST SUITE")
    print("=" * 60)

    try:
        await test_demand_score_calculator()
        await test_risk_scorer()
        await test_enhanced_opportunity_service()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
