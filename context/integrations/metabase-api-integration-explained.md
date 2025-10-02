# Metabase API Integration - Wie funktioniert das?

**Version:** v2.2.3
**Created:** 2025-10-01

---

## 🤔 Grundlegendes Konzept

### Die zwei getrennten Systeme

```
┌─────────────────────┐           ┌─────────────────────┐
│  SOLEFLIP API       │           │     METABASE        │
│  (FastAPI)          │           │  (BI Dashboard)     │
│  Port 8000          │           │  Port 6400          │
└─────────────────────┘           └─────────────────────┘
         │                                   │
         │                                   │
         └───────────┬───────────────────────┘
                     │
              ┌──────▼──────┐
              │  PostgreSQL │
              │  Database   │
              └─────────────┘
```

**Wichtig:** Die SoleFlipper API und Metabase sind zwei **unabhängige** Systeme, die beide auf dieselbe PostgreSQL-Datenbank zugreifen!

---

## 📋 Wie funktioniert die Integration?

### 1. Die SoleFlipper API erstellt Materialized Views

**Was macht die API?**

Die SoleFlipper API hat einen speziellen Endpunkt, der **Materialized Views** in der PostgreSQL-Datenbank erstellt:

```bash
# Du rufst die API auf:
curl -X POST "http://localhost:8000/api/v1/metabase/views/create"

# Die API führt dann aus:
CREATE MATERIALIZED VIEW analytics.metabase_executive_metrics AS
SELECT
    DATE_TRUNC('day', o.sold_at) AS sale_date,
    p.name AS platform_name,
    SUM(o.gross_sale) AS total_revenue,
    ...
FROM transactions.orders o
JOIN core.platforms p ON o.platform_id = p.id
GROUP BY ...;
```

**Ergebnis:** In der Datenbank gibt es jetzt eine **fertige Tabelle** mit vorberechneten Daten im Schema `analytics`.

---

### 2. Metabase liest direkt aus der Datenbank

**Metabase kennt die SoleFlipper API nicht!**

Metabase verbindet sich **direkt** mit PostgreSQL und liest die Materialized Views:

```
User öffnet Dashboard in Metabase
         │
         ├──> Metabase sendet SQL Query
         │    SELECT * FROM analytics.metabase_executive_metrics
         │    WHERE sale_date > '2025-01-01'
         │
         ├──> PostgreSQL liefert Daten zurück
         │
         └──> Metabase zeigt Chart/Tabelle an
```

**Metabase braucht KEINE API** - es liest die Daten wie ein normaler SQL Client!

---

## 🔄 Wann brauchst du die API?

Die SoleFlipper API wird **nur** für das **Management** der Views verwendet:

### API Use Cases

| Aufgabe | Warum API? | Wann? |
|---------|------------|-------|
| Views erstellen | Komplexe SQL-Logik zentral verwaltet | Einmalig beim Setup |
| Views aktualisieren | Neue Daten in Views laden | Täglich/Stündlich automatisch |
| View Status prüfen | Monitoring & Troubleshooting | Bei Problemen |
| Dashboard Templates | Vorkonfigurierte Layouts | Optional für Export |

---

## 🎯 Praktisches Beispiel: Workflow von Anfang bis Ende

### Schritt 1: Setup (einmalig)

```bash
# 1. Views mit der API erstellen
curl -X POST "http://localhost:8000/api/v1/metabase/views/create"

# Was passiert:
# - API erstellt 7 Materialized Views in PostgreSQL
# - Views haben Namen wie: analytics.metabase_executive_metrics
# - Views enthalten vorberechnete Aggregationen
```

---

### Schritt 2: Metabase Verbindung (einmalig)

```
1. Öffne Metabase: http://localhost:6400
2. Gehe zu: Settings → Admin → Databases → Add Database
3. Konfiguriere:
   - Name: SoleFlipper
   - Type: PostgreSQL
   - Host: localhost (oder postgres bei Docker)
   - Port: 5432
   - Database: soleflip
   - Username: dein_user
   - Password: dein_passwort

4. Klicke "Save"
5. Metabase scannt automatisch alle Tabellen/Views
```

**Wichtig:** Ab hier spricht Metabase **direkt** mit PostgreSQL, NICHT mit der API!

---

### Schritt 3: Dashboard in Metabase erstellen

**Option A: Manuelle Erstellung**

```
1. In Metabase: New → Dashboard
2. Add Question
3. Data: SoleFlipper Database → analytics → metabase_executive_metrics
4. Wähle Felder aus: sale_month, total_revenue
5. Visualisierung: Line Chart
6. Save
```

**Option B: Template von API holen (optional)**

```bash
# API liefert vorkonfiguriertes Dashboard-Layout
curl "http://localhost:8000/api/v1/metabase/dashboards/executive" > template.json

# Du kannst das Template als Vorlage nutzen
# (Metabase Import-Feature für JSON)
```

---

### Schritt 4: Daten aktualisieren

**Problem:** Du hast neue Orders in der Datenbank, aber die Materialized Views zeigen alte Daten!

**Lösung A: API für Refresh nutzen**

```bash
# Alle Views aktualisieren
curl -X POST "http://localhost:8000/api/v1/metabase/sync/all"

# Was passiert:
# - API führt aus: REFRESH MATERIALIZED VIEW analytics.metabase_executive_metrics
# - Dauert ca. 75-90 Sekunden für alle 7 Views
# - Danach zeigt Metabase automatisch neue Daten
```

**Lösung B: Automatische Aktualisierung (pg_cron)**

```bash
# Einmalig: Automatische Refresh-Jobs einrichten
curl -X POST "http://localhost:8000/api/v1/metabase/setup/refresh-schedule"

# Was passiert:
# - API erstellt pg_cron Jobs in PostgreSQL
# - Hourly Views werden jede Stunde um :00 aktualisiert
# - Daily Views werden täglich um 2 Uhr nachts aktualisiert
# - Weekly Views werden montags um 3 Uhr aktualisiert
```

**Lösung C: Event-driven Refresh**

```python
# In deinem Order-Service Code
from domains.integration.metabase.services import MetabaseSyncService

async def create_order(order_data):
    # Order erstellen
    order = await order_repository.create(order_data)

    # Betroffene Views automatisch aktualisieren
    sync_service = MetabaseSyncService()
    await sync_service.sync_on_order_event()

    return order
```

---

## 🔍 Detaillierter Datenfluss

### Beispiel: Revenue Chart in Metabase Dashboard

```
1. USER ACTION
   └─> User öffnet "Executive Dashboard" in Metabase

2. METABASE QUERY
   └─> Metabase generiert SQL:
       SELECT
           sale_month,
           SUM(total_revenue) AS revenue
       FROM analytics.metabase_executive_metrics
       WHERE sale_month >= '2025-01-01'
       GROUP BY sale_month
       ORDER BY sale_month

3. POSTGRESQL AUSFÜHRUNG
   └─> PostgreSQL führt Query aus
       ├─> Liest aus Materialized View (NICHT aus transactions.orders!)
       ├─> View ist bereits aggregiert → SCHNELL (<100ms)
       └─> Nutzt Index auf sale_month

4. DATENRÜCKGABE
   └─> PostgreSQL liefert Ergebnis:
       2025-01-01 | 15420.50
       2025-02-01 | 18230.75
       2025-03-01 | 22150.00

5. METABASE VISUALISIERUNG
   └─> Metabase rendert Line Chart mit den Daten
```

**Die API ist NICHT beteiligt** in diesem Prozess!

---

## 🤷 Warum dann überhaupt eine API?

### Vorteile der API-basierten View-Verwaltung

**1. Zentrale Verwaltung komplexer SQL-Logik**

```python
# OHNE API: Du müsstest SQL-Statements manuell in PostgreSQL ausführen
# Problem: 520 Zeilen komplexes SQL verteilt auf 7 Views
# Fehleranfällig, schwer wartbar

# MIT API: Alles zentral in Python definiert
view_config = MetabaseViewConfig.EXECUTIVE_METRICS
# SQL ist versioniert, dokumentiert, testbar
```

**2. Versionskontrolle & Deployment**

```bash
# Views sind Teil des Git-Repos
git commit -m "feat: add customer_geography view"

# Bei Deployment automatisch ausgeführt
python domains/integration/metabase/setup_metabase.py
```

**3. Monitoring & Status-Checks**

```bash
# Schnell prüfen, ob alle Views existieren und aktuell sind
curl "http://localhost:8000/api/v1/metabase/views/status" | jq

# Output:
{
  "total_views": 7,
  "existing_views": 7,
  "total_rows": 5428,
  "views": [
    {
      "name": "metabase_executive_metrics",
      "exists": true,
      "rows": 2145,
      "indexes": 3
    },
    ...
  ]
}
```

**4. Event-driven Updates**

```python
# Automatisch relevante Views aktualisieren wenn Daten sich ändern

# Neuer Order → refresh executive_metrics, platform_performance
await sync_service.sync_on_order_event()

# Neues Inventory → refresh inventory_status, product_performance
await sync_service.sync_on_inventory_event()
```

**5. Dashboard Templates & Best Practices**

```bash
# API liefert erprobte Dashboard-Layouts
curl "http://localhost:8000/api/v1/metabase/dashboards/executive"

# Output: Vollständige Dashboard-Konfiguration mit:
# - Optimaler Card-Anordnung
# - Richtigen Parametern
# - Best-Practice Visualisierungen
```

---

## 📊 Vergleich: MIT vs OHNE API

### Szenario: Neue Metabase-Installation

**OHNE API (Manueller Ansatz):**

```sql
-- 1. Manuell in psql/pgAdmin einloggen
psql -U postgres -d soleflip

-- 2. View-SQL manuell eingeben (520 Zeilen!)
CREATE MATERIALIZED VIEW analytics.metabase_executive_metrics AS
SELECT ... (100 Zeilen SQL)
...

-- 3. Indexes manuell erstellen
CREATE INDEX idx_exec_metrics_date ON ...;
CREATE INDEX idx_exec_metrics_month ON ...;
CREATE INDEX idx_exec_metrics_platform ON ...;

-- 4. Wiederholen für 6 weitere Views (jeweils 60-80 Zeilen SQL)
-- 5. Bei Fehlern: Alles manuell debuggen

-- 6. Refresh manuell ausführen
REFRESH MATERIALIZED VIEW analytics.metabase_executive_metrics;
-- (7x wiederholen für alle Views)

-- 7. Cron Jobs manuell einrichten
SELECT cron.schedule('refresh_exec_metrics', '0 * * * *', ...);
-- (7x wiederholen)
```

**Zeitaufwand:** 2-3 Stunden, fehleranfällig

---

**MIT API (Automatisierter Ansatz):**

```bash
# 1. Ein Befehl
python domains/integration/metabase/setup_metabase.py

# Fertig! (10-15 Sekunden)
# - Alle 7 Views erstellt
# - Alle Indexes angelegt
# - Status validiert
# - Dashboard Templates generiert
```

**Zeitaufwand:** 15 Sekunden, fehlerfrei

---

## 🔄 Typische Workflows

### Workflow 1: Initiales Setup (einmalig)

```bash
# 1. SoleFlipper API starten
uvicorn main:app --reload

# 2. Metabase Views erstellen via API
python domains/integration/metabase/setup_metabase.py

# 3. Metabase starten (falls noch nicht läuft)
docker-compose up metabase -d

# 4. Metabase mit PostgreSQL verbinden (UI)
# Settings → Admin → Add Database → PostgreSQL

# 5. In Metabase: Browse → SoleFlipper → analytics
# Hier siehst du alle 7 Views als Tabellen

# 6. Dashboards in Metabase erstellen
# New Dashboard → Add Questions → Wähle Views aus
```

---

### Workflow 2: Täglicher Betrieb (automatisch)

```bash
# Option A: Automatische Aktualisierung via pg_cron (empfohlen)
# Einmalig eingerichtet, läuft dann automatisch:
# - Hourly views: Jede Stunde
# - Daily views: Täglich 2 AM
# - Weekly views: Montags 3 AM

# Option B: Manuelle Aktualisierung bei Bedarf
curl -X POST "http://localhost:8000/api/v1/metabase/sync/all"

# Option C: Event-driven (im Code integriert)
# Automatisch bei jedem neuen Order/Inventory
```

**Metabase selbst macht NICHTS** - es zeigt nur die Daten aus den Views an!

---

### Workflow 3: Troubleshooting

```bash
# Dashboard zeigt veraltete Daten?

# 1. Prüfe View Status
curl "http://localhost:8000/api/v1/metabase/views/status" | jq

# 2. Überprüfe letzte Aktualisierung
# (im Output von Schritt 1)

# 3. Manuell aktualisieren
curl -X POST "http://localhost:8000/api/v1/metabase/sync/all"

# 4. In Metabase: Refresh Dashboard (F5)
```

---

## 🎓 Zusammenfassung: Die Rollenverteilung

### SoleFlipper API

**Verantwortlich für:**
- ✅ Views **erstellen** (CREATE MATERIALIZED VIEW)
- ✅ Views **aktualisieren** (REFRESH MATERIALIZED VIEW)
- ✅ Views **löschen** (DROP MATERIALIZED VIEW)
- ✅ Status **überwachen** (Rows, Indexes, Existenz)
- ✅ Refresh-Schedule **verwalten** (pg_cron Jobs)
- ✅ Dashboard-Templates **bereitstellen** (JSON Konfigurationen)

**NICHT verantwortlich für:**
- ❌ Daten an Metabase senden
- ❌ Metabase Dashboards erstellen
- ❌ Metabase User Authentication
- ❌ Chart-Rendering

---

### Metabase

**Verantwortlich für:**
- ✅ Daten aus PostgreSQL **abfragen** (SELECT * FROM analytics.*)
- ✅ Dashboards **erstellen** und **anzeigen**
- ✅ Charts/Tabellen **visualisieren**
- ✅ User **Authentication** & **Permissions**
- ✅ Fragen/Queries **speichern**
- ✅ Dashboard **Sharing** & **Embedding**

**NICHT verantwortlich für:**
- ❌ Materialized Views erstellen
- ❌ Daten aggregieren (das machen die Views)
- ❌ Views aktualisieren
- ❌ Mit SoleFlipper API kommunizieren

---

### PostgreSQL

**Verantwortlich für:**
- ✅ Materialized Views **speichern**
- ✅ Daten **aggregieren** (beim REFRESH)
- ✅ Queries **ausführen** (von Metabase)
- ✅ Indexes **nutzen** für Performance
- ✅ pg_cron Jobs **ausführen** (automatische Refresh)

---

## 💡 Häufige Fragen

### Q: Muss die SoleFlipper API laufen, damit Metabase funktioniert?

**A: NEIN!** Sobald die Views einmal erstellt sind, kann Metabase sie völlig unabhängig nutzen.

```
API läuft:     ✅ Views erstellen/updaten möglich
API stoppt:    ✅ Metabase funktioniert weiter
               ❌ Aber: Keine automatischen Updates mehr (außer pg_cron)
```

---

### Q: Werden Daten in Echtzeit aktualisiert?

**A: NEIN!** Materialized Views sind **Snapshots**.

```
10:00 Uhr - Order erstellt in transactions.orders
10:00 Uhr - Metabase zeigt ALTE Daten (View noch nicht aktualisiert)
10:15 Uhr - API refresht View (oder pg_cron)
10:15 Uhr - Metabase zeigt NEUE Daten

Alternative für Echtzeit:
- Nutze normale Views statt Materialized Views (langsamer)
- Oder: Event-driven Refresh direkt nach Order-Erstellung
```

---

### Q: Kann ich die Views auch direkt in SQL erstellen ohne API?

**A: JA!** Die API ist nur ein Komfort-Feature.

```sql
-- Du kannst die SQL-Statements auch manuell ausführen
-- Kopiere SQL aus: domains/integration/metabase/config/materialized_views.py

CREATE MATERIALIZED VIEW analytics.metabase_executive_metrics AS
SELECT
    DATE_TRUNC('day', o.sold_at) AS sale_date,
    ...
FROM transactions.orders o
...;

-- Aber: API ist einfacher, versioniert, dokumentiert
```

---

### Q: Wie greife ich von Metabase auf die Views zu?

**A: Wie auf normale Tabellen!**

```
1. In Metabase: New Question → Simple Question
2. Pick Data: SoleFlipper Database
3. Schema wählen: analytics
4. Table wählen: metabase_executive_metrics
5. Felder auswählen: sale_month, total_revenue
6. Visualisierung wählen: Line Chart
```

---

### Q: Was passiert, wenn ich einen View in Metabase ändere?

**A: NICHTS in der Datenbank!** Metabase ändert nur die **Query** oder **Visualisierung**.

```
Metabase Änderungen:       Nur in Metabase gespeichert
PostgreSQL Änderungen:     Via API oder manuelles SQL
```

---

## 🎯 Best Practices

### 1. Nutze die API für Setup & Management

```bash
# Erstellen/Löschen/Status → API
curl -X POST "http://localhost:8000/api/v1/metabase/views/create"

# Dashboards erstellen → Metabase UI
# (Bessere Visualisierungs-Optionen)
```

---

### 2. Automatisiere Refreshes mit pg_cron

```bash
# Einmalig einrichten
curl -X POST "http://localhost:8000/api/v1/metabase/setup/refresh-schedule"

# Danach: Hände weg, läuft automatisch
```

---

### 3. Event-driven Updates für kritische Views

```python
# Bei jedem neuen Order: Refresh relevante Views
async def create_order(order_data):
    order = await order_repository.create(order_data)
    await sync_service.sync_on_order_event()  # API Call
    return order
```

---

### 4. Monitoring mit Status Endpoint

```bash
# Täglich prüfen (z.B. via Monitoring Tool)
curl "http://localhost:8000/api/v1/metabase/views/status"

# Alert wenn:
# - Views fehlen (exists: false)
# - Row Count = 0
# - Zu viele Rows (Performance-Problem)
```

---

## 📖 Weiterführende Dokumentation

- **Vollständige API Referenz:** `domains/integration/metabase/README.md`
- **Quick Start:** `context/metabase-integration-quickstart.md`
- **Architektur:** `context/metabase-architecture-overview.md`

---

**Last Updated:** 2025-10-01
**Version:** v2.2.3
