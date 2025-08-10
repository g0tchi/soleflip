# 🚀 SoleFlipper Quick Start Guide

## 5-Minute Setup

### 1. Prerequisites Check
```bash
# Verify Python version (3.11+ required)
python --version

# Verify PostgreSQL is installed and running
pg_isready

# Create database
createdb soleflip
```

### 2. Install & Configure
```bash
# Install dependencies
pip install fastapi[all] sqlalchemy[asyncio] alembic psycopg2-binary structlog

# Set environment variable
export DATABASE_URL="postgresql://username:password@localhost/soleflip"

# Run database setup
alembic upgrade head
```

### 3. Start Application
```bash
# Start development server
uvicorn main:app --reload

# Verify it's running
curl http://localhost:8000/health
```

### 4. Test Data Import
```bash
# Upload a CSV file (StockX format)
curl -X POST "http://localhost:8000/api/v1/integration/webhooks/stockx/upload" \
  -F "file=@your_data.csv" \
  -F "validate_only=true"
```

### 5. View Documentation
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## First Data Import

### Sample StockX CSV Format
```csv
Order Number,Sale Date,Item,Size,Listing Price,SKU,Seller Fee,Total Payout
SX-001,01/15/2024 10:30:00,Nike Air Jordan 1,9,180.00,555088-101,17.10,143.55
SX-002,01/16/2024 14:20:00,Adidas Yeezy 350,10.5,250.00,FY2903,23.75,204.80
```

### Upload and Process
```bash
# Upload for validation only
curl -X POST "http://localhost:8000/api/v1/integration/webhooks/stockx/upload" \
  -F "file=@stockx_data.csv" \
  -F "validate_only=true"

# Upload and import data
curl -X POST "http://localhost:8000/api/v1/integration/webhooks/stockx/upload" \
  -F "file=@stockx_data.csv" \
  -F "batch_size=1000"
```

## Essential Commands

### Database Operations
```bash
# Check current migration
alembic current

# Create new migration
alembic revision --autogenerate -m "Add new feature"

# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test types
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m api           # API tests only
```

### API Usage Examples

#### Check Import Status
```bash
# Get all import batches
curl http://localhost:8000/api/v1/integration/webhooks/import-status

# Get specific batch status
curl http://localhost:8000/api/v1/integration/webhooks/import-status/{batch-id}
```

#### Manual File Upload
```bash
# Auto-detect file type
curl -X POST "http://localhost:8000/api/v1/integration/webhooks/manual/upload" \
  -F "file=@unknown_format.csv" \
  -F "source_type=auto"
```

#### Notion Integration
```bash
# Import Notion database export
curl -X POST "http://localhost:8000/api/v1/integration/webhooks/notion/import" \
  -H "Content-Type: application/json" \
  -d @notion_export.json
```

## Troubleshooting Quick Fixes

### Database Connection Issues
```bash
# Test database connection
psql "postgresql://user:password@localhost/soleflip" -c "SELECT 1;"

# Check if database exists
psql -h localhost -U postgres -l | grep soleflip

# Recreate database if needed
dropdb soleflip && createdb soleflip && alembic upgrade head
```

### Application Won't Start
```bash
# Check Python path
which python

# Install missing dependencies
pip install -r requirements.txt

# Check port availability
lsof -i :8000

# Start with debug logging
uvicorn main:app --reload --log-level debug
```

### Import Processing Failures
```bash
# Check application logs
tail -f logs/application.log

# Validate file format
head -5 your_data.csv

# Test with validation only first
curl -X POST "http://localhost:8000/api/v1/integration/webhooks/stockx/upload" \
  -F "file=@your_data.csv" \
  -F "validate_only=true"
```

## Next Steps

1. **Set up Metabase**: Follow `docs/metabase_setup_guide.md`
2. **Configure n8n**: Use webhook endpoints for automation
3. **Customize validation**: Modify `domains/integration/services/validators.py`
4. **Add new data sources**: Extend import processors
5. **Monitor performance**: Use `/health` endpoint and database metrics

## Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/new-import-source

# 2. Add your code
# domains/integration/services/new_validator.py

# 3. Write tests
# tests/unit/test_new_validator.py

# 4. Run tests
pytest tests/unit/test_new_validator.py

# 5. Test API endpoints
curl -X POST "http://localhost:8000/api/v1/your-new-endpoint"

# 6. Generate migration if needed
alembic revision --autogenerate -m "Add new source support"

# 7. Commit and push
git add . && git commit -m "Add new import source" && git push
```

## Production Checklist

- [ ] Set secure `SECRET_KEY` environment variable
- [ ] Configure `ALLOWED_ORIGINS` for CORS
- [ ] Set up SSL/TLS certificates
- [ ] Configure database connection pooling
- [ ] Set up log rotation
- [ ] Configure backup strategy
- [ ] Set up monitoring/alerting
- [ ] Configure rate limiting
- [ ] Set up Metabase dashboards
- [ ] Test import/export procedures

---

**Need help?** Check the full `README.md` or create an issue on GitHub.