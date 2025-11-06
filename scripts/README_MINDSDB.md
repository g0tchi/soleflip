# MindsDB Knowledge Base Setup für SoleFlipper

## Problem: IP-basierter Zugriff

Die MindsDB-Instanz unter `https://minds.netzhouse.synology.me/` ist durch eine **IP-basierte Zugriffsbeschränkung** geschützt. Daher muss das Script von einem System mit Zugriff auf die Instanz ausgeführt werden (z.B. im gleichen Netzwerk oder mit VPN-Zugang).

## Lösung: Lokales Python-Script

Das bereitgestellte Script `create_mindsdb_knowledge_bases.py` erstellt automatisch Knowledge Bases mit dem Inhalt des `context/`-Ordners.

---

## Voraussetzungen

### 1. Python 3.7+ installiert
```bash
python3 --version
```

### 2. Requests-Bibliothek installieren
```bash
pip install requests
```

### 3. Netzwerkzugang zur MindsDB-Instanz
- Im gleichen Netzwerk wie der Synology NAS, oder
- VPN-Verbindung zum Netzwerk, oder
- Direkter Zugriff auf den Synology NAS

---

## Verwendung

### Schnellstart

1. **Zugangsdaten prüfen**

   Öffne `create_mindsdb_knowledge_bases.py` und überprüfe die Konfiguration:
   ```python
   MINDSDB_URL = "https://minds.netzhouse.synology.me"
   USERNAME = "g0tchi"
   PASSWORD = "iK3C9NX7czMQhXQ3"
   PROJECT_NAME = "soleflipper"
   ```

2. **Script ausführen**
   ```bash
   cd /path/to/soleflip
   python3 scripts/create_mindsdb_knowledge_bases.py
   ```

3. **Fortschritt beobachten**

   Das Script zeigt detaillierte Ausgaben:
   ```
   ============================================================
   MindsDB Knowledge Base Creator for SoleFlipper
   ============================================================

   🔐 Authenticating with MindsDB...
   ✅ Successfully authenticated!
   📁 Creating project 'soleflipper'...
   ✅ Project 'soleflipper' created successfully

   Processing category: migrations
   📄 Found 15 files in migrations
   📚 Creating knowledge base 'kb_migrations'...
   ✅ Knowledge base 'kb_migrations' created successfully
   ...
   ```

---

## Was wird erstellt?

Das Script erstellt **6 Knowledge Bases** im MindsDB-Projekt `soleflipper`:

| Knowledge Base | Inhalt | Dateien |
|----------------|---------|---------|
| **kb_migrations** | Datenbankmigrationen, Schema-Evolution | ~15 .md Dateien |
| **kb_integrations** | StockX, Metabase, Awin, APIs | ~10 .md Dateien |
| **kb_architecture** | System-Design, Datenmodelle | ~12 .md Dateien |
| **kb_refactoring** | Code-Qualität, Best Practices | ~12 .md Dateien |
| **kb_notion** | Notion-Integration | ~7 .md Dateien |
| **kb_archived** | Historische Dokumentation | ~10 .md Dateien |

### Ausgeschlossene Dateien

Das Script überspringt automatisch:
- Binärdateien (.png, .jpg, .pdf)
- Komprimierte Dateien (.csv.gz)
- Große Datensamples

---

## Fehlerbehebung

### ❌ "Authentication failed"

**Problem:** Login-Credentials sind falsch

**Lösung:**
1. Prüfe Username/Password im Script
2. Teste manuellen Login im Browser: `https://minds.netzhouse.synology.me/`

---

### ❌ "Access denied" / "Connection refused"

**Problem:** Keine Netzwerkverbindung zur MindsDB-Instanz

**Lösungen:**
1. **Gleiche Netzwerk:** Bist du im gleichen Netzwerk wie der Synology NAS?
2. **VPN:** Verbinde dich mit dem VPN
3. **Firewall:** Prüfe Synology Firewall-Einstellungen
4. **Port:** Stelle sicher, dass Port 443 (HTTPS) erreichbar ist

Test-Befehl:
```bash
curl -I https://minds.netzhouse.synology.me/
```

Erwartete Ausgabe (sollte NICHT "Access denied" sein):
```
HTTP/2 200 OK
```

---

### ❌ "Context directory not found"

**Problem:** Script wird vom falschen Verzeichnis ausgeführt

**Lösung:**
```bash
cd /home/user/soleflip
python3 scripts/create_mindsdb_knowledge_bases.py
```

---

### ❌ "No markdown files found"

**Problem:** Context-Ordner ist leer oder hat keine .md-Dateien

**Lösung:**
```bash
# Prüfe, ob der context/-Ordner existiert
ls -la context/

# Prüfe, ob Markdown-Dateien vorhanden sind
find context/ -name "*.md"
```

---

## Manuelle Alternative

Falls das automatische Script nicht funktioniert, kannst du die Knowledge Bases auch **manuell über das MindsDB Web-Interface** erstellen:

### Schritt 1: In MindsDB einloggen
1. Öffne: `https://minds.netzhouse.synology.me/`
2. Login mit: `g0tchi` / `iK3C9NX7czMQhXQ3`

### Schritt 2: Projekt erstellen
1. Klicke auf **"Projects"**
2. Klicke auf **"Create Project"**
3. Name: `soleflipper`
4. Klicke **"Create"**

### Schritt 3: Knowledge Base erstellen (für jede Kategorie)
1. Wähle Projekt `soleflipper`
2. Klicke auf **"Knowledge Bases"**
3. Klicke **"Create Knowledge Base"**
4. Name: z.B. `kb_migrations`
5. Füge Markdown-Dateien hinzu (Drag & Drop oder Copy-Paste)
6. Klicke **"Create"**

Wiederhole Schritt 3 für alle 6 Kategorien.

---

## Erweiterte Konfiguration

### Andere MindsDB-Instanz verwenden

Ändere im Script:
```python
MINDSDB_URL = "https://your-mindsdb-instance.com"
```

### Anderen Projekt-Namen verwenden

Ändere im Script:
```python
PROJECT_NAME = "your_project_name"
```

### Nur bestimmte Kategorien verarbeiten

Kommentiere ungewünschte Kategorien aus:
```python
categories = {
    "migrations": CONTEXT_DIR / "migrations",
    # "integrations": CONTEXT_DIR / "integrations",  # Auskommentiert
    "architecture": CONTEXT_DIR / "architecture",
    # ...
}
```

---

## Technische Details

### Authentifizierung

Das Script versucht mehrere Authentifizierungsmethoden:
1. **POST** zu `/api/login` mit username/password
2. **POST** zu `/cloud/login` mit email/password
3. **HTTP Basic Auth** als Fallback

### API-Endpunkte

- **Login:** `POST /api/login`
- **SQL Query:** `POST /api/sql/query`
- **Create Knowledge Base:** SQL-Befehl via `/api/sql/query`

### MindsDB SQL-Syntax

```sql
-- Projekt erstellen
CREATE DATABASE soleflipper

-- Knowledge Base erstellen
CREATE KNOWLEDGE_BASE soleflipper.kb_migrations
USING
    engine = 'openai',
    model = 'gpt-4',
    content = '# Markdown Content...'
```

---

## Support

Bei Problemen:
1. Prüfe die detaillierte Fehlerausgabe des Scripts
2. Teste manuellen Zugriff im Browser
3. Prüfe Netzwerkverbindung und Firewall
4. Kontaktiere den Synology NAS-Administrator

---

**Erstellt:** 2025-11-05
**Version:** 1.0.0
**Autor:** Claude Code Assistant
