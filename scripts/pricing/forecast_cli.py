#!/usr/bin/env python3
"""
Forecast CLI - Command-line interface for sales forecasting operations
Production-ready tool for generating and managing forecasts
"""
import argparse
import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, ".")


from domains.analytics.repositories.forecast_repository import ForecastRepository
from domains.analytics.services.forecast_engine import (
    ForecastConfig,
    ForecastEngine,
    ForecastHorizon,
    ForecastLevel,
    ForecastModel,
)
from shared.database.connection import get_db_session


class ForecastCLI:
    """Command-line interface for forecasting operations"""

    def __init__(self):
        self.db_session = None
        self.forecast_engine = None
        self.repository = None

    async def initialize(self):
        """Initialize database connections and services"""
        self.db_session = get_db_session()
        self.forecast_engine = ForecastEngine(self.db_session)
        self.repository = ForecastRepository(self.db_session)
        logger.info("Forecast CLI initialized successfully")

    async def cleanup(self):
        """Cleanup database connections"""
        if self.db_session:
            await self.db_session.close()
        logger.info("Forecast CLI cleanup completed")

    # =====================================================
    # FORECAST COMMANDS
    # =====================================================

    async def generate_forecasts(self, args):
        """Generate sales forecasts using specified configuration"""
        try:
            # Parse model and configuration
            model = ForecastModel(args.model)
            horizon = ForecastHorizon(args.horizon)
            level = ForecastLevel(args.level)

            # Create forecast configuration
            config = ForecastConfig(
                model=model,
                horizon=horizon,
                level=level,
                prediction_days=args.prediction_days or 30,
                confidence_level=args.confidence_level or 0.95,
                min_history_days=args.min_history_days or 90,
            )

            # Parse entity IDs if provided
            entity_ids = None
            if args.entity_ids:
                entity_ids = [uuid.UUID(id.strip()) for id in args.entity_ids.split(",")]
            elif args.entity_id:
                entity_ids = [uuid.UUID(args.entity_id)]

            # Generate run ID
            run_id = uuid.uuid4()

            print("🚀 Starting forecast generation...")
            print(f"Run ID: {run_id}")
            print(f"Model: {model.value}")
            print(f"Level: {level.value}")
            print(f"Horizon: {horizon.value}")
            print(f"Prediction Days: {config.prediction_days}")

            # Generate forecasts
            results = await self.forecast_engine.generate_forecasts(
                config=config, entity_ids=entity_ids, run_id=run_id
            )

            if not results:
                print("❌ No forecasts generated. Check data availability and configuration.")
                return

            print(f"✅ Generated {len(results)} forecasts")

            # Display results summary
            if args.show_results:
                await self._display_forecast_results(results, args)

            # Export results if requested
            if args.export_file:
                await self._export_forecast_results(results, args.export_file, args.export_format)
                print(f"📁 Results exported to {args.export_file}")

            print(f"💾 Forecasts saved with run ID: {run_id}")

        except Exception as e:
            logger.error(f"Error generating forecasts: {str(e)}")
            print(f"❌ Error: {str(e)}")

    async def forecast_accuracy(self, args):
        """Analyze and display forecast accuracy metrics"""
        try:
            if not args.run_id:
                # Get recent forecast runs
                print("📊 RECENT FORECAST ACCURACY")
                print("=" * 50)

                accuracy_records = await self.repository.get_model_accuracy_history(
                    model_name=args.model_name or "ensemble",
                    forecast_level=args.level,
                    forecast_horizon=args.horizon,
                    days_back=args.days or 90,
                )

                if not accuracy_records:
                    print("❌ No accuracy records found")
                    return

                # Group by model and display
                model_metrics = {}
                for record in accuracy_records:
                    key = f"{record.model_name}_{record.forecast_level}_{record.forecast_horizon}"
                    if key not in model_metrics:
                        model_metrics[key] = []
                    model_metrics[key].append(record)

                for model_key, records in model_metrics.items():
                    model_name, level, horizon = model_key.split("_")
                    latest_record = records[0]  # Most recent

                    print(f"\n📈 {model_name.upper()} - {level}/{horizon}")
                    print(
                        f"   MAPE: {latest_record.mape_score:.2f}%"
                        if latest_record.mape_score
                        else "   MAPE: N/A"
                    )
                    print(
                        f"   RMSE: {latest_record.rmse_score:.2f}"
                        if latest_record.rmse_score
                        else "   RMSE: N/A"
                    )
                    print(
                        f"   MAE:  {latest_record.mae_score:.2f}"
                        if latest_record.mae_score
                        else "   MAE: N/A"
                    )
                    print(
                        f"   R²:   {latest_record.r2_score:.4f}"
                        if latest_record.r2_score
                        else "   R²: N/A"
                    )
                    print(f"   Records: {latest_record.records_evaluated}")
                    print(f"   Period: {latest_record.evaluation_period_days} days")
                    print(f"   Date: {latest_record.accuracy_date}")

            else:
                # Calculate accuracy for specific run
                run_id = uuid.UUID(args.run_id)

                print(f"🎯 CALCULATING ACCURACY FOR RUN: {run_id}")

                # This would require actual sales data to compare against
                # For now, we'll show the forecast details
                forecasts = await self.repository.get_forecast_by_run(run_id)

                if not forecasts:
                    print("❌ No forecasts found for this run ID")
                    return

                print(f"📊 Found {len(forecasts)} forecast records")

                # Group by entity and display
                entity_forecasts = {}
                for forecast in forecasts:
                    entity_key = str(
                        forecast.product_id or forecast.brand_id or forecast.category_id
                    )
                    if entity_key not in entity_forecasts:
                        entity_forecasts[entity_key] = []
                    entity_forecasts[entity_key].append(forecast)

                for entity_id, entity_forecasts_list in list(entity_forecasts.items())[
                    :5
                ]:  # Show first 5
                    total_forecast = sum(f.forecasted_units for f in entity_forecasts_list)
                    avg_confidence = sum(
                        f.confidence_lower or 0 for f in entity_forecasts_list
                    ) / len(entity_forecasts_list)

                    print(f"\n📦 Entity {entity_id[:8]}...")
                    print(f"   Total Forecast: {total_forecast:.1f} units")
                    print(f"   Avg Confidence: {avg_confidence:.2f}")
                    print(f"   Forecast Days: {len(entity_forecasts_list)}")

                # Note about accuracy calculation
                print("\n💡 To calculate actual accuracy, provide sales data for comparison")
                print(
                    f"   Use: forecast_cli accuracy --run-id {run_id} --actual-data sales_data.csv"
                )

        except Exception as e:
            logger.error(f"Error analyzing forecast accuracy: {str(e)}")
            print(f"❌ Error: {str(e)}")

    async def list_forecasts(self, args):
        """List and filter existing forecasts"""
        try:
            # Parse filters
            level = args.level
            horizon = args.horizon
            entity_id = uuid.UUID(args.entity_id) if args.entity_id else None
            limit_days = args.days or 30

            print("📋 LISTING FORECASTS")
            print("=" * 50)
            print(f"Level: {level}")
            print(f"Horizon: {horizon}")
            print(f"Days: {limit_days}")
            if entity_id:
                print(f"Entity ID: {entity_id}")

            # Get forecasts
            forecasts = await self.repository.get_latest_forecasts(
                forecast_level=level,
                forecast_horizon=horizon,
                limit_days=limit_days,
                entity_id=entity_id,
            )

            if not forecasts:
                print("\n❌ No forecasts found matching criteria")
                return

            # Group forecasts by entity
            entity_groups = {}
            for forecast in forecasts:
                entity_key = str(forecast.product_id or forecast.brand_id or forecast.category_id)
                if entity_key not in entity_groups:
                    entity_groups[entity_key] = []
                entity_groups[entity_key].append(forecast)

            print(f"\n📊 Found {len(forecasts)} forecasts for {len(entity_groups)} entities")

            # Display summary for each entity
            for entity_id, entity_forecasts in list(entity_groups.items())[
                : args.limit if args.limit else 10
            ]:
                entity_forecasts.sort(key=lambda f: f.forecast_date)

                # Get entity name if possible
                entity_name = "Unknown"
                first_forecast = entity_forecasts[0]
                if first_forecast.product and first_forecast.product.name:
                    entity_name = first_forecast.product.name
                elif first_forecast.brand and first_forecast.brand.name:
                    entity_name = first_forecast.brand.name
                elif first_forecast.category and first_forecast.category.name:
                    entity_name = first_forecast.category.name

                total_units = sum(f.forecasted_units for f in entity_forecasts)
                total_revenue = sum(f.forecasted_revenue for f in entity_forecasts)
                avg_confidence = sum(
                    (f.confidence_lower or 0 + f.confidence_upper or 0) / 2
                    for f in entity_forecasts
                ) / len(entity_forecasts)

                print(f"\n🎯 {entity_name}")
                print(f"   ID: {entity_id}")
                print(f"   Model: {entity_forecasts[0].model_name}")
                print(
                    f"   Period: {entity_forecasts[0].forecast_date} to {entity_forecasts[-1].forecast_date}"
                )
                print(f"   Total Units: {total_units:.1f}")
                print(f"   Total Revenue: €{total_revenue:.2f}")
                print(f"   Avg Confidence: {avg_confidence:.1f}")

                if args.show_daily and len(entity_forecasts) <= 7:
                    print("   Daily Breakdown:")
                    for forecast in entity_forecasts:
                        print(
                            f"     {forecast.forecast_date}: {forecast.forecasted_units:.1f} units"
                        )

        except Exception as e:
            logger.error(f"Error listing forecasts: {str(e)}")
            print(f"❌ Error: {str(e)}")

    async def demand_analysis(self, args):
        """Analyze demand patterns and trends"""
        try:
            # Parse parameters
            entity_type = args.level
            entity_id = uuid.UUID(args.entity_id) if args.entity_id else None
            days_back = args.days or 90

            print("📈 DEMAND PATTERN ANALYSIS")
            print("=" * 50)
            print(f"Level: {entity_type}")
            print(f"Period: {days_back} days")
            if entity_id:
                print(f"Entity ID: {entity_id}")

            # Get demand patterns
            patterns = await self.repository.get_demand_patterns(
                entity_type=entity_type, entity_id=entity_id, days_back=days_back
            )

            if not patterns:
                print("\n❌ No demand patterns found")
                return

            # Analyze patterns
            pattern_summary = {}
            for pattern in patterns:
                period_type = pattern.period_type
                if period_type not in pattern_summary:
                    pattern_summary[period_type] = {
                        "patterns": [],
                        "avg_demand": 0,
                        "avg_velocity": 0,
                        "trend_directions": {},
                    }

                pattern_summary[period_type]["patterns"].append(pattern)
                pattern_summary[period_type]["avg_demand"] += float(pattern.demand_score)
                if pattern.velocity_rank:
                    pattern_summary[period_type]["avg_velocity"] += pattern.velocity_rank

                trend = pattern.trend_direction or "stable"
                if trend not in pattern_summary[period_type]["trend_directions"]:
                    pattern_summary[period_type]["trend_directions"][trend] = 0
                pattern_summary[period_type]["trend_directions"][trend] += 1

            # Display analysis
            for period_type, summary in pattern_summary.items():
                pattern_count = len(summary["patterns"])
                avg_demand = summary["avg_demand"] / pattern_count
                avg_velocity = (
                    summary["avg_velocity"] / pattern_count if summary["avg_velocity"] > 0 else 0
                )

                print(f"\n📊 {period_type.upper()} PATTERNS ({pattern_count} records)")
                print(f"   Average Demand Score: {avg_demand:.4f}")
                if avg_velocity > 0:
                    print(f"   Average Velocity Rank: {avg_velocity:.1f}")

                # Trend analysis
                trends = summary["trend_directions"]
                if trends:
                    print("   Trends:")
                    for trend, count in trends.items():
                        percentage = (count / pattern_count) * 100
                        print(f"     {trend.title()}: {count} ({percentage:.1f}%)")

                # Show recent patterns if requested
                if args.show_recent:
                    recent_patterns = sorted(
                        summary["patterns"], key=lambda p: p.pattern_date, reverse=True
                    )[:5]
                    print("   Recent Patterns:")
                    for pattern in recent_patterns:
                        seasonality = (
                            f" (Season: {pattern.seasonality_factor:.2f})"
                            if pattern.seasonality_factor
                            else ""
                        )
                        print(
                            f"     {pattern.pattern_date}: {pattern.demand_score:.4f}{seasonality}"
                        )

        except Exception as e:
            logger.error(f"Error analyzing demand patterns: {str(e)}")
            print(f"❌ Error: {str(e)}")

    async def backfill_forecasts(self, args):
        """Generate forecasts for past periods to validate models"""
        try:
            # Parse parameters
            model = ForecastModel(args.model)
            horizon = ForecastHorizon(args.horizon)
            level = ForecastLevel(args.level)

            # Calculate date ranges
            end_date = datetime.now().date() - timedelta(days=args.gap_days or 7)
            start_date = end_date - timedelta(days=args.backfill_days or 30)

            print("🔄 BACKFILL FORECAST GENERATION")
            print("=" * 50)
            print(f"Model: {model.value}")
            print(f"Period: {start_date} to {end_date}")
            print(f"Gap Days: {args.gap_days or 7}")

            entity_ids = None
            if args.entity_ids:
                entity_ids = [uuid.UUID(id.strip()) for id in args.entity_ids.split(",")]

            # Generate historical forecasts day by day
            current_date = start_date
            total_forecasts = 0

            while current_date <= end_date:
                print(f"📅 Processing {current_date}...")

                # Create configuration for this date
                config = ForecastConfig(
                    model=model,
                    horizon=horizon,
                    level=level,
                    prediction_days=args.prediction_days or 7,
                    confidence_level=0.95,
                )

                run_id = uuid.uuid4()

                try:
                    # Generate forecasts as of this historical date
                    results = await self.forecast_engine.generate_forecasts(
                        config=config, entity_ids=entity_ids, run_id=run_id
                    )

                    if results:
                        total_forecasts += len(results)
                        print(f"   ✅ Generated {len(results)} forecasts")
                    else:
                        print("   ⚠️ No forecasts generated")

                except Exception as e:
                    print(f"   ❌ Error: {str(e)}")

                current_date += timedelta(days=1)

            print("\n✅ Backfill completed:")
            print(f"   Total Forecasts: {total_forecasts}")
            print(f"   Days Processed: {(end_date - start_date).days + 1}")

        except Exception as e:
            logger.error(f"Error in forecast backfill: {str(e)}")
            print(f"❌ Error: {str(e)}")

    # =====================================================
    # HELPER METHODS
    # =====================================================

    async def _display_forecast_results(self, results, args):
        """Display forecast results summary"""
        print("\n📊 FORECAST RESULTS SUMMARY")
        print("=" * 50)

        for i, result in enumerate(results[: args.result_limit if args.result_limit else 5], 1):
            entity_name = f"Entity {str(result.entity_id)[:8]}..."

            total_units = sum(pred["forecasted_units"] for pred in result.predictions)
            total_revenue = sum(pred["forecasted_revenue"] for pred in result.predictions)
            avg_confidence = sum(
                pred["confidence_upper"] - pred["confidence_lower"] for pred in result.predictions
            ) / len(result.predictions)

            print(f"\n{i}. {entity_name}")
            print(f"   Model: {result.model_name}")
            print(f"   Total Units: {total_units:.1f}")
            print(f"   Total Revenue: €{total_revenue:.2f}")
            print(f"   Avg Confidence Width: ±{avg_confidence/2:.1f}")

            if result.model_metrics:
                print("   Model Metrics:")
                for metric, value in result.model_metrics.items():
                    if isinstance(value, (int, float)):
                        print(f"     {metric}: {value:.3f}")

            if result.feature_importance and args.show_features:
                print("   Top Features:")
                sorted_features = sorted(
                    result.feature_importance.items(), key=lambda x: x[1], reverse=True
                )
                for feature, importance in sorted_features[:3]:
                    print(f"     {feature}: {importance:.3f}")

    async def _export_forecast_results(self, results, filename, format_type):
        """Export forecast results to file"""
        if format_type == "json":
            # Convert to JSON-serializable format
            export_data = []
            for result in results:
                export_item = {
                    "entity_id": str(result.entity_id),
                    "entity_type": result.entity_type,
                    "model_name": result.model_name,
                    "model_version": result.model_version,
                    "predictions": [
                        {
                            "date": pred["forecast_date"].isoformat(),
                            "units": float(pred["forecasted_units"]),
                            "revenue": float(pred["forecasted_revenue"]),
                            "confidence_lower": float(pred["confidence_lower"]),
                            "confidence_upper": float(pred["confidence_upper"]),
                        }
                        for pred in result.predictions
                    ],
                    "model_metrics": result.model_metrics,
                    "feature_importance": result.feature_importance,
                }
                export_data.append(export_item)

            with open(filename, "w") as f:
                json.dump(export_data, f, indent=2)

        elif format_type == "csv":
            import csv

            with open(filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "entity_id",
                        "entity_type",
                        "model_name",
                        "forecast_date",
                        "forecasted_units",
                        "forecasted_revenue",
                        "confidence_lower",
                        "confidence_upper",
                    ]
                )

                for result in results:
                    for pred in result.predictions:
                        writer.writerow(
                            [
                                str(result.entity_id),
                                result.entity_type,
                                result.model_name,
                                pred["forecast_date"].isoformat(),
                                pred["forecasted_units"],
                                pred["forecasted_revenue"],
                                pred["confidence_lower"],
                                pred["confidence_upper"],
                            ]
                        )


def create_parser():
    """Create command-line argument parser"""
    parser = argparse.ArgumentParser(description="SoleFlipper Forecast CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate Forecasts Command
    gen_parser = subparsers.add_parser("generate", help="Generate sales forecasts")
    gen_parser.add_argument(
        "--model",
        required=True,
        choices=["linear_trend", "seasonal_naive", "random_forest", "ensemble"],
        help="Forecasting model to use",
    )
    gen_parser.add_argument(
        "--horizon",
        required=True,
        choices=["daily", "weekly", "monthly"],
        help="Forecast time horizon",
    )
    gen_parser.add_argument(
        "--level",
        required=True,
        choices=["product", "brand", "category", "platform"],
        help="Forecast aggregation level",
    )
    gen_parser.add_argument("--entity-id", help="Specific entity UUID to forecast")
    gen_parser.add_argument("--entity-ids", help="Comma-separated entity UUIDs")
    gen_parser.add_argument(
        "--prediction-days", type=int, default=30, help="Number of days to forecast"
    )
    gen_parser.add_argument(
        "--confidence-level", type=float, default=0.95, help="Confidence level for intervals"
    )
    gen_parser.add_argument(
        "--min-history-days", type=int, default=90, help="Minimum historical data required"
    )
    gen_parser.add_argument("--show-results", action="store_true", help="Display results summary")
    gen_parser.add_argument("--result-limit", type=int, help="Limit number of results to display")
    gen_parser.add_argument("--show-features", action="store_true", help="Show feature importance")
    gen_parser.add_argument("--export-file", help="Export results to file")
    gen_parser.add_argument(
        "--export-format", choices=["json", "csv"], default="json", help="Export format"
    )

    # Forecast Accuracy Command
    acc_parser = subparsers.add_parser("accuracy", help="Analyze forecast accuracy")
    acc_parser.add_argument("--run-id", help="Specific forecast run UUID to analyze")
    acc_parser.add_argument("--model-name", help="Filter by model name")
    acc_parser.add_argument(
        "--level", choices=["product", "brand", "category"], help="Filter by forecast level"
    )
    acc_parser.add_argument(
        "--horizon", choices=["daily", "weekly", "monthly"], help="Filter by horizon"
    )
    acc_parser.add_argument("--days", type=int, default=90, help="Days of history to analyze")
    acc_parser.add_argument("--actual-data", help="CSV file with actual sales data for comparison")

    # List Forecasts Command
    list_parser = subparsers.add_parser("list", help="List existing forecasts")
    list_parser.add_argument(
        "--level",
        required=True,
        choices=["product", "brand", "category", "platform"],
        help="Forecast level to list",
    )
    list_parser.add_argument(
        "--horizon",
        required=True,
        choices=["daily", "weekly", "monthly"],
        help="Forecast horizon to list",
    )
    list_parser.add_argument("--entity-id", help="Filter by entity UUID")
    list_parser.add_argument("--days", type=int, default=30, help="Days ahead to show")
    list_parser.add_argument("--limit", type=int, help="Limit number of entities to show")
    list_parser.add_argument("--show-daily", action="store_true", help="Show daily breakdown")

    # Demand Analysis Command
    demand_parser = subparsers.add_parser("demand-analysis", help="Analyze demand patterns")
    demand_parser.add_argument(
        "--level", required=True, choices=["product", "brand", "category"], help="Analysis level"
    )
    demand_parser.add_argument("--entity-id", help="Specific entity UUID to analyze")
    demand_parser.add_argument("--days", type=int, default=90, help="Days of history to analyze")
    demand_parser.add_argument("--show-recent", action="store_true", help="Show recent patterns")

    # Backfill Forecasts Command
    backfill_parser = subparsers.add_parser(
        "backfill", help="Generate historical forecasts for validation"
    )
    backfill_parser.add_argument(
        "--model",
        required=True,
        choices=["linear_trend", "seasonal_naive", "random_forest", "ensemble"],
        help="Forecasting model",
    )
    backfill_parser.add_argument(
        "--horizon", required=True, choices=["daily", "weekly", "monthly"], help="Forecast horizon"
    )
    backfill_parser.add_argument(
        "--level", required=True, choices=["product", "brand", "category"], help="Forecast level"
    )
    backfill_parser.add_argument("--backfill-days", type=int, default=30, help="Days to backfill")
    backfill_parser.add_argument("--gap-days", type=int, default=7, help="Gap from current date")
    backfill_parser.add_argument(
        "--prediction-days", type=int, default=7, help="Forecast period length"
    )
    backfill_parser.add_argument("--entity-ids", help="Comma-separated entity UUIDs")

    return parser


async def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = ForecastCLI()

    try:
        await cli.initialize()

        # Route to appropriate command handler
        if args.command == "generate":
            await cli.generate_forecasts(args)
        elif args.command == "accuracy":
            await cli.forecast_accuracy(args)
        elif args.command == "list":
            await cli.list_forecasts(args)
        elif args.command == "demand-analysis":
            await cli.demand_analysis(args)
        elif args.command == "backfill":
            await cli.backfill_forecasts(args)
        else:
            print(f"❌ Unknown command: {args.command}")

    except KeyboardInterrupt:
        print("\n⏹️ Operation cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"❌ Unexpected error: {str(e)}")
    finally:
        await cli.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
