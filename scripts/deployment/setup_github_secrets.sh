#!/bin/bash

# SoleFlipper GitHub Secrets Setup Script
# This script sets up all required GitHub secrets for CI/CD deployment

set -e

echo "=========================================="
echo "SoleFlipper GitHub Secrets Setup"
echo "=========================================="

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ GitHub CLI is not authenticated"
    echo "Please run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI is installed and authenticated"

# Get repository information
REPO_INFO=$(gh repo view --json name,owner)
REPO_NAME=$(echo $REPO_INFO | python -c "import sys, json; print(json.load(sys.stdin)['name'])")
REPO_OWNER=$(echo $REPO_INFO | python -c "import sys, json; print(json.load(sys.stdin)['owner']['login'])")

echo "📦 Repository: $REPO_OWNER/$REPO_NAME"

# Function to generate and set a secret
set_secret() {
    local secret_name=$1
    local secret_value=$2
    local environment=${3:-""}
    
    if [ -n "$environment" ]; then
        echo "Setting environment secret: $secret_name (environment: $environment)"
        gh secret set "$secret_name" --body "$secret_value" --env "$environment"
    else
        echo "Setting repository secret: $secret_name"
        gh secret set "$secret_name" --body "$secret_value"
    fi
}

# Function to generate Fernet key
generate_fernet_key() {
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
}

# Function to generate JWT secret
generate_jwt_secret() {
    python -c "import secrets; print(secrets.token_urlsafe(32))"
}

# Function to generate database password
generate_db_password() {
    python -c "import secrets; print(''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*') for _ in range(16)))"
}

echo "🔑 Generating secrets..."

# Generate common secrets
JWT_SECRET=$(generate_jwt_secret)
echo "Generated JWT_SECRET_KEY"

# Set common secrets
set_secret "JWT_SECRET_KEY" "$JWT_SECRET"

echo ""
echo "🏗️ Setting up STAGING environment secrets..."

# Generate staging secrets
STAGING_ENCRYPTION_KEY=$(generate_fernet_key)
STAGING_DB_PASSWORD=$(generate_db_password)
STAGING_DB_URL="postgresql+asyncpg://soleflip_user:$STAGING_DB_PASSWORD@staging-db:5432/soleflip"

# Create staging environment if it doesn't exist
echo "Creating staging environment..."
gh api repos/$REPO_OWNER/$REPO_NAME/environments/staging -X PUT --silent 2>/dev/null || true

# Set staging secrets
set_secret "DATABASE_URL" "$STAGING_DB_URL" "staging"
set_secret "FIELD_ENCRYPTION_KEY" "$STAGING_ENCRYPTION_KEY" "staging"
set_secret "API_URL" "https://staging-api.soleflip.com" "staging"

echo ""
echo "🚀 Setting up PRODUCTION environment secrets..."

# Generate production secrets
PRODUCTION_ENCRYPTION_KEY=$(generate_fernet_key)
PRODUCTION_DB_PASSWORD=$(generate_db_password)
PRODUCTION_DB_URL="postgresql+asyncpg://soleflip_user:$PRODUCTION_DB_PASSWORD@prod-db:5432/soleflip"

# Create production environment if it doesn't exist
echo "Creating production environment..."
gh api repos/$REPO_OWNER/$REPO_NAME/environments/production -X PUT --silent 2>/dev/null || true

# Set production secrets
set_secret "DATABASE_URL" "$PRODUCTION_DB_URL" "production"
set_secret "FIELD_ENCRYPTION_KEY" "$PRODUCTION_ENCRYPTION_KEY" "production"
set_secret "API_URL" "https://api.soleflip.com" "production"

echo ""
echo "📋 Summary of set secrets:"
echo "========================="
echo "Repository secrets:"
echo "- JWT_SECRET_KEY"
echo ""
echo "Staging environment:"
echo "- DATABASE_URL"
echo "- FIELD_ENCRYPTION_KEY" 
echo "- API_URL"
echo ""
echo "Production environment:"
echo "- DATABASE_URL"
echo "- FIELD_ENCRYPTION_KEY"
echo "- API_URL"

echo ""
echo "⚠️  Manual setup required:"
echo "========================="
echo "1. Set up actual database servers for staging and production"
echo "2. Update database URLs with real server addresses"
echo "3. Add external API credentials:"
echo "   - STOCKX_CLIENT_ID"
echo "   - STOCKX_CLIENT_SECRET" 
echo "   - STOCKX_REFRESH_TOKEN"
echo "4. Set up environment protection rules:"
echo "   - Go to Settings → Environments"
echo "   - Add required reviewers for production"
echo "   - Configure deployment branches"

echo ""
echo "🔍 To verify secrets:"
echo "gh secret list"
echo "gh secret list --env staging"
echo "gh secret list --env production"

echo ""
echo "✅ GitHub Secrets setup complete!"
echo ""
echo "📖 Next steps:"
echo "1. Review and update database URLs with real server addresses"
echo "2. Add external API credentials manually"
echo "3. Test deployment with: gh workflow run deploy.yml -f environment=staging"
echo "4. Set up monitoring and alerts"

echo ""
echo "🔐 Security reminders:"
echo "- Rotate these secrets regularly"
echo "- Never share or commit secrets"
echo "- Monitor secret usage in GitHub Actions logs"
echo "- Set up alerts for failed deployments"