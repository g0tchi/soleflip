# Memori MCP Server - Claude Code Integration

Anleitung zur Einrichtung des Memori MCP Servers für Claude Code auf dem VPS.

## ✅ Was ist bereits eingerichtet

1. **HTTP REST API** (`http://localhost:8090`) - läuft in Docker
   - Für n8n Workflows
   - Für direkten API-Zugriff

2. **MCP Server** (lokal) - für Claude Code
   - Läuft außerhalb Docker
   - Kommuniziert via stdio mit Claude Code

## 🔧 Claude Code Konfiguration

### Option 1: Automatische Konfiguration

Füge diese Konfiguration zu deiner Claude Code MCP-Config hinzu:

**Datei**: `claude_code_config.json` (bereits erstellt)

```json
{
  "mcpServers": {
    "memori": {
      "command": "/home/g0tchi/projects/soleflip/integrations/memori-mcp/.venv/bin/python",
      "args": ["/home/g0tchi/projects/soleflip/integrations/memori-mcp/server.py"],
      "env": {
        "MEMORI_DATABASE_URL": "postgresql://soleflip:SoleFlip2025SecureDB!@localhost:5432/memori",
        "MEMORI_NAMESPACE": "soleflip",
        "MEMORI_LOGGING_LEVEL": "INFO"
      }
    }
  }
}
```

### Option 2: Claude Desktop Integration

Wenn du Claude Desktop verwendest, füge dies zu deiner Config hinzu:

**macOS/Linux**: `~/.config/claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "memori-soleflip": {
      "command": "ssh",
      "args": [
        "user@your-vps-ip",
        "cd /home/g0tchi/projects/soleflip/integrations/memori-mcp && source .venv/bin/activate && python server.py"
      ],
      "env": {}
    }
  }
}
```

## 🚀 Verfügbare MCP Tools

Sobald konfiguriert, hast du in Claude Code Zugriff auf:

### 1. `store_memory`
Speichert Informationen für spätere Verwendung.

**Parameter:**
```json
{
  "content": "Text to remember",
  "namespace": "soleflip",  // optional
  "metadata": {"key": "value"}  // optional
}
```

**Beispiel:**
```
Du: Erinnere dich: Wir verwenden FastAPI für die API-Schicht
Claude: [verwendet store_memory Tool]
✓ Memory gespeichert: "Projekt verwendet FastAPI für API-Schicht"
```

### 2. `search_memory`
Sucht nach gespeicherten Informationen.

**Parameter:**
```json
{
  "query": "search term",
  "namespace": "soleflip",  // optional
  "limit": 5  // optional, default: 5
}
```

**Beispiel:**
```
Du: Welches Framework nutzen wir für die API?
Claude: [verwendet search_memory mit query="API Framework"]
Gefunden: "Projekt verwendet FastAPI für API-Schicht"
```

### 3. `list_memories`
Listet die letzten Memories auf.

**Parameter:**
```json
{
  "namespace": "soleflip",  // optional
  "limit": 10  // optional, default: 10
}
```

## 🧪 Testen der MCP Integration

### Manueller Test (ohne Claude Code)

```bash
cd /home/g0tchi/projects/soleflip/integrations/memori-mcp
source .venv/bin/activate
python server.py
```

Der Server startet und wartet auf stdio-Eingaben. Du kannst JSON-RPC Nachrichten senden:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list"}
```

### Test mit Claude Code

Wenn die MCP-Config korrekt ist:

1. **Claude Code starten**
2. **Prüfe verfügbare Tools**: Claude sollte die Memori-Tools automatisch sehen
3. **Teste einen Command**:
   ```
   Speichere folgendes: Die Soleflip API läuft auf Port 8000
   ```

Claude wird automatisch das `store_memory` Tool verwenden.

## 📊 Use Cases

### 1. Projekt-Kontext über Sessions hinweg

**Problem**: Claude vergisst zwischen Sessions alles.

**Lösung**: Wichtige Architektur-Entscheidungen speichern.

```
Du: Merke dir: Wir nutzen PostgreSQL mit asyncpg, FastAPI für REST API,
    und n8n für Workflows

Claude: [speichert in Memory]
✓ Projekt-Kontext gespeichert

--- Nächste Session ---

Du: Welche Technologien nutzen wir?
Claude: [sucht in Memory]
Ihr verwendet PostgreSQL mit asyncpg, FastAPI und n8n.
```

### 2. Code-Patterns und Conventions

```
Du: Speichere: Wir verwenden structured logging mit structlog,
    alle Logs im JSON-Format

Claude: ✓ Gespeichert als Code-Convention
```

### 3. Bug-Tracking und Lösungen

```
Du: Merke dir: Bug bei Docker health check -
    Lösung war urllib.request statt curl zu verwenden

Claude: ✓ Bug-Lösung gespeichert
```

### 4. Deployment-Notizen

```
Du: Speichere: Memori läuft auf Port 8090, n8n kann via
    http://memori-api:8080 intern zugreifen

Claude: ✓ Deployment-Info gespeichert
```

## 🔍 Troubleshooting

### MCP Server startet nicht

```bash
# Check Python version (needs 3.11+)
python3 --version

# Reinstall dependencies
cd /home/g0tchi/projects/soleflip/integrations/memori-mcp
rm -rf .venv
./setup_local_mcp.sh

# Test database connection
source .venv/bin/activate
python -c "import asyncpg; print('asyncpg OK')"
```

### Database Connection Error

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Test connection
psql -h localhost -U soleflip -d memori -c "SELECT 1"

# Check password in .env.local
cat .env.local | grep MEMORI_DATABASE_URL
```

### Claude Code doesn't see tools

1. **Restart Claude Code** after adding MCP config
2. **Check config path** is correct
3. **Check Python path** in config matches actual venv location
4. **Check logs** in Claude Code for MCP errors

## 🔄 Dual Setup Übersicht

```
┌─────────────────────────────────────────────────────────────┐
│                     Memori Integration                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐              ┌──────────────────┐    │
│  │   n8n Workflows  │──HTTP REST──▶│  Docker          │    │
│  │   (Port 5678)    │              │  Memori API      │    │
│  └──────────────────┘              │  (Port 8090)     │    │
│                                     └────────┬─────────┘    │
│                                              │              │
│  ┌──────────────────┐              ┌────────▼─────────┐    │
│  │  Claude Code     │──stdio MCP──▶│  Local MCP       │    │
│  │  (on desktop)    │              │  Server (.venv)  │    │
│  └──────────────────┘              └────────┬─────────┘    │
│                                              │              │
│                     ┌────────────────────────▼──────┐       │
│                     │   PostgreSQL Database         │       │
│                     │   (memori table)              │       │
│                     └───────────────────────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Beide** greifen auf die **gleiche PostgreSQL Datenbank** zu!

## 📝 Nächste Schritte

1. ✅ HTTP API läuft in Docker (Port 8090)
2. ✅ MCP Server eingerichtet (lokal)
3. ✅ Claude Code Config erstellt
4. 🔲 Claude Code MCP Config hinzufügen
5. 🔲 Ersten Memory-Test durchführen

## 📚 Weitere Dokumentation

- **HTTP API**: `docs/integrations/memori-mcp-setup.md`
- **Portainer Deployment**: `docs/integrations/portainer-memori-deployment.md`
- **n8n Integration**: Siehe HTTP API Dokumentation

## 🆘 Support

Bei Problemen:
1. Logs checken: `docker compose logs memori-mcp`
2. MCP Server manuell testen (siehe oben)
3. Claude Code Logs prüfen
4. PostgreSQL Connection testen
