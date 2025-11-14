# Memori MCP - Verwendungsanleitung

Persistente Erinnerungen für Claude Code im Soleflip-Projekt.

## 🎯 Was ist Memori?

Memori ermöglicht es Claude Code, Informationen über Sessions hinweg zu speichern und abzurufen. Perfekt für:

- 📝 Projekt-Dokumentation on-the-fly
- 🏗️ Architektur-Entscheidungen festhalten
- 🐛 Troubleshooting-Lösungen dokumentieren
- 🔧 Development-Workflows merken
- 💡 Best Practices teilen

## ⚡ Schnellstart

### 1. Erste Erinnerung speichern

```
💬 Du: Speichere: Das Soleflip-Projekt verwendet FastAPI und PostgreSQL
```

### 2. Erinnerung abrufen

```
💬 Du: Was weißt du über das Soleflip-Projekt?

🤖 Claude: Das Soleflip-Projekt verwendet FastAPI und PostgreSQL...
```

### 3. Alle Erinnerungen anzeigen

```
💬 Du: Zeige alle gespeicherten Erinnerungen
```

## 🚀 Installation & Setup

### Status prüfen

```bash
# MCP-Server testen
./test_mcp.sh

# Funktionale Tests
.venv/bin/python functional_test.py

# MCP-Tools testen
.venv/bin/python test_mcp_tools.py
```

### Konfiguration

Die Konfiguration erfolgt automatisch über `.claude/.mcp.json`:

```json
{
  "mcpServers": {
    "memori": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/server.py"],
      "env": {
        "MEMORI_DATABASE_URL": "postgresql://...",
        "MEMORI_NAMESPACE": "soleflip",
        "MEMORI_LOGGING_LEVEL": "INFO"
      }
    }
  }
}
```

**Wichtig**: Nach Änderungen an der Konfiguration muss Claude Code neu gestartet werden!

## 📚 Dokumentation

| Dokument | Beschreibung |
|----------|--------------|
| [CHEAT_SHEET.md](./CHEAT_SHEET.md) | Schnellreferenz - Die wichtigsten Befehle |
| [Quick-Start Guide](../../docs/integrations/memori-quick-start.md) | Ausführliche Anleitung mit Beispielen |
| [Setup-Dokumentation](../../docs/integrations/memori-mcp-setup.md) | Vollständige Installation und Konfiguration |

### Empfohlene Lesereihenfolge

1. **Neu hier?** → Start mit [CHEAT_SHEET.md](./CHEAT_SHEET.md)
2. **Erste Schritte** → [Quick-Start Guide](../../docs/integrations/memori-quick-start.md)
3. **Installation/Probleme** → [Setup-Dokumentation](../../docs/integrations/memori-mcp-setup.md)

## 🎓 Häufige Use Cases

### Projekt-Architektur dokumentieren

```
Speichere [ARCHITEKTUR]: Soleflip verwendet Domain-Driven Design:
- domains/ → Business logic by domain
- shared/ → Cross-cutting concerns
- migrations/ → Database migrations
```

### API-Endpoints merken

```
Speichere [API]: Batch Enrichment:
POST /api/v1/inventory/batch-enrich
- Max 100 items per request
- Returns enriched items with product details
```

### Fehler und Lösungen

```
Speichere [BUGFIX]: asyncpg connection timeout:
- Setze pool_pre_ping=True
- Erhöhe pool_size auf 15
- Verwende 'async with' für Sessions
```

### Development Commands

```
Speichere [CMD]: Wichtige Commands:
- make dev → Start server
- make test → Run tests
- make check → Quality checks
- make db-migrate → New migration
```

## 🔍 Verfügbare MCP-Tools

Nach Claude Code Neustart stehen folgende Tools zur Verfügung:

| Tool | Beschreibung | Verwendung |
|------|--------------|------------|
| `store_memory` | Erinnerung speichern | "Speichere: ..." |
| `search_memory` | Nach Erinnerungen suchen | "Suche nach: ..." |
| `list_memories` | Alle Erinnerungen auflisten | "Zeige alle Erinnerungen" |

## 🏷️ Best Practices

### 1. Nutze Präfixe für Struktur

```
[ARCHITEKTUR] - Architektur-Entscheidungen
[API] - API-Dokumentation
[BUGFIX] - Fehlerbehebungen
[CONFIG] - Konfiguration
[CMD] - Commands
```

### 2. Sei spezifisch

✅ **Gut**: "Batch-Enrichment-Endpoint akzeptiert max. 100 Items"
❌ **Schlecht**: "API hat Limits"

### 3. Füge Kontext hinzu

✅ **Gut**: "Repository Pattern in domains/inventory/repositories/inventory_repository.py:15"
❌ **Schlecht**: "Wir nutzen Repository Pattern"

### 4. Session-Zusammenfassungen

Am Ende einer Session:
```
Speichere [SESSION] 2025-11-13: Implementiert:
- Batch-Enrichment-Endpoint
- Tests für neue Features
- Migration für metadata-Felder
Status: Alle Tests bestehen ✅
```

## 🛠️ Troubleshooting

### Memory nicht gefunden

```
💬 Du: Zeige alle Erinnerungen
```
→ Prüfe, ob Memory tatsächlich gespeichert wurde

### Tools nicht verfügbar

1. Prüfe ob Memori in `.claude/settings.local.json` aktiviert ist
2. **Starte Claude Code neu**
3. Verifiziere Server: `./test_mcp.sh`

### Verbindungsfehler

```bash
# Datenbank prüfen
docker exec soleflip-postgres psql -U soleflip -d memori -c "SELECT COUNT(*) FROM memories;"

# Server-Logs (falls Docker)
docker logs soleflip-memori-mcp

# Verbindung testen
.venv/bin/python functional_test.py
```

## 📊 Status & Statistiken

### Aktuelle Memories anzeigen

```bash
docker exec soleflip-postgres psql -U soleflip -d memori -c "
SELECT
    namespace,
    COUNT(*) as total,
    MAX(created_at) as latest
FROM memories
GROUP BY namespace;
"
```

### Backup erstellen

```bash
docker exec soleflip-postgres pg_dump -U soleflip memori > memori_backup_$(date +%Y%m%d).sql
```

## 🔐 Sicherheit

### ❌ NICHT speichern:
- Passwörter
- API-Keys
- Produktions-Credentials
- Personenbezogene Daten (PII)

### ✅ Speichern:
- Architektur-Patterns
- API-Dokumentation
- Public Code-Snippets
- Troubleshooting-Guides

## 🎯 Nächste Schritte

1. **[Cheat Sheet lesen](./CHEAT_SHEET.md)** - Die wichtigsten Befehle
2. **Erste Memory speichern** - "Speichere: Test Memory"
3. **[Quick-Start Guide](../../docs/integrations/memori-quick-start.md)** - Detaillierte Beispiele
4. **Regelmäßig nutzen** - Mache Memory-Speicherung zur Gewohnheit!

## 🔗 Links

- [Memori GitHub](https://github.com/GibsonAI/memori)
- [MCP Protocol](https://modelcontextprotocol.io)
- [Soleflip Developer Guide](../../CLAUDE.md)

---

**Viel Erfolg! 🚀**

Bei Fragen oder Problemen siehe [Setup-Dokumentation](../../docs/integrations/memori-mcp-setup.md#troubleshooting).
