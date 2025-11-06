# Deployment & Operations Guide

**Purpose**: Production deployment, monitoring, and operational procedures
**Last Updated**: 2025-11-06

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Development Setup](#development-setup)
3. [Production Deployment](#production-deployment)
4. [Docker Operations](#docker-operations)
5. [Database Management](#database-management)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Security](#security)

---

## Quick Start

### Initial Setup (First Time)

```bash
# 1. Clone repository
git clone https://github.com/your-org/soleflip.git
cd soleflip

# 2. Complete setup (installs deps + creates DB)
make quick-start

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add to .env as FIELD_ENCRYPTION_KEY

# 5. Start development server
make dev
```

**Server will be available at**: `http://localhost:8000`
**API Docs**: `http://localhost:8000/docs`

---

## Development Setup

### Prerequisites

- **Python**: 3.11+ (required)
- **PostgreSQL**: 13+ (or use Docker)
- **Redis**: 6+ (optional, for caching)
- **Node.js**: 18+ (for n8n integration, optional)

### Environment Variables

**Required**:
```bash
DATABASE_URL=postgresql://user:pass@localhost/soleflip
FIELD_ENCRYPTION_KEY=your_fernet_key_here
ENVIRONMENT=development
```

**Optional** (Production):
```bash
# StockX Integration
STOCKX_CLIENT_ID=your_client_id
STOCKX_CLIENT_SECRET=your_client_secret
STOCKX_REFRESH_TOKEN=your_refresh_token
STOCKX_API_KEY=your_api_key

# Redis Caching
REDIS_URL=redis://localhost:6379/0

# Monitoring
SENTRY_DSN=your_sentry_dsn
```

### Development Workflow

```bash
# Start development server (hot reload enabled)
make dev

# Run tests before committing
make check               # Lint + type-check + test

# Run specific test category
make test-unit
make test-integration
make test-api

# Database operations
make db-migrate          # Create new migration
make db-upgrade          # Apply migrations
make db-downgrade        # Rollback last migration
make db-reset            # DANGER: Reset entire database

# Code formatting
make format              # Auto-format with black, isort, ruff
make lint                # Check formatting and linting
make type-check          # Run mypy type checking
```

---

## Production Deployment

### Docker Deployment (Recommended)

**1. Build and start services**:
```bash
# Build images
make docker-build

# Start all services (API, DB, Metabase, n8n, Adminer)
make docker-up

# Or use docker-compose directly
docker-compose up --build -d
```

**2. Verify deployment**:
```bash
# Check service health
make health

# View logs
make docker-logs

# Check container status
docker-compose ps
```

**Services Available**:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Metabase**: http://localhost:6400 (Analytics)
- **n8n**: http://localhost:5678 (Automation)
- **Adminer**: http://localhost:8220 (DB GUI)

---

### Manual Deployment (VPS/Server)

**1. Server Setup**:
```bash
# Install dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install python3.11 python3.11-venv postgresql redis-server nginx

# Create application user
sudo useradd -m -s /bin/bash soleflip
sudo su - soleflip
```

**2. Application Deployment**:
```bash
# Clone repository
git clone https://github.com/your-org/soleflip.git
cd soleflip

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e .

# Configure environment
cp .env.example .env
nano .env  # Edit with production settings

# Run database migrations
alembic upgrade head

# Test server
uvicorn main:app --host 0.0.0.0 --port 8000
```

**3. Systemd Service** (Production Process Management):

Create `/etc/systemd/system/soleflip.service`:
```ini
[Unit]
Description=SoleFlipper API Service
After=network.target postgresql.service

[Service]
Type=simple
User=soleflip
Group=soleflip
WorkingDirectory=/home/soleflip/soleflip
Environment="PATH=/home/soleflip/soleflip/venv/bin"
ExecStart=/home/soleflip/soleflip/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable soleflip
sudo systemctl start soleflip
sudo systemctl status soleflip
```

**4. Nginx Reverse Proxy**:

Create `/etc/nginx/sites-available/soleflip`:
```nginx
server {
    listen 80;
    server_name api.soleflip.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Enable site**:
```bash
sudo ln -s /etc/nginx/sites-available/soleflip /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**5. SSL/TLS with Let's Encrypt**:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.soleflip.com
```

---

## Docker Operations

### Common Commands

```bash
# Start services
make docker-up
# or
docker-compose up -d

# Stop services
make docker-down
# or
docker-compose down

# View logs
make docker-logs
# or
docker-compose logs -f

# Restart specific service
docker-compose restart api

# Execute command in container
docker-compose exec api bash
docker-compose exec db psql -U postgres
```

### Service Management

**API Service**:
```bash
# Restart API
docker-compose restart api

# View API logs
docker-compose logs -f api

# Run migration in container
docker-compose exec api alembic upgrade head

# Run tests in container
docker-compose exec api pytest -v
```

**Database Service**:
```bash
# Access PostgreSQL shell
docker-compose exec db psql -U postgres -d soleflip

# Backup database
docker-compose exec db pg_dump -U postgres soleflip > backup_$(date +%Y%m%d).sql

# Restore database
docker-compose exec -T db psql -U postgres soleflip < backup_20251106.sql

# View database logs
docker-compose logs -f db
```

### Docker Compose Configuration

**File**: `docker-compose.yml`

**Services**:
- `api`: FastAPI application
- `db`: PostgreSQL database
- `metabase`: Analytics and BI
- `n8n`: Workflow automation
- `adminer`: Database GUI

---

## Database Management

### Migrations

**Create Migration**:
```bash
# Auto-generate from model changes
make db-migrate
# or
alembic revision --autogenerate -m "Add new field to Product"

# Review migration file
# Edit migrations/versions/{hash}_add_new_field.py if needed
```

**Apply Migrations**:
```bash
# Apply all pending migrations
make db-upgrade
# or
alembic upgrade head

# Apply specific migration
alembic upgrade {revision_hash}

# Check current version
alembic current
```

**Rollback Migrations**:
```bash
# Rollback one migration
make db-downgrade
# or
alembic downgrade -1

# Rollback to specific version
alembic downgrade {revision_hash}

# Rollback all migrations
alembic downgrade base
```

### Backup & Restore

**Automated Backups**:
```bash
# Create timestamped backup
make backup
# Creates: backups/soleflip_backup_YYYYMMDD_HHMMSS.sql

# Schedule daily backups (crontab)
0 2 * * * cd /path/to/soleflip && make backup
```

**Manual Backup**:
```bash
# Dump entire database
pg_dump -U postgres soleflip > backup.sql

# Dump specific table
pg_dump -U postgres -t products soleflip > products_backup.sql

# Dump with compression
pg_dump -U postgres soleflip | gzip > backup.sql.gz
```

**Restore**:
```bash
# From SQL dump
psql -U postgres soleflip < backup.sql

# From compressed dump
gunzip -c backup.sql.gz | psql -U postgres soleflip

# Using Makefile
make restore BACKUP_FILE=backups/soleflip_backup_20251106_120000.sql
```

### Database Maintenance

```bash
# Vacuum database (cleanup)
psql -U postgres -d soleflip -c "VACUUM ANALYZE;"

# Reindex database
psql -U postgres -d soleflip -c "REINDEX DATABASE soleflip;"

# Check database size
psql -U postgres -d soleflip -c "SELECT pg_size_pretty(pg_database_size('soleflip'));"

# Check table sizes
psql -U postgres -d soleflip -c "
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;
"
```

---

## Monitoring

### Health Checks

**Endpoints**:
```bash
# Application health
curl http://localhost:8000/health

# Readiness check (all dependencies)
curl http://localhost:8000/health/ready

# Liveness check (basic)
curl http://localhost:8000/health/live

# Prometheus metrics
curl http://localhost:8000/metrics
```

**Expected Response** (healthy):
```json
{
  "status": "healthy",
  "timestamp": "2025-11-06T12:00:00Z",
  "database": "connected",
  "redis": "connected",
  "version": "2.3.1"
}
```

### System Monitoring

**Resource Usage**:
```bash
# Real-time monitoring
make monitor

# CPU and memory usage
htop

# Disk usage
df -h

# Database connections
psql -U postgres -d soleflip -c "SELECT count(*) FROM pg_stat_activity;"
```

### Logs

**Application Logs**:
```bash
# Follow logs in real-time
make logs
# or
tail -f logs/app.log

# Search logs
grep "ERROR" logs/app.log
grep "StockX" logs/app.log | tail -20

# View last 100 lines
tail -100 logs/app.log
```

**Structured Logging** (JSON format):
```json
{
  "event": "api_request",
  "method": "POST",
  "path": "/api/pricing/calculate",
  "status_code": 200,
  "duration_ms": 45.2,
  "timestamp": "2025-11-06T12:00:00Z",
  "request_id": "abc123"
}
```

### Performance Metrics

**Key Metrics to Monitor**:
- API response time (target: <200ms p95)
- Database query time (target: <50ms p95)
- Error rate (target: <0.1%)
- Request rate (QPS)
- Database connections (target: <80% pool)
- Memory usage (target: <80% available)

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

**Error**: `sqlalchemy.exc.OperationalError: could not connect to server`

**Solutions**:
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection settings
psql -U postgres -h localhost -p 5432

# Verify DATABASE_URL in .env
echo $DATABASE_URL

# Test connection
python -c "from shared.database.connection import db_manager; import asyncio; asyncio.run(db_manager.initialize())"
```

#### 2. Migration Failed

**Error**: `alembic.util.exc.CommandError: Target database is not up to date`

**Solutions**:
```bash
# Check current version
alembic current

# Check pending migrations
alembic history

# Force to latest
alembic stamp head
alembic upgrade head

# If corrupted, reset (DANGER: loses data)
make db-reset
```

#### 3. Port Already in Use

**Error**: `OSError: [Errno 98] Address already in use`

**Solutions**:
```bash
# Find process using port 8000
lsof -i :8000
# or
netstat -tuln | grep 8000

# Kill process
kill -9 <PID>

# Use different port
uvicorn main:app --port 8001
```

#### 4. Import Errors / Module Not Found

**Error**: `ModuleNotFoundError: No module named 'domains'`

**Solutions**:
```bash
# Reinstall in development mode
pip install -e .

# Check PYTHONPATH
echo $PYTHONPATH

# Clear Python cache
make clean

# Verify virtual environment
which python
```

#### 5. StockX API Errors

**Error**: `401 Unauthorized` or `429 Too Many Requests`

**Solutions**:
```bash
# Check credentials in database
psql -U postgres -d soleflip -c "SELECT key, value FROM system_config WHERE key LIKE 'stockx%';"

# Test authentication
curl -X POST https://accounts.stockx.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{"grant_type":"refresh_token","refresh_token":"YOUR_TOKEN","client_id":"YOUR_ID","client_secret":"YOUR_SECRET"}'

# Check rate limiting
# Default: 10 req/sec (can be adjusted in stockx_service.py:141)
```

---

## Security

### Best Practices

**1. Environment Variables**:
```bash
# Never commit .env files
git check-ignore .env  # Should return .env

# Use strong encryption keys
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Rotate keys periodically (every 90 days)
```

**2. Database Security**:
```bash
# Use strong passwords
# Change default PostgreSQL password
psql -U postgres -c "ALTER USER postgres PASSWORD 'new_strong_password';"

# Restrict database access (pg_hba.conf)
# Allow only localhost connections for production DB
```

**3. API Security**:
```bash
# Enable CORS properly (main.py)
# Only allow trusted origins in production

# Use HTTPS in production
# Enforce with Nginx and Let's Encrypt

# Implement rate limiting
# Use FastAPI rate limit middleware
```

**4. Dependency Security**:
```bash
# Check for vulnerabilities
make security-check
# or
pip-audit
bandit -r domains/ shared/

# Update dependencies regularly
pip list --outdated
pip install --upgrade <package>
```

**5. Secrets Management**:
```bash
# Use environment variables (not hardcoded)
# Use vault systems for production (AWS Secrets Manager, HashiCorp Vault)

# Never log sensitive data
# Filter out API keys, passwords, tokens from logs
```

---

## Pre-Deployment Checklist

**Before deploying to production**:

- [ ] All tests passing (`make test`)
- [ ] Code linted and formatted (`make format && make lint`)
- [ ] Type checking passed (`make type-check`)
- [ ] Security scan passed (`make security-check`)
- [ ] Database migrations tested
- [ ] Environment variables configured
- [ ] SSL/TLS certificate installed
- [ ] Monitoring and logging configured
- [ ] Backup strategy implemented
- [ ] Load testing completed (if applicable)
- [ ] Documentation updated

**Deployment Command**:
```bash
make deploy-check  # Runs all pre-deployment checks
```

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Development commands reference
- [Testing Guide](testing/TESTING_GUIDE.md) - Testing procedures
- [API Endpoints Reference](API_ENDPOINTS.md) - API documentation
- [Features Guide](FEATURES.md) - Feature-to-code mapping

---

**Last Updated**: 2025-11-06
**Maintainer**: SoleFlipper Development Team
**Status**: ✅ Production Ready
