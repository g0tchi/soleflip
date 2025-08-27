# SoleFlipper CLI Tool

Ein umfassendes Command-Line Interface für alle SoleFlipper API-Funktionen.

## Installation

```bash
# CLI-Abhängigkeiten installieren
python setup_cli.py

# Oder manuell
pip install click rich
```

## Verwendung

```bash
# Alle verfügbaren Commands anzeigen
python cli_simple.py --help

# StockX Commands
python cli_simple.py stockx --help

# Database Commands  
python cli_simple.py db --help

# Utils Commands
python cli_simple.py utils --help

# Import Commands
python cli_simple.py import-data --help
```

## Verfügbare Commands

### 🔌 Verbindungstest
```bash
# Teste Datenbank und API Verbindungen
python cli_simple.py utils test-connection
```

### 📈 StockX API Operations

#### Aktive Orders abrufen
```bash
# Alle aktiven Orders
python cli_simple.py stockx active-orders

# Mit Limit
python cli_simple.py stockx active-orders --limit 5
```

#### Historische Orders abrufen  
```bash
# Orders der letzten 30 Tage
python cli_simple.py stockx historical-orders --days 30

# Mit Limit
python cli_simple.py stockx historical-orders --days 7 --limit 10
```

#### Produktsuche
```bash
# Suche nach Produkten
python cli_simple.py stockx search "jordan 1"

# Mit Paginierung
python cli_simple.py stockx search "yeezy" --page 2 --size 5

# Mit Limit
python cli_simple.py stockx search "nike" --limit 3
```

#### Produktdetails
```bash
# Detaillierte Produktinformationen
python cli_simple.py stockx product-details PRODUCT_ID
```

#### Deine Listings
```bash
# Alle deine aktiven Listings
python cli_simple.py stockx listings

# Mit Limit  
python cli_simple.py stockx listings --limit 15
```

### 🗄️ Database Operations

#### Database Status
```bash
# Grundlegende Datenbankinfos
python cli_simple.py db status

# Detaillierte Statistiken
python cli_simple.py db stats
```

#### Import History
```bash
# Letzte Import-Batches anzeigen
python cli_simple.py db recent-imports
```

### 📥 Data Import Operations

#### StockX Import
```bash
# Dry Run - zeigt was importiert werden würde
python cli_simple.py import-data from-stockx --dry-run

# Import der letzten 7 Tage
python cli_simple.py import-data from-stockx --days 7

# Import der letzten 30 Tage
python cli_simple.py import-data from-stockx --days 30 --dry-run
```

### 🔧 Utility Functions

#### Order Details
```bash
# Detaillierte Order-Informationen
python cli_simple.py utils order-details ORDER_NUMBER
```

#### Datenexport
```bash
# Export als JSON
python cli_simple.py utils export-data orders.json --days 30

# Export als CSV
python cli_simple.py utils export-data orders.csv --format csv --days 7
```

## Beispiel-Session

```bash
# 1. Verbindung testen
python cli_simple.py utils test-connection

# 2. Aktive Orders prüfen  
python cli_simple.py stockx active-orders

# 3. Datenbank Status prüfen
python cli_simple.py db status

# 4. Nach Produkten suchen
python cli_simple.py stockx search "jordan 1 chicago"

# 5. Dry-Run Import
python cli_simple.py import-data from-stockx --dry-run

# 6. Daten exportieren
python cli_simple.py utils export-data backup.json --days 30
```

## Output Beispiele

### StockX Active Orders
```
Found 1 active orders:
--------------------------------------------------------------------------------
1. Order: 77051712-76951471
   Product: Nike Air Jordan 1 High OG "Chicago"
   Amount: $21
   Status: AUTHENTICATED
   Date: 2025-08-18
```

### Database Status
```
Database Status:
----------------------------------------
Status: healthy
Database Type: PostgreSQL
Pool Size: 20
Active Connections: 2
```

### Product Search
```
Search results for 'jordan 1' (1247 total):
--------------------------------------------------------------------------------
1. ID: air-jordan-1-retro-high-og-chicago-reimagined
   Title: Jordan 1 Retro High OG Chicago Reimagined
   Brand: Jordan
   Style ID: DZ5485-612

2. ID: air-jordan-1-low-black-white
   Title: Jordan 1 Low Black White  
   Brand: Jordan
   Style ID: 553558-040
```

## Fehlerbehandlung

Das CLI behandelt folgende Fehler graceful:
- Datenbankverbindungsfehler
- StockX API-Limits
- Ungültige Parameter
- Netzwerkprobleme

## Performance

- Alle Commands verwenden Connection Pooling
- Async/Await für optimale Performance
- Automatisches Session Management
- Timeout-Handling für API-Calls

## Erweiterungen

Das CLI kann einfach um weitere Commands erweitert werden:
- Neue API-Endpoints
- Zusätzliche Export-Formate
- Mehr Datenbank-Operationen
- Batch-Processing-Features

## Troubleshooting

### Häufige Probleme

1. **Unicode Encoding Errors**
   - Das CLI wurde für Windows-Kompatibilität optimiert
   - Keine Emoji/Unicode-Zeichen in der Ausgabe

2. **Database Connection Failed**
   - Prüfe .env Datei
   - Stelle sicher dass DATABASE_URL gesetzt ist

3. **StockX API Errors**
   - API-Credentials in der Datenbank prüfen
   - Rate Limits beachten

4. **Import Errors**  
   - Vollständige Import-Funktionalität über FastAPI verwenden
   - CLI bietet Preview/Dry-Run Modus