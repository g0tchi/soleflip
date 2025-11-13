# Memori MCP Server Dockerfile
# Multi-stage build for optimized image size
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user first
RUN useradd -m -u 1000 memori

# Copy installed packages from builder to memori user home
COPY --from=builder /root/.local /home/memori/.local

# Fix ownership
RUN chown -R memori:memori /home/memori/.local

# Make sure scripts in .local are usable
ENV PATH=/home/memori/.local/bin:$PATH
ENV PYTHONPATH=/home/memori/.local/lib/python3.11/site-packages:$PYTHONPATH

# Copy application code and fix ownership
COPY --chown=memori:memori http_server.py .
COPY --chown=memori:memori config.py .

USER memori

# Expose HTTP port
EXPOSE 8080

# Environment variables (defaults, override via docker-compose)
ENV MEMORI_DATABASE_URL="postgresql://soleflip:password@postgres:5432/memori"
ENV MEMORI_NAMESPACE="soleflip"
ENV MEMORI_CONSCIOUS_INGEST="true"
ENV MEMORI_AUTO_INGEST="true"
ENV MEMORI_VERBOSE="false"
ENV MEMORI_LOGGING_LEVEL="INFO"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health'); print('OK')"

# Run HTTP server
CMD ["python", "http_server.py"]
