# Pricing & Forecasting System - Deployment Guide

## Overview
This guide covers the deployment and configuration of the SoleFlipper Pricing & Forecasting system. The system provides intelligent pricing strategies and ML-powered sales forecasting capabilities.

## Security Notice ⚠️
**IMPORTANT**: This system is designed for TEST SCHEMA ONLY. Do not deploy to production without proper security review and hardening.

## Prerequisites

### System Requirements
- Python 3.9+
- PostgreSQL 12+
- 4GB RAM minimum (8GB recommended for ML models)
- 50GB disk space for historical data storage

### Python Dependencies
```bash
pip install -r requirements.txt

# Core dependencies:
pip install sqlalchemy asyncpg alembic pandas numpy scikit-learn statsmodels
```

### Database Setup
Ensure PostgreSQL is running and accessible:
```bash
# Test connection
psql -h localhost -U your_user -d soleflip -c "SELECT version();"
```

## Environment Variables

### Required Environment Variables
Create a `.env` file with the following variables:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://username:password@host:port/database
POSTGRES_DB=soleflip
POSTGRES_USER=soleflip_user
POSTGRES_PASSWORD=secure_password_here
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Field Encryption (Required for sensitive data)
FIELD_ENCRYPTION_KEY=your-32-character-base64-key-here

# Pricing Configuration
PRICING_DEFAULT_MARGIN=20.0
PRICING_MAX_DISCOUNT=50.0
PRICING_MIN_MARGIN=5.0

# ML Model Configuration  
FORECAST_MODEL_PATH=/app/models/
FORECAST_CACHE_TTL=3600
FORECAST_BATCH_SIZE=1000

# Redis (Optional - for caching)
REDIS_URL=redis://localhost:6379/0

# API Keys (Optional - for external data)
STOCKX_API_KEY=your_stockx_key
GOAT_API_KEY=your_goat_key

# Security
SECRET_KEY=your-secret-key-for-jwt-tokens
ALLOWED_HOSTS=localhost,127.0.0.1
DEBUG=false

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/soleflip/pricing.log
```

### Security Requirements
1. **Encryption Key**: Generate using:
   ```python
   from cryptography.fernet import Fernet
   key = Fernet.generate_key()
   print(key.decode())
   ```

2. **Database User**: Create dedicated user with minimal privileges:
   ```sql
   CREATE USER soleflip_pricing WITH PASSWORD 'secure_password';
   GRANT CONNECT ON DATABASE soleflip TO soleflip_pricing;
   GRANT USAGE ON SCHEMA pricing, analytics TO soleflip_pricing;
   GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA pricing, analytics TO soleflip_pricing;
   ```

3. **File Permissions**: Restrict access to configuration files:
   ```bash
   chmod 600 .env
   chmod 700 /var/log/soleflip/
   ```

## Database Migration

### 1. Run Alembic Migrations
```bash
# Navigate to project root
cd /path/to/soleflip-fix-missing-encryption-key

# Run migrations
alembic upgrade head

# Verify migration
alembic current
alembic history --verbose
```

### 2. Verify Schema Creation
```sql
-- Check if schemas were created
SELECT schema_name FROM information_schema.schemata 
WHERE schema_name IN ('pricing', 'analytics');

-- Check if tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'pricing';

SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'analytics';
```

### 3. Seed Initial Data (Optional)
```bash
# Create basic pricing rules
python scripts/pricing/pricing_cli.py update-rules \
  --name "Default Markup" \
  --type "markup" \
  --value 1.25 \
  --conditions "brand=Nike"

# Create brand multipliers
python scripts/pricing/pricing_cli.py update-rules \
  --name "Premium Brand" \
  --type "brand_multiplier" \
  --value 1.15 \
  --conditions "brand IN (Jordan, Yeezy)"
```

## CLI Tool Setup

### 1. Pricing CLI
```bash
# Test pricing calculations
python scripts/pricing/pricing_cli.py calculate \
  --product-id 123 \
  --strategy cost_plus \
  --output json

# Update pricing rules
python scripts/pricing/pricing_cli.py update-rules \
  --name "Holiday Sale" \
  --type "discount" \
  --value 0.85 \
  --start-date "2024-12-01" \
  --end-date "2024-12-31"
```

### 2. Forecast CLI
```bash
# Generate forecasts
python scripts/pricing/forecast_cli.py generate \
  --days 30 \
  --model ensemble \
  --output csv \
  --file forecasts.csv

# Check forecast accuracy
python scripts/pricing/forecast_cli.py accuracy \
  --days 7 \
  --model all
```

### 3. Setup Cron Jobs
```crontab
# Daily pricing updates (6 AM)
0 6 * * * cd /path/to/soleflip && python scripts/pricing/pricing_cli.py bulk-update --all

# Hourly forecasts (business hours)
0 9-17 * * 1-5 cd /path/to/soleflip && python scripts/pricing/forecast_cli.py generate --days 7

# Weekly accuracy reports (Monday 9 AM)
0 9 * * 1 cd /path/to/soleflip && python scripts/pricing/forecast_cli.py accuracy --days 7 --output email
```

## Metabase Dashboard Setup

### 1. Database Connection
1. Create read-only user for Metabase:
   ```sql
   CREATE USER metabase_reader WITH PASSWORD 'secure_metabase_password';
   GRANT CONNECT ON DATABASE soleflip TO metabase_reader;
   GRANT USAGE ON SCHEMA pricing, analytics, public TO metabase_reader;
   GRANT SELECT ON ALL TABLES IN SCHEMA pricing, analytics, public TO metabase_reader;
   ```

2. Add connection in Metabase Admin panel

### 2. Import Dashboards
1. Use SQL queries from `docs/metabase_pricing_kpis_dashboard.sql`
2. Use SQL queries from `docs/metabase_sales_forecast_dashboard.sql`  
3. Follow setup guide in `docs/metabase_dashboard_setup_guide.md`

## Monitoring & Logging

### 1. Application Logs
```bash
# Create log directory
sudo mkdir -p /var/log/soleflip
sudo chown $USER:$USER /var/log/soleflip

# Log rotation setup
cat > /etc/logrotate.d/soleflip << EOF
/var/log/soleflip/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    create 0644 soleflip soleflip
}
EOF
```

### 2. Database Monitoring
Monitor key metrics:
- Price calculation performance
- Forecast generation time  
- Database connection pool usage
- Failed pricing rule applications

### 3. Health Checks
```bash
# Database connectivity
python -c "
import asyncio
from domains.pricing.repositories.pricing_repository import PricingRepository

async def test_connection():
    repo = PricingRepository()
    try:
        rules = await repo.get_active_price_rules()
        print(f'✅ Database connected. Found {len(rules)} active rules')
    except Exception as e:
        print(f'❌ Database error: {e}')

asyncio.run(test_connection())
"

# Model availability
python -c "
try:
    from sklearn.ensemble import RandomForestRegressor
    from statsmodels.tsa.seasonal import seasonal_decompose
    print('✅ ML libraries available')
except ImportError as e:
    print(f'❌ Missing ML library: {e}')
"
```

## Performance Optimization

### 1. Database Indexes
Ensure these indexes exist:
```sql
-- Pricing performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_price_history_product_date 
ON pricing.price_history(product_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_forecasts_date_product 
ON analytics.sales_forecasts(forecast_date, product_id);

-- Query optimization indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_prices_updated 
ON pricing.market_prices(updated_at DESC) WHERE competitor_price IS NOT NULL;
```

### 2. Connection Pooling
Configure asyncpg pool settings:
```python
# In your database configuration
DATABASE_CONFIG = {
    "min_size": 10,
    "max_size": 20,
    "max_queries": 50000,
    "max_inactive_connection_lifetime": 300,
}
```

### 3. Caching Strategy
```python
# Redis caching for pricing calculations
CACHE_CONFIG = {
    "pricing_rules": {"ttl": 3600},  # 1 hour
    "brand_multipliers": {"ttl": 1800},  # 30 minutes  
    "market_prices": {"ttl": 300},  # 5 minutes
}
```

## Backup & Recovery

### 1. Database Backups
```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/var/backups/soleflip"
DATE=$(date +%Y%m%d_%H%M%S)

pg_dump -h localhost -U soleflip_user soleflip \
  --schema=pricing --schema=analytics \
  > "${BACKUP_DIR}/pricing_analytics_${DATE}.sql"

# Compress and retain 30 days
gzip "${BACKUP_DIR}/pricing_analytics_${DATE}.sql"
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

### 2. Model Backups  
```bash
# Backup trained ML models
tar -czf "/var/backups/soleflip/models_$(date +%Y%m%d).tar.gz" /app/models/
```

## Security Hardening

### 1. Network Security
- Use VPN or private networks for database access
- Configure firewall rules to limit database port access
- Enable SSL/TLS for all database connections

### 2. Application Security  
- Regular dependency updates: `pip-audit`
- Input validation on all CLI parameters
- SQL injection protection via parameterized queries
- Rate limiting on API endpoints (if applicable)

### 3. Data Protection
- Encrypt sensitive fields using FIELD_ENCRYPTION_KEY
- Regular security audits of pricing data access
- Implement data retention policies

## Troubleshooting

### Common Issues

#### 1. Migration Failures
```bash
# Check migration status
alembic current

# Rollback if needed
alembic downgrade -1

# Repair and retry
alembic upgrade head
```

#### 2. CLI Permission Errors
```bash
# Fix Python module path
export PYTHONPATH="${PYTHONPATH}:/path/to/soleflip"

# Fix database permissions
GRANT USAGE ON ALL SEQUENCES IN SCHEMA pricing, analytics TO soleflip_pricing;
```

#### 3. ML Model Failures
```bash
# Install missing dependencies
pip install scikit-learn statsmodels

# Check model cache
ls -la /app/models/
chmod 755 /app/models/
```

#### 4. Performance Issues
- Monitor slow queries in PostgreSQL logs
- Check connection pool exhaustion
- Verify index usage with EXPLAIN ANALYZE

### Support
For deployment issues:
1. Check logs in `/var/log/soleflip/`
2. Verify environment variables
3. Test database connectivity
4. Review Metabase dashboard queries

## Production Checklist

Before deploying to production:

- [ ] Security review completed
- [ ] All environment variables configured
- [ ] Database migrations tested
- [ ] Backup procedures tested
- [ ] Monitoring alerts configured  
- [ ] Performance benchmarks established
- [ ] Documentation updated
- [ ] Team training completed

**Remember**: This system handles sensitive pricing data. Always follow your organization's security policies and conduct thorough testing before production deployment.