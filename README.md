# SoleFlipper 

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/yourusername/soleflip)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/postgresql-15+-blue.svg)](https://postgresql.org)

> **Professional Sneaker Resale Management System with Advanced Brand Intelligence**

SoleFlipper is a comprehensive sneaker resale management platform featuring advanced analytics, brand intelligence, and automated data processing capabilities. Built for serious resellers and businesses managing high-volume sneaker transactions.

## 🚀 Quick Start

```bash
# Clone repository
git clone <repository-url>
cd soleflip

# Install dependencies
pip install -r requirements.txt

# Setup database
docker-compose up -d postgres

# Run migrations
alembic upgrade head

# Start application
python main.py
```

📖 **Detailed setup instructions**: [`docs/setup/QUICKSTART.md`](docs/setup/QUICKSTART.md)

## 🏗️ Architecture

### Core Components

- **🔧 Core Application** (`main.py`, `pyproject.toml`) - FastAPI application with async support
- **🏢 Business Logic** (`domains/`) - Modular domain-driven architecture
- **🛠️ Utilities** (`scripts/`) - Database, analytics, and processing scripts  
- **📊 Data Management** (`data/`) - Backups, samples, and development data
- **⚙️ Configuration** (`config/`) - N8N workflows and external service configs
- **📈 Analytics** (`sql/`) - Dashboard queries and database improvements
- **📚 Documentation** (`docs/`) - Comprehensive guides and API documentation

### Directory Structure

```
soleflip/
├── 🎯 Core Files
│   ├── main.py              # FastAPI application entry point
│   ├── pyproject.toml       # Project configuration and dependencies
│   └── docker-compose.yml   # Docker services configuration
│
├── 🏢 Business Logic
│   ├── domains/             # Domain-driven architecture
│   │   ├── integration/     # Data import and processing
│   │   ├── inventory/       # Product and inventory management
│   │   ├── products/        # Product processing services
│   │   └── sales/           # Transaction and sales management
│   │
│   ├── shared/              # Shared utilities and models
│   │   ├── database/        # Database connections and models
│   │   ├── error_handling/  # Exception handling
│   │   └── logging/         # Application logging
│   │
│   └── migrations/          # Database schema migrations
│
├── 🛠️ Scripts & Utilities
│   ├── scripts/
│   │   ├── database/        # Backup and database management
│   │   ├── brand_intelligence/ # Brand analytics and deep dive
│   │   └── transactions/    # Transaction processing utilities
│   │
│   ├── data/
│   │   ├── backups/         # Database backup files
│   │   ├── samples/         # Sample data for testing
│   │   └── dev/             # Development databases
│   │
│   ├── config/              # External service configurations
│   │   └── n8n/             # N8N workflow definitions
│   │
│   └── sql/                 # SQL queries and improvements
│       ├── improvements/    # Database optimization scripts
│       └── dashboards/      # Analytics and dashboard queries
│
├── 📚 Documentation
│   ├── docs/
│   │   ├── setup/           # Installation and setup guides
│   │   ├── guides/          # Feature-specific guides
│   │   ├── api/             # API documentation and collections
│   │   └── completed_tasks/ # Project milestone documentation
│   │
│   └── temp_cleanup/        # Organized legacy scripts (72 files)
│
└── 🧪 Testing
    └── tests/               # Unit, integration, and API tests
```

## ✨ Key Features

### 🧠 Brand Intelligence System *(v2.0 New)*
- **Deep Brand Analytics** - Comprehensive brand profiles with founder info, financial data, sustainability scores
- **Historical Timeline** - 29+ major brand milestones and innovation events
- **Collaboration Tracking** - Partnership analysis with success metrics and hype scores
- **Cultural Impact Analysis** - Brand influence scoring and tier classification
- **Financial Performance** - Multi-year revenue, growth, and profitability analysis

### 📊 Advanced Analytics
- **Executive Dashboards** - High-level KPIs and performance metrics
- **Brand Performance Correlation** - Connect brand intelligence with sales data
- **Metabase Integration** - Pre-built dashboard queries and visualizations
- **Real-time Analytics** - Live transaction and inventory tracking

### 🔄 Data Processing
- **Automated Imports** - CSV processing with validation and transformation
- **N8N Integration** - Workflow automation for data synchronization
- **Duplicate Detection** - Intelligent duplicate identification and removal
- **Data Quality Checks** - Comprehensive validation and integrity monitoring

### 🗄️ Database Management
- **PostgreSQL Backend** - Robust relational database with advanced schemas
- **Automated Backups** - Scheduled backups with metadata and integrity checks
- **Migration System** - Alembic-based schema versioning and upgrades
- **Multi-Schema Architecture** - Core, Sales, Integration, and Analytics schemas

## 🎯 Recent Enhancements (v2.0)

### Brand Deep Dive System
- ✅ **Extended Brand Profiles** - 25+ new fields including founder, headquarters, financials
- ✅ **Historical Events Tracking** - 29 major milestones across top brands
- ✅ **Collaboration Network** - Nike x Off-White, Adidas x Kanye, and more
- ✅ **Financial Analytics** - Revenue, growth rates, and profitability metrics
- ✅ **Sustainability Scoring** - ESG metrics and environmental impact ratings

### Data Architecture Improvements
- ✅ **Professional File Organization** - 95+ files organized into logical directory structure
- ✅ **Comprehensive Documentation** - Versioned guides and setup instructions
- ✅ **Advanced Analytics Views** - 7 new database views for brand intelligence
- ✅ **Dashboard-Ready Queries** - 30+ pre-built SQL queries for visualization

## 📋 Prerequisites

- **Python 3.11+** - Modern Python with async support
- **PostgreSQL 15+** - Primary database system
- **Docker & Docker Compose** - Containerized services
- **Node.js 16+ *(optional)*** - For N8N automation workflows

## ⚡ Installation

### 1. Environment Setup
```bash
# Clone repository
git clone <repository-url>
cd soleflip

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\\Scripts\\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup
```bash
# Start PostgreSQL with Docker
docker-compose up -d postgres

# Run database migrations
alembic upgrade head

# Verify installation
python scripts/database/check_database_integrity.py
```

### 3. Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env  # Configure database connection, API keys, etc.
```

### 4. Start Application
```bash
# Development mode
python main.py

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 🔧 Configuration

### Database Connection
```env
DATABASE_URL=postgresql://username:password@localhost:5432/soleflip
```

### External Services
- **N8N Automation**: Configure workflows in `config/n8n/`
- **Metabase Analytics**: Import dashboards from `docs/completed_tasks/`
- **API Integration**: Setup webhook endpoints for external platforms

## 📊 Analytics & Dashboards

### Brand Intelligence Dashboards
- **Executive Overview** - Brand performance KPIs and revenue metrics
- **Historical Timeline** - Brand milestones and innovation events
- **Collaboration Network** - Partnership analysis with success metrics
- **Financial Performance** - Multi-year revenue and growth analysis
- **Cultural Impact** - Brand influence and market position analysis

### Pre-built SQL Queries
- `sql/dashboards/brand_dashboard_queries.sql` - 30+ analytics queries
- `sql/improvements/` - Database optimization scripts
- Ready for import into Metabase, Grafana, or other visualization tools

## 🚀 Usage Examples

### Import Sales Data
```bash
# Process CSV sales report
python domains/integration/api/webhooks.py --import sales_data.csv

# Verify import
python scripts/database/check_database_integrity.py
```

### Generate Analytics
```bash
# Create brand intelligence summary
python scripts/brand_intelligence/brand_deep_dive_summary.py

# Export dashboard queries
python scripts/brand_intelligence/brand_deep_dive_views.py
```

### Backup & Restore
```bash
# Create comprehensive backup
python scripts/database/create_backup.py

# Restore from backup
python scripts/database/restore_backup.py backup_file.sql
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test category
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/api/           # API endpoint tests

# Generate coverage report
pytest --cov=domains --cov-report=html
```

## 📦 Dependencies

### Core Framework
- **FastAPI** - Modern async web framework
- **SQLAlchemy** - Python SQL toolkit and ORM
- **Alembic** - Database migration tool
- **asyncpg** - High-performance PostgreSQL driver

### Analytics & Processing
- **Pandas** - Data manipulation and analysis
- **NumPy** - Numerical computing
- **Pydantic** - Data validation and settings

### Development Tools
- **Pytest** - Testing framework
- **Black** - Code formatter
- **isort** - Import sorting
- **mypy** - Static type checker

## 🔒 Security & Best Practices

### Database Security
- ✅ SQL injection protection via SQLAlchemy ORM
- ✅ Connection pooling and timeout management
- ✅ Automated backup encryption
- ✅ Role-based access control

### API Security
- ✅ Request validation with Pydantic
- ✅ Rate limiting and throttling
- ✅ CORS configuration
- ✅ Error handling and logging

## 🚀 Deployment

### Docker Deployment
```bash
# Build and deploy
docker-compose up -d

# Scale services
docker-compose up -d --scale web=3
```

### Production Checklist
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] SSL certificates installed
- [ ] Backup system configured
- [ ] Monitoring and logging setup
- [ ] Load balancer configured

## 📈 Performance

### Database Optimizations
- **Indexed Queries** - Strategic indexes on frequently queried columns
- **Connection Pooling** - Efficient database connection management
- **Query Optimization** - Analyzed and optimized slow queries
- **Automated Cleanup** - Regular maintenance and statistics updates

### Application Performance
- **Async Processing** - Non-blocking I/O operations
- **Caching Strategy** - Redis integration for frequently accessed data
- **Background Tasks** - Celery integration for heavy processing
- **Resource Monitoring** - Memory and CPU usage optimization

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit changes** (`git commit -m 'Add amazing feature'`)
4. **Push to branch** (`git push origin feature/amazing-feature`)
5. **Open Pull Request**

### Development Guidelines
- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation
- Use meaningful commit messages

## 📋 Changelog

### Version 2.0.0 (2025-08-07) - Brand Intelligence Release
#### ✨ New Features
- **Brand Deep Dive System** - Comprehensive brand analytics and intelligence
- **Historical Timeline Tracking** - Major brand milestones and events
- **Collaboration Analysis** - Partnership success metrics and hype scoring
- **Cultural Impact Assessment** - Brand influence and market position analysis
- **Financial Performance Analytics** - Multi-year revenue and growth analysis

#### 🏗️ Infrastructure
- **Professional File Organization** - Restructured codebase with logical directory hierarchy
- **Advanced Analytics Views** - 7 new database views for brand intelligence
- **Dashboard-Ready Queries** - 30+ pre-built SQL queries for visualization tools
- **Comprehensive Documentation** - Versioned guides and setup instructions

#### 🔧 Improvements
- **Database Schema Extensions** - 25+ new brand profile fields
- **Automated Backup System** - Enhanced backup with metadata and integrity checks
- **Code Organization** - Moved 95+ files from root to organized directory structure
- **Documentation Versioning** - Professional documentation with version control

### Version 1.x - Legacy Releases
- Core sneaker resale management functionality
- Basic analytics and reporting
- CSV import and data processing
- N8N workflow integration

## 🐛 Known Issues

- CSV files with special characters may require UTF-8 encoding
- Large dataset imports may require increased memory allocation
- N8N workflows require manual configuration after deployment

## 📞 Support

### Documentation
- **Setup Guide**: [`docs/setup/QUICKSTART.md`](docs/setup/QUICKSTART.md)
- **API Documentation**: [`docs/api/`](docs/api/)
- **Feature Guides**: [`docs/guides/`](docs/guides/)

### Getting Help
- **Issues**: Report bugs and feature requests via GitHub Issues
- **Discussions**: Community support and questions
- **Wiki**: Detailed technical documentation and tutorials

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** - For the excellent async web framework
- **SQLAlchemy** - For robust database ORM capabilities
- **PostgreSQL** - For reliable data storage and analytics
- **Metabase** - For powerful dashboard and visualization capabilities
- **N8N** - For flexible workflow automation

---

**SoleFlipper v2.0** - *Professional Sneaker Resale Management with Advanced Brand Intelligence*

*Built with ❤️ for the sneaker community*