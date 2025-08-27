# StockX API - Initial Authentication & Credential Setup

This guide explains the **one-time process** required to get and securely store the credentials needed for the automated StockX API integration.

The application includes an all-in-one helper script that makes this process simple and secure.

---

### Prerequisites

1.  **Create a StockX Application:**
    *   Log in to your StockX account and go to your developer settings page.
    *   Create a new application.
    *   During setup, you will be asked for an **Allowed Callback URI / Redirect URI**. This is where StockX will send the user after they authorize your app. You have two main options:
        *   **Local Method:** Use a simple, non-existent URL like `https://localhost/callback`. This is easy and requires no external services.
        *   **n8n Method (Recommended for automation):** Create a new workflow in n8n with a "Webhook" node. Copy the "Test URL" provided by n8n. This allows you to see the authorization code even if you are not running the setup on a local machine.
    *   Add your chosen URI to the "Allowed Callback URLs" list in your StockX app settings. **The URL must match exactly.**
    *   StockX will give you a **Client ID** and a **Client Secret**. Have these ready.
    *   You will also need your general **API Key** from the StockX developer portal.

2.  **Set Environment Variables:**
    *   Ensure your `.env` file is created (you can copy `.env.example`).
    *   Make sure `DATABASE_URL` is correctly configured to point to your database.
    *   Make sure you have set a `FIELD_ENCRYPTION_KEY`. If you need to generate one, run this in a Python terminal:
        ```python
        from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())
        ```
        Then add it to your `.env` file.

### Running the Setup Script

The script will handle everything: generating the authorization link, exchanging the code for a refresh token, and securely saving all your credentials in the database.

1.  Open a terminal or command prompt in the root directory of the SoleFlipper application.
2.  Run the following command:
    ```bash
    python scripts/setup/get_refresh_token.py
    ```
3.  The script is interactive and will guide you through the following steps:
    *   It will ask for your **Client ID** and your chosen **Callback URI**.
    *   It will then provide you with a **URL to open in your browser**.
    *   You will authorize the application in your browser.
    *   StockX will then redirect you. You need to find the **`code`** parameter from this redirect.
        *   **If using the Local Method:** The code will be in your browser's address bar, like `https://localhost/callback?code=A1b2C3d4...`
        *   **If using the n8n Method:** Go to your n8n workflow, look at the last execution, and find the `code` value in the received `query` data.
    *   **Copy only the value of the `code`** and **paste it back into the script** when prompted.
    *   Finally, the script will ask for your **Client Secret** and **API Key**.

If all steps are successful, the script will confirm that all credentials have been encrypted and saved to the database.

---

**Setup is now complete!** The SoleFlipper application is now fully configured to communicate with the StockX API.
