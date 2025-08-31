#!/usr/bin/env python3
"""
Generate secrets for SoleFlipper deployment.
Creates all necessary encryption keys and provides setup instructions.
"""

import secrets
import base64
from cryptography.fernet import Fernet
import argparse
import json
from typing import Dict, Any


def generate_fernet_key() -> str:
    """Generate a Fernet encryption key"""
    return Fernet.generate_key().decode()


def generate_jwt_secret() -> str:
    """Generate a JWT secret key"""
    return secrets.token_urlsafe(32)


def generate_session_secret() -> str:
    """Generate a session secret key"""
    return secrets.token_hex(32)


def generate_database_password() -> str:
    """Generate a secure database password"""
    # Generate 16 character password with letters, numbers, special chars
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(16))


def generate_all_secrets(environment: str = "development") -> Dict[str, Any]:
    """Generate all required secrets for an environment"""

    secrets_data = {
        # Encryption
        "FIELD_ENCRYPTION_KEY": generate_fernet_key(),
        "JWT_SECRET_KEY": generate_jwt_secret(),
        "SESSION_SECRET": generate_session_secret(),
        # Database
        "DB_PASSWORD": generate_database_password(),
        # API Configuration
        "API_SECRET_KEY": generate_jwt_secret(),
        # Environment info
        "environment": environment,
        "generated_at": "2025-08-30T15:54:00Z",
    }

    return secrets_data


def format_database_url(
    host: str = "localhost",
    port: int = 5432,
    database: str = "soleflip",
    username: str = "soleflip_user",
    password: str = None,
) -> str:
    """Format database URL"""
    if not password:
        password = "REPLACE_WITH_ACTUAL_PASSWORD"

    return f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"


def print_github_secrets_commands(secrets_data: Dict[str, Any], environment: str):
    """Print GitHub CLI commands to set secrets"""

    env_prefix = f"{environment.upper()}_" if environment != "development" else ""

    print(f"\n[GITHUB] GitHub Secrets Setup Commands for {environment.title()}")
    print("=" * 60)
    print("Copy and run these commands in your terminal:\n")

    # Database URL
    db_url = format_database_url(password=secrets_data["DB_PASSWORD"])
    print(f'gh secret set {env_prefix}DATABASE_URL --body "{db_url}"')

    # Encryption key
    print(
        f'gh secret set {env_prefix}FIELD_ENCRYPTION_KEY --body "{secrets_data["FIELD_ENCRYPTION_KEY"]}"'
    )

    # JWT secret
    print(f'gh secret set JWT_SECRET_KEY --body "{secrets_data["JWT_SECRET_KEY"]}"')

    # API URL (example)
    if environment == "production":
        api_url = "https://api.soleflip.com"
    elif environment == "staging":
        api_url = "https://staging-api.soleflip.com"
    else:
        api_url = "http://localhost:8000"

    print(f'gh secret set {env_prefix}API_URL --body "{api_url}"')

    print("\n[OPTIONAL] Additional Optional Secrets:")
    print("# External API credentials (replace with actual values)")
    print('gh secret set STOCKX_CLIENT_ID --body "your_stockx_client_id"')
    print('gh secret set STOCKX_CLIENT_SECRET --body "your_stockx_client_secret"')
    print('gh secret set STOCKX_REFRESH_TOKEN --body "your_stockx_refresh_token"')

    print("\n# Monitoring (optional)")
    print('gh secret set SENTRY_DSN --body "your_sentry_dsn"')

    print("\n# Notifications (optional)")
    print('gh secret set SLACK_WEBHOOK_URL --body "your_slack_webhook"')


def save_secrets_to_env_file(secrets_data: Dict[str, Any], filename: str = ".env.secrets"):
    """Save secrets to .env file for local development"""

    with open(filename, "w") as f:
        f.write("# Generated secrets for SoleFlipper\n")
        f.write("# DO NOT COMMIT THIS FILE TO VERSION CONTROL\n\n")

        f.write("# Database Configuration\n")
        db_url = format_database_url(password=secrets_data["DB_PASSWORD"])
        f.write(f'DATABASE_URL="{db_url}"\n\n')

        f.write("# Encryption\n")
        f.write(f'FIELD_ENCRYPTION_KEY="{secrets_data["FIELD_ENCRYPTION_KEY"]}"\n')
        f.write(f'JWT_SECRET_KEY="{secrets_data["JWT_SECRET_KEY"]}"\n\n')

        f.write("# Environment\n")
        f.write(f'ENVIRONMENT="{secrets_data["environment"]}"\n\n')

        f.write("# External APIs (replace with actual values)\n")
        f.write('# STOCKX_CLIENT_ID="your_client_id"\n')
        f.write('# STOCKX_CLIENT_SECRET="your_client_secret"\n')
        f.write('# STOCKX_REFRESH_TOKEN="your_refresh_token"\n')

    print(f"[OK] Secrets saved to {filename}")
    print(f"[WARNING] Remember to add {filename} to .gitignore!")


def main():
    parser = argparse.ArgumentParser(description="Generate secrets for SoleFlipper deployment")
    parser.add_argument(
        "--environment",
        "-e",
        choices=["development", "staging", "production"],
        default="development",
        help="Environment to generate secrets for",
    )
    parser.add_argument("--output-file", "-o", help="Output file to save secrets (optional)")
    parser.add_argument(
        "--format", "-f", choices=["env", "json", "github"], default="github", help="Output format"
    )

    args = parser.parse_args()

    print(f"[SECRETS] Generating secrets for {args.environment} environment...")

    # Generate secrets
    secrets_data = generate_all_secrets(args.environment)

    if args.format == "github":
        print_github_secrets_commands(secrets_data, args.environment)

        # Also save to .env file for local development
        if args.environment == "development":
            save_secrets_to_env_file(secrets_data)

    elif args.format == "env":
        filename = args.output_file or f".env.{args.environment}"
        save_secrets_to_env_file(secrets_data, filename)

    elif args.format == "json":
        filename = args.output_file or f"secrets_{args.environment}.json"
        with open(filename, "w") as f:
            json.dump(secrets_data, f, indent=2)
        print(f"[OK] Secrets saved to {filename}")

    print(f"\n[SECURITY] Security Notes:")
    print("1. Store these secrets securely")
    print("2. Never commit secrets to version control")
    print("3. Rotate secrets regularly")
    print("4. Use different secrets for each environment")

    print(f"\n[NEXT] Next Steps:")
    print("1. Run the GitHub CLI commands above")
    print("2. Verify secrets in GitHub repository settings")
    print("3. Test deployment workflow")
    print("4. Set up environment protection rules")


if __name__ == "__main__":
    main()
