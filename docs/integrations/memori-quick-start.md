# Memori MCP Quick-Start Guide

Schnelleinstieg zur Nutzung von Memori für persistente Erinnerungen in Claude Code.

## 🚀 Voraussetzungen

- ✅ Memori MCP Server installiert und konfiguriert
- ✅ Claude Code mit aktiviertem Memori-Server (Neustart erforderlich)
- ✅ PostgreSQL-Datenbank läuft

## 📝 Grundlegende Verwendung

### 1. Erinnerungen Speichern

**Einfache Erinnerung:**
```
Speichere: Das Soleflip-Projekt verwendet FastAPI als Backend-Framework
```

**Mit Kontext:**
```
Merke dir: Die Authentifizierung erfolgt über JWT-Tokens mit einer Gültigkeit von 24 Stunden. Die Token-Blacklist wird in Redis gecacht.
```

**Technische Details:**
```
Speichere diese Information: Die Datenbank verwendet Multi-Schema-Architektur mit folgenden Schemas: transactions, inventory, products, analytics
```

### 2. Erinnerungen Suchen

**Einfache Suche:**
```
Suche nach: FastAPI
```

**Spezifische Abfrage:**
```
Was hast du über Authentifizierung gespeichert?
```

**Technische Suche:**
```
Finde alle Informationen über die Datenbank-Architektur
```

### 3. Erinnerungen Auflisten

```
Zeige mir alle gespeicherten Erinnerungen
```

```
Liste die letzten 5 Memories auf
```

## 🎯 Praktische Use Cases

### Use Case 1: Projekt-Architektur dokumentieren

**Szenario**: Du arbeitest an verschiedenen Teilen des Projekts und möchtest wichtige Architektur-Entscheidungen festhalten.

```
💬 Du: Speichere: Das Pricing-Modul verwendet einen Smart-Pricing-Algorithmus basierend auf:
- Aktueller Marktnachfrage
- Historischen Verkaufsdaten
- Lagerbestand und Dead-Stock-Analyse
- Saisonalen Trends

Claude: ✅ Gespeichert! [verwendet mcp__memori__store_memory]
```

**Später in einer neuen Session:**
```
💬 Du: Wie funktioniert unser Pricing-Algorithmus?

Claude: [verwendet mcp__memori__search_memory]
Laut meiner Erinnerung verwendet das Pricing-Modul einen Smart-Pricing-Algorithmus basierend auf...
```

### Use Case 2: API-Endpoints dokumentieren

```
💬 Du: Merke dir diese API-Endpoints:
- POST /api/v1/inventory/items - Neues Inventory-Item erstellen
- GET /api/v1/inventory/items/{id} - Item abrufen
- PATCH /api/v1/inventory/items/{id} - Item aktualisieren
- POST /api/v1/inventory/batch-enrich - Batch-Anreicherung

Claude: ✅ API-Endpoints gespeichert!
```

### Use Case 3: Fehleranalyse und Lösungen

```
💬 Du: Speichere diese Lösung: Bei "asyncpg connection timeout" Fehler:
1. Überprüfe pool_pre_ping=True in der Engine-Konfiguration
2. Erhöhe pool_size auf 15 für NAS-Umgebungen
3. Setze pool_timeout auf 30 Sekunden
4. Verwende async with für Session-Management

Claude: ✅ Troubleshooting-Lösung gespeichert!
```

**Später bei ähnlichem Problem:**
```
💬 Du: Was war nochmal die Lösung für asyncpg connection timeout?

Claude: [sucht in Memories] Hier ist die dokumentierte Lösung...
```

### Use Case 4: Entwicklungsumgebung und Commands

```
💬 Du: Speichere wichtige Development Commands:
- make dev - Entwicklungsserver starten
- make test - Alle Tests ausführen
- make db-migrate - Neue Migration erstellen
- make check - Code-Qualität prüfen
- docker exec soleflip-postgres psql -U soleflip - DB-Zugriff

Claude: ✅ Development Commands gespeichert!
```

### Use Case 5: Abhängigkeiten und Konfiguration

```
💬 Du: Merke dir: Für ML-Features müssen die optionalen Dependencies installiert werden:
pip install -e ".[ml]"
Dies installiert: scikit-learn, statsmodels, scipy für ARIMA-Forecasting

Claude: ✅ Dependency-Information gespeichert!
```

## 🏗️ Best Practices

### 1. **Strukturierte Informationen**

✅ **Gut:**
```
Speichere: Inventory-Item-Status:
- available: Auf Lager und verkaufsbereit
- sold: Verkauft
- reserved: Reserviert für Order
- dead_stock: Überbestand, reduziert
```

❌ **Vermeiden:**
```
Speichere: Status gibt's verschiedene
```

### 2. **Kontext hinzufügen**

✅ **Gut:**
```
Merke dir: Die StockX-Integration verwendet OAuth2-Flow.
Credentials werden verschlüsselt in der DB gespeichert.
Refresh-Token-Handling erfolgt automatisch im StockXService.
Siehe: domains/integration/services/stockx_service.py:45
```

❌ **Vermeiden:**
```
StockX nutzt OAuth2
```

### 3. **Kategorisierung durch Präfixe**

```
# Architektur-Entscheidungen
Speichere [ARCHITEKTUR]: Wir verwenden Repository Pattern für alle Data-Access-Layer

# Troubleshooting
Speichere [BUGFIX]: Memory-Leak in Background-Tasks durch fehlende Session-Cleanup

# Konfiguration
Speichere [CONFIG]: PostgreSQL Connection Pool: size=15, max_overflow=20, pre_ping=True

# API-Dokumentation
Speichere [API]: Batch-Enrichment-Endpoint akzeptiert max. 100 Items pro Request
```

### 4. **Regelmäßige Konsolidierung**

Periodisch alle Memories reviewen:
```
Zeige mir alle gespeicherten Erinnerungen
```

Veraltete oder redundante Informationen bereinigen.

## 🔍 Erweiterte Suchtechniken

### Nach Themenbereich suchen

```
Finde alle Informationen über:
- Datenbank-Migrationen
- API-Endpoints
- Performance-Optimierungen
- Sicherheits-Konfiguration
```

### Kombinierte Suche

```
Suche nach: FastAPI und PostgreSQL
```

```
Was weißt du über Testing und pytest?
```

## 📊 Namespace-Organisation

Memori verwendet Namespaces zur Organisation. Standard: `soleflip`

**Mögliche zukünftige Namespaces:**
- `soleflip_architecture` - Architektur-Entscheidungen
- `soleflip_bugs` - Bekannte Bugs und Fixes
- `soleflip_api` - API-Dokumentation
- `soleflip_devops` - Deployment und Infrastruktur

## 🛠️ Troubleshooting

### Memory wird nicht gefunden

**Problem**: Gespeicherte Information wird nicht gefunden.

**Lösung**:
1. Prüfe Schreibweise der Suchbegriffe
2. Verwende allgemeinere Begriffe
3. Liste alle Memories auf: "Zeige alle Erinnerungen"

### Zu viele oder irrelevante Ergebnisse

**Lösung**: Sei spezifischer in der Suche
```
❌ "Suche nach: API"
✅ "Suche nach: Batch-Enrichment API Endpoint"
```

### Memory nicht verfügbar nach Neustart

**Problem**: Gespeicherte Memories scheinen verschwunden.

**Lösung**:
1. Prüfe, ob Memori-Server läuft (siehe Installation)
2. Stelle sicher, dass Claude Code neu geladen wurde
3. Verifiziere Datenbank-Verbindung:
   ```bash
   cd integrations/memori-mcp
   ./test_mcp.sh
   ```

## 💡 Power-User-Tipps

### 1. Session-Zusammenfassungen

Am Ende einer Entwicklungssession:
```
Speichere eine Zusammenfassung: Heute implementiert:
- Batch-Enrichment-Endpoint für Inventory-Items
- Tests für neue Repository-Methoden
- Migration für zusätzliche Metadata-Felder
Status: Alle Tests bestehen, bereit für Review
```

### 2. Entscheidungs-Logbuch

```
Speichere [ENTSCHEIDUNG] 2025-11-13: Wir verwenden Alembic statt SQLAlchemy-Migrate
weil:
- Bessere async-Support
- Aktivere Community
- Einfachere Syntax für komplexe Migrationen
```

### 3. Code-Snippets und Patterns

```
Speichere [PATTERN]: Repository-Pattern-Template:
```python
class XRepository(BaseRepository[Model]):
    def __init__(self, session: AsyncSession):
        super().__init__(Model, session)

    async def custom_method(self):
        stmt = select(Model).where(...)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```
```

### 4. Wichtige Ressourcen

```
Speichere [DOCS]: Wichtige Dokumentation:
- CLAUDE.md - Entwickler-Guide
- docs/integrations/memori-mcp-setup.md - Memori Setup
- docs/guides/stockx_auth_setup.md - StockX Integration
```

## 🔐 Sicherheitshinweise

### Was NICHT speichern:

❌ Passwörter, API-Keys, Secrets
❌ Personenbezogene Daten (PII)
❌ Produktions-Credentials
❌ Interne vertrauliche Informationen

### Was speichern:

✅ Architektur-Entscheidungen
✅ Code-Patterns und Best Practices
✅ Öffentliche API-Dokumentation
✅ Troubleshooting-Guides
✅ Development-Workflows

## 📈 Nächste Schritte

1. **Jetzt ausprobieren**: Speichere deine erste Erinnerung!
2. **Konventionen etablieren**: Definiere Präfixe für dein Team
3. **Regelmäßig nutzen**: Mache Memory-Speicherung zur Gewohnheit
4. **Feedback geben**: Was fehlt? Was könnte besser sein?

## 🔗 Weiterführende Ressourcen

- [Vollständige Setup-Dokumentation](./memori-mcp-setup.md)
- [Memori GitHub Repository](https://github.com/GibsonAI/memori)
- [MCP Protocol Dokumentation](https://modelcontextprotocol.io)

---

**Viel Erfolg mit Memori! 🎉**

Bei Fragen oder Problemen siehe [Troubleshooting-Guide](./memori-mcp-setup.md#troubleshooting).
