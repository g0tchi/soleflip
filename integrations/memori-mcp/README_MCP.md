# Memori MCP Server Setup

## Quick Start für Claude Code

### 1. Setup (bereits erledigt ✅)

```bash
cd /home/g0tchi/projects/soleflip/integrations/memori-mcp
./setup_local_mcp.sh
```

### 2. Claude Code Konfiguration

Füge die Konfiguration aus `claude_code_config.json` zu deiner Claude Code MCP-Config hinzu.

**Wichtig**: Der MCP Server muss **lokal laufen** (nicht in Docker), da er stdio-Kommunikation benötigt.

### 3. Verfügbare Tools

- `store_memory` - Informationen speichern
- `search_memory` - Gespeicherte Informationen suchen
- `list_memories` - Letzte Memories auflisten

### 4. Beispiel

```
Du: Merke dir: Wir nutzen PostgreSQL mit asyncpg für die Datenbank
Claude: [nutzt store_memory Tool]
✓ Memory gespeichert
```

## Dual Setup

**Für n8n**: HTTP API in Docker → `http://localhost:8090`
**Für Claude Code**: MCP Server lokal → stdio

**Beide** nutzen die gleiche PostgreSQL `memori` Datenbank!

## Dokumentation

Siehe: `docs/integrations/memori-claude-code-setup.md`
