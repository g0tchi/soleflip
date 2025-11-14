# n8n Integration Setup Guide

This guide explains how to set up n8n for receiving arbitrage alert notifications.

## Overview

The SoleFlip Arbitrage Alert System uses n8n as a notification router. When new arbitrage opportunities matching your criteria are found, the system sends a webhook to n8n, which then routes the notification to your preferred channels (Discord, Email, Telegram, etc.).

## Architecture

```
SoleFlip Alert Service
       ↓
  n8n Webhook
       ↓
  Format Data
       ↓
   ┌──────┴──────┐
   ↓      ↓      ↓
Discord Email Telegram
```

## Setup Steps

### 1. Import the Workflow

1. Open your n8n instance
2. Click "Workflows" → "Import from File"
3. Select `n8n-workflow-example.json` from `domains/arbitrage/docs/`
4. The workflow will be imported with the name "SoleFlip Arbitrage Alerts"

### 2. Configure Credentials

#### Discord Webhook
1. Go to your Discord server settings
2. Navigate to "Integrations" → "Webhooks"
3. Click "New Webhook"
4. Copy the webhook URL
5. In n8n, open the "Send to Discord" node
6. Click "Create New Credential"
7. Paste your Discord webhook URL
8. Save

#### Email (SMTP)
1. In n8n, open the "Send Email" node
2. Click "Create New Credential"
3. Enter your SMTP server details:
   - Host: smtp.gmail.com (for Gmail)
   - Port: 587
   - Secure: true
   - User: your-email@gmail.com
   - Password: your-app-password
4. Save

**Note:** For Gmail, you need to create an [App Password](https://support.google.com/accounts/answer/185833).

#### Telegram Bot
1. Create a Telegram bot via [@BotFather](https://t.me/botfather)
2. Copy the API token
3. Get your chat ID (send a message to @userinfobot)
4. In n8n, open the "Send to Telegram" node
5. Click "Create New Credential"
6. Enter your bot token
7. Save

### 3. Activate the Workflow

1. Click the "Activate" toggle in the top right
2. The webhook URL will be generated
3. Copy the webhook URL (it will look like: `https://your-n8n-instance.com/webhook/soleflip-arbitrage-alert`)

### 4. Create an Alert in SoleFlip

Use the webhook URL when creating your alert:

```bash
curl -X POST "http://localhost:8000/api/v1/arbitrage/alerts" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_name": "High Profit Opportunities",
    "n8n_webhook_url": "https://your-n8n-instance.com/webhook/soleflip-arbitrage-alert",
    "min_profit_margin": 20.0,
    "min_gross_profit": 50.0,
    "min_feasibility_score": 70,
    "max_risk_level": "MEDIUM",
    "notification_config": {
      "discord": true,
      "email": true,
      "telegram": false
    },
    "alert_frequency_minutes": 15
  }'
```

## Notification Channels

### Discord

Notifications are sent as rich embeds with:
- Alert name as title
- Total opportunities and potential profit
- Average feasibility score and profit margin
- Timestamp

**Example:**
```
🔔 New Arbitrage Opportunities: High Profit Opportunities

Found 5 profitable opportunities!

💰 Total Potential Profit: €450.50
📊 Avg Feasibility: 82.5/100
📈 Avg Profit Margin: 35.2%
```

### Email

HTML-formatted emails with:
- Summary statistics
- Table of all opportunities with details
- Direct links to buy URLs

### Telegram

Markdown-formatted messages with:
- Alert summary
- List of opportunities with key metrics
- Risk levels and feasibility scores

## Customization

### Modify Notification Format

Edit the respective nodes in n8n to customize the message format:

**Discord Embed Colors:**
- `3447003` (blue) - Default
- `15158332` (red) - High risk
- `3066993` (green) - Low risk

**Email Template:**
Edit the HTML in the "Send Email" node's `text` parameter to customize the email layout.

**Telegram Format:**
Telegram supports Markdown. Edit the message in the "Send to Telegram" node.

### Add More Channels

You can add additional notification channels:

1. Add a new IF node to check notification config
2. Add the respective service node (Slack, SMS, etc.)
3. Connect it to the "Format Data" node

### Filter by Risk Level

Add an IF node after "Format Data" to filter opportunities:

```javascript
{{$json.opportunities.filter(o => o.risk_level === 'LOW').length > 0}}
```

## Testing

### Test the Workflow

1. In n8n, click "Execute Workflow" button
2. Manually trigger with test data
3. Check that notifications are sent to configured channels

### Test with SoleFlip

1. Create a test alert with very broad criteria
2. Wait for the next scan cycle (or trigger manually)
3. Check your notification channels

## Payload Structure

The webhook receives this JSON structure:

```json
{
  "alert": {
    "id": "uuid",
    "name": "Alert Name",
    "user_id": "uuid"
  },
  "notification_config": {
    "discord": true,
    "email": false,
    "telegram": false
  },
  "opportunities": [
    {
      "product_name": "Nike Air Max 90",
      "product_sku": "SKU-123",
      "brand": "Nike",
      "buy_price": 120.00,
      "sell_price": 180.00,
      "gross_profit": 60.00,
      "profit_margin": 50.0,
      "roi": 50.0,
      "buy_source": "awin",
      "buy_supplier": "Afew Store",
      "buy_url": "https://...",
      "stock_qty": 5,
      "feasibility_score": 85,
      "demand_score": 78.5,
      "risk_level": "LOW",
      "estimated_days_to_sell": 7,
      "demand_breakdown": { ... },
      "risk_details": { ... }
    }
  ],
  "summary": {
    "total_opportunities": 5,
    "avg_profit_margin": 45.2,
    "avg_feasibility": 82.5,
    "total_potential_profit": 450.50
  },
  "timestamp": "2025-11-14T12:00:00Z"
}
```

## Troubleshooting

### Webhook Not Receiving Data

1. Check that the workflow is activated
2. Verify the webhook URL is correct in your alert configuration
3. Check n8n execution logs for errors

### Notifications Not Sending

1. Verify credentials are configured correctly
2. Check the IF nodes are evaluating true
3. Review the notification_config in your alert

### Rate Limiting

If you're hitting rate limits:
- Increase `alert_frequency_minutes` in your alert
- Reduce `max_opportunities_per_alert` to send fewer opportunities

## Advanced Configuration

### User-Specific Settings

Modify the "Format Data" node to fetch user-specific settings:

```javascript
// Fetch user email and Telegram chat ID from database
const userId = $input.item.json.alert.user_id;

// Example: Query your user database
const userData = await fetchUserData(userId);

return {
  json: {
    ...formattedData,
    user_email: userData.email,
    telegram_chat_id: userData.telegram_chat_id
  }
};
```

### Conditional Formatting

Add conditions to change notification style based on opportunity quality:

```javascript
const riskColor = {
  'LOW': 3066993,    // Green
  'MEDIUM': 3447003, // Blue
  'HIGH': 15158332   // Red
}[$json.opportunities[0].risk_level];
```

## Support

For issues or questions:
- Check the n8n [documentation](https://docs.n8n.io/)
- Review SoleFlip arbitrage domain README
- Check application logs for webhook errors
