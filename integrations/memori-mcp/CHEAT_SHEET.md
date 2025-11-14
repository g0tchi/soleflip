# Memori MCP Cheat Sheet

Schnellreferenz für die Verwendung von Memori in Claude Code.

## 🎯 Grundbefehle

| Aktion | Beispiel |
|--------|----------|
| **Speichern** | `Speichere: [Information]` |
| **Suchen** | `Suche nach: [Begriff]` |
| **Auflisten** | `Zeige alle Erinnerungen` |
| **Kontext** | `Was weißt du über [Thema]?` |

## 💬 Beispiel-Prompts

### Speichern

```
✅ "Speichere: Das API-Rate-Limit beträgt 100 Requests pro Minute"
✅ "Merke dir: Tests werden mit pytest ausgeführt"
✅ "Dokumentiere: Die Datenbank verwendet Connection Pooling mit size=15"
```

### Suchen

```
✅ "Suche nach: Rate Limit"
✅ "Was weißt du über pytest?"
✅ "Finde Informationen zur Datenbank-Konfiguration"
```

### Auflisten

```
✅ "Zeige alle gespeicherten Erinnerungen"
✅ "Liste die letzten 5 Memories auf"
✅ "Was hast du bisher gespeichert?"
```

## 🏷️ Empfohlene Präfixe

Strukturiere deine Memories mit Präfixen:

```
[ARCHITEKTUR] - Architektur-Entscheidungen
[API] - API-Endpoints und Verhalten
[BUGFIX] - Bekannte Bugs und Lösungen
[CONFIG] - Konfigurations-Details
[PATTERN] - Code-Patterns und Templates
[DOCS] - Wichtige Dokumentations-Links
[CMD] - Häufig verwendete Commands
[ENTSCHEIDUNG] - Team-Entscheidungen mit Datum
```

### Beispiele

```
Speichere [ARCHITEKTUR]: Repository Pattern für alle Data Access Layer
Speichere [API]: POST /api/v1/inventory/batch-enrich akzeptiert max 100 Items
Speichere [BUGFIX]: Connection timeout → Erhöhe pool_pre_ping auf True
Speichere [CONFIG]: Redis Cache TTL für Pricing: 300 Sekunden
Speichere [CMD]: make dev - Startet Entwicklungsserver mit Hot-Reload
```

## 📋 Soleflip-Spezifische Memories

### Projekt-Struktur

```
Speichere [ARCHITEKTUR]: Domain-Driven Design mit folgenden Domains:
- integration: StockX API, CSV imports
- inventory: Product inventory, dead stock analysis
- pricing: Smart pricing, auto-listing
- products: Product catalog, brand intelligence
- analytics: Forecasting, KPI calculations
- orders: Multi-platform order management
```

### Development Commands

```
Speichere [CMD]: Soleflip Development Workflow:
1. make dev - Start dev server
2. make test - Run all tests
3. make format - Auto-format code
4. make check - Lint + type-check + test
5. make db-migrate - Create migration
```

### API-Struktur

```
Speichere [API]: Soleflip API-Basis:
- Base URL: http://localhost:8000
- Docs: /docs (Swagger)
- Health: /health
- Admin routes: /api/admin/* (security-restricted)
```

### Database

```
Speichere [CONFIG]: PostgreSQL Multi-Schema:
- schemas: transactions, inventory, products, analytics
- Connection: pool_size=15, max_overflow=20, pool_pre_ping=True
- Migrations: Alembic (auto-apply on startup)
```

### Testing

```
Speichere [CMD]: Testing mit pytest:
- pytest -m unit → Unit tests
- pytest -m integration → Integration tests
- pytest -m api → API tests
- pytest --cov → Coverage report
```

## 🚫 Was NICHT speichern

```
❌ Passwörter oder API-Keys
❌ Produktions-Credentials
❌ Personenbezogene Daten
❌ Interne vertrauliche Infos
```

## ✅ Was speichern

```
✅ Architektur-Patterns
✅ API-Dokumentation
✅ Troubleshooting-Guides
✅ Development-Workflows
✅ Code-Conventions
✅ Deployment-Prozesse
```

## 🔧 Troubleshooting

| Problem | Lösung |
|---------|--------|
| Memory nicht gefunden | Liste alle auf: "Zeige alle Erinnerungen" |
| Zu viele Ergebnisse | Spezifischere Suchbegriffe verwenden |
| Tools nicht verfügbar | Claude Code neu starten |
| Verbindungsfehler | `cd integrations/memori-mcp && ./test_mcp.sh` |

## 📊 Status prüfen

```bash
# MCP-Server testen
cd integrations/memori-mcp
./test_mcp.sh

# Datenbank prüfen
docker exec soleflip-postgres psql -U soleflip -d memori -c "SELECT COUNT(*) FROM memories;"

# Logs anzeigen
docker logs soleflip-memori-mcp  # Falls Docker-Setup
```

## 🎓 Pro-Tipps

1. **Session-Ende-Zusammenfassung**: Speichere am Ende jeder Session eine Zusammenfassung
2. **Entscheidungs-Log**: Dokumentiere wichtige Entscheidungen mit Datum und Begründung
3. **Fehlerlog**: Halte Lösungen für aufgetretene Fehler fest
4. **Konsistente Präfixe**: Nutze immer die gleichen Präfixe für bessere Auffindbarkeit
5. **Regelmäßiges Review**: Prüfe monatlich gespeicherte Memories auf Aktualität

## 📚 Weitere Dokumentation

- [Quick-Start Guide](../../docs/integrations/memori-quick-start.md)
- [Vollständige Setup-Dokumentation](../../docs/integrations/memori-mcp-setup.md)
- [Soleflip Developer Guide](../../CLAUDE.md)

---

**Quick Access**: Halte dieses Cheat-Sheet für schnelle Referenz bereit!
