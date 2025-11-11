"""
Generate v2.2.1 Compatible Budibase Configuration
=================================================

Script to generate realistic, working Budibase configuration for SoleFlipper v2.2.1
"""

import asyncio
import json
import logging
from pathlib import Path

from ..schemas.budibase_models import BudibaseEnvironment
from ..services.config_generator import BudibaseConfigGenerator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def generate_production_config():
    """Generate production-ready Budibase configuration"""

    logger.info("🚀 Starting v2.2.1 Budibase Config Generation")

    # Initialize generator
    generator = BudibaseConfigGenerator()

    # Generate configuration
    config = await generator.generate_app_config(
        app_name="SoleFlipper Business App v2.2.1",
        environment=BudibaseEnvironment.DEVELOPMENT,
        validate_endpoints=True,
    )

    # Validate configuration
    validation_result = await generator.validate_config(config)

    # Log validation results
    logger.info(
        f"Configuration validation: {'✅ VALID' if validation_result.is_valid else '❌ INVALID'}"
    )

    if validation_result.errors:
        logger.error("❌ Validation Errors:")
        for error in validation_result.errors:
            logger.error(f"  - {error}")

    if validation_result.warnings:
        logger.warning("⚠️ Validation Warnings:")
        for warning in validation_result.warnings:
            logger.warning(f"  - {warning}")

    if validation_result.missing_endpoints:
        logger.info("🔍 Missing Endpoints (will be skipped):")
        for endpoint in validation_result.missing_endpoints:
            logger.info(f"  - {endpoint}")

    # Export configurations
    config_dir = Path(__file__).parent / "generated"
    config_dir.mkdir(exist_ok=True)

    # Main configuration
    main_config_path = config_dir / "soleflip-app-v221.json"
    generator.export_config(config, str(main_config_path))

    # Individual component configs for Budibase import
    await export_component_configs(config, config_dir)

    logger.info(f"✅ Generated configurations in {config_dir}")
    logger.info(
        f"📊 Stats: {len(config.data_sources)} data sources, {len(config.screens)} screens, {len(config.automations)} automations"
    )

    return config, validation_result


async def export_component_configs(config, config_dir):
    """Export individual component configurations"""

    # Data sources
    datasources_config = {"datasources": [ds.dict() for ds in config.data_sources]}
    with open(config_dir / "datasources-v221.json", "w") as f:
        json.dump(datasources_config, f, indent=2, default=str)

    # Screens
    screens_config = {"screens": [screen.dict() for screen in config.screens]}
    with open(config_dir / "screens-v221.json", "w") as f:
        json.dump(screens_config, f, indent=2, default=str)

    # Automations
    automations_config = {"automations": [automation.dict() for automation in config.automations]}
    with open(config_dir / "automations-v221.json", "w") as f:
        json.dump(automations_config, f, indent=2, default=str)

    # Validation report
    validation_result = await BudibaseConfigGenerator().validate_config(config)
    validation_report = {
        "validation_timestamp": str(validation_result),
        "summary": {
            "total_data_sources": len(config.data_sources),
            "total_screens": len(config.screens),
            "total_automations": len(config.automations),
            "is_valid": validation_result.is_valid,
            "error_count": len(validation_result.errors),
            "warning_count": len(validation_result.warnings),
        },
        "details": validation_result.dict(),
    }
    with open(config_dir / "validation-report-v221.json", "w") as f:
        json.dump(validation_report, f, indent=2, default=str)


if __name__ == "__main__":
    asyncio.run(generate_production_config())
