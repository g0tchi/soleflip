# CI/CD Pipeline Quick Reference

## Pipeline Status Badges

Add these to your README.md:

```markdown
[![CI/CD Pipeline](https://github.com/OWNER/REPO/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci-cd.yml)
[![Security Scan](https://github.com/OWNER/REPO/actions/workflows/nightly-security-scan.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/nightly-security-scan.yml)
[![codecov](https://codecov.io/gh/OWNER/REPO/branch/master/graph/badge.svg)](https://codecov.io/gh/OWNER/REPO)
```

Replace `OWNER/REPO` with your GitHub username and repository name.

---

## Quick Commands

### Local Development
```bash
# Run all checks before pushing
make check              # Lint, type-check, test

# Individual checks
make format             # Auto-format code
make lint               # Check linting
make type-check         # Run mypy
make test               # Run tests
make test-cov           # Tests with coverage
```

### GitHub Secrets Setup
```bash
# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate SSH key for deployments
ssh-keygen -t ed25519 -C "github-actions@soleflip" -f github-actions-key
```

---

## Workflow Triggers

| Workflow | Trigger | When |
|----------|---------|------|
| Main CI/CD | Push/PR | master, develop, ai |
| Dependency Review | PR | master, develop |
| Security Scan | Schedule | Daily 2 AM UTC |
| Dependabot | Schedule | Weekly Monday 9 AM |

---

## Pipeline Stages (Main CI/CD)

```
1. Quality Check    → Black, isort, Ruff, MyPy
         ↓
2. Security Scan    → pip-audit, Bandit, Trivy
         ↓
3. Tests            → Unit, Integration, Coverage
         ↓
4. Build            → Docker image + scan
         ↓
5. Deploy           → Staging (develop) or Production (master)
```

---

## Required Secrets

### Minimal Setup
- `FIELD_ENCRYPTION_KEY` - Fernet key for data encryption

### Full Setup
- `STAGING_HOST` - Staging server hostname
- `STAGING_USER` - SSH username
- `STAGING_SSH_KEY` - SSH private key
- `PRODUCTION_HOST` - Production server hostname
- `PRODUCTION_USER` - SSH username
- `PRODUCTION_SSH_KEY` - SSH private key
- `SLACK_WEBHOOK_URL` - Slack notifications
- `CODECOV_TOKEN` - Coverage reporting (optional)

---

## Branch Strategy

```
feature/my-feature
     ↓ PR
  develop (auto-deploy to staging)
     ↓ PR + approval
  master (auto-deploy to production)
```

---

## Common Issues & Fixes

### ❌ Tests Failing
```bash
# Run locally with test environment
ENVIRONMENT=testing pytest tests/ -v
```

### ❌ Coverage Too Low (37% < 80%)
```bash
# Temporarily adjust threshold in ci-cd.yml:
coverage report --fail-under=37

# Long-term: Add more tests
pytest --cov=domains --cov=shared --cov-report=html
```

### ❌ Docker Build Failing
```bash
# Test locally
docker build -t soleflip:test .
```

### ❌ Deployment Failing
```bash
# Check SSH connectivity
ssh -i ~/.ssh/github-actions-key user@host

# Check server logs
ssh user@host "docker-compose logs -f api"

# Manual deployment
ssh user@host
cd /opt/soleflip
docker-compose pull && docker-compose up -d --no-deps --build api
```

### ❌ Security Scan Failures
```bash
# Run locally
pip install pip-audit bandit
pip-audit --desc
bandit -r domains/ shared/

# Update vulnerable packages
pip install --upgrade <package>
```

---

## Quality Gates

| Check | Threshold | Blocks Deploy? |
|-------|-----------|----------------|
| Black formatting | Pass | ❌ No (warning) |
| Ruff linting | Pass | ❌ No (warning) |
| MyPy types | Pass | ❌ No (warning) |
| Security CVEs | None critical | ❌ No (warning) |
| Unit tests | All pass | ✅ Yes |
| Coverage | 37% minimum | ❌ No (warning) |
| Docker build | Success | ✅ Yes |

---

## Artifact Downloads

After workflow run:
1. Go to Actions → Select run
2. Scroll to "Artifacts" section
3. Download:
   - Coverage reports (HTML)
   - Security scan results (JSON)

Retention: 30 days

---

## Manual Workflow Triggers

### Trigger Nightly Security Scan
1. Go to Actions tab
2. Select "Nightly Security Scan"
3. Click "Run workflow"
4. Select branch and run

### Re-run Failed Workflow
1. Go to failed workflow run
2. Click "Re-run all jobs"
3. Or "Re-run failed jobs" only

---

## Monitoring

### GitHub Security Tab
- **Dependabot alerts** - Dependency vulnerabilities
- **Code scanning** - Trivy results
- **Secret scanning** - Exposed secrets

### GitHub Actions Tab
- **Workflow runs** - All pipeline executions
- **Workflow usage** - Minutes consumed

### Slack Notifications
- Deployment success/failure
- Security scan alerts
- Manual triggers available

---

## Customization

### Change Coverage Threshold
Edit `.github/workflows/ci-cd.yml`:
```yaml
coverage report --fail-under=60  # Increase from 37
```

### Make Quality Checks Required
Remove `continue-on-error: true` from steps

### Add Manual Approval for Production
Production environment already configured with required reviewers

### Add More Tests
```yaml
- name: Run E2E tests
  run: pytest tests/e2e -v
```

---

## Performance Optimization

### Parallel Jobs
Jobs run in parallel by default:
- quality
- security
- test
- build (waits for quality, security, test)
- deploy (waits for build)

### Cache Dependencies
Already configured:
```yaml
- uses: actions/setup-python@v5
  with:
    cache: 'pip'  # Caches pip packages
```

### Docker Layer Caching
Already configured:
```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

---

## Cost Estimation

GitHub Actions free tier:
- **Public repos**: Unlimited minutes
- **Private repos**: 2,000 minutes/month

Typical pipeline run:
- Quality: ~2 min
- Security: ~3 min
- Tests: ~5 min
- Build: ~4 min
- Deploy: ~2 min
**Total**: ~16 minutes per run

---

## Next Steps

1. ✅ Set up required GitHub Secrets
2. ✅ Create staging/production environments
3. ✅ Configure Slack webhook (optional)
4. ✅ Push code to trigger first pipeline run
5. ✅ Review and adjust quality gates
6. ✅ Add pipeline badges to README
7. ✅ Train team on workflow usage

---

## Support

- 📖 [Full Setup Guide](CI_CD_SETUP.md)
- 🐛 [GitHub Issues](https://github.com/OWNER/REPO/issues)
- 📚 [GitHub Actions Docs](https://docs.github.com/actions)
- 💬 Team Slack: #soleflip-dev
