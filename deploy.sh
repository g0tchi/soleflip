#!/bin/bash
set -e

# Soleflip API Deployment Script for Production/Hetzner
# This script builds the Docker image and deploys the complete stack

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$PROJECT_ROOT/nas-deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Soleflip Deployment Script v2.0     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""
echo "Project root: $PROJECT_ROOT"
echo "Deployment config: $DEPLOY_DIR"
echo ""

# Check if .env exists
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    echo -e "${RED}✗ ERROR: .env file not found!${NC}"
    echo "  Expected location: $DEPLOY_DIR/.env"
    echo "  Create from: $DEPLOY_DIR/.env.portainer.example"
    exit 1
fi

# Load and validate environment variables
echo -e "${YELLOW}Validating environment configuration...${NC}"
source "$DEPLOY_DIR/.env"

MISSING_VARS=""

if [ -z "$POSTGRES_PASSWORD" ]; then
    MISSING_VARS="${MISSING_VARS}\n  - POSTGRES_PASSWORD"
fi

if [ -z "$FIELD_ENCRYPTION_KEY" ]; then
    MISSING_VARS="${MISSING_VARS}\n  - FIELD_ENCRYPTION_KEY"
fi

if [ -z "$N8N_ENCRYPTION_KEY" ]; then
    MISSING_VARS="${MISSING_VARS}\n  - N8N_ENCRYPTION_KEY"
fi

if [ -z "$REDIS_PASSWORD" ]; then
    echo -e "${YELLOW}⚠ WARNING: REDIS_PASSWORD not set (recommended for production)${NC}"
fi

if [ -n "$MISSING_VARS" ]; then
    echo -e "${RED}✗ ERROR: Required environment variables missing:${NC}"
    echo -e "${MISSING_VARS}"
    exit 1
fi

echo -e "${GREEN}✓ Environment configuration valid${NC}"
echo ""

# Step 1: Build Docker Image
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 1: Building Soleflip API Docker Image${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

docker build \
    -t soleflip-api:latest \
    --target production \
    -f "$PROJECT_ROOT/Dockerfile" \
    "$PROJECT_ROOT"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
    echo "  Image: soleflip-api:latest"
else
    echo -e "${RED}✗ Docker build failed${NC}"
    exit 1
fi

echo ""

# Step 2: Update docker compose to use built image
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 2: Preparing Deployment Configuration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$DEPLOY_DIR"

# Create deployment-specific compose file
cp docker-compose.portainer.yml docker-compose.deploy.yml

# Replace build section with image reference for soleflip-api
sed -i '/soleflip-api:/,/container_name: soleflip-api/ {
    /build:/,/target: production/d
}' docker-compose.deploy.yml

sed -i '/soleflip-api:/a \    image: soleflip-api:latest' docker-compose.deploy.yml

echo -e "${GREEN}✓ Deployment configuration prepared${NC}"
echo ""

# Step 3: Deploy Stack
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 3: Deploying Stack${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

docker compose -f docker-compose.deploy.yml up -d

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Stack deployed successfully${NC}"
else
    echo -e "${RED}✗ Stack deployment failed${NC}"
    rm -f docker-compose.deploy.yml
    exit 1
fi

# Clean up temporary file
rm -f docker-compose.deploy.yml

echo ""

# Step 4: Health Checks
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 4: Health Checks${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo "Waiting for services to start..."
sleep 5

# Check PostgreSQL
echo -n "PostgreSQL 17:      "
for i in {1..15}; do
    if docker exec soleflip-postgres pg_isready -U soleflip > /dev/null 2>&1; then
        echo -e "${GREEN}✓ healthy${NC}"
        break
    fi
    if [ $i -eq 15 ]; then
        echo -e "${RED}✗ unhealthy${NC}"
    fi
    sleep 2
done

# Check Redis
echo -n "Redis:              "
if docker exec soleflip-redis redis-cli -a "$REDIS_PASSWORD" PING > /dev/null 2>&1; then
    echo -e "${GREEN}✓ healthy${NC}"
else
    echo -e "${YELLOW}⚠ check manually${NC}"
fi

# Check Soleflip API
echo -n "Soleflip API:       "
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ healthy${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ unhealthy${NC}"
    fi
    sleep 2
done

# Check n8n
echo -n "n8n:                "
if docker ps --filter "name=soleflip-n8n" --filter "status=running" | grep -q soleflip-n8n; then
    echo -e "${GREEN}✓ running${NC}"
else
    echo -e "${YELLOW}⚠ check manually${NC}"
fi

# Check Metabase
echo -n "Metabase:           "
if docker ps --filter "name=soleflip-metabase" --filter "status=running" | grep -q soleflip-metabase; then
    echo -e "${GREEN}✓ running${NC}"
else
    echo -e "${YELLOW}⚠ check manually${NC}"
fi

# Check Adminer
echo -n "Adminer:            "
if docker ps --filter "name=soleflip-adminer" --filter "status=running" | grep -q soleflip-adminer; then
    echo -e "${GREEN}✓ running${NC}"
else
    echo -e "${YELLOW}⚠ check manually${NC}"
fi

echo ""

# Display service URLs
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Deployment Complete! 🚀${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}Service URLs (adjust IP for remote access):${NC}"
echo ""
echo "  📊 Soleflip API:    http://localhost:8000"
echo "  📖 API Docs:        http://localhost:8000/docs"
echo "  🔄 n8n:             http://localhost:5678"
echo "  📈 Metabase:        http://localhost:6400"
echo "  🗄️  Adminer:         http://localhost:8220"
echo "  🐘 PostgreSQL:      localhost:5432"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo ""
echo "  View all logs:"
echo "    docker compose -f $DEPLOY_DIR/docker-compose.portainer.yml logs -f"
echo ""
echo "  View API logs only:"
echo "    docker logs -f soleflip-api"
echo ""
echo "  Restart a service:"
echo "    docker compose -f $DEPLOY_DIR/docker-compose.portainer.yml restart <service>"
echo ""
echo "  Stop entire stack:"
echo "    docker compose -f $DEPLOY_DIR/docker-compose.portainer.yml down"
echo ""
echo "  Check service status:"
echo "    docker compose -f $DEPLOY_DIR/docker-compose.portainer.yml ps"
echo ""
echo -e "${GREEN}Happy coding! 💻${NC}"
echo ""
