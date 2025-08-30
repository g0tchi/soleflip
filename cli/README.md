# 💎 Retro Admin CLI 💎

Ein nostalgisches Keygen-inspiriertes CLI-Tool für Datenbank- und API-Management.

## 🎮 Features

### 🎨 Retro Keygen Style
- ASCII-Art Startscreen mit animierten Fortschrittsbalken
- Interaktive Benutzereingabe mit "Codename"-System
- Fake Key-Generierung mit Animationen
- Matrix-Effekte und Glitch-Text

### 🔐 Sicherheit & Logging
- Session Management mit eindeutigen Session-IDs
- Umfassendes Logging (Access, Error, Audit)
- Sicherheitschecks für Produktions-/Test-Umgebungen
- Verschlüsselungsschlüssel-Validierung

### 🗄️ Datenbank-Operations
- PostgreSQL-Integration mit SQLAlchemy
- Interactive SQL-Query-Interface (nur SELECT erlaubt)
- Datenexport nach CSV
- Tabellen-Browser mit Statistiken

### 🛍️ Shopify Integration
- REST API-Anbindung
- Produkt-Management und -Updates
- Inventory-Synchronisation
- Katalog-Export

### 📊 Awin Affiliate-Daten
- CSV-Import mit Validierung
- API-Synchronisation (vorbereitet)
- Import-Historie
- Datenvalidierung

## 🚀 Installation

1. **Dependencies installieren:**
```bash
cd retro_cli
pip install -r requirements.txt
```

2. **Konfiguration erstellen:**
```bash
cp .env.example .env
# .env-Datei mit deinen Credentials bearbeiten
```

3. **CLI starten:**
```bash
python cli.py
```

## ⚙️ Konfiguration

### Umgebungsvariablen (.env)

```bash
# Datenbank
DB_HOST=localhost
DB_PORT=5432
DB_NAME=soleflip
DB_USER=postgres
DB_PASSWORD=dein_passwort
DB_TEST_NAME=soleflip_test

# Shopify (optional)
SHOPIFY_SHOP_NAME=dein-shop-name
SHOPIFY_ACCESS_TOKEN=dein_access_token
SHOPIFY_API_VERSION=2024-01

# Awin (optional)
AWIN_API_TOKEN=dein_awin_token
AWIN_ADVERTISER_ID=deine_advertiser_id
AWIN_PUBLISHER_ID=deine_publisher_id

# System
FIELD_ENCRYPTION_KEY=dein_verschluesselungsschluessel
ENVIRONMENT=development  # oder 'production'
DEBUG=true
LOG_LEVEL=INFO
TEST_MODE=false
```

## 🎯 Verwendung

### Startup-Sequenz
1. **Retro Banner** mit ASCII-Art
2. **System-Initialisierung** mit animierten Fortschrittsbalken
3. **Benutzer-Authentifizierung** mit Codename-Eingabe
4. **Fake Key-Generierung** im Keygen-Stil

### Hauptmenü-Optionen

```
╔════════════════════════════════════════════════╗
║            RETRO ADMIN CONTROL PANEL           ║
╚════════════════════════════════════════════════╝
  [1] Database Operations
  [2] Shopify Management  
  [3] Awin Data Import
  [4] Security & Status
  [5] Logs & Analytics
  [Q] Quit
```

### Database Operations
- **List Tables**: Zeige alle Tabellen mit Statistiken
- **Run Query**: Interactive SQL-Interface (nur SELECT)
- **Export Data**: CSV-Export von Tabellen
- **Import Data**: CSV-Import (vorbereitet)

### Shopify Management
- **List Products**: Zeige Produkte mit Status
- **Update Product**: Produkt-Details bearbeiten
- **Sync Inventory**: Inventory-Abgleich
- **Export Catalog**: Vollständiger Katalog-Export

### Awin Data Import
- **Import CSV**: CSV-Dateien analysieren und importieren
- **Sync API Data**: Direkte API-Synchronisation
- **View Import History**: Historie aller Imports
- **Data Validation**: Datenvalidierung und -prüfung

### Security & Status
- **Umgebungs-Sicherheit**: Produktions-/Test-Modus-Checks
- **Service-Status**: Datenbank, Shopify, Awin
- **Session-Info**: Aktuelle Session-Details
- **Verschlüsselungs-Status**: Key-Konfiguration

### Logs & Analytics
- **Access Logs**: Zugriffs-Protokolle
- **Error Logs**: Fehler-Protokolle  
- **Audit Trail**: Audit-Spur aller Aktionen
- **Session History**: Session-Statistiken

## 🔒 Sicherheitsfeatures

### Test-Modus
- Automatische Test-Datenbank-Verwendung
- Sichere Entwicklungsumgebung
- Keine Produktionsdaten-Manipulation

### Branch-Strategie
- Separate Feature-Branches für Entwicklung
- DB-Migrations in Test-Schema
- Produktions-Sicherheitschecks

### Logging
- **Access Log**: Alle Benutzeraktionen
- **Error Log**: Systemfehler und Exceptions
- **Audit Log**: Sicherheitsrelevante Ereignisse
- **Session Log**: Täglich archivierte Sessions

### Session Management
- Eindeutige Session-IDs mit SHA256
- Aktivitätsverfolgung pro Session
- Automatische Session-Archivierung
- Notfall-Logout bei Unterbrechung

## 🎨 Retro-Style Elemente

### ASCII-Art
- Responsives Banner-Design
- Terminal-width-adaptive Layouts
- Rahmen und Boxen im Retro-Stil

### Animationen
- Keygen-Style Loading-Spinner
- Matrix-Effekte
- Typewriter-Effekte
- Glitch-Text-Generierung

### Farbschema
- Cyan/Magenta Hauptfarben
- Grün für Erfolg, Rot für Fehler
- Gelb für Warnungen, Blau für Info

## 📁 Projektstruktur

```
retro_cli/
├── cli.py           # Haupt-CLI-Interface
├── utils.py         # ASCII-Art & Animationen
├── config.py        # Konfigurationsmanagement
├── db.py           # Datenbank-Operationen
├── shopify.py      # Shopify API-Integration
├── awin.py         # Awin Affiliate-Import
├── security.py     # Logging & Sicherheit
├── requirements.txt # Python-Dependencies
├── .env.example    # Konfigurationstemplate
├── README.md       # Diese Datei
└── tests/          # Unit-Tests (geplant)
```

## 🧪 Test-Modus

Für sicheres Testen ohne Produktionsdaten-Risiko:

```bash
# In .env setzen:
TEST_MODE=true
ENVIRONMENT=development
```

## 🤖 Entwicklung

### Code-Stil
- Type-Hints für bessere Dokumentation
- Defensive Programmierung
- Ausführliche Fehlerbehandlung
- Security-First-Ansatz

### Erweiterungen
- Modulares Design für einfache Erweiterungen
- Plugin-System vorbereitet
- API-Abstraktionen für neue Services
- Konfigurierbare Sicherheitsrichtlinien

## 📜 Lizenz

Dieses Projekt ist für interne Verwendung entwickelt. Alle Rechte vorbehalten.

## 🎉 Credits

- **Retro Keygen Style**: Inspiriert von klassischen 90er/2000er Keygens
- **CLI Framework**: Eigene Implementierung mit Python
- **ASCII Art**: Responsive Terminal-Art-Engine
- **Security**: Enterprise-Grade Logging und Session-Management

---

**💜 Viel Spaß mit dem Retro Admin CLI! 💜**