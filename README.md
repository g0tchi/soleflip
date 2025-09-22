# SoleFlipper 

[![Version](https://img.shields.io/badge/version-2.2.0-blue.svg)](https://github.com/yourusername/soleflip)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/postgresql-15+-blue.svg)](https://postgresql.org)

> **Professional Sneaker Resale Management System with Advanced Brand Intelligence**

SoleFlipper is a comprehensive sneaker resale management platform featuring advanced analytics, brand intelligence, and automated data processing capabilities. Built for serious resellers and businesses managing high-volume sneaker transactions.

## 🚀 Docker-based Setup (Recommended)

This is the recommended way to run the entire SoleFlipper stack, including the API, database, Metabase, and n8n.

### Prerequisites
- Docker and Docker Compose installed on your system.

### 1. Configure Environment
First, create a `.env` file for your configuration. You can copy the provided example file:
```bash
cp .env.example .env
```
Now, open the `.env` file in a text editor and **set a secure `FIELD_ENCRYPTION_KEY`**. You can generate one with this command:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
The `DATABASE_URL` in the `.env.example` is already configured for this Docker setup.

### 2. Run the Stack
With the `.env` file configured, start all services using Docker Compose:
```bash
docker-compose up --build -d
```
- `--build` will build the API image for the first time.
- `-d` will run the services in the background.

### 3. Accessing Services
- **SoleFlipper API**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/docs`
- **Metabase**: `http://localhost:6400`
- **n8n**: `http://localhost:5678`
- **Adminer (Database GUI)**: `http://localhost:8220`

The first time you run the stack, the API service will automatically run database migrations.

### 4. Initial Setup (StockX API)
To use the StockX features, you need to perform a one-time setup to get your API credentials. Follow the detailed guide here:
> **StockX Setup Guide:** [`docs/guides/stockx_auth_setup.md`](docs/guides/stockx_auth_setup.md)

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
│   ├── domains/             # Domain-driven architecture (DDD)
│   │   ├── integration/
│   │   ├── inventory/
│   │   ├── products/
│   │   └── sales/
│   │
│   ├── shared/              # Shared utilities (DB connection, models)
│   └── migrations/          # Database schema migrations
│
├── 🛠️ Scripts & Utilities
│   ├── scripts/             # Admin, setup, and operational scripts
│   ├── data/                # Sample data and backups
│   └── sql/                 # SQL for improvements, etc.
│
├── ⚙️ Configuration & Analytics
│   ├── config/              # Configs for n8n, API docs, etc.
│   │   ├── api/
│   │   └── n8n/
│   │
│   └── metabase/            # Metabase queries, views, and dashboards
│       ├── queries/
│       └── views/
│
├── 📚 Documentation
│   ├── docs/
│       ├── setup/
│       └── guides/
│
└── 🧪 Testing
    └── tests/               # Unit, integration, and API tests
```

## ✨ Key Features

### 🆕 Recent Features (v2.2.0)
- **🚀 QuickFlip Arbitrage System**: Automated detection of profitable arbitrage opportunities across platforms
- **💼 Budibase Integration**: Low-code business application for visual StockX API management
- **🏭 Supplier Management**: Complete supplier account import and management system
- **🐳 Enhanced Docker Infrastructure**: Production-ready Synology NAS deployment support
- **📈 StockX API Enhancements**: Comprehensive gap analysis and improved endpoint validation

### 🧠 Brand Intelligence System
- **Deep Brand Analytics**: Comprehensive brand profiles with founder info, financial data, sustainability scores.
- **Historical Timeline**: Track major brand milestones and innovation events.
- **Collaboration Tracking**: Analyze partnership success with metrics and hype scores.
- **Cultural Impact Analysis**: Brand influence scoring and tier classification.
- **Financial Performance**: Multi-year revenue, growth, and profitability analysis.

### 📊 Advanced Analytics
- **Executive Dashboards**: High-level KPIs and performance metrics.
- **Metabase Integration**: Pre-built dashboards and queries for immediate insights. See `metabase/` for details.
- **Real-time Analytics**: Live transaction and inventory tracking.

### 🔄 Data Processing & Automation
- **StockX API Integration**: Automated, scheduled fetching of orders from the StockX API with OAuth2 support.
- **N8N Workflows**: Pre-built workflows in `config/n8n/` for data synchronization and automation.
- **Legacy CSV Imports**: Robust processing pipeline with validation and transformation.

### 🗄️ Robust Backend
- **PostgreSQL Database**: Strong, relational database with an advanced, multi-schema architecture.
- **Automated Backups**: Reliable, scheduled backups with integrity checks using the `scripts/database/create_backup.py` script.
- **Alembic Migrations**: Keeps the database schema versioned and in sync.

## 📋 Prerequisites

- **Docker & Docker Compose**: For running the entire application stack.
- **Python 3.11+**: For running helper scripts locally.

## 🔧 Configuration

### Database & Services
The application is configured using environment variables. Copy the example file and customize it for your environment:
```bash
cp .env.example .env
```
Key variables to configure in your `.env` file:
- `DATABASE_URL`: Connection string for your PostgreSQL database.
- `FIELD_ENCRYPTION_KEY`: A secret key for encrypting sensitive data. Generate one with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### StockX & n8n API Keys
For full functionality, you need to configure API credentials for StockX and n8n.

1.  **StockX API**: The application requires OAuth2 credentials to fetch data from StockX. Follow the detailed guide to get your `client_id`, `client_secret`, and `refresh_token`.
    > **Full Guide**: [`docs/guides/stockx_auth_setup.md`](docs/guides/stockx_auth_setup.md)

2.  **n8n Workflows**: The workflows in `config/n8n/` may require API keys or other credentials to be configured within the n8n UI. See the guides in `docs/guides/n8n_integration/` for more details.

## 📊 Analytics & Dashboards (Metabase)

This project is designed for deep analytics using Metabase. We provide pre-built assets to get you started quickly.

-   **Dashboard Import File**: A ready-to-import Metabase dashboard file is located at `metabase/metabase_dashboards.json`.
-   **Dashboard SQL Queries**: The powerful SQL queries that power the dashboards can be found in `metabase/queries/brand_dashboard_sql_queries.sql`. These can be used for reference or to build your own custom dashboards.

For instructions on setting up Metabase and importing these assets, see the guide:
> **Setup Guide**: [`docs/metabase_setup_guide.md`](docs/metabase_setup_guide.md)

## 🚀 Usage Examples

### Import Sales Data
```bash
# To process a legacy CSV sales report:
python domains/integration/api/webhooks.py --import sales_data.csv
```

### Run a Database Health Check
```bash
# Verify database integrity and get statistics:
python scripts/database/check_database_integrity.py
```

### Create a Backup
```bash
# Create a comprehensive, verified database backup:
python scripts/database/create_backup.py
```
This will create a backup file and a `restore_backup.sh` script in the same directory for easy recovery.

### Restore from a Backup
```bash
# To restore, run the generated shell script:
cd scripts/database/
./restore_backup.sh
```

## 🧪 Testing

The project has a comprehensive test suite.
```bash
# Run all tests
pytest

# Run specific test categories (unit, integration)
pytest -m unit
pytest -m integration

# Generate a test coverage report
pytest --cov=domains --cov-report=html
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1.  **Fork the repository.**
2.  Create a new feature branch (`git checkout -b feature/my-new-feature`).
3.  Commit your changes (`git commit -m 'Add some feature'`).
4.  Push to the branch (`git push origin feature/my-new-feature`).
5.  **Open a Pull Request.**

Please ensure your code follows PEP 8, includes tests for new features, and updates documentation where necessary.

## 📋 Changelog

All notable changes to this project are documented in the `CHANGELOG.md` file.
> **[View the full Changelog](CHANGELOG.md)**

## 📞 Support & Contact

-   **Documentation**: For detailed guides on setup, features, and architecture, please browse the `docs/` directory.
-   **Bug Reports & Feature Requests**: If you encounter a bug or have an idea for a new feature, please open an issue on GitHub.
-   **General Questions**: For general questions and community discussions, please use the GitHub Discussions section.

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.