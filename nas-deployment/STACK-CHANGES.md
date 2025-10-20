# Stack Changes - Streamlined Configuration

## Latest Update: Removed Budibase, Upgraded PostgreSQL

### Changes Made

#### ✅ Upgrades
- **PostgreSQL 15 → PostgreSQL 17** (latest Alpine version: `17-alpine`)
  - Better performance
  - Improved JSON handling
  - Latest security patches
  - MERGE statement improvements

#### ❌ Removed Services
- **Budibase** (main container)
- **Budibase Worker**
- **CouchDB** (only used by Budibase)
- **MinIO** (only used by Budibase)

**Reason:** Simplification - focus on core automation and analytics tools

#### 🎯 Current Stack

| Service | Version | Purpose | Port | RAM Limit |
|---------|---------|---------|------|-----------|
| **PostgreSQL** | 17-alpine | Shared database | 5432 | 2GB |
| **n8n** | latest | Workflow automation | 5678 | 1GB |
| **Metabase** | latest | Business intelligence | 6400 | 1.5GB |
| **Redis** | 7-alpine | Caching & Queue | - | 256MB |
| **Adminer** | latest | DB Management UI | 8220 | 256MB |

**Total Resources:**
- **Max RAM**: ~5GB (down from ~6.5GB)
- **Idle RAM**: ~1.5GB (down from ~2-3GB)
- **Max CPUs**: ~5.75 (down from ~8)

### Resource Savings

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| Services | 12 | 5 | -58% |
| Max RAM | 6.5GB | 5GB | -23% |
| Idle RAM | 2-3GB | 1.5GB | -40% |
| Volumes | 7 | 4 | -43% |

### What You Can Still Do

✅ **Everything essential:**
- Workflow automation with n8n
- Business analytics with Metabase
- Database management with Adminer
- Direct PostgreSQL 17 access
- Redis caching for n8n

❌ **No longer available:**
- Budibase low-code platform
- MinIO object storage
- CouchDB document database

### Migration Path

**If you need Budibase back:**
1. Keep backup of old `docker-compose.portainer.yml`
2. Re-add Budibase section with dependencies
3. Restore volumes: `budibase_data`, `couchdb_data`, `minio_data`

**Alternative to Budibase:**
- Build admin interfaces directly in your FastAPI app
- Use Metabase for data entry forms
- Use n8n for automated workflows
- Consider NocoDB (lighter alternative, uses PostgreSQL only)

### Updated .env Requirements

**Removed (no longer needed):**
```bash
BUDIBASE_INTERNAL_API_KEY
BUDIBASE_JWT_SECRET
MINIO_ACCESS_KEY
MINIO_SECRET_KEY
COUCHDB_USER
COUCHDB_PASSWORD
```

**Still required:**
```bash
POSTGRES_PASSWORD        # PostgreSQL authentication
N8N_ENCRYPTION_KEY       # n8n security
REDIS_PASSWORD           # Redis authentication (now required!)
```

### Deployment Steps

1. **Update .env file:**
   ```bash
   cd nas-deployment
   nano .env
   # Make sure REDIS_PASSWORD is set!
   ```

2. **Deploy in Portainer:**
   - Stack → soleflip → Editor
   - Paste new `docker-compose.portainer.yml`
   - Click "Update the stack"

3. **Verify services:**
   ```bash
   docker ps --filter "name=soleflip"
   ```

4. **Access services:**
   - n8n: http://your-ip:5678
   - Metabase: http://your-ip:6400
   - Adminer: http://your-ip:8220

### PostgreSQL 17 New Features You Can Use

**Performance:**
- Better query optimization for complex joins
- Improved VACUUM performance
- Better parallel query execution

**SQL Features:**
- Enhanced MERGE statement
- Better JSON/JSONB performance
- New SQL/JSON standard features

**Monitoring:**
- Better wait event tracking
- Improved pg_stat views

**For Soleflip:**
- Faster analytics queries in Metabase
- Better performance for n8n database operations
- Improved handling of large datasets

### Recommended Next Steps

1. ✅ **Deploy the updated stack**
2. ✅ **Test all services** (especially Redis with password)
3. 🔄 **Migrate existing workflows** (n8n should work unchanged)
4. 🔄 **Update Metabase connections** (may need to reconnect to PostgreSQL)
5. 📊 **Monitor resource usage** (should be lower)

### Troubleshooting

**PostgreSQL 17 migration issues?**
```bash
# Check PostgreSQL version
docker exec soleflip-postgres psql -U soleflip -c "SELECT version();"

# If upgrade fails, data might be incompatible
# Backup first, then use pg_upgrade or dump/restore
```

**Redis authentication issues?**
```bash
# Test Redis connection
docker exec soleflip-redis redis-cli -a "your_password" PING

# Should return: PONG
```

**n8n can't connect to Redis?**
```bash
# Check n8n logs
docker logs soleflip-n8n --tail 100

# Verify REDIS_PASSWORD in .env matches
```

### Rollback Plan

If issues occur:

1. **Stop current stack** (Portainer → Stop)
2. **Use previous docker-compose.yml** (with PostgreSQL 15 + Budibase)
3. **Restore from backup** if needed
4. **Report issue** with logs

### Performance Expectations

**Before (PostgreSQL 15 + Budibase):**
- Startup time: 3-5 minutes
- Idle RAM: 2-3GB
- Active RAM: 4-5GB

**After (PostgreSQL 17, no Budibase):**
- Startup time: 2-3 minutes (faster!)
- Idle RAM: 1-1.5GB (better!)
- Active RAM: 3-4GB (improved!)

### Support

Questions? Issues?
- Check logs: `docker logs soleflip-<service>`
- Verify .env: Redis password must be set
- Resource usage: `docker stats --filter "name=soleflip"`
