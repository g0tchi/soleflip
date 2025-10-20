# Multi-stage build for production optimization
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy requirements and source code structure for installation
COPY pyproject.toml ./
COPY README.md ./
COPY main.py ./
COPY domains/ ./domains/
COPY shared/ ./shared/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY migrations/ ./migrations/

# Install Python dependencies
RUN pip install -e .

# Development stage
FROM base as development

# Install development dependencies
RUN pip install -e .[dev]

# Copy source code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command for development
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Copy source code
COPY --chown=appuser:appuser . .

# Production dependencies are already installed in base stage
# No need to reinstall

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Testing stage for CI/CD
FROM development as testing

# Run tests
RUN python -m pytest tests/ --tb=short

# Final production stage
FROM production as final