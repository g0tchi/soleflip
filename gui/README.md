# 🎮 SoleFlipper GUI - Retro Admin Interface

Eine nostalgische Tauri-Desktop-Anwendung mit React für die SoleFlipper-Plattform, inspiriert vom klassischen Keygen-Stil der 90er/2000er Jahre.

## ✨ Features

### 🎨 Retro Design
- **Keygen-inspirierte UI** mit ASCII-Art und Neon-Effekten
- **Matrix-Stil Animationen** und Glitch-Effekte  
- **Mehrere Farbthemen**: Cyan, Green, Magenta, Amber
- **Responsive Design** mit Desktop-optimierten Layouts

### 🔧 Funktionen
- **Dashboard** - Echtzeit-Metriken und Systemstatus
- **Inventory Management** - Produktverwaltung mit Filtern
- **Analytics** - Brand-Performance und Business-Intelligence
- **Data Import** - StockX-Integration und CSV-Import
- **Database Interface** - SQL-Query-Tool (Read-Only)
- **Settings** - Anpassbare Einstellungen und Themes

### 🚀 Technologie
- **Tauri** - Rust-basiertes Desktop-Framework
- **React 18** - Moderne UI-Bibliothek
- **TypeScript** - Type-Safe Development
- **Tailwind CSS** - Utility-First Styling
- **Vite** - Schneller Build-Tool

## 🛠️ Installation & Setup

### Voraussetzungen
- **Node.js** 18+
- **Rust** 1.60+
- **Tauri CLI** installiert

### 1. Dependencies installieren
```bash
cd soleflip-gui
npm install
```

### 2. Tauri CLI installieren (falls nicht vorhanden)
```bash
npm install -g @tauri-apps/cli
```

### 3. Development starten
```bash
npm run tauri dev
```

### 4. Production Build
```bash
npm run tauri build
```

## 📁 Projektstruktur

```
soleflip-gui/
├── src/                    # React Frontend
│   ├── components/         # UI Components
│   │   ├── Layout.tsx      # Haupt-Layout mit Sidebar
│   │   ├── StatusBar.tsx   # System-Status-Anzeige
│   │   └── RetroTitle.tsx  # ASCII-Art Titel
│   ├── pages/              # Route Pages
│   │   ├── Dashboard.tsx   # Haupt-Dashboard
│   │   ├── Inventory.tsx   # Produktverwaltung
│   │   ├── Analytics.tsx   # Analysen
│   │   ├── Import.tsx      # Datenimport
│   │   ├── Database.tsx    # SQL-Interface
│   │   └── Settings.tsx    # Einstellungen
│   ├── styles/             # CSS/Styling
│   │   └── globals.css     # Retro-CSS-Klassen
│   └── main.tsx            # React Entry Point
│
├── src-tauri/              # Rust Backend
│   ├── src/
│   │   ├── main.rs         # Tauri Entry Point
│   │   ├── commands.rs     # Tauri Commands
│   │   └── api.rs          # API Client
│   ├── Cargo.toml          # Rust Dependencies
│   └── tauri.conf.json     # Tauri Konfiguration
│
└── dist/                   # Build Output
```

## 🎨 Retro Design System

### Farb-Palette
```css
--retro-cyan: #00ffff      /* Matrix Cyan */
--retro-green: #00ff00     /* Terminal Green */
--retro-magenta: #ff00ff   /* Neon Magenta */
--retro-yellow: #ffff00    /* Amber Yellow */
--retro-purple: #8b00ff    /* Electric Purple */
```

### CSS-Klassen
- `.retro-button` - Neon-Button mit Hover-Effekten
- `.retro-card` - Karten mit Glow-Effekten
- `.retro-table` - Tabellen im Terminal-Stil
- `.ascii-art` - ASCII-Art-Darstellung
- `.animate-glow` - Glow-Animation

### Animationen
- **Glow Effects** - Leuchtende Neon-Effekte
- **Matrix Rain** - Matrix-Stil Background
- **Scan Lines** - Retro-CRT-Effekte
- **Glitch Text** - Zufällige Text-Störungen

## 🔌 API Integration

### Rust Commands
```rust
// System Status
get_system_status() -> SystemStatus

// Dashboard Metriken  
get_dashboard_metrics() -> DashboardMetrics

// Inventory
get_inventory_items(limit: Option<i32>) -> Vec<InventoryItem>

// Import
import_stockx_data(from_date: String, to_date: String) -> ImportResponse
get_import_status(batch_id: String) -> ImportStatus

// Database
run_database_query(query: String) -> Vec<HashMap<String, Value>>
export_data_csv(table: String) -> String
```

### Frontend Usage
```typescript
import { invoke } from '@tauri-apps/api/tauri';

const data = await invoke<DashboardMetrics>('get_dashboard_metrics');
```

## ⚙️ Konfiguration

### Tauri Permissions
```json
{
  "http": {
    "scope": ["http://localhost:8000/**", "https://api.stockx.com/**"]
  },
  "notification": { "all": true },
  "dialog": { "open": true, "save": true }
}
```

### API Endpoint
Standard: `http://localhost:8000` (FastAPI Backend)

## 🧪 Development

### Commands
```bash
# Development mit Hot-Reload
npm run tauri dev

# Frontend separat
npm run dev

# Production Build
npm run tauri build

# Type-Check
npm run tsc

# Linting
npm run lint
```

### Debugging
- **Rust Backend**: Console-Logs in Terminal
- **Frontend**: Browser DevTools (F12)
- **Tauri DevTools**: Automatisch verfügbar in Dev-Mode

## 📦 Build & Distribution

### Windows
```bash
npm run tauri build
```
Erstellt: `src-tauri/target/release/bundle/msi/SoleFlipper_1.0.0_x64_de-DE.msi`

### Linux
```bash
npm run tauri build
```
Erstellt: `src-tauri/target/release/bundle/deb/soleflip-gui_1.0.0_amd64.deb`

### macOS
```bash
npm run tauri build
```
Erstellt: `src-tauri/target/release/bundle/dmg/SoleFlipper_1.0.0_x64.dmg`

## 🔐 Sicherheit

- **Read-Only Database** - Nur SELECT-Queries erlaubt
- **API Validation** - Alle Requests validiert
- **CORS Protection** - Nur erlaubte Origins
- **Input Sanitization** - XSS-Schutz

## 🎮 Keygen-Stil Features

### ASCII-Art Banner
```
╔═══════════════════════╗
║                       ║
║      S O L E F L I P  ║
║                       ║
╚═══════════════════════╝
```

### Animations
- **Matrix-Effekte** im Background
- **Scan-Lines** über UI-Elemente
- **Glitch-Text** bei Titel
- **Neon-Glow** bei interaktiven Elementen

### Sound-Design (geplant)
- Retro-Keygen-Sounds
- Terminal-Klick-Sounds
- Success/Error-Chimes

## 🚀 Deployment

### Standalone-Executable
Die Tauri-App kompiliert zu einer einzelnen `.exe`-Datei (~10MB) ohne externe Dependencies.

### Auto-Update (geplant)
Integration mit Tauri-Update-System für automatische Updates.

## 🤝 Development Guidelines

### Code-Stil
- **TypeScript** für Type-Safety
- **Functional Components** mit Hooks
- **Tailwind CSS** für Styling
- **Rust** für Backend-Logic

### UI-Prinzipien
- **Retro-First** - Alle UI-Elemente im Keygen-Stil
- **Performance** - Optimiert für Desktop-Performance
- **Accessibility** - Keyboard-Navigation unterstützt

## 📄 Lizenz

MIT License - Siehe LICENSE-Datei für Details.

---

**🎮 Entwickelt mit Liebe für die Retro-Ästhetik der 90er/2000er Jahre! 🎮**