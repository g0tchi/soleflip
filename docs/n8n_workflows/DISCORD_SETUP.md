# Discord Setup für n8n Workflows

Schnelle Anleitung zum Einrichten von Discord-Benachrichtigungen für die SoleFlipper Workflows.

## 🚀 Warum Discord statt Slack?

**Vorteile:**
- ✅ **Einfacher Setup** - Nur Webhook URL, kein OAuth
- ✅ **Keine App-Installation** - Funktioniert sofort
- ✅ **Rich Embeds** - Bessere Formatierung als Slack
- ✅ **Kostenlos** - Kein Paid Plan erforderlich
- ✅ **Schneller** - Direkter HTTP POST, keine API-Limits

## 📋 Setup (5 Minuten)

### 1. Discord Webhook erstellen

1. **Öffnen Sie Ihren Discord Server**
   - Falls Sie noch keinen haben: [Discord Server erstellen](https://discord.com/)

2. **Gehen Sie zu Server-Einstellungen**
   - Rechtsklick auf Server → "Server-Einstellungen"
   - Oder: Klick auf Server-Name → "Server-Einstellungen"

3. **Navigieren Sie zu Integrationen**
   - Linke Sidebar → "Integrationen"
   - Klicken Sie "Webhooks"

4. **Erstellen Sie einen neuen Webhook**
   - Klicken Sie "Neuer Webhook"
   - Name: **"SoleFlipper Bot"**
   - Channel: Wählen Sie einen Channel (z.B. `#alerts` oder `#orders`)
   - Optional: Laden Sie ein Avatar hoch

5. **Kopieren Sie die Webhook-URL**
   - Klicken Sie "Webhook-URL kopieren"
   - Format: `https://discord.com/api/webhooks/123456789/AbCdEfGhIjK...`

### 2. Webhook URL in n8n konfigurieren

#### Option A: Environment Variable (Empfohlen)

```bash
# Fügen Sie zur .env Datei hinzu
echo 'DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL' >> .env

# Restart n8n
docker-compose restart n8n
```

#### Option B: Direkt in Workflows

Für jeden Workflow:
1. Öffnen Sie den Workflow in n8n
2. Finden Sie den "Send to Discord" Node
3. Ersetzen Sie `={{ $env.DISCORD_WEBHOOK_URL }}` mit Ihrer URL
4. **Achtung:** Nicht empfohlen - URL ist dann im Workflow hart codiert

### 3. Testen

```bash
# Test die Webhook URL
curl -X POST "YOUR_DISCORD_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "embeds": [{
      "title": "🎉 Test Message",
      "description": "SoleFlipper n8n integration is working!",
      "color": 3066993
    }]
  }'
```

Wenn erfolgreich, sehen Sie eine Nachricht im Discord Channel!

## 📊 Discord Channels organisieren

**Empfohlene Channel-Struktur:**

```
📁 SOLEFLIP AUTOMATION
  ├─ 📢 #orders          → Order Monitor, Webhook Handler
  ├─ 📦 #inventory       → Dead Stock, Low Stock Alerts
  ├─ 💰 #pricing         → Price Monitoring Alerts
  └─ 📊 #reports         → Daily Analytics Report
```

**Setup:**

1. Erstellen Sie die Channels
2. Erstellen Sie für jeden Channel einen separaten Webhook
3. Verwenden Sie unterschiedliche Environment Variables:

```bash
# .env
DISCORD_WEBHOOK_ORDERS=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_INVENTORY=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_PRICING=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_REPORTS=https://discord.com/api/webhooks/...
```

4. Update die Workflows, um die richtige Variable zu verwenden

## 🎨 Discord Embed Farben

Die Workflows verwenden Farben für verschiedene Alert-Typen:

| Workflow | Farbe | Hex | RGB |
|----------|-------|-----|-----|
| Order Monitor | 🟢 Grün | #2ECC71 | `3066993` |
| Dead Stock Alert | 🔴 Rot | #E74C3C | `15158332` |
| Low Stock Alert | 🟡 Gelb | #FFC107 | `16776960` |
| Analytics Report | 🔵 Blau | #3498DB | `3447003` |
| Price Alerts | 🟠 Orange | #FF6600 | `16753920` |
| Webhook Events | 🟣 Lila | #9B59B6 | `5763719` |

## 🔧 Erweiterte Konfiguration

### Multiple Webhooks für verschiedene Workflows

**In n8n:**
1. Gehen Sie zu "Settings" → "Variables"
2. Fügen Sie hinzu:
   - `DISCORD_WEBHOOK_ORDERS`
   - `DISCORD_WEBHOOK_INVENTORY`
   - `DISCORD_WEBHOOK_PRICING`
   - `DISCORD_WEBHOOK_REPORTS`

**In Workflows:**
```javascript
// Statt:
url: "={{ $env.DISCORD_WEBHOOK_URL }}"

// Verwenden Sie:
url: "={{ $env.DISCORD_WEBHOOK_ORDERS }}"
```

### Mentions (@everyone, @role)

Für wichtige Alerts können Sie Mentions hinzufügen:

```javascript
const embed = {
  title: '🚨 CRITICAL: Dead Stock Alert',
  description: '@everyone Please review immediately!',
  // ... rest of embed
};

return {
  json: {
    content: '@everyone',  // Top-level mention
    embeds: [embed]
  }
};
```

**Wichtig:** Aktivieren Sie "Mentions" in den Webhook-Einstellungen!

### Custom Avatar & Username

Sie können für jeden Post Avatar und Username ändern:

```javascript
return {
  json: {
    username: 'SoleFlipper Bot',
    avatar_url: 'https://your-domain.com/bot-avatar.png',
    embeds: [embed]
  }
};
```

## 🛠️ Troubleshooting

### "Webhook URL is invalid"

**Problem:** URL Format ist falsch

**Lösung:**
```bash
# Korrekt:
https://discord.com/api/webhooks/123456789/AbCdEfG...

# Falsch:
discord.com/api/webhooks/...  # Fehlt https://
https://discordapp.com/...     # Alte Domain
```

### "Missing Access"

**Problem:** Webhook wurde gelöscht oder Channel wurde gelöscht

**Lösung:**
1. Gehen Sie zu Server-Einstellungen → Integrationen → Webhooks
2. Prüfen Sie, ob der Webhook noch existiert
3. Erstellen Sie ggf. einen neuen Webhook

### "Embeds are empty"

**Problem:** Embed-Struktur ist falsch

**Lösung:** Prüfen Sie die Embed-Struktur:
```javascript
{
  embeds: [{  // Muss ein Array sein!
    title: "Title",
    description: "Description",
    color: 3066993,  // Integer, nicht String!
    fields: [...]
  }]
}
```

### Keine Benachrichtigungen im Discord

**Problem:** Discord Notifications sind deaktiviert

**Lösung:**
1. Rechtsklick auf Channel → "Benachrichtigungseinstellungen"
2. Aktivieren Sie "Alle Nachrichten"
3. Optional: Aktivieren Sie Desktop/Mobile Notifications

## 📚 Ressourcen

- **Discord Webhook Docs:** https://discord.com/developers/docs/resources/webhook
- **Embed Visualizer:** https://leovoel.github.io/embed-visualizer/
- **Color Picker:** https://www.color-hex.com/

## ✅ Checkliste

- [ ] Discord Server erstellt/vorhanden
- [ ] Webhook erstellt für jeden gewünschten Channel
- [ ] Webhook URL(s) kopiert
- [ ] Environment Variable(s) in .env gesetzt
- [ ] n8n restarted (`docker-compose restart n8n`)
- [ ] Webhook mit curl getestet
- [ ] Workflows importiert und aktiviert
- [ ] Erste Benachrichtigung empfangen

## 🎉 Fertig!

Ihre Discord-Integration ist jetzt aktiv! Sie erhalten automatisch:

- **Alle 15 Minuten:** Neue Orders (wenn vorhanden)
- **Alle 6 Stunden:** Low Stock Alerts
- **Alle 2 Stunden:** Price Monitoring Alerts
- **Täglich 8:00 Uhr:** Dead Stock Report
- **Täglich 8:30 Uhr:** Analytics Report
- **Real-time:** StockX Webhook Events

**Viel Erfolg mit Ihren Automatisierungen!** 🚀
