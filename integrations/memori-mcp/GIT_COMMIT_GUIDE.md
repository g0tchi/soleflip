# Git Commit Guide für Memori MCP

## 📦 Was wird zu Git hinzugefügt?

### ✅ Source Code & Konfiguration
```
integrations/memori-mcp/
├── server.py              ← MCP-Server Implementierung
├── http_server.py         ← HTTP-Server (optional)
├── config.py              ← Konfigurationsschema
├── requirements.txt       ← Python Dependencies
├── Dockerfile             ← Docker-Konfiguration
```

### ✅ Scripts & Tools
```
├── setup_local_mcp.sh     ← Lokales Setup-Script
├── test_mcp.sh           ← MCP-Server Test-Script
├── functional_test.py     ← Funktionale Tests
├── test_mcp_tools.py      ← MCP-Tools Tests
├── test_memory_operations.py ← Memory Operations Tests
```

### ✅ Dokumentation
```
├── START_HERE.md          ← Einstiegspunkt
├── CHEAT_SHEET.md         ← Schnellreferenz
├── README_USAGE.md        ← Verwendungsanleitung
├── README_MCP.md          ← MCP-Dokumentation
├── README.md              ← Original README
├── INSTALLATION.md        ← Installation für neue Devs
├── GIT_COMMIT_GUIDE.md    ← Dieser Guide
```

### ✅ Git-Konfiguration
```
├── .gitignore             ← Ignoriert .venv, .env.local, etc.
├── .env.example           ← Beispiel-Konfiguration (OHNE Secrets!)
├── .portainerignore       ← Portainer-Ignore
```

### ❌ Wird NICHT committed (durch .gitignore)
```
├── .venv/                 ← Virtual Environment (lokal)
├── .env.local            ← Lokale Konfiguration mit SECRETS!
├── __pycache__/          ← Python Cache
├── *.pyc                 ← Compiled Python
├── *.log                 ← Log-Dateien
```

## 🚀 Wie committed man das Modul?

### Option 1: Alles auf einmal (empfohlen)

```bash
cd /home/g0tchi/projects/soleflip

# 1. .gitignore und .env.example sind bereits gestaged
# 2. Rest hinzufügen (außer ignored files)
git add integrations/memori-mcp/

# 3. Status prüfen (sollte .venv und .env.local NICHT zeigen!)
git status

# 4. Commit erstellen
git commit -m "feat: Add Memori MCP Server integration

- MCP Server implementation with store/search/list tools
- PostgreSQL-based persistent memory storage
- Comprehensive documentation and quick-start guides
- Test scripts for validation
- Docker support

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# 5. Zu GitHub pushen
git push origin master
```

### Option 2: Schrittweise (kontrollierter)

```bash
cd /home/g0tchi/projects/soleflip

# 1. Erst die Kern-Dateien
git add integrations/memori-mcp/server.py
git add integrations/memori-mcp/config.py
git add integrations/memori-mcp/requirements.txt

# 2. Tests
git add integrations/memori-mcp/*test*.py
git add integrations/memori-mcp/test_mcp.sh

# 3. Dokumentation
git add integrations/memori-mcp/*.md

# 4. Git-Konfiguration
git add integrations/memori-mcp/.gitignore
git add integrations/memori-mcp/.env.example

# 5. Rest (Docker, Scripts)
git add integrations/memori-mcp/Dockerfile
git add integrations/memori-mcp/setup_local_mcp.sh

# 6. Status prüfen
git status

# 7. Commit
git commit -m "feat: Add Memori MCP Server integration"

# 8. Push
git push origin master
```

## ⚠️ WICHTIG: Vor dem Commit prüfen!

```bash
# 1. Stelle sicher, dass .venv NICHT dabei ist!
git status | grep -E "(\.venv|__pycache__)"
# ← Sollte NICHTS ausgeben!

# 2. Stelle sicher, dass .env.local NICHT dabei ist!
git status | grep "\.env\.local"
# ← Sollte NICHTS ausgeben!

# 3. Prüfe, welche Dateien staged sind
git status --short

# 4. Zeige alle Änderungen an
git diff --cached
```

## 🔐 Sicherheits-Checkliste

Vor dem Push zu GitHub:

- [ ] `.venv/` wird NICHT committed (durch .gitignore)
- [ ] `.env.local` wird NICHT committed (durch .gitignore)
- [ ] `.env.example` enthält KEINE echten Passwörter
- [ ] Keine Secrets in Code oder Dokumentation
- [ ] `.gitignore` ist vorhanden und korrekt

## 📊 Nach dem Push

### 1. Verifizieren auf GitHub

Gehe zu: `https://github.com/[your-username]/soleflip/tree/master/integrations/memori-mcp`

Sollte zeigen:
- ✅ Alle `.py` Dateien
- ✅ Alle `.md` Dateien
- ✅ `requirements.txt`, `Dockerfile`
- ✅ `.gitignore`, `.env.example`
- ❌ NICHT: `.venv/`, `.env.local`

### 2. Für andere Entwickler

Andere können jetzt das Repo klonen und einrichten:

```bash
git clone https://github.com/[username]/soleflip.git
cd soleflip/integrations/memori-mcp

# Siehe INSTALLATION.md für Setup-Anleitung
```

## 📝 Commit-Message-Vorschläge

### Variante 1: Kurz
```
feat: Add Memori MCP Server integration

🤖 Generated with Claude Code
```

### Variante 2: Detailliert (empfohlen)
```
feat: Add Memori MCP Server integration

Features:
- MCP Server with store/search/list memory tools
- PostgreSQL-based persistent storage
- Namespace isolation (default: soleflip)
- Comprehensive test suite
- Full documentation suite

Technical:
- Python 3.11+ with asyncpg
- FastAPI HTTP server (optional)
- Docker support
- Claude Code integration ready

Documentation:
- Quick-start guide with examples
- Cheat sheet for common commands
- Installation guide for new developers
- Troubleshooting guide

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

### Variante 3: Conventional Commits
```
feat(integration): add Memori MCP server for persistent memory

- Implement MCP protocol server with stdio transport
- Add PostgreSQL storage with memories table
- Provide store_memory, search_memory, list_memories tools
- Include comprehensive documentation and tests
- Add Docker configuration for deployment

BREAKING CHANGE: None

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

## 🔄 Updates committen

Bei zukünftigen Änderungen:

```bash
# Änderungen hinzufügen
git add integrations/memori-mcp/

# Commit mit aussagekräftiger Message
git commit -m "docs: Update Memori MCP documentation"
# oder
git commit -m "fix: Resolve database connection timeout"
# oder
git commit -m "feat: Add delete_memory tool"

# Push
git push origin master
```

## 🎯 Best Practices

1. **Kleine, atomare Commits**: Jede logische Änderung ein Commit
2. **Aussagekräftige Messages**: Beschreibe WAS und WARUM
3. **Test vor Commit**: Stelle sicher, dass Tests laufen
4. **Keine Secrets**: Doppelt prüfen vor jedem Push
5. **Documentation aktuell halten**: Docs bei Code-Änderungen updaten

---

**Bereit zum Committen? Folge der Option 1 oben! 🚀**
