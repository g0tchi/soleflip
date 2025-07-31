FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml .
RUN pip install fastapi uvicorn sqlalchemy[asyncio] alembic psycopg2-binary asyncpg \
    pandas python-multipart pydantic python-dotenv structlog

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]