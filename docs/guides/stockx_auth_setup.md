# StockX API - Initial Authentication Setup Guide

This guide explains the **one-time manual process** required to get the initial credentials needed for the automated StockX API integration.

The StockX API uses OAuth2, which requires you to grant permission to your application to access your account data. This process generates a long-lived **Refresh Token** that the application can then use to get temporary access tokens automatically.

You only need to do this once.

---

### Step 1: Create a StockX Application

1.  Log in to your StockX account.
2.  Go to your developer settings page (this is usually under your account settings or at a specific developer portal URL provided by StockX).
3.  Create a new application. You will be asked for:
    *   **Application Name:** e.g., "SoleFlipper Integration"
    *   **Description:** A brief description.
    *   **Callback URI / Redirect URI:** This is a crucial field. For the purpose of this setup, you can set it to a simple, non-existent URL like `https://localhost/callback`. You will need this exact URL later.
4.  After creating the app, StockX will provide you with a **Client ID** and a **Client Secret**. Copy these two values and keep them safe.

### Step 2: Generate an Authorization Code

Now you need to grant your new application access to your account.

1.  Construct the following URL in a text editor. Replace `{YOUR_CLIENT_ID}` and `{YOUR_CALLBACK_URI}` with the values from Step 1.

    ```
    https://accounts.stockx.com/authorize?response_type=code&client_id={YOUR_CLIENT_ID}&redirect_uri={YOUR_CALLBACK_URI}&scope=offline_access%20openid&audience=gateway.stockx.com&state=soleflipper-setup
    ```

    **Example:**
    ```
    https://accounts.stockx.com/authorize?response_type=code&client_id=AbcDEfg12345&redirect_uri=https://localhost/callback&scope=offline_access%20openid&audience=gateway.stockx.com&state=soleflipper-setup
    ```

2.  Open the complete URL in your web browser.
3.  You will be prompted to log in to StockX (if you aren't already) and then asked to authorize your application. Click **"Allow"** or **"Authorize"**.
4.  After authorizing, your browser will be redirected to the callback URI you specified (e.g., `https://localhost/callback`). The page will likely show an error because it doesn't exist, **but this is expected**.
5.  Look at the URL in your browser's address bar. It will look something like this:

    ```
    https://localhost/callback?code=A1b2C3d4E5f6G7h8&state=soleflipper-setup
    ```

6.  Copy the value of the `code` parameter. In the example above, it's `A1b2C3d4E5f6G7h8`. This is your temporary **Authorization Code**. It is only valid for a short time.

### Step 3: Exchange Authorization Code for a Refresh Token

Now you will use the helper script provided in this application to exchange the temporary code for your permanent Refresh Token.

1.  Open a terminal or command prompt in the root directory of the SoleFlipper application.
2.  Run the following command:
    ```bash
    python scripts/setup/get_refresh_token.py
    ```
3.  The script will prompt you to enter the following one by one:
    *   Your **Client ID** (from Step 1)
    *   Your **Client Secret** (from Step 1)
    *   Your **Authorization Code** (from Step 2)
    *   Your **Callback URI** (the same one you used in the URL, e.g., `https://localhost/callback`)

4.  The script will make a request to the StockX servers. If successful, it will print your **Refresh Token**.

    ```
    SUCCESS!
    Your Refresh Token is: gI_Abc123...

    Please store this value securely.
    ```

5.  Copy this Refresh Token.

### Step 4: Store Credentials in the Database

You now have all the necessary credentials. The final step is to save them securely in the SoleFlipper database.

1.  **Client ID, Client Secret, and Refresh Token** need to be stored in the `core.system_config` table. You can use a database tool (like DBeaver, pgAdmin, etc.) to insert them.
2.  **API Key:** Your general StockX API Key (provided separately by StockX in your developer portal) also needs to be stored.
3.  **Encryption Key:** Remember to set the `FIELD_ENCRYPTION_KEY` environment variable before running the main application.

**You need to add these four rows to the `core.system_config` table:**

| key                    | value_encrypted                               | description                          |
| ---------------------- | --------------------------------------------- | ------------------------------------ |
| `stockx_client_id`     | *Your Client ID from Step 1*                  | StockX OAuth Client ID               |
| `stockx_client_secret` | *Your Client Secret from Step 1*              | StockX OAuth Client Secret           |
| `stockx_refresh_token` | *Your Refresh Token from Step 3*              | StockX OAuth Refresh Token           |
| `stockx_api_key`       | *Your general API Key from StockX developer portal* | StockX general API Key (for x-api-key header) |

**Important:** The application's encryption is handled by the model layer. When inserting these values manually via SQL, you would typically need to encrypt them first. The helper script is designed to simplify this, but for manual entry, a dedicated admin script is the most secure approach. For now, direct insertion is the simplest path if you have direct database access.

---

**Setup is now complete!** The SoleFlipper application will now be able to automatically refresh its access token and fetch data from the StockX API on your behalf.
