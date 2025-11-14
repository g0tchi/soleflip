#!/usr/bin/env python3
"""
Check GitHub repository secrets configuration.
Verifies that all required secrets are present for deployment.
"""

import json
import subprocess
import sys
from typing import Any, Dict, List, Set


class SecretChecker:
    """Check GitHub repository secrets configuration"""

    def __init__(self):
        self.required_secrets = {
            "production": {
                "PRODUCTION_DATABASE_URL",
                "PRODUCTION_ENCRYPTION_KEY",
                "PRODUCTION_API_URL",
                "JWT_SECRET_KEY",
            },
            "staging": {
                "STAGING_DATABASE_URL",
                "STAGING_ENCRYPTION_KEY",
                "STAGING_API_URL",
                "JWT_SECRET_KEY",
            },
            "common": {"JWT_SECRET_KEY", "GITHUB_TOKEN"},  # Automatically provided
            "optional": {
                "STOCKX_CLIENT_ID",
                "STOCKX_CLIENT_SECRET",
                "STOCKX_REFRESH_TOKEN",
                "SENTRY_DSN",
                "SLACK_WEBHOOK_URL",
                "DATADOG_API_KEY",
            },
        }

    def run_gh_command(self, command: List[str]) -> Dict[str, Any]:
        """Run GitHub CLI command and return JSON result"""
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)

            if result.stdout.strip():
                return json.loads(result.stdout)
            return {}

        except subprocess.CalledProcessError as e:
            print(f"❌ GitHub CLI error: {e.stderr}")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            return {}

    def get_repository_secrets(self) -> Set[str]:
        """Get list of configured repository secrets"""
        secrets_data = self.run_gh_command(["gh", "secret", "list", "--json", "name"])

        if isinstance(secrets_data, list):
            return {secret["name"] for secret in secrets_data}
        return set()

    def get_environment_secrets(self, environment: str) -> Set[str]:
        """Get secrets for specific environment"""
        try:
            secrets_data = self.run_gh_command(
                ["gh", "secret", "list", "--env", environment, "--json", "name"]
            )

            if isinstance(secrets_data, list):
                return {secret["name"] for secret in secrets_data}
        except Exception:
            # Environment might not exist yet
            pass
        return set()

    def check_repository_info(self):
        """Check basic repository information"""
        print("🔍 Repository Information")
        print("=" * 40)

        repo_info = self.run_gh_command(
            ["gh", "repo", "view", "--json", "name,owner,defaultBranch,visibility"]
        )

        if repo_info:
            print(
                f"Repository: {repo_info.get('owner', {}).get('login', 'N/A')}/{repo_info.get('name', 'N/A')}"
            )
            print(f"Default Branch: {repo_info.get('defaultBranch', 'N/A')}")
            print(f"Visibility: {repo_info.get('visibility', 'N/A')}")
        else:
            print("❌ Could not retrieve repository information")
            print("Make sure you're in the correct directory and GitHub CLI is authenticated")
            return False

        return True

    def check_secrets_status(self):
        """Check status of all required secrets"""
        print("\n🔐 Secrets Configuration Status")
        print("=" * 40)

        # Get configured secrets
        repo_secrets = self.get_repository_secrets()
        staging_secrets = self.get_environment_secrets("staging")
        production_secrets = self.get_environment_secrets("production")

        all_configured = repo_secrets | staging_secrets | production_secrets

        print(f"📊 Total configured secrets: {len(all_configured)}")

        if repo_secrets:
            print(f"Repository secrets: {len(repo_secrets)}")
        if staging_secrets:
            print(f"Staging secrets: {len(staging_secrets)}")
        if production_secrets:
            print(f"Production secrets: {len(production_secrets)}")

        # Check each environment
        self._check_environment_secrets("staging", staging_secrets | repo_secrets)
        self._check_environment_secrets("production", production_secrets | repo_secrets)
        self._check_optional_secrets(all_configured)

    def _check_environment_secrets(self, environment: str, configured_secrets: Set[str]):
        """Check secrets for specific environment"""
        print(f"\n🏗️ {environment.title()} Environment")
        print("-" * 30)

        required = self.required_secrets.get(environment, set()) | self.required_secrets["common"]

        missing_secrets = required - configured_secrets
        present_secrets = required & configured_secrets

        if present_secrets:
            print("✅ Configured secrets:")
            for secret in sorted(present_secrets):
                print(f"   • {secret}")

        if missing_secrets:
            print("❌ Missing secrets:")
            for secret in sorted(missing_secrets):
                print(f"   • {secret}")
        else:
            print(f"🎉 All required secrets configured for {environment}!")

    def _check_optional_secrets(self, configured_secrets: Set[str]):
        """Check optional secrets"""
        print("\n🔧 Optional Secrets")
        print("-" * 20)

        optional_configured = self.required_secrets["optional"] & configured_secrets
        optional_missing = self.required_secrets["optional"] - configured_secrets

        if optional_configured:
            print("✅ Configured optional secrets:")
            for secret in sorted(optional_configured):
                print(f"   • {secret}")

        if optional_missing:
            print("⚠️ Optional secrets not configured:")
            for secret in sorted(optional_missing):
                print(f"   • {secret}")

    def check_environments(self):
        """Check GitHub environments configuration"""
        print("\n🌍 GitHub Environments")
        print("=" * 25)

        try:
            # This might not work with all GitHub CLI versions
            env_result = self.run_gh_command(["gh", "api", "repos/{owner}/{repo}/environments"])

            if env_result and "environments" in env_result:
                environments = [env["name"] for env in env_result["environments"]]
                print(f"Configured environments: {', '.join(environments)}")

                for env in ["staging", "production"]:
                    if env in environments:
                        print(f"✅ {env} environment exists")
                    else:
                        print(f"❌ {env} environment missing")
            else:
                print("⚠️ Could not check environments (this is normal for some repos)")

        except Exception:
            print("⚠️ Could not check environments configuration")

    def provide_setup_instructions(self):
        """Provide next steps for setup"""
        print("\n📋 Next Steps")
        print("=" * 15)
        print("1. Run the secret generation script:")
        print("   python scripts/deployment/generate_secrets.py --environment staging")
        print("   python scripts/deployment/generate_secrets.py --environment production")
        print("")
        print("2. Set up GitHub environments:")
        print("   Go to Settings → Environments in your GitHub repository")
        print("   Create 'staging' and 'production' environments")
        print("")
        print("3. Configure environment protection rules:")
        print("   - Require reviewers for production")
        print("   - Set deployment branches")
        print("")
        print("4. Test the deployment workflow:")
        print("   gh workflow run deploy.yml -f environment=staging")
        print("")
        print("📖 Full guide: docs/DEPLOYMENT_SECRETS_SETUP.md")


def main():
    """Main function"""
    print("🔍 SoleFlipper GitHub Secrets Checker")
    print("=" * 50)

    # Check if GitHub CLI is available
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ GitHub CLI (gh) not found or not authenticated")
        print("Please install GitHub CLI and authenticate with: gh auth login")
        sys.exit(1)

    checker = SecretChecker()

    # Run all checks
    if not checker.check_repository_info():
        sys.exit(1)

    checker.check_secrets_status()
    checker.check_environments()
    checker.provide_setup_instructions()

    print("\n✨ Check complete!")


if __name__ == "__main__":
    main()
