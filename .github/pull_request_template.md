## Description
<!-- Provide a brief description of the changes in this PR -->


## Type of Change
<!-- Mark the relevant option with an 'x' -->

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] ♻️ Code refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] ✅ Test update
- [ ] 🔧 Configuration/build change

## Related Issues
<!-- Link to related issues using #issue_number -->

Closes #
Related to #

## Changes Made
<!-- List the main changes in this PR -->

-
-
-

## Testing
<!-- Describe the tests you ran and how to reproduce them -->

### Test Coverage
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Coverage maintained or improved (current: 37%, target: 80%)

### Manual Testing
<!-- Describe manual testing performed -->

```bash
# Commands used for testing
make test
# etc.
```

**Test Environment:**
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.11.6]
- Database: [e.g., PostgreSQL 15]

## Code Quality Checklist
<!-- Check all that apply -->

- [ ] Code follows the project's style guidelines (Black, isort, Ruff)
- [ ] Type hints added/updated (MyPy passes)
- [ ] No linting errors (`make lint` passes)
- [ ] All tests pass (`make test` passes)
- [ ] Documentation updated (if applicable)
- [ ] CLAUDE.md updated (if new commands/patterns added)

## Security Checklist
<!-- For security-related changes -->

- [ ] No secrets committed
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Input validation implemented
- [ ] Authentication/authorization checked
- [ ] Sensitive data encrypted (using EncryptedFieldMixin)

## Database Changes
<!-- For changes affecting the database -->

- [ ] Migration created (`make db-migrate`)
- [ ] Migration tested (up and down)
- [ ] No data loss on migration
- [ ] Indexes added where appropriate
- [ ] Backward compatible

**Migration file:** `migrations/versions/YYYY_MM_DD_HHMM_description.py`

## API Changes
<!-- For changes affecting the API -->

- [ ] OpenAPI/Swagger docs updated automatically
- [ ] Response models updated
- [ ] Error handling implemented
- [ ] Backward compatible (or breaking change noted)
- [ ] Rate limiting considered

**Affected endpoints:**
- `GET /api/v1/...`
- `POST /api/v1/...`

## Deployment Notes
<!-- Special instructions for deployment -->

### Environment Variables
<!-- List any new or changed environment variables -->

```bash
# New variables required:
NEW_VAR=value

# Changed variables:
EXISTING_VAR=new_value
```

### Migration Commands
<!-- Commands to run during deployment -->

```bash
# Run before deployment:
alembic upgrade head

# Run after deployment:
# N/A
```

### Rollback Plan
<!-- How to rollback if this PR causes issues -->

```bash
# Rollback commands:
alembic downgrade -1
docker-compose restart api
```

## Performance Impact
<!-- Describe any performance implications -->

- [ ] No performance impact
- [ ] Performance improved (describe below)
- [ ] Performance regression (justified below)

**Details:**


## Screenshots/Logs
<!-- Add screenshots or log outputs if applicable -->

### Before


### After


## Checklist Before Merge
<!-- Final checks before merging -->

- [ ] All CI/CD checks pass
- [ ] Code reviewed and approved
- [ ] Branch is up to date with target branch
- [ ] No merge conflicts
- [ ] Tested on staging (for production PRs)
- [ ] Documentation complete
- [ ] Ready for production

## Additional Notes
<!-- Any additional information for reviewers -->


---

**Reviewer Notes:**
- Please review code quality, security, and test coverage
- Check for breaking changes
- Verify migration safety
- Ensure documentation is complete
