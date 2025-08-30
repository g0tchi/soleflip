# GitHub Secrets Configuration Guide

## Required Secrets for CI/CD Pipeline

This document outlines all GitHub Secrets that need to be configured for the SoleFlipper deployment pipeline.

## 🔑 Production Environment Secrets

### Database Configuration
- **`PRODUCTION_DATABASE_URL`**: PostgreSQL connection string for production
  ```
  postgresql+asyncpg://username:password@host:port/database_name
  ```

- **`PRODUCTION_ENCRYPTION_KEY`**: Fernet encryption key for sensitive data
  ```bash
  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

### API Configuration  
- **`PRODUCTION_API_URL`**: Base URL for production API
  ```
  https://api.soleflip.com
  ```

## 🧪 Staging Environment Secrets

### Database Configuration
- **`STAGING_DATABASE_URL`**: PostgreSQL connection string for staging
  ```
  postgresql+asyncpg://username:password@host:port/database_name
  ```

- **`STAGING_ENCRYPTION_KEY`**: Fernet encryption key for staging
  ```bash
  # Generate separate key for staging
  ```

### API Configuration
- **`STAGING_API_URL`**: Base URL for staging API
  ```
  https://staging-api.soleflip.com
  ```

## 🔐 Authentication & Security

### JWT Configuration
- **`JWT_SECRET_KEY`**: Secret key for JWT token signing
  ```bash
  # Generate with: openssl rand -hex 32
  ```

### External API Keys
- **`STOCKX_CLIENT_ID`**: StockX API client ID
- **`STOCKX_CLIENT_SECRET`**: StockX API client secret  
- **`STOCKX_REFRESH_TOKEN`**: StockX API refresh token

## 🚀 Deployment Configuration

### Container Registry
- **`GHCR_TOKEN`**: GitHub Container Registry token (automatically provided as GITHUB_TOKEN)

### Monitoring & Observability
- **`SENTRY_DSN`** (Optional): Sentry error tracking DSN
- **`DATADOG_API_KEY`** (Optional): DataDog monitoring API key

## 📧 Notifications

### Slack Integration (Optional)
- **`SLACK_WEBHOOK_URL`**: Webhook URL for deployment notifications
- **`SLACK_CHANNEL`**: Channel for notifications

### Email Notifications (Optional)
- **`SMTP_HOST`**: SMTP server host
- **`SMTP_USER`**: SMTP username
- **`SMTP_PASS`**: SMTP password

## 🛠️ Setup Instructions

### 1. Navigate to Repository Settings
```
https://github.com/YOUR_USERNAME/soleflip/settings/secrets/actions
```

### 2. Add Required Secrets
Click "New repository secret" and add each secret listed above.

### 3. Environment-Specific Secrets
For staging and production environments:
1. Go to Settings → Environments
2. Create "staging" and "production" environments
3. Add environment-specific secrets

### 4. Verify Configuration
Run the deployment workflow to verify all secrets are configured correctly:
```bash
# Trigger manual deployment to staging
gh workflow run deploy.yml -f environment=staging
```

## 🔍 Security Best Practices

### Secret Rotation
- Rotate database passwords quarterly
- Rotate encryption keys annually
- Rotate API keys when compromise is suspected

### Access Control
- Limit secret access to deployment workflows only
- Use environment protection rules for production
- Enable required reviewers for production deployments

### Monitoring
- Monitor secret usage in GitHub Actions logs
- Set up alerts for failed authentications
- Regular security audits of active secrets

## 📋 Checklist

- [ ] Production database configured
- [ ] Staging database configured
- [ ] Encryption keys generated and stored
- [ ] JWT secret configured
- [ ] API URLs set
- [ ] External API credentials configured
- [ ] Container registry access verified
- [ ] Monitoring tools configured (optional)
- [ ] Notification channels set up (optional)
- [ ] Test deployment to staging successful
- [ ] Production deployment tested

## 🆘 Troubleshooting

### Common Issues
1. **Database Connection Failed**: Verify DATABASE_URL format and credentials
2. **Encryption Error**: Ensure FIELD_ENCRYPTION_KEY is valid Fernet key
3. **JWT Token Invalid**: Check JWT_SECRET_KEY is properly set
4. **API Authentication Failed**: Verify external API credentials

### Getting Help
- Check GitHub Actions logs for specific error messages
- Verify secret names match exactly (case-sensitive)
- Test credentials manually before adding to GitHub

---

**Note**: Never commit actual secret values to version control. Always use GitHub Secrets or environment variables for sensitive data.