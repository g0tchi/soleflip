# n8n Workflow Documentation

This document provides an overview of the n8n workflows used in the SoleFlipper project. These workflows, located in the `/config/n8n/` directory, automate various tasks, primarily focused on data synchronization between external services like Notion and the application's database.

## Summary of Workflows

| File Name                                    | Workflow Name                             | Trigger                                   | Key Action                                                              |
| -------------------------------------------- | ----------------------------------------- | ----------------------------------------- | ----------------------------------------------------------------------- |
| `n8n_periodic_stockx_fetch.json`             | Periodischer StockX Datenabruf            | Schedule (Every Monday at 2:00 AM)        | Calls the SoleFlipper API to trigger a weekly StockX data fetch.        |
| `n8n_direct_db_inventory_status.json`        | Notion to DB: Inventory Status Changes    | Webhook (`/notion-inventory-status`)      | Updates inventory status directly in the database based on Notion changes. |
| `n8n_direct_db_supplier_update.json`         | Notion to DB: Supplier Updates            | Webhook (`/notion-supplier-update`)       | Updates supplier information directly in the database from Notion.      |
| `n8n_direct_db_transaction_updates.json`     | Notion to DB: Transaction Price Updates   | Webhook (`/notion-transaction-update`)    | Updates transaction financial details directly in the database from Notion. |
| `n8n_notion_supplier_sync_workflow.json`     | Notion Supplier Sync to SoleFlipper       | Webhook (`/notion-supplier-sync`)         | Calls the SoleFlipper API to update supplier info; includes Slack notifications. |

---

## 1. Periodic StockX Data Fetch

-   **File:** `n8n_periodic_stockx_fetch.json`
-   **Name:** `Periodischer StockX Datenabruf`
-   **Purpose:** To automatically trigger a process in the main application to fetch the latest data from the StockX API on a regular schedule.
-   **Trigger:**
    -   **Type:** Schedule (Cron Job)
    -   **Schedule:** Every Monday at 2:00 AM (`0 2 * * 1`).
-   **Steps:**
    1.  The workflow starts automatically based on the schedule.
    2.  It sends a `POST` request to an endpoint in the SoleFlipper API (e.g., `/api/v1/integration/stockx/trigger-fetch`).
    3.  It checks the API response status.
    4.  If the API call fails, it sends an email notification with error details.
-   **Configuration Notes:**
    -   The target API URL is a placeholder (`https://<IHRE_API_URL>/...`) and must be configured in n8n.
    -   Requires an API Key credential to be configured in n8n to authenticate with the SoleFlipper API.
    -   Requires SMTP credentials to be configured in n8n for sending email notifications.

---

## 2. Notion to DB Sync Workflows (Direct Database)

The following three workflows listen for webhooks from Notion and write changes directly to the PostgreSQL database. This provides a fast and direct way to sync data, but bypasses the application's API logic.

### 2.1. Inventory Status Changes

-   **File:** `n8n_direct_db_inventory_status.json`
-   **Name:** `Notion to DB: Inventory Status Changes`
-   **Purpose:** To sync inventory status changes (e.g., "Available", "Sold") from a Notion database to the application.
-   **Trigger:**
    -   **Type:** Webhook
    -   **URL Path:** `/notion-inventory-status`
-   **Steps:**
    1.  Receives a webhook when a page in Notion is updated.
    2.  Extracts the new status and product identifiers (SKU, size, etc.).
    3.  Updates the `status` in the `products.inventory` table.
    4.  **Special Logic:** If the new status is "sold", it automatically creates a new record in the `sales.transactions` table.
-   **Configuration Notes:**
    -   Requires PostgreSQL credentials to be configured in n8n.
    -   The Notion database must be configured to send webhooks to this endpoint upon updates.

### 2.2. Supplier Updates

-   **File:** `n8n_direct_db_supplier_update.json`
-   **Name:** `Notion to DB: Supplier Updates`
-   **Purpose:** To update the supplier for a transaction based on a change made in Notion.
-   **Trigger:**
    -   **Type:** Webhook
    -   **URL Path:** `/notion-supplier-update`
-   **Steps:**
    1.  Receives a webhook from Notion.
    2.  Filters to ensure the update contains a supplier and order number.
    3.  Extracts the supplier name and order number.
    4.  Updates the `notes` field in `sales.transactions` and the `supplier` field in `products.inventory` for the matching order.
-   **Configuration Notes:**
    -   Requires PostgreSQL credentials.

### 2.3. Transaction Price Updates

-   **File:** `n8n_direct_db_transaction_updates.json`
-   **Name:** `Notion to DB: Transaction Price Updates`
-   **Purpose:** To update financial details (sale price, fees, shipping cost) of a transaction from Notion.
-   **Trigger:**
    -   **Type:** Webhook
    -   **URL Path:** `/notion-transaction-update`
-   **Steps:**
    1.  Receives a webhook from Notion.
    2.  Extracts pricing data and order identifiers.
    3.  Calculates the new `net_profit`.
    4.  Updates the corresponding record in the `sales.transactions` table with all new financial figures.
-   **Configuration Notes:**
    -   Requires PostgreSQL credentials.

---

## 3. Notion to API Sync Workflow (API-based)

This workflow provides a more robust method for syncing from Notion by using the application's own API.

-   **File:** `n8n_notion_supplier_sync_workflow.json`
-   **Name:** `Notion Supplier Sync to SoleFlipper`
-   **Purpose:** To sync supplier information from Notion to the application via the official API, with added monitoring.
-   **Trigger:**
    -   **Type:** Webhook
    -   **URL Path:** `/notion-supplier-sync`
-   **Steps:**
    1.  Receives a webhook from Notion when a supplier is changed.
    2.  Transforms the incoming data into a JSON payload for the SoleFlipper API.
    3.  Calls the `/api/v1/integration/n8n/notion/sync` endpoint in the main application.
    4.  Checks the API response.
    5.  Sends a success or failure notification to a configured **Slack** channel.
-   **Configuration Notes:**
    -   This is the recommended approach for Notion integration as it respects the application's business logic and validation.
    -   Requires API credentials for the SoleFlipper API to be configured in n8n.
    -   Requires Slack API credentials for notifications.
