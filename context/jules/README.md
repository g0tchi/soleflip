# SoleFlipper API

![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)
![Framework](https://img.shields.io/badge/framework-FastAPI-green.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

SoleFlipper is a professional sneaker resale management system designed to provide a robust, scalable, and production-ready backend for tracking inventory, sales, and market data across multiple platforms.

## Table of Contents

- [Project Purpose & Architecture](#project-purpose--architecture)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
  - [Local Setup](#local-setup)
  - [Docker Setup](#docker-setup)
- [Running the Application](#running-the-application)
  - [Locally](#locally)
  - [With Docker](#with-docker)
- [Running Tests, Linters, and Type Checks](#running-tests-linters-and-type-checks)
- [Environment Configuration](#environment-configuration)
- [Key Components](#key-components)
- [Further Documentation](#further-documentation)

## Project Purpose & Architecture

The primary purpose of the SoleFlipper API is to centralize and automate the management of a sneaker resale business. It provides a comprehensive set of tools for:

- **Inventory Management**: Tracking individual items, their purchase price, condition, and status.
- **Sales Tracking**: Recording sales transactions and calculating profit.
- **Market Integration**: Connecting to external platforms like StockX to sync listings, orders, and market data.
- **Data Enrichment**: Automatically enhancing product data with details from external catalogs.
- **Analytics**: Providing insights into sales performance, profit margins, and inventory value.

The application follows a modular, domain-driven architecture:

- **`main.py`**: The main entry point that initializes the FastAPI application, middleware, and routers.
- **`shared/`**: Contains cross-cutting concerns and shared utilities like database connections, logging, error handling, and configuration management.
- **`domains/`**: Encapsulates the core business logic, separated into distinct domains (e.g., `products`, `inventory`, `integration`, `sales`). Each domain has its own API router, services, and repository logic.
- **`cli/`**: Contains command-line interface scripts for various tasks.
- **`migrations/`**: Alembic database migration scripts.
- **`tests/`**: Unit and integration tests for the application.

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 14+** (for local setup)
- **Docker and Docker Compose** (for Docker-based setup)
- **`make`** (for using Makefile shortcuts)

## Environment Setup

### Local Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    The `Makefile` provides a convenient way to install all necessary dependencies.
    ```bash
    make install-dev
    ```
    This will install both production and development dependencies and set up pre-commit hooks.

4.  **Set up the database:**
    Ensure your PostgreSQL server is running. Then, create the database:
    ```bash
    make db-setup
    ```
    This command creates the `soleflip` database (if it doesn't exist) and applies all migrations.

5.  **Configure environment variables:**
    Copy the example environment file and update it with your local configuration, especially the `DATABASE_URL` and `FIELD_ENCRYPTION_KEY`.
    ```bash
    cp .env.example .env
    # Edit .env with your settings
    ```
    You can generate a new encryption key with:
    ```bash
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ```

### Docker Setup

1.  **Clone the repository and navigate to the directory.**

2.  **Configure environment variables:**
    Copy the example environment file. The default `DATABASE_URL` is configured to work with the Docker setup. You must still provide your own secrets.
    ```bash
    cp .env.example .env
    # Edit .env, paying special attention to secrets and StockX credentials.
    ```
    The `docker-compose.yml` file may contain user/group IDs (`PUID`/`PGID`) that need to be adjusted for your system. Check the comments in the file.

3.  **Build and start the services:**
    ```bash
    make docker-up
    ```
    This command will build the API image and start all services (API, database, Metabase, etc.) in detached mode.

## Running the Application

### Locally

To run the application in development mode with hot-reloading:

```bash
make dev
```

The API will be available at `http://localhost:8000`.

### With Docker

If you used the Docker setup, the application is already running after the `make docker-up` command. You can view the logs for all services using:

```bash
make docker-logs
```

## Running Tests, Linters, and Type Checks

The project is equipped with a suite of quality assurance tools, all accessible via the `Makefile`.

-   **Run all tests:**
    ```bash
    make test
    ```
-   **Run tests with coverage report:**
    ```bash
    make test-cov
    ```
    The report will be generated in the `htmlcov/` directory.

-   **Run linting and formatting checks:**
    ```bash
    make lint
    ```
-   **Automatically format the code:**
    ```bash
    make format
    ```
-   **Run static type checking with MyPy:**
    ```bash
    make type-check
    ```
-   **Run all checks (lint, type-check, test):**
    ```bash
    make check
    ```

## Environment Configuration

The application is configured via environment variables, which can be placed in a `.env` file in the project root. Refer to `.env.example` for a complete list of available variables.

**Key required variables:**

-   `DATABASE_URL`: The full connection string for your PostgreSQL or SQLite database.
-   `FIELD_ENCRYPTION_KEY`: A 32-byte base64-encoded key for encrypting sensitive data.
-   `SECRET_KEY`: A secret key for signing tokens.
-   `STOCKX_CLIENT_ID`, `STOCKX_CLIENT_SECRET`, `STOCKX_REFRESH_TOKEN`, `STOCKX_API_KEY`: Credentials for the StockX API integration.

## Key Components

-   **`main.py`**: The application entry point. Configures and starts the FastAPI server.
-   **`shared/database/connection.py`**: Contains the `DatabaseManager` for handling all database connections and sessions.
-   **`shared/config/settings.py`**: Manages all application settings using Pydantic for validation.
-   **`domains/products/api/router.py`**: Defines the API endpoints related to product management and enrichment.
-   **`domains/inventory/api/router.py`**: Defines the API endpoints for inventory CRUD and listing management.
-   **`domains/integration/services/stockx_service.py`**: Contains all the logic for interacting with the external StockX API, including authentication and data fetching.

## Further Documentation

-   **`context/`**: This directory contains generated documentation artifacts, including changelogs and summaries from automated processes.
-   **`CHANGELOG.md`**: A manually maintained log of major changes and new features in the project.
-   **API Docs**: When the application is running, interactive API documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc).