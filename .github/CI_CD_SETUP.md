# CI/CD Pipeline Setup Guide

This guide explains how to set up and use the GitHub Actions CI/CD pipeline for SoleFlipper.

## Overview

The pipeline consists of 4 main workflows:

1. **Main CI/CD Pipeline** (`ci-cd.yml`) - Runs on every push and PR
2. **Dependency Review** (`dependency-review.yml`) - Reviews dependencies in PRs
3. **Nightly Security Scan** (`nightly-security-scan.yml`) - Daily security checks
4. **Dependabot** (`dependabot.yml`) - Automated dependency updates

## Pipeline Stages

### 1. Code Quality Checks
- **Black** - Code formatting
- **isort** - Import sorting
- **Ruff** - Fast Python linter
- **MyPy** - Static type checking

All checks run with `continue-on-error: true` to allow the pipeline to complete and show all issues.

### 2. Security Scanning
- **pip-audit** - CVE scanning for Python packages
- **Bandit** - Python security linting
- **Trivy** - Comprehensive vulnerability scanner
- Results uploaded to GitHub Security tab

### 3. Testing
- **Unit Tests** - Fast, isolated tests
- **Integration Tests** - Database and service integration tests
- **Coverage** - Generates coverage reports (current: 37%, target: 80%)
- Uses PostgreSQL and Redis services for integration tests

### 4. Docker Build
- Multi-stage Docker build
- Pushed to GitHub Container Registry (ghcr.io)
- Tagged with branch name, SHA, and version
- Scanned for vulnerabilities with Trivy

### 5. Deployment
- **Staging** - Auto-deploy from `develop` branch
- **Production** - Auto-deploy from `master` branch
- Includes health checks and rollback capability

## Required GitHub Secrets

### Essential Secrets
```bash
FIELD_ENCRYPTION_KEY    # Fernet encryption key for sensitive data
```

### Optional Secrets (for full functionality)
```bash
# Staging Environment
STAGING_HOST            # Staging server hostname
STAGING_USER            # SSH username for staging
STAGING_SSH_KEY         # SSH private key for staging

# Production Environment
PRODUCTION_HOST         # Production server hostname
PRODUCTION_USER         # SSH username for production
PRODUCTION_SSH_KEY      # SSH private key for production

# Notifications
SLACK_WEBHOOK_URL       # Slack webhook for notifications

# Coverage (optional)
CODECOV_TOKEN          # Codecov.io token for coverage reporting
```

## Setting Up Secrets

### 1. Navigate to Repository Settings
```
GitHub Repository → Settings → Secrets and variables → Actions
```

### 2. Add Required Secrets
Click "New repository secret" and add each secret:

#### Generate Encryption Key
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### Generate SSH Key for Deployments
```bash
ssh-keygen -t ed25519 -C "github-actions@soleflip" -f github-actions-key
# Add public key to server: ~/.ssh/authorized_keys
# Add private key to GitHub Secrets: STAGING_SSH_KEY / PRODUCTION_SSH_KEY
```

### 3. Set Up Environments

#### Create Staging Environment
1. Go to Settings → Environments → New environment
2. Name: `staging`
3. Add environment-specific secrets if needed
4. Optional: Add required reviewers

#### Create Production Environment
1. Go to Settings → Environments → New environment
2. Name: `production`
3. **Important:** Add required reviewers for production deployments
4. Set deployment branch rule to `master` only

## Workflow Triggers

### Main CI/CD Pipeline
- **Push** to `master`, `develop`, or `ai` branches
- **Pull Request** to `master` or `develop`

### Dependency Review
- **Pull Request** to `master` or `develop`

### Nightly Security Scan
- **Schedule**: Every night at 2 AM UTC
- **Manual**: Can be triggered via "Actions" tab

### Dependabot
- **Schedule**: Weekly on Mondays at 9 AM (Europe/Berlin)
- Creates PRs for dependency updates

## Using the Pipeline

### Running Tests Locally
Before pushing, ensure tests pass locally:
```bash
# Run all quality checks
make check

# Run tests
make test

# Run security checks (requires pip-audit, bandit)
pip install pip-audit bandit
make security-check
```

### Viewing Pipeline Results

#### In Pull Requests
- Check status at the bottom of the PR
- Click "Details" to see full logs
- View security scan results in "Security" tab

#### In Actions Tab
1. Go to "Actions" tab in repository
2. Select workflow run
3. View job logs and artifacts

### Artifacts

The pipeline generates several artifacts:

1. **Coverage Reports** - HTML coverage report
2. **Security Reports** - JSON reports from security scans
3. Retained for 30 days (configurable)

Download artifacts from the Actions tab → Select run → Scroll to "Artifacts"

## Branch Strategy

### Recommended Workflow
```
feature/my-feature → develop → master
```

1. **Feature Branches** - Development work
2. **develop** - Integration branch, auto-deploys to staging
3. **master** - Production branch, auto-deploys to production

### Example Workflow
```bash
# Create feature branch
git checkout -b feature/new-pricing-algorithm

# Make changes and commit
git add .
git commit -m "feat: Implement dynamic pricing algorithm"

# Push and create PR to develop
git push origin feature/new-pricing-algorithm
# Create PR on GitHub: feature/new-pricing-algorithm → develop

# After PR approval and merge to develop
# Pipeline automatically deploys to staging

# After staging verification, create PR
# develop → master (requires approval)

# After merge to master
# Pipeline automatically deploys to production
```

## Deployment Process

### Staging Deployment
1. Merge PR to `develop` branch
2. Pipeline automatically builds and tests
3. If all checks pass, deploys to staging
4. Runs health check
5. Sends Slack notification

### Production Deployment
1. Create PR from `develop` to `master`
2. Require code review and approval
3. Merge PR
4. Pipeline automatically builds and tests
5. If all checks pass, deploys to production
6. Runs health check
7. Sends Slack notification
8. Creates GitHub deployment record

### Manual Deployment
If automatic deployment fails, deploy manually:
```bash
ssh user@production-host
cd /opt/soleflip
docker-compose pull
docker-compose up -d --no-deps --build api
docker-compose exec -T api alembic upgrade head
docker-compose restart api
```

## Monitoring & Notifications

### Slack Notifications
Configure Slack webhook to receive:
- Deployment success/failure
- Security scan alerts
- Test failures

### GitHub Security Tab
- View security vulnerabilities
- Review Dependabot alerts
- Check Trivy scan results

## Troubleshooting

### Tests Failing
```bash
# Check test logs in Actions tab
# Run locally with same environment:
ENVIRONMENT=testing pytest tests/
```

### Coverage Below Threshold
```bash
# Current: 37%, Target: 80%
# Temporarily lower threshold in pyproject.toml:
# --cov-fail-under=37

# Or increase test coverage:
pytest --cov=domains --cov=shared --cov-report=html
open htmlcov/index.html
```

### Docker Build Failing
```bash
# Test build locally:
docker build -t soleflip:test .

# Check Dockerfile syntax
docker build --no-cache -t soleflip:test .
```

### Deployment Failing
```bash
# Check SSH connectivity:
ssh -i ~/.ssh/github-actions-key user@host

# Check server logs:
ssh user@host "cd /opt/soleflip && docker-compose logs -f api"

# Verify health endpoint:
curl -f https://soleflip.com/health
```

### Security Scan Failures
```bash
# Run locally:
pip install pip-audit bandit
pip-audit
bandit -r domains/ shared/

# Fix vulnerabilities:
pip install --upgrade <package>
```

## Best Practices

### 1. Commit Messages
Follow conventional commits:
```
feat: Add new pricing algorithm
fix: Resolve inventory count bug
docs: Update API documentation
chore: Update dependencies
test: Add unit tests for pricing service
```

### 2. Pull Requests
- Keep PRs small and focused
- Write descriptive PR titles
- Fill out PR template
- Link related issues
- Request reviews

### 3. Testing
- Write tests for new features
- Maintain or increase coverage
- Run tests locally before pushing
- Fix failing tests immediately

### 4. Security
- Review Dependabot PRs weekly
- Check security scan results
- Update dependencies regularly
- Never commit secrets

### 5. Deployment
- Test on staging before production
- Deploy during low-traffic hours
- Monitor logs after deployment
- Have rollback plan ready

## Quality Gates

The pipeline enforces these quality gates:

| Stage | Gate | Action if Failed |
|-------|------|------------------|
| Quality | Black/isort/Ruff | Continue (warning) |
| Security | Critical CVEs | Continue (warning) |
| Tests | Unit tests pass | **Block deployment** |
| Coverage | 37% minimum | Continue (warning) |
| Build | Docker build | **Block deployment** |

**Note:** Most checks use `continue-on-error: true` to show all issues without blocking. Adjust as needed for your team's requirements.

## Customization

### Adjust Coverage Threshold
Edit `.github/workflows/ci-cd.yml`:
```yaml
- name: Generate coverage report
  run: |
    coverage report --fail-under=60  # Change from 37 to 60
```

### Change Deployment Strategy
Edit deploy jobs in `ci-cd.yml`:
```yaml
deploy-production:
  # Add manual approval:
  environment:
    name: production
    # This requires manual approval in GitHub
```

### Add More Security Scans
Add to security job:
```yaml
- name: Run SAST with Semgrep
  uses: returntocorp/semgrep-action@v1
```

## Support

For issues or questions:
1. Check workflow logs in Actions tab
2. Review this documentation
3. Check GitHub Actions documentation
4. Create an issue in the repository

## Next Steps

1. ✅ Set up required secrets
2. ✅ Create staging and production environments
3. ✅ Configure Slack webhook (optional)
4. ✅ Set up Codecov (optional)
5. ✅ Create first PR to test pipeline
6. ✅ Monitor and adjust quality gates
7. ✅ Train team on workflow usage
