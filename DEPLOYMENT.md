# Soleflip Deployment Guide

## Quick Start

Deploy the complete Soleflip stack with a single command:

```bash
./deploy.sh
```

This will:
1. ✅ Build the Soleflip API Docker image
2. ✅ Deploy PostgreSQL 17, Redis, n8n, Metabase, Adminer
3. ✅ Run health checks on all services
4. ✅ Display service URLs

## Prerequisites

### System Requirements

**Minimum:**
- 8GB RAM
- 4-core CPU
- 20GB free disk space
- Docker & Docker Compose installed

**Recommended:**
- 12GB+ RAM
- 6-core+ CPU
- 50GB+ free disk space

### Docker Installation

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

## Configuration

### 1. Environment Setup

```bash
cd nas-deployment
cp .env.portainer.example .env
```

### 2. Configure Environment Variables

Edit `nas-deployment/.env`:

```bash
# Required - Change these!
POSTGRES_PASSWORD=your_secure_password
FIELD_ENCRYPTION_KEY=generate_with_command_below
N8N_ENCRYPTION_KEY=generate_with_command_below
REDIS_PASSWORD=your_redis_password

# Optional
STOCKX_CLIENT_ID=
STOCKX_CLIENT_SECRET=
```

### 3. Generate Encryption Keys

```bash
# Field encryption key (for database)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# n8n encryption key
openssl rand -hex 32
```

## Deployment

### Standard Deployment

```bash
# From project root
./deploy.sh
```

### Manual Deployment Steps

If you prefer manual control:

```bash
# 1. Build API image
docker build -t soleflip-api:latest --target production .

# 2. Deploy stack
cd nas-deployment
docker-compose -f docker-compose.portainer.yml up -d

# 3. Check status
docker-compose -f docker-compose.portainer.yml ps
```

## Service Access

After deployment, services are available at:

| Service | URL | Purpose |
|---------|-----|---------|
| **Soleflip API** | http://localhost:8000 | REST API |
| **API Documentation** | http://localhost:8000/docs | Interactive Swagger UI |
| **n8n** | http://localhost:5678 | Workflow automation |
| **Metabase** | http://localhost:6400 | Business intelligence |
| **Adminer** | http://localhost:8220 | Database management |
| **PostgreSQL** | localhost:5432 | Direct database access |

### Remote Access

For remote access (e.g., Hetzner server), replace `localhost` with your server IP:

```
http://157.90.21.65:8000  # Example Hetzner IP
```

## Database Management

### Access via Adminer

1. Open http://localhost:8220
2. Login:
   - **System:** PostgreSQL
   - **Server:** `postgres`
   - **Username:** `soleflip`
   - **Password:** (from `.env` → `POSTGRES_PASSWORD`)
   - **Database:** Choose from dropdown

### Direct PostgreSQL Access

```bash
# Via Docker
docker exec -it soleflip-postgres psql -U soleflip -d soleflip

# Via local psql client
psql -h localhost -p 5432 -U soleflip -d soleflip
```

### Available Databases

- `soleflip` - Main application database
- `n8n` - n8n workflow data
- `metabase` - Metabase configuration

## Stack Management

### View Logs

```bash
# All services
docker-compose -f nas-deployment/docker-compose.portainer.yml logs -f

# Specific service
docker logs -f soleflip-api
docker logs -f soleflip-postgres
docker logs -f soleflip-n8n
```

### Restart Services

```bash
cd nas-deployment

# Restart specific service
docker-compose -f docker-compose.portainer.yml restart soleflip-api

# Restart all services
docker-compose -f docker-compose.portainer.yml restart
```

### Stop Stack

```bash
cd nas-deployment
docker-compose -f docker-compose.portainer.yml down
```

### Stop and Remove Data

**⚠️ WARNING: This deletes all data!**

```bash
cd nas-deployment
docker-compose -f docker-compose.portainer.yml down -v
```

## Troubleshooting

### API won't start

**Check logs:**
```bash
docker logs soleflip-api --tail 100
```

**Common issues:**
- Database not ready → Wait 30 seconds after deployment
- Missing encryption key → Check `.env` file
- Port 8000 already in use → Change port in `docker-compose.portainer.yml`

### PostgreSQL connection failed

**Check PostgreSQL health:**
```bash
docker exec soleflip-postgres pg_isready -U soleflip
```

**Check logs:**
```bash
docker logs soleflip-postgres --tail 50
```

### Redis authentication failed

**Test Redis connection:**
```bash
docker exec soleflip-redis redis-cli -a "your_password" PING
# Should return: PONG
```

### n8n workflows not executing

**Check Redis connection:**
```bash
docker logs soleflip-n8n | grep -i redis
```

n8n requires Redis for queue management. Ensure Redis is running and password is correct.

### Metabase won't start

Metabase can take 2-5 minutes on first startup (database initialization).

**Check startup progress:**
```bash
docker logs soleflip-metabase -f
```

**If stuck, restart:**
```bash
docker restart soleflip-metabase
```

## Database Migrations

### Run Migrations

Migrations run automatically on API startup. To run manually:

```bash
docker exec -it soleflip-api alembic upgrade head
```

### Create New Migration

```bash
# Inside container
docker exec -it soleflip-api alembic revision --autogenerate -m "description"

# Or locally (if you have the environment)
alembic revision --autogenerate -m "description"
```

### Rollback Migration

```bash
docker exec -it soleflip-api alembic downgrade -1
```

## Backup & Restore

### Backup Database

```bash
# Full backup
docker exec soleflip-postgres pg_dumpall -U soleflip > backup-$(date +%Y%m%d-%H%M%S).sql

# Single database
docker exec soleflip-postgres pg_dump -U soleflip soleflip > soleflip-backup.sql
```

### Restore Database

```bash
# Full restore
docker exec -i soleflip-postgres psql -U soleflip < backup.sql

# Single database
docker exec -i soleflip-postgres psql -U soleflip -d soleflip < soleflip-backup.sql
```

## Production Considerations

### Security

1. **Change all default passwords** in `.env`
2. **Use strong encryption keys** (generate new ones, don't use examples)
3. **Set up firewall rules**:
   ```bash
   sudo ufw allow 22/tcp   # SSH
   sudo ufw allow 8000/tcp # API (or use reverse proxy)
   sudo ufw enable
   ```
4. **Use HTTPS** with reverse proxy (nginx/Caddy)
5. **Regular backups** (automated via cron)

### Reverse Proxy Example (nginx)

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Monitoring

**Resource usage:**
```bash
docker stats --filter "name=soleflip"
```

**API health:**
```bash
curl http://localhost:8000/health
```

## Updates & Maintenance

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and redeploy
./deploy.sh
```

### Update Docker Images

```bash
cd nas-deployment

# Pull latest images
docker-compose -f docker-compose.portainer.yml pull

# Restart with new images
docker-compose -f docker-compose.portainer.yml up -d
```

### Clean Up

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes (careful!)
docker volume prune

# Remove everything unused
docker system prune -a --volumes
```

## Performance Tuning

### Adjust Resource Limits

Edit `nas-deployment/docker-compose.portainer.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 2G      # Adjust based on your system
      cpus: '2.0'
```

### PostgreSQL Performance

For better performance on systems with more RAM:

```yaml
environment:
  POSTGRES_SHARED_BUFFERS: 512MB  # 25% of RAM
  POSTGRES_EFFECTIVE_CACHE_SIZE: 2GB  # 50% of RAM
```

## Getting Help

- **API Issues:** Check logs with `docker logs soleflip-api`
- **Database Issues:** Check `TROUBLESHOOTING.md` in `nas-deployment/`
- **Stack Issues:** Check `STACK-CHANGES.md` for recent modifications

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Docker Network                     │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Soleflip API │  │     n8n      │  │ Metabase  │ │
│  │  (FastAPI)   │  │  (Workflows) │  │    (BI)   │ │
│  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘ │
│         │                 │                 │        │
│         └─────────────────┼─────────────────┘        │
│                           │                          │
│         ┌─────────────────┴─────────────────┐        │
│         │       PostgreSQL 17 (Alpine)      │        │
│         │    (soleflip, n8n, metabase DBs)  │        │
│         └───────────────────────────────────┘        │
│                                                       │
│         ┌───────────────┐    ┌──────────────┐        │
│         │  Redis 7      │    │   Adminer    │        │
│         │  (Cache/Queue)│    │  (DB Admin)  │        │
│         └───────────────┘    └──────────────┘        │
└─────────────────────────────────────────────────────┘
```

**Total Resources:**
- Max RAM: ~6GB
- Idle RAM: ~2GB
- CPUs: ~6-7 cores (max)
