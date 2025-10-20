# Soleflip Stack Optimization Summary

## Changes Made (October 2025)

### Removed Services (Performance Optimization)
- **Supabase Studio** - Removed (incomplete configuration, requires Kong + Meta services)
  - Was using significant resources
  - Not essential for core functionality
  - Alternative: Use Adminer for database management

### Optimized Services

#### 1. PostgreSQL
- Added resource limits: 2GB RAM max, 2 CPUs
- Performance tuning: max_connections=100, shared_buffers=256MB
- Optimized cache: effective_cache_size=1GB

#### 2. n8n (Workflow Automation)
- Resource limits: 1GB RAM, 1.5 CPUs
- Added Redis queue integration for better performance
- Execution timeouts: 3600s default, 7200s max
- Enabled metrics and health checks

#### 3. Metabase (Business Intelligence)
- **Reduced from 2GB to 1.5GB RAM** (25% reduction)
- Optimized JVM: -Xmx1g -Xms512m (was -Xmx2g)
- Added G1GC with tuning: MaxGCPauseMillis=200, UseStringDeduplication
- Jetty threading: 50 max threads (down from default 254)
- Resource limits: 1.5GB RAM, 1.5 CPUs

#### 4. Budibase (Low-Code Platform)
- Resource limits: 1GB RAM, 1 CPU
- Set NODE_ENV=production, LOG_LEVEL=warn
- Worker optimized: 512MB RAM, 0.5 CPU

#### 5. Redis (Caching & Queuing)
- **Optimized memory management**: maxmemory=256mb with LRU eviction
- Shared by n8n and Budibase
- Resource limits: 256MB RAM, 0.5 CPU
- Added health checks

#### 6. MinIO (Object Storage)
- Resource limits: 512MB RAM, 0.5 CPU
- Added health checks
- Console accessible on port 9003

#### 7. CouchDB (Budibase Backend)
- Resource limits: 512MB RAM, 0.5 CPU

#### 8. Adminer (Database UI)
- Lightweight alternative to Supabase Studio
- Resource limits: 256MB RAM, 0.25 CPU
- Added useful plugins: tables-filter, tinymce

### Total Resource Footprint

**Before Optimization:**
- Unknown (Supabase dependencies not fully defined)
- Metabase: 2GB RAM

**After Optimization:**
- **Total RAM**: ~6.5GB max (conservative estimate)
- **Total CPUs**: ~8 CPUs max (concurrent load)
- **Idle RAM**: ~2-3GB (most services idle)
- **Production RAM**: ~4-5GB (normal operation)

**Per Service:**
| Service | RAM Limit | RAM Reserved | CPU Limit | CPU Reserved |
|---------|-----------|--------------|-----------|--------------|
| PostgreSQL | 2GB | 512MB | 2.0 | 0.5 |
| n8n | 1GB | 256MB | 1.5 | 0.25 |
| Metabase | 1.5GB | 512MB | 1.5 | 0.25 |
| Budibase | 1GB | 256MB | 1.0 | 0.25 |
| Budibase Worker | 512MB | 128MB | 0.5 | 0.1 |
| Redis | 256MB | 64MB | 0.5 | 0.1 |
| MinIO | 512MB | 128MB | 0.5 | 0.1 |
| CouchDB | 512MB | 128MB | 0.5 | 0.1 |
| Adminer | 256MB | 64MB | 0.25 | 0.1 |
| **TOTAL** | **~6.5GB** | **~2GB** | **~8 CPUs** | **~1.75 CPUs** |

### Performance Improvements

1. **Memory Footprint Reduced**
   - Metabase: -25% (2GB → 1.5GB)
   - Removed Supabase overhead
   - Redis limited to 256MB with smart eviction

2. **CPU Efficiency**
   - Resource limits prevent CPU hogging
   - Metabase JVM tuned for lower resource usage
   - Production mode enabled for Node.js services

3. **Database Performance**
   - PostgreSQL connection pool tuning
   - Shared database for all services (no duplication)
   - Health checks ensure service readiness

4. **Startup Time**
   - Dependency ordering optimized
   - Health checks ensure proper startup sequence

### Service Access (Default Config)

| Service | Port | Purpose |
|---------|------|---------|
| n8n | 5678 | Workflow automation & webhooks |
| Metabase | 6400 | Business intelligence & analytics |
| Budibase | 8280 | Low-code application platform |
| Adminer | 8220 | Database management UI |
| MinIO Console | 9003 | Object storage console |
| MinIO API | 9002 | S3-compatible API |
| PostgreSQL | 5432 | Direct database access |

### Recommended NAS Specifications

**Minimum:**
- 8GB RAM (leaves ~1.5GB for system)
- 4-core CPU
- 20GB free storage (for volumes)

**Recommended:**
- 12GB+ RAM (comfortable overhead)
- 6-core+ CPU
- 50GB+ free storage

**Optimal:**
- 16GB+ RAM (excellent performance)
- 8-core+ CPU
- 100GB+ SSD storage (database performance)

### Migration from Previous Stack

If upgrading from the Supabase-enabled stack:

1. **Backup data first**:
   ```bash
   docker exec soleflip-postgres pg_dumpall -U soleflip > backup.sql
   ```

2. **Stop old stack**:
   ```bash
   # In Portainer: Stop and remove stack
   ```

3. **Deploy new stack**:
   ```bash
   # In Portainer: Deploy updated docker-compose.portainer.yml
   ```

4. **Verify services**:
   ```bash
   # Check all containers are healthy
   docker ps --filter "name=soleflip"
   ```

5. **Restore data if needed**:
   ```bash
   docker exec -i soleflip-postgres psql -U soleflip < backup.sql
   ```

### Database Management

**Via Adminer (Recommended):**
- URL: http://your-nas-ip:8220
- Server: `postgres`
- Username: `soleflip`
- Password: (from .env POSTGRES_PASSWORD)
- Database: Choose from dropdown (soleflip, n8n, metabase)

**Via Direct Connection:**
```bash
psql -h your-nas-ip -p 5432 -U soleflip -d soleflip
```

### Volume Management

All volumes are explicitly named for easy identification:
- `soleflip-postgres-data` - Database storage
- `soleflip-n8n-data` - n8n workflows and credentials
- `soleflip-metabase-data` - Metabase app data
- `soleflip-budibase-data` - Budibase apps
- `soleflip-couchdb-data` - CouchDB (Budibase backend)
- `soleflip-redis-data` - Redis cache persistence
- `soleflip-minio-data` - MinIO object storage

### Monitoring & Health Checks

All services include health checks:
- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`
- MinIO: `/minio/health/live`
- Metabase: `/api/health`

Monitor in Portainer or via:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Security Best Practices

1. **Change all default passwords** in .env
2. **Generate strong keys**:
   ```bash
   openssl rand -hex 32  # For encryption keys
   openssl rand -base64 32  # For JWT secrets
   ```
3. **Use Redis password** (set REDIS_PASSWORD)
4. **Restrict port access** via Synology firewall
5. **Regular backups** of PostgreSQL data

### Troubleshooting

**High memory usage:**
- Check Metabase JAVA_OPTS (adjust -Xmx if needed)
- Verify Redis maxmemory policy is working
- Monitor with: `docker stats`

**Slow startup:**
- Normal first-time: 2-5 minutes
- Check health checks: `docker ps`
- View logs: `docker logs soleflip-<service>`

**Service won't start:**
- Check dependencies (postgres must be healthy first)
- Verify .env file is present
- Check port conflicts: `netstat -tulpn | grep <port>`

### Next Steps

1. Review and update `.env` file with secure credentials
2. Deploy stack in Portainer
3. Access services and complete initial setup
4. Configure Metabase connection to PostgreSQL
5. Set up n8n workflows
6. Create Budibase apps if needed

### Support

For issues or questions:
- Check logs: `docker logs soleflip-<service>`
- Portainer Events: Stack → Events tab
- GitHub Issues: https://github.com/your-repo/issues
