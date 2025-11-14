# Memori MCP Server - Portainer Deployment Guide

## Portainer Stack Deployment

### Option 1: Update Existing Soleflip Stack

1. **Öffne Portainer Web UI**: `http://your-nas-ip:9000`
2. Navigiere zu **Stacks** → Dein Soleflip Stack
3. Klicke auf **Editor**
4. Das Memori-Service ist bereits in `docker-compose.yml` integriert

### Service Konfiguration in Portainer

Der Memori-Service ist als **optionales Profil** konfiguriert. Um es in Portainer zu aktivieren:

#### Methode A: Profil in Portainer aktivieren

1. Gehe zu deinem Stack
2. Unter **Environment variables** → füge hinzu:
   ```
   COMPOSE_PROFILES=memori
   ```
3. Klicke **Update the stack**

#### Methode B: Service-Profil entfernen (Always-On)

Wenn du Memori dauerhaft aktivieren möchtest:

1. Im Stack Editor, finde den Memori-Service
2. Entferne diese Zeilen:
   ```yaml
   profiles:
     - memori  # Optional service, enable with --profile memori
   ```
3. Update Stack

### Environment Variables in Portainer

Füge diese Variablen im Portainer Stack hinzu:

**Stack → Environment variables → Add variable:**

```
MEMORI_NAMESPACE=soleflip
MEMORI_CONSCIOUS_INGEST=true
MEMORI_AUTO_INGEST=true
MEMORI_OPENAI_API_KEY=sk-your-key-here
MEMORI_LOGGING_LEVEL=INFO
MEMORI_VERBOSE=false
```

Oder nutze die **Advanced mode** und füge ein:

```env
MEMORI_NAMESPACE=soleflip
MEMORI_CONSCIOUS_INGEST=true
MEMORI_AUTO_INGEST=true
MEMORI_OPENAI_API_KEY=sk-your-key-here
MEMORI_LOGGING_LEVEL=INFO
MEMORI_VERBOSE=false
MEMORI_MAX_MEMORIES_PER_QUERY=5
MEMORI_CONTEXT_LIMIT=3
```

### Deployment Steps

1. **Portainer öffnen** → Stacks → Soleflip Stack
2. **Environment variables hinzufügen** (siehe oben)
3. **Profile aktivieren**:
   - Entweder `COMPOSE_PROFILES=memori` setzen
   - Oder `profiles:` Zeilen aus YAML entfernen
4. **Update Stack** → Warten bis alle Services starten
5. **Verify**: Gehe zu **Containers** → Check `soleflip-memori-mcp` Status

### Stack Volume Management

Das Memori-Volume wird automatisch erstellt:
- **Name**: `soleflip-memori-data`
- **Driver**: local
- **Backup**: Über Portainer Volumes → Browse → Download

### Networking in Portainer

Memori nutzt das bestehende `soleflip-network`:
- Interner Zugriff: `http://memori-mcp:8080` (von n8n/anderen Services)
- Kein externer Port exposed (sicher)
- Kommuniziert mit PostgreSQL über `postgres:5432`

## Portainer-spezifische Features

### 1. Container Logs anzeigen

1. Portainer → Containers → `soleflip-memori-mcp`
2. **Logs** Tab → Live logs anzeigen
3. Filter für Errors: Suche nach `"level":"error"`

### 2. Container Stats monitoren

1. Containers → `soleflip-memori-mcp` → **Stats** Tab
2. CPU, Memory, Network Usage in Echtzeit
3. Bei Performance-Problemen: Limits in Stack anpassen

### 3. Container Console Access

1. Containers → `soleflip-memori-mcp` → **Console**
2. Select shell: `/bin/sh`
3. Debug-Commands:
   ```bash
   # Check Python packages
   pip list | grep memori

   # Test DB connection
   python -c "import asyncpg; print('OK')"

   # View config
   env | grep MEMORI
   ```

### 4. Restart Policy

Bereits konfiguriert als `restart: unless-stopped`:
- Container startet automatisch nach NAS-Reboot
- Stoppt nur bei manuellem Stop in Portainer

## Integration mit anderen Stack-Services

### n8n Integration über Portainer

1. **n8n Container Console öffnen**:
   - Portainer → Containers → `soleflip-n8n` → Console

2. **MCP Config testen**:
   ```bash
   # From n8n container
   curl http://memori-mcp:8080/health
   ```

3. **n8n Workflow**:
   - Verwende `http://memori-mcp:8080` als MCP Server URL
   - Alle Services sind im selben Docker-Netzwerk

### Database Zugriff über Adminer

1. Öffne Adminer: `http://your-nas-ip:8220`
2. Login:
   - System: **PostgreSQL**
   - Server: **postgres**
   - Username: **soleflip**
   - Password: (dein `POSTGRES_PASSWORD`)
   - Database: **memori**
3. Browse Memori Tables

## Backup & Restore in Portainer

### Memori Data Backup

**Option 1: Volume Backup**
1. Portainer → Volumes → `soleflip-memori-data`
2. Browse → Download wichtige Files

**Option 2: Database Backup**
1. Portainer → Containers → `soleflip-postgres` → Console
2. Execute:
   ```bash
   pg_dump -U soleflip memori > /var/lib/postgresql/data/memori_backup.sql
   ```
3. Download via Portainer Volume Browser

**Option 3: Automated Backup (Synology)**
```bash
# SSH in NAS
docker exec soleflip-postgres pg_dump -U soleflip memori > /volume1/docker/backups/memori_$(date +%Y%m%d).sql
```

### Restore

1. Portainer → Containers → `soleflip-postgres` → Console
2. Execute:
   ```bash
   psql -U soleflip memori < /var/lib/postgresql/data/memori_backup.sql
   ```

## Stack Updates via Portainer

### Memori Code Updates

Wenn du `server.py` oder andere Files änderst:

1. **Portainer → Stacks → Soleflip**
2. Aktiviere **Build images** (Checkbox)
3. **Update the stack**
4. Portainer rebuildet automatisch das Memori-Image

### Environment Variable Updates

1. Stack → Environment variables
2. Änderungen vornehmen
3. **Update stack** (ohne Build nötig)
4. Container wird neu erstellt mit neuen Variablen

## Troubleshooting in Portainer

### Service startet nicht

1. **Check Logs**:
   - Containers → `soleflip-memori-mcp` → Logs
   - Suche nach `"level":"error"`

2. **Check Dependencies**:
   - Containers → Verify `soleflip-postgres` is **healthy**
   - Check `soleflip-network` exists

3. **Rebuild Image**:
   - Stacks → Soleflip → Enable "Build images"
   - Update stack

### Container ist Unhealthy

1. **Inspect Container**:
   - Containers → `soleflip-memori-mcp` → Inspect
   - Check "Health" section

2. **Manual Health Check**:
   - Console → Execute:
     ```bash
     python -c "import sys; sys.exit(0)"
     ```

3. **Adjust Health Check** (in Stack YAML):
   ```yaml
   healthcheck:
     interval: 60s  # Increase if needed
     start_period: 60s
   ```

### Memory/CPU Limits

Wenn Container zu viel Ressourcen nutzt:

1. **Stack Editor** → Memori Service → `deploy.resources`
2. Anpassen:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 256M  # Reduzieren
         cpus: '0.25'
   ```

## Production Best Practices

### 1. Resource Monitoring

Setze Alerts in Portainer:
- Containers → `soleflip-memori-mcp` → Stats
- Monitor: Memory > 400MB = Warning

### 2. Log Rotation

Portainer → Stacks → Add to memori service:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 3. Secrets Management

Für Production: Nutze Docker Secrets statt ENV vars

1. **Create Secret** in Portainer:
   - Secrets → Add secret
   - Name: `memori_openai_key`
   - Value: `sk-your-key`

2. **Update Stack**:
   ```yaml
   memori-mcp:
     secrets:
       - memori_openai_key
     environment:
       MEMORI_OPENAI_API_KEY_FILE: /run/secrets/memori_openai_key

   secrets:
     memori_openai_key:
       external: true
   ```

## Portainer Stack Template

Falls du einen komplett neuen Stack erstellen möchtest:

```yaml
version: '3.8'

services:
  memori-mcp:
    build: ./integrations/memori-mcp
    container_name: soleflip-memori-mcp
    restart: unless-stopped
    environment:
      MEMORI_DATABASE_URL: postgresql+asyncpg://soleflip:${POSTGRES_PASSWORD}@postgres:5432/memori
      MEMORI_NAMESPACE: ${MEMORI_NAMESPACE:-soleflip}
      MEMORI_OPENAI_API_KEY: ${MEMORI_OPENAI_API_KEY:-}
    networks:
      - soleflip-network
    depends_on:
      - postgres
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

networks:
  soleflip-network:
    external: true
```

## Synology NAS Spezifika

### File Upload zu Container

1. Portainer → Volumes → `soleflip-memori-data` → Browse
2. Upload Files direkt via Web UI
3. Oder SSH + Docker CP:
   ```bash
   docker cp local_file.py soleflip-memori-mcp:/app/
   ```

### Container Auto-Start

Bereits konfiguriert via `restart: unless-stopped`:
- Startet automatisch nach NAS-Reboot
- Überleben DSM Updates

### Network Access vom NAS

```bash
# SSH in Synology NAS
docker exec -it soleflip-memori-mcp python -c "print('Memori OK')"
```

## Support & Monitoring

### Portainer Webhooks

Setze Notifications für Container-Status:
1. Portainer → Endpoints → Docker endpoint → Webhook
2. Configure für Slack/Discord/Email
3. Trigger: Container stopped/unhealthy

### Health Monitoring

Nutze Portainer Edge Agent für:
- CPU/Memory Alerts
- Container Health Status
- Automatic restarts on failure

## Quick Reference

| Task | Portainer Location |
|------|-------------------|
| View Logs | Containers → memori-mcp → Logs |
| Restart Service | Containers → memori-mcp → Restart |
| Update Config | Stacks → Soleflip → Editor |
| Check Stats | Containers → memori-mcp → Stats |
| Console Access | Containers → memori-mcp → Console |
| Database Access | Adminer on port 8220 |
| Volume Backup | Volumes → memori-data → Browse |

## Next Steps

1. ✅ Deploy Stack in Portainer mit Memori aktiviert
2. ✅ Environment Variables konfigurieren
3. ✅ Service-Health verifizieren
4. 🔄 Ersten n8n-Workflow mit Memory erstellen
5. 🔄 Claude Code MCP-Integration testen

Fragen zur Portainer-Deployment?
