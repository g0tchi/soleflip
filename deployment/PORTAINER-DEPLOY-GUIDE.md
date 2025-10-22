# 🚀 Soleflip Stack Deployment in Portainer - Schritt für Schritt

## Vorbereitung abgeschlossen! ✅

Die `.env` Datei mit sicheren Credentials wurde bereits erstellt:
- PostgreSQL Passwort: ✅
- n8n Encryption Key: ✅
- Budibase API Keys: ✅
- Alle anderen Secrets: ✅

## 📋 Deployment Schritte

### 1. Portainer öffnen

Öffne in deinem Browser:
```
http://localhost:9000
```

### 2. Admin Account erstellen (nur beim ersten Start)

- **Username**: admin (oder deine Wahl)
- **Password**: Mindestens 12 Zeichen, sicher wählen!
- Klicke **Create user**

### 3. Environment auswählen

- Klicke **Get Started**
- Wähle **local** (Docker environment)

### 4. Stack erstellen

#### 4.1 Navigation
- Linkes Menü: **Stacks**
- Button: **+ Add stack**

#### 4.2 Stack Konfiguration
- **Name**: `soleflip-stack`
- **Build method**: Wähle **Web editor**

#### 4.3 Docker Compose einfügen
Kopiere den **kompletten Inhalt** dieser Datei:
```
nas-deployment/docker-compose.portainer.yml
```

Füge ihn in den Web Editor ein.

#### 4.4 Environment Variables laden

**Methode 1: .env File hochladen (empfohlen)**
1. Scrolle runter zu **Environment variables**
2. Wähle **Advanced mode**
3. Klicke auf **Load variables from .env file**
4. Wähle die Datei: `nas-deployment/.env`

**Methode 2: Manuell kopieren**
1. Öffne `nas-deployment/.env`
2. Kopiere den Inhalt
3. Füge ihn in **Advanced mode** ein

#### 4.5 Deployment starten
- Klicke **Deploy the stack**
- Warte ~2-5 Minuten (es werden viele Images heruntergeladen)

### 5. Deployment Status überwachen

In Portainer siehst du:
- **Containers** werden erstellt
- **Images** werden gepullt
- **Volumes** werden angelegt
- **Network** wird konfiguriert

Grüne Häkchen = alles läuft! ✅

### 6. Container Status prüfen

Gehe zu **Containers** im linken Menü. Folgende Container sollten laufen:

| Container | Status | Port |
|-----------|--------|------|
| soleflip-postgres | Running (healthy) | 5432 |
| soleflip-n8n | Running | 5678 |
| soleflip-metabase | Running (healthy) | 6400 |
| soleflip-budibase | Running | 8280 |
| soleflip-budibase-worker | Running | - |
| soleflip-couchdb | Running | - |
| soleflip-redis | Running | - |
| soleflip-minio | Running | 9000, 9001 |
| soleflip-adminer | Running | 8220 |

**Hinweis**: `soleflip-supabase` könnte fehlschlagen (benötigt zusätzliche Services). Das ist ok - die anderen Services funktionieren trotzdem!

## 🎯 Services nutzen

### n8n - Workflow Automation
```
http://localhost:5678
```
**Erster Start:**
1. Email & Passwort für Admin-Account festlegen
2. Optional: Newsletter abbestellen
3. Los geht's mit Workflows!

### Metabase - Business Intelligence
```
http://localhost:6400
```
**Erster Start:**
1. Sprache wählen (Deutsch/English)
2. Account erstellen (Name, Email, Passwort)
3. **Wichtig**: Bei "Add your data" → **"I'll add my data later"** wählen
4. Später kannst du die Soleflip PostgreSQL-Datenbank verbinden:
   - Host: `localhost` (oder `postgres` innerhalb Docker)
   - Port: `5432`
   - Database: `soleflip`
   - User: `soleflip`
   - Password: (aus .env → POSTGRES_PASSWORD)

### Budibase - Low-Code Platform
```
http://localhost:8280
```
**Erster Start:**
1. Admin-Account erstellen
2. PostgreSQL als Datasource hinzufügen:
   - **Data Sources** → **Add new**
   - Typ: **PostgreSQL**
   - Host: `postgres` (interner Docker DNS)
   - Port: `5432`
   - Database: `soleflip`
   - User: `soleflip`
   - Password: (aus .env → POSTGRES_PASSWORD)

### Adminer - Database UI
```
http://localhost:8220
```
**Login:**
- System: **PostgreSQL**
- Server: `postgres` (oder `localhost`)
- Username: `soleflip`
- Password: (aus .env → POSTGRES_PASSWORD)
- Database: `soleflip`

### MinIO Console - Object Storage
```
http://localhost:9001
```
**Login:**
- Username: `budibase` (aus .env → MINIO_ACCESS_KEY)
- Password: (aus .env → MINIO_SECRET_KEY)

## 🔧 Stack Verwaltung in Portainer

### Stack stoppen
1. **Stacks** → `soleflip-stack`
2. Button: **Stop**

### Stack starten
1. **Stacks** → `soleflip-stack`
2. Button: **Start**

### Stack neu starten
1. **Stacks** → `soleflip-stack`
2. Button: **Restart**

### Stack löschen (⚠️ Vorsicht!)
1. **Stacks** → `soleflip-stack`
2. Button: **Delete**
3. Optional: **Automatically remove the stack's persistent volumes** (ALLE DATEN GEHEN VERLOREN!)

### Logs anschauen
1. **Containers** → Klick auf Container-Name
2. Tab: **Logs**
3. Optional: **Auto-refresh** aktivieren

### Container Console öffnen
1. **Containers** → Klick auf Container-Name
2. Button: **>_ Console**
3. Wähle `/bin/sh` oder `/bin/bash`
4. Button: **Connect**

## 🐛 Troubleshooting

### Container startet nicht
1. Gehe zu **Containers**
2. Klick auf den fehlerhaften Container
3. Tab **Logs** → Fehlermeldung suchen
4. Häufige Probleme:
   - **Port bereits belegt**: Ändere Port in docker-compose.yml
   - **Zu wenig RAM**: Reduziere JAVA_OPTS in .env (z.B. `-Xmx1g` statt `-Xmx2g`)
   - **Volume Permission**: Check Volume Permissions in **Volumes**

### PostgreSQL verbindet nicht
1. Check ob `soleflip-postgres` läuft und "healthy" ist
2. Logs checken: **Containers** → `soleflip-postgres` → **Logs**
3. Test-Verbindung via Adminer: http://localhost:8220

### Services sind langsam
1. **Dashboard** → Check **Resources**
2. RAM/CPU Usage zu hoch?
   - Stoppe nicht benötigte Services
   - Reduziere JAVA_OPTS für Metabase
3. **Stats** für einzelne Container: **Containers** → Klick auf Container → Tab **Stats**

### Stack komplett neu aufsetzen
⚠️ **ALLE DATEN GEHEN VERLOREN!**

1. **Stacks** → `soleflip-stack` → **Delete**
2. ✅ **Remove persistent volumes** aktivieren
3. Warte bis alles gelöscht ist
4. Deployment von vorne starten (Schritt 4)

## 📊 Resource Monitoring

In Portainer **Dashboard** siehst du:
- **CPU Usage** - Prozessorauslastung
- **Memory Usage** - RAM-Auslastung
- **Container Count** - Anzahl laufender Container
- **Image Count** - Anzahl lokaler Images
- **Volume Count** - Anzahl Volumes

Pro Container:
- **Containers** → Container auswählen → Tab **Stats**

## 🔐 Sicherheit

### Portainer Passwort ändern
1. Klicke auf dein **Username** oben rechts
2. **My account**
3. **Change password**

### Service Passwörter ändern
**Nach dem ersten Setup** solltest du diese Passwörter NICHT mehr ändern:
- ❌ N8N_ENCRYPTION_KEY (n8n kann dann nicht mehr auf Credentials zugreifen!)
- ❌ BUDIBASE_JWT_SECRET (Sessions werden ungültig)

**Diese können geändert werden**:
- ✅ POSTGRES_PASSWORD (aber überall anpassen!)
- ✅ MINIO_SECRET_KEY
- ✅ COUCHDB_PASSWORD

### Backup erstellen

**Methode 1: PostgreSQL Backup (in Portainer)**
1. **Containers** → `soleflip-postgres` → **>_ Console**
2. Command: `/bin/sh` → **Connect**
3. Führe aus:
   ```sh
   pg_dumpall -U soleflip > /tmp/backup.sql
   ```
4. **Files** → Download `/tmp/backup.sql`

**Methode 2: Volume Backup**
1. **Volumes** → Wähle Volume (z.B. `soleflip-stack_postgres_data`)
2. **Export** → ZIP herunterladen

## ✅ Erfolgs-Checkliste

Nach erfolgreichem Deployment:
- [ ] Alle 9 Container laufen (außer ggf. supabase)
- [ ] n8n erreichbar unter http://localhost:5678
- [ ] Metabase erreichbar unter http://localhost:6400
- [ ] Budibase erreichbar unter http://localhost:8280
- [ ] Adminer erreichbar unter http://localhost:8220
- [ ] PostgreSQL verbindbar (Test via Adminer)
- [ ] Admin-Accounts für n8n, Metabase, Budibase erstellt
- [ ] PostgreSQL als Datasource in Budibase hinzugefügt

## 🎉 Fertig!

Dein kompletter Soleflip Development Stack läuft jetzt!

**Nächste Schritte:**
- Workflows in n8n erstellen (z.B. StockX Integration)
- Dashboards in Metabase bauen
- Admin-UIs in Budibase entwickeln
- Deine FastAPI App mit dem Stack verbinden

**Viel Erfolg! 🚀**

---

Bei Problemen: Check die Logs in Portainer oder die ausführliche Anleitung in `PORTAINER-SETUP.md`
