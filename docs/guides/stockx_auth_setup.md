# StockX API - Initial Authentication & Credential Setup

This guide explains the **one-time process** required to get and securely store the credentials needed for the automated StockX API integration.

The application includes an all-in-one helper script that makes this process simple and secure.

---

### Prerequisites

1.  **Create a StockX Application:**
    *   Log in to your StockX account and go to your developer settings page.
    *   Create a new application.
    *   During setup, you will be asked for a **Callback URI / Redirect URI**. Set this to `https://localhost/callback`. You will need to provide this exact URL to the script.
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
    *   It will ask for your **Client ID** and **Callback URI**.
    *   It will then provide you with a **URL to open in your browser**.
    *   You will authorize the application in your browser.
    *   You will then **copy the full URL** you are redirected to and **paste it back into the script**.
    *   Finally, it will ask for your **Client Secret** and **API Key**.

If all steps are successful, the script will confirm that all credentials have been encrypted and saved to the database.

---

**Setup is now complete!** The SoleFlipper application is now fully configured to communicate with the StockX API.
