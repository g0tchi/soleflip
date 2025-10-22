# Soleflip Stack auf Synology NAS mit Portainer

## 🎯 Übersicht

Diese Docker Compose Konfiguration stellt einen kompletten Development Stack bereit:

- **PostgreSQL** - Zentrale Datenbank für alle Services
- **n8n** - Workflow Automation (StockX Integration, etc.)
- **Metabase** - Business Intelligence & Analytics
- **Budibase** - Low-Code Platform für Admin UIs
- **Adminer** - Datenbank Management UI

## ✅ Kompatibilität

**Alle Tools nutzen PostgreSQL** - optimal für Ressourcen-Effizienz:
- Supabase ist PostgreSQL-basiert (für volles Supabase, separates Setup nötig)
- n8n nutzt PostgreSQL für Workflow-Daten
- Metabase nutzt PostgreSQL für App-Daten
- Budibase kann PostgreSQL als Datasource nutzen

## 📋 Voraussetzungen

### Synology NAS
- DSM 7.0 oder höher
- Docker Package installiert
- Portainer installiert (optional, aber empfohlen)
- Mindestens 4GB RAM (8GB+ empfohlen)

### Ports (müssen frei sein)
- 5432 - PostgreSQL
- 5678 - n8n
- 6400 - Metabase
- 8220 - Adminer
- 8280 - Budibase
- 9000/9001 - MinIO (Object Storage für Budibase)

## 🚀 Installation

### Schritt 1: Dateien vorbereiten

1. Erstelle einen Ordner auf deiner Synology NAS (z.B. `/volume1/docker/soleflip`)

2. Kopiere folgende Dateien in diesen Ordner:
   - `docker-compose.portainer.yml`
   - `init-databases.sql`
   - `.env.portainer.example`

### Schritt 2: Umgebungsvariablen konfigurieren

1. Kopiere `.env.portainer.example` zu `.env`:
   ```bash
   cp .env.portainer.example .env
   ```

2. Bearbeite `.env` und ändere **alle** Passwörter und Secrets:
   ```bash
   nano .env  # oder verwende File Station Editor
   ```

3. **Sichere Keys generieren** (auf deinem lokalen Rechner oder via SSH):
   ```bash
   # PostgreSQL Password
   pwgen -s 32 1

   # n8n Encryption Key (genau 32 Zeichen)
   openssl rand -hex 32

   # JWT Secrets
   openssl rand -base64 32

   # Budibase API Key
   openssl rand -hex 32
   ```

### Schritt 3: Deployment mit Portainer

#### Option A: Über Portainer Web UI

1. Öffne Portainer: `http://[NAS-IP]:9000`

2. Gehe zu **Stacks** → **Add stack**

3. Konfiguration:
   - **Name**: `soleflip-stack`
   - **Build method**: Web editor
   - Kopiere den Inhalt von `docker-compose.portainer.yml`

4. Scrolle nach unten zu **Environment variables**

5. Klicke auf **Load variables from .env file** und lade deine `.env` Datei hoch

6. Klicke auf **Deploy the stack**

#### Option B: Über Docker Compose (SSH)

1. SSH auf deine Synology:
   ```bash
   ssh admin@[NAS-IP]
   ```

2. Navigiere zum Projekt-Ordner:
   ```bash
   cd /volume1/docker/soleflip
   ```

3. Starte den Stack:
   ```bash
   docker-compose -f docker-compose.portainer.yml up -d
   ```

### Schritt 4: Verifizierung

1. **Check Container Status** (in Portainer oder via SSH):
   ```bash
   docker ps
   ```

   Alle Container sollten "healthy" oder "running" sein.

2. **Check Logs** bei Problemen:
   ```bash
   docker-compose -f docker-compose.portainer.yml logs
   ```

## 🔐 Erste Anmeldung & Setup

### PostgreSQL (Adminer)
```
URL: http://[NAS-IP]:8220
System: PostgreSQL
Server: postgres
Username: soleflip
Password: [DEIN POSTGRES_PASSWORD]
Database: soleflip
```

### n8n
```
URL: http://[NAS-IP]:5678
```
- Beim ersten Start: Account anlegen
- Email & Passwort festlegen
- WICHTIG: n8n Encryption Key in `.env` nicht ändern nach dem ersten Start!

### Metabase
```
URL: http://[NAS-IP]:6400
```
- Beim ersten Start: Setup Wizard durchlaufen
- **Wichtig**: Wähle "I'll add my data later" beim Setup
- Die Metabase App-Datenbank ist bereits konfiguriert (PostgreSQL)

### Budibase
```
URL: http://[NAS-IP]:8280
```
- Beim ersten Start: Admin Account anlegen
- PostgreSQL als Datasource hinzufügen:
  - Host: `postgres` (interner DNS)
  - Port: `5432`
  - Database: `soleflip`
  - User: `soleflip`
  - Password: [DEIN POSTGRES_PASSWORD]

## 🔧 Verwaltung

### Stack starten/stoppen

**Via Portainer**:
- Stacks → soleflip-stack → Start/Stop/Restart

**Via SSH**:
```bash
cd /volume1/docker/soleflip

# Starten
docker-compose -f docker-compose.portainer.yml up -d

# Stoppen
docker-compose -f docker-compose.portainer.yml down

# Neu starten
docker-compose -f docker-compose.portainer.yml restart

# Logs anzeigen
docker-compose -f docker-compose.portainer.yml logs -f
```

### Updates durchführen

```bash
cd /volume1/docker/soleflip

# Images aktualisieren
docker-compose -f docker-compose.portainer.yml pull

# Stack neu starten mit neuen Images
docker-compose -f docker-compose.portainer.yml up -d
```

### Backups erstellen

#### PostgreSQL Datenbank Backup
```bash
# Alle Datenbanken
docker exec soleflip-postgres pg_dumpall -U soleflip > backup-$(date +%Y%m%d).sql

# Einzelne Datenbank
docker exec soleflip-postgres pg_dump -U soleflip soleflip > soleflip-backup-$(date +%Y%m%d).sql
```

#### Volume Backup (über Synology Hyper Backup)
Sichere diese Ordner:
- `/volume1/docker/soleflip` (Konfiguration)
- Docker Volumes (normalerweise unter `/volume1/@docker/volumes/`)

## 🐛 Troubleshooting

### Container startet nicht
```bash
# Logs checken
docker logs soleflip-[service-name]

# Beispiel
docker logs soleflip-postgres
docker logs soleflip-n8n
```

### PostgreSQL Connection Failed
1. Check ob PostgreSQL Container läuft: `docker ps | grep postgres`
2. Check Health: `docker inspect soleflip-postgres | grep Health -A 10`
3. Test Connection:
   ```bash
   docker exec -it soleflip-postgres psql -U soleflip -d soleflip
   ```

### Port bereits belegt
```bash
# Finde Prozess auf Port (z.B. 5678)
sudo netstat -tulpn | grep 5678

# Ändere Port in docker-compose.portainer.yml
# z.B. "5679:5678" statt "5678:5678"
```

### Zu wenig Speicher
1. Check RAM Usage: `docker stats`
2. Reduziere JAVA_OPTS für Metabase in `.env`:
   ```bash
   JAVA_OPTS="-Xmx1g -XX:+UseG1GC"  # statt 2g
   ```

### Vollständiger Reset (⚠️ ALLE DATEN GEHEN VERLOREN!)
```bash
cd /volume1/docker/soleflip

# Stack stoppen und Volumes löschen
docker-compose -f docker-compose.portainer.yml down -v

# Neu starten
docker-compose -f docker-compose.portainer.yml up -d
```

## 📊 Ressourcen Monitoring

### Container Stats anzeigen
```bash
docker stats
```

### Volume Größen checken
```bash
docker system df -v
```

## 🔒 Sicherheit

### Firewall Regeln (Synology DSM)
1. Gehe zu **Systemsteuerung** → **Sicherheit** → **Firewall**
2. Erstelle Regel für dein lokales Netzwerk
3. Erlaube nur notwendige Ports (5678, 6400, 8220, 8280)
4. **Nicht empfohlen**: Direkte Internet-Exposition ohne Reverse Proxy

### Reverse Proxy Setup (für externen Zugriff)
Verwende Synologys **Application Portal** oder **nginx**:
1. SSL Zertifikat einrichten (Let's Encrypt)
2. Reverse Proxy für jeden Service
3. Optional: HTTP Basic Auth hinzufügen

## 🔄 Integration mit Soleflip Projekt

Dein bestehendes Soleflip FastAPI Backend kann:
- **Dieselbe PostgreSQL Datenbank** verwenden
- **n8n Webhooks** triggern für Automation
- **Metabase** für Analytics nutzen
- **Budibase** für Admin-UIs verwenden

### Verbindung zum Stack
```python
# In deiner FastAPI App (.env)
DATABASE_URL=postgresql://soleflip:[PASSWORD]@[NAS-IP]:5432/soleflip
```

## 📚 Weitere Ressourcen

- [n8n Dokumentation](https://docs.n8n.io)
- [Metabase Dokumentation](https://www.metabase.com/docs)
- [Budibase Dokumentation](https://docs.budibase.com)
- [PostgreSQL Dokumentation](https://www.postgresql.org/docs/)

## ❓ Hilfe & Support

Bei Problemen:
1. Check Logs: `docker-compose logs [service-name]`
2. Check Container Health: `docker ps`
3. Verifiziere `.env` Konfiguration
4. Stelle sicher, dass alle Ports frei sind

---

**Viel Erfolg mit deinem Soleflip Stack! 🚀**
