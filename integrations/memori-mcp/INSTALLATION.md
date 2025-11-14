# Memori MCP - Installation für neue Entwickler

Diese Anleitung ist für Entwickler, die das Projekt von GitHub klonen.

## 📦 Nach dem Klonen

### 1. Verzeichnis wechseln

```bash
cd integrations/memori-mcp
```

### 2. Virtuelle Umgebung erstellen

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# oder
.venv\Scripts\activate     # Windows
```

### 3. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 4. Umgebungsvariablen konfigurieren

```bash
# Beispiel-Datei kopieren
cp .env.example .env.local

# Dann .env.local bearbeiten und ausfüllen:
# - MEMORI_DATABASE_URL mit echten Credentials
# - Andere Optionen nach Bedarf anpassen
```

### 5. Datenbank erstellen

```bash
# Stelle sicher, dass PostgreSQL läuft
docker exec soleflip-postgres psql -U soleflip -c "CREATE DATABASE memori;"

# Oder ohne Docker:
psql -U soleflip -c "CREATE DATABASE memori;"
```

Die Tabellen werden automatisch beim ersten Start erstellt.

### 6. Testen

```bash
# Server-Test
./test_mcp.sh

# Funktionale Tests
.venv/bin/python functional_test.py

# MCP-Tools testen
.venv/bin/python test_mcp_tools.py
```

### 7. Claude Code konfigurieren

Die Konfiguration sollte bereits in `.claude/.mcp.json` im Projekt-Root vorhanden sein.

Falls nicht, siehe [Setup-Dokumentation](../../docs/integrations/memori-mcp-setup.md).

## 🔐 Wichtig: Sicherheit

- ❌ **NIEMALS** `.env.local` committen!
- ❌ **NIEMALS** echte Passwörter in Code oder Docs!
- ✅ Nur `.env.example` mit Platzhaltern committen

## 📚 Weiter mit

Nach erfolgreicher Installation:
- [START_HERE.md](./START_HERE.md) - Schnelleinstieg
- [CHEAT_SHEET.md](./CHEAT_SHEET.md) - Befehls-Referenz

## 🛠️ Troubleshooting

### Virtual Environment Probleme

```bash
# Venv löschen und neu erstellen
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Datenbank-Verbindung fehlgeschlagen

```bash
# Verbindung testen
docker exec soleflip-postgres psql -U soleflip -d memori -c "SELECT 1;"

# Oder direkt:
psql postgresql://soleflip:password@localhost:5432/memori -c "SELECT 1;"
```

### MCP-Server startet nicht

```bash
# Logs prüfen
MEMORI_DATABASE_URL="..." .venv/bin/python server.py

# Mit Verbose-Logging
MEMORI_LOGGING_LEVEL=DEBUG MEMORI_VERBOSE=true .venv/bin/python server.py
```

## 🔗 Weitere Hilfe

Siehe [Setup-Dokumentation](../../docs/integrations/memori-mcp-setup.md#troubleshooting)
