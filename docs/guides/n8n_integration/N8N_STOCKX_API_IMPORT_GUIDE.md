# n8n Workflow Guide: Automated StockX Order Import via API

This guide provides a step-by-step walkthrough for creating an n8n workflow that automatically fetches the latest sales data from StockX every day and imports it into the SoleFlipper system.

This new API-based method is the recommended approach for automated imports, replacing the manual CSV upload.

## Prerequisites

1.  **API Credentials Configured:** Ensure your StockX API Key and JWT Token are correctly configured in the SoleFlipper system via the `core.system_config` table. The `key` names must be `stockx_api_key` and `stockx_jwt_token`.
2.  **SoleFlipper API Running:** The main SoleFlipper application must be running and accessible from your n8n instance.

## Workflow Overview

The workflow will consist of three simple nodes:
1.  **Schedule Trigger:** To run the workflow automatically every day.
2.  **Set Dates Node:** A "Set" node to define the `from_date` and `to_date` for the import.
3.  **HTTP Request Node:** To call the SoleFlipper API endpoint.

---

### Step 1: Create a New Workflow

1.  In your n8n dashboard, click on **"Add workflow"**.
2.  Start with an empty workflow.

### Step 2: Configure the Schedule Trigger

This node will start the workflow at a specified time.

1.  Click the **"+"** button and add a **Schedule** trigger node.
2.  **Trigger Interval:** Set this to `Every Day`.
3.  **Hour:** Set a time when the workflow should run, for example, `3` (for 3:00 AM). This is a good time to run daily imports as it's usually off-peak.
4.  **Timezone:** Select your local timezone to ensure the workflow runs at the correct time.

*Your Schedule node should look something like this:*
```
[Schedule Trigger]
- Trigger Interval: Every Day
- Hour: 3
- Timezone: Europe/Berlin
```

### Step 3: Set the Import Dates

This node will create the date range for the import. We will configure it to always fetch the data from "yesterday".

1.  Add a new node by clicking the **"+"** below the trigger and select the **Set** node.
2.  Under **Values to Set**, configure one value:
    *   **Name:** `jsonData`
    *   **Value:** This is where we use an n8n expression. Click the "fx" button and enter the following:
        ```javascript
        {{
          {
            "from_date": $now.minus({days: 1}).toFormat('yyyy-MM-dd'),
            "to_date": $now.minus({days: 1}).toFormat('yyyy-MM-dd')
          }
        }}
        ```
    *   **Explanation:**
        *   `$now` is a special n8n variable representing the current date and time.
        *   `.minus({days: 1})` subtracts one day.
        *   `.toFormat('yyyy-MM-dd')` formats the date into the `YYYY-MM-DD` string required by the API.
        *   We set both `from_date` and `to_date` to the same day to fetch all orders from that specific day.

3.  Ensure the "Data Is JSON" switch is **ON**.

*Your Set node should look something like this:*
```
[Set Node: "Set Import Dates"]
- Values to Set:
  - jsonData = (Expression -> { "from_date": ..., "to_date": ... })
- Data Is JSON: ON
```

### Step 4: Configure the HTTP Request Node

This is the final node that calls our new API endpoint.

1.  Add a new node by clicking the **"+"** below the Set node and select the **HTTP Request** node.
2.  Configure the following properties:
    *   **Method:** `POST`
    *   **URL:** Enter the URL to your running SoleFlipper application's endpoint. For example:
        ```
        http://localhost:8000/api/v1/integration/stockx/import-orders
        ```
        (Replace `localhost:8000` with your actual host and port if different).
    *   **Send Body:** `true`
    *   **Body Content Type:** `JSON`
    *   **JSON/RAW Parameters:** `true`
    *   **Body:** This field will automatically reference the data from the previous node. It should be:
        ```
        ={{ $('Set Dates Node').item.json.jsonData }}
        ```
        (You can use the expression editor to select this).

*Your HTTP Request node should look something like this:*
```
[HTTP Request Node: "Trigger StockX Import"]
- Method: POST
- URL: http://localhost:8000/api/v1/integration/stockx/import-orders
- Send Body: ON
- Body Content Type: JSON
- Body: ={{ $('Set Dates Node').item.json.jsonData }}
```

### Step 5: Activate and Save the Workflow

1.  Give your workflow a descriptive name, like "Daily StockX API Import".
2.  Click the **"Active"** toggle at the top right of the screen to turn the workflow on.
3.  Save the workflow.

That's it! Your n8n workflow is now configured to automatically fetch yesterday's StockX orders every day at 3:00 AM and import them into SoleFlipper. You can monitor the import status using the `/api/v1/integration/import-status` endpoint.
