# 🐳 SoleFlip Docker Setup für Synology NAS

Komplettes Docker-Setup für die SoleFlip Platform optimiert für Synology NAS Umgebungen.

## 📋 Überblick der Services

| Service | Port | Beschreibung | URL |
|---------|------|--------------|-----|
| **API** | 8000 | SoleFlip FastAPI Backend | http://your-nas:8000 |
| **PostgreSQL** | - | Hauptdatenbank (intern) | - |
| **Redis** | - | Cache & Session Store (intern) | - |
| **Metabase** | 6400 | Analytics Dashboard | http://your-nas:6400 |
| **Budibase** | 10000 | Low-Code Platform | http://your-nas:10000 |
| **N8N** | 5678 | Workflow Automation | http://your-nas:5678 |
| **Adminer** | 8220 | Database Management | http://your-nas:8220 |
| **Nginx** | 80/443 | Reverse Proxy (optional) | http://your-nas |

## 🚀 Quick Start

### 1. Vorbereitung auf Synology NAS

```bash
# SSH in Ihr Synology NAS
ssh admin@your-nas-ip

# Wechseln zu Docker Verzeichnis
cd /volume1/docker

# Repository klonen oder Dateien hochladen
# ... (Upload via File Station oder git clone)

cd soleflipper
```

### 2. Setup ausführen

```bash
# Setup-Script ausführbar machen
chmod +x scripts/setup-synology.sh

# Setup ausführen
./scripts/setup-synology.sh
```

### 3. Konfiguration anpassen

```bash
# Umgebungsvariablen bearbeiten
vi .env

# Wichtige Einstellungen:
# - DOMAIN_NAME=your-nas.synology.me
# - POSTGRES_PASSWORD=secure_password
# - REDIS_PASSWORD=secure_password
# - Email-Einstellungen für Metabase
```

### 4. Services starten

```bash
# Alle Services starten
docker compose -f docker-compose.improved.yml up -d

# Logs verfolgen
docker compose -f docker-compose.improved.yml logs -f

# Status prüfen
docker compose -f docker-compose.improved.yml ps
```

## 🔧 Detaillierte Konfiguration

### Environment Variables (.env)

```bash
# Wichtigste Einstellungen die angepasst werden müssen:

# Domain für Ihr Synology NAS
DOMAIN_NAME=your-nas.synology.me

# Sichere Passwörter generieren
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)

# StockX API (für Integration)
STOCKX_CLIENT_ID=your_client_id
STOCKX_CLIENT_SECRET=your_client_secret

# Email für Benachrichtigungen
METABASE_SMTP_HOST=mail.infomaniak.com
METABASE_SMTP_USER=your_email@domain.com
METABASE_SMTP_PASS=your_email_password
```

### Erste Schritte nach dem Start

#### 1. API Health Check
```bash
curl http://your-nas:8000/health
```

#### 2. Metabase Setup
- Öffnen: http://your-nas:6400
- Account erstellen
- PostgreSQL Datenbank verbinden:
  - Host: `soleflip-postgres`
  - Port: `5432`
  - Database: `soleflip`
  - Username: `postgres`
  - Password: `[Ihr POSTGRES_PASSWORD]`

#### 3. Budibase Setup
- Öffnen: http://your-nas:10000
- Account erstellen
- API Integration konfigurieren:
  - Base URL: `http://soleflip-api:8000`

#### 4. N8N Setup
- Öffnen: http://your-nas:5678
- Login mit Credentials aus .env
- Workflows für StockX Integration erstellen

## 📁 Datenverzeichnisse

Alle persistenten Daten werden in `/volume1/docker/soleflipper/` gespeichert:

```
/volume1/docker/soleflipper/
├── postgres_data/          # PostgreSQL Daten
├── redis_data/             # Redis Daten
├── metabase_data/          # Metabase Konfiguration
├── budibase_data/          # Budibase Apps & Daten
├── n8n_data/              # N8N Workflows
├── api_logs/              # API Logs
├── api_uploads/           # Hochgeladene Dateien
├── backups/               # Automatische Backups
├── ssl/                   # SSL Zertifikate
└── nginx_logs/            # Nginx Logs
```

## 🔄 Backup & Wartung

### Automatische Backups

Das Setup enthält einen automatischen Backup-Service:
- **Frequenz:** Täglich um 2 Uhr nachts
- **Retention:** 30 Tage
- **Location:** `/volume1/docker/soleflipper/backups/`

### Manuelle Backups

```bash
# Alle Datenbanken sichern
docker compose -f docker-compose.improved.yml exec postgres pg_dumpall -U postgres > backup_all.sql

# Einzelne Datenbank sichern
docker compose -f docker-compose.improved.yml exec postgres pg_dump -U postgres soleflip > backup_soleflip.sql

# Redis Daten sichern
docker compose -f docker-compose.improved.yml exec redis redis-cli BGSAVE
```

### Updates

```bash
# Images aktualisieren
docker compose -f docker-compose.improved.yml pull

# Services neu starten
docker compose -f docker-compose.improved.yml up -d

# Alte Images entfernen
docker system prune -f
```

## 🚨 Troubleshooting

### Häufige Probleme

#### Service startet nicht
```bash
# Logs prüfen
docker compose -f docker-compose.improved.yml logs service-name

# Container Status prüfen
docker ps -a

# Ressourcen prüfen
docker stats
```

#### Berechtigungsprobleme
```bash
# Korrekte Berechtigungen setzen
sudo chown -R 1026:100 /volume1/docker/soleflipper
sudo chmod -R 755 /volume1/docker/soleflipper
```

#### Netzwerk-Probleme
```bash
# Docker Netzwerk prüfen
docker network ls
docker network inspect soleflip_soleflip-network

# Container IP prüfen
docker inspect soleflip-api | grep IPAddress
```

#### Database Connection Probleme
```bash
# Database Verbindung testen
docker compose -f docker-compose.improved.yml exec postgres psql -U postgres -d soleflip -c "SELECT 1;"

# API Database Verbindung testen
docker compose -f docker-compose.improved.yml exec api python -c "
from shared.database.connection import db_manager
import asyncio
async def test():
    await db_manager.initialize()
    print('Database connection successful')
asyncio.run(test())
"
```

## 🔧 Performance Optimierung

### Für Synology NAS

```yaml
# Optimierte Resource Limits
deploy:
  resources:
    limits:
      memory: 512M      # Reduziert für NAS
      cpus: '0.5'       # Begrenzt CPU Usage
    reservations:
      memory: 256M      # Garantierte Mindest-RAM
      cpus: '0.25'      # Garantierte CPU
```

### Redis Memory Optimierung

```bash
# Redis Memory Usage prüfen
docker compose -f docker-compose.improved.yml exec redis redis-cli INFO memory

# Memory Policy anpassen
docker compose -f docker-compose.improved.yml exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

## 🌐 Reverse Proxy Setup (Optional)

Für Produktionsumgebungen mit SSL:

1. **SSL Zertifikate erstellen/kopieren**
```bash
# Let's Encrypt Zertifikate nach SSL Verzeichnis kopieren
cp /usr/syno/etc/certificate/_archive/*/cert.pem /volume1/docker/soleflipper/ssl/
cp /usr/syno/etc/certificate/_archive/*/privkey.pem /volume1/docker/soleflipper/ssl/
```

2. **Nginx HTTPS Konfiguration**
```bash
# SSL Konfiguration zu nginx/conf.d/ssl.conf hinzufügen
vi nginx/conf.d/ssl.conf
```

3. **Services neu starten**
```bash
docker compose -f docker-compose.improved.yml restart nginx
```

## 📊 Monitoring

### Service Health Checks

```bash
# Alle Health Checks prüfen
for service in api postgres redis metabase budibase n8n; do
  echo "=== $service ==="
  docker compose -f docker-compose.improved.yml exec $service curl -f http://localhost:8000/health 2>/dev/null || echo "Health check failed"
done
```

### Log Monitoring

```bash
# Live Logs aller Services
docker compose -f docker-compose.improved.yml logs -f

# Nur API Logs
docker compose -f docker-compose.improved.yml logs -f api

# Errors filtern
docker compose -f docker-compose.improved.yml logs | grep -i error
```

## 🆘 Support

Bei Problemen:

1. **Logs sammeln**
2. **System Info sammeln** (`docker version`, `docker compose version`)
3. **Error Details** aus den Logs kopieren
4. **Issue erstellen** mit allen relevanten Informationen

---

**💡 Tipp:** Nutzen Sie Synology Task Scheduler für regelmäßige Wartungsaufgaben wie Image Updates und Cleanup.