#!/bin/bash

# SoleFlip Setup Script for Synology NAS
# This script prepares the Synology environment for Docker deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_ROOT="/volume1/docker/soleflipper"
PROJECT_NAME="soleflip"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  SoleFlip Synology Setup Script${NC}"
echo -e "${BLUE}======================================${NC}"

# Function to create directory if it doesn't exist
create_directory() {
    local dir=$1
    if [ ! -d "$dir" ]; then
        echo -e "${YELLOW}Creating directory: $dir${NC}"
        mkdir -p "$dir"
        chown 1026:100 "$dir"
        chmod 755 "$dir"
    else
        echo -e "${GREEN}Directory exists: $dir${NC}"
    fi
}

# Create required directories
echo -e "${BLUE}Creating Docker directories...${NC}"
create_directory "$DOCKER_ROOT"
create_directory "$DOCKER_ROOT/postgres_data"
create_directory "$DOCKER_ROOT/redis_data"
create_directory "$DOCKER_ROOT/metabase_data"
create_directory "$DOCKER_ROOT/budibase_data"
create_directory "$DOCKER_ROOT/n8n_data"
create_directory "$DOCKER_ROOT/api_logs"
create_directory "$DOCKER_ROOT/api_uploads"
create_directory "$DOCKER_ROOT/backups"
create_directory "$DOCKER_ROOT/ssl"
create_directory "$DOCKER_ROOT/nginx_logs"
create_directory "$DOCKER_ROOT/metabase/plugins"
create_directory "$DOCKER_ROOT/n8n/files"

# Set correct permissions
echo -e "${BLUE}Setting permissions...${NC}"
chown -R 1026:100 "$DOCKER_ROOT"
find "$DOCKER_ROOT" -type d -exec chmod 755 {} \;
find "$DOCKER_ROOT" -type f -exec chmod 644 {} \;

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed or not in PATH${NC}"
    echo -e "${YELLOW}Please install Docker via Synology Package Center${NC}"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo -e "${RED}Docker Compose is not available${NC}"
    echo -e "${YELLOW}Please ensure Docker Compose is installed${NC}"
    exit 1
fi

# Generate encryption key if not exists
if [ ! -f ".env" ]; then
    echo -e "${BLUE}Creating .env file...${NC}"
    cp .env.template .env

    # Generate Fernet key
    FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    sed -i "s/generate_with_fernet_key/$FERNET_KEY/g" .env

    # Generate JWT secret
    JWT_SECRET=$(openssl rand -hex 32)
    sed -i "s/your_jwt_secret_key_here/$JWT_SECRET/g" .env

    # Generate Budibase secrets
    BUDIBASE_JWT=$(openssl rand -hex 32)
    BUDIBASE_API_KEY=$(openssl rand -hex 32)
    sed -i "s/your_budibase_jwt_secret_here/$BUDIBASE_JWT/g" .env
    sed -i "s/your_budibase_api_key_here/$BUDIBASE_API_KEY/g" .env

    echo -e "${GREEN}.env file created with generated secrets${NC}"
    echo -e "${YELLOW}Please edit .env file with your specific configuration${NC}"
else
    echo -e "${GREEN}.env file already exists${NC}"
fi

# Create additional environment files
if [ ! -f ".env.api" ]; then
    echo -e "${BLUE}Creating .env.api file...${NC}"
    cat > .env.api << EOF
# API Specific Environment Variables
API_TITLE=SoleFlip API
API_VERSION=1.0.0
API_DESCRIPTION=SoleFlip Sneaker Arbitrage Platform API

# Performance Settings
API_WORKERS=4
WORKER_CLASS=uvicorn.workers.UvicornWorker
WORKER_CONNECTIONS=1000

# Logging
LOG_FORMAT=json
LOG_ROTATION=daily
LOG_RETENTION_DAYS=30

# Cache Settings
CACHE_TTL=300
CACHE_MAX_SIZE=1000

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10
EOF
    echo -e "${GREEN}.env.api file created${NC}"
fi

# Display setup completion
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  Setup completed successfully!${NC}"
echo -e "${GREEN}======================================${NC}"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Edit .env file with your configuration"
echo -e "2. Update DOMAIN_NAME in .env with your Synology DDNS"
echo -e "3. Configure email settings if needed"
echo -e "4. Run: ${BLUE}docker compose -f docker-compose.improved.yml up -d${NC}"
echo
echo -e "${YELLOW}Service URLs:${NC}"
echo -e "API:      http://your-nas:8000"
echo -e "Metabase: http://your-nas:6400"
echo -e "Budibase: http://your-nas:10000"
echo -e "N8N:      http://your-nas:5678"
echo -e "Adminer:  http://your-nas:8220"
echo
echo -e "${YELLOW}Data directories:${NC}"
echo -e "All data is stored in: $DOCKER_ROOT"
echo -e "Backups are stored in: $DOCKER_ROOT/backups"
echo