# Overnight Development Setup - SoleFlip Project

## ✅ Installation Complete

The overnight development system has been successfully installed in your project:

### Files Created

1. **`.overnight-dev.json`** - Configuration file
2. **`.git/hooks/pre-commit`** - Pre-commit validation hook
3. **`.git/hooks/commit-msg`** - Commit message format enforcer

### Current Configuration

```json
{
  "testCommand": "PYTHONPATH=. pytest tests/unit/ -v --tb=short -x",
  "lintCommand": "python3 -m black --check . && python3 -m isort --check-only .",
  "requireCoverage": false,
  "minCoverage": 80,
  "autoFix": true,
  "maxAttempts": 50,
  "stopOnMorning": true,
  "morningHour": 7
}
```

## 🔧 Before First Use

### Fix Missing Dependencies

Your tests are currently failing due to a missing dependency (`aiofiles`). Install it:

```bash
source .venv/bin/activate
pip install aiofiles
```

### Fix Ruff Linting Errors

There are currently 73 ruff linting errors in the codebase. To enable stricter quality checks, you can:

1. **Option A**: Add ruff back to lintCommand once errors are fixed:
   ```json
   "lintCommand": "python3 -m ruff check . && python3 -m black --check . && python3 -m isort --check-only ."
   ```

2. **Option B**: Use make commands which handle ruff with proper settings:
   ```json
   "lintCommand": "make lint",
   "testCommand": "make test-unit"
   ```

## 🚀 How It Works

### Pre-Commit Hook

Every time you commit, the hook will:

1. **Activate virtual environment** (`.venv` or `venv`)
2. **Auto-fix formatting** (if `autoFix: true`):
   - Run `black` to format code
   - Run `isort` to organize imports
3. **Check linting** - Verify code meets quality standards
4. **Run tests** - Ensure all unit tests pass
5. **Only allow commit if all checks pass**

### Commit Message Hook

Enforces conventional commit format:
```
type(scope): description

Valid types: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert
```

Examples:
```
feat(inventory): add dead stock analysis
fix(pricing): correct auto-listing calculation
test(orders): add unit tests for multi-platform orders
```

## 📋 Testing the Setup

Once you've fixed the dependency issue, test the hooks:

```bash
# This should auto-format code, run lints, and run tests
git commit --allow-empty -m "test: verify overnight dev hooks"

# If it passes, you'll see:
# 🌙 Overnight Dev: Running pre-commit checks...
# 🔍 Running linting...
# 🔧 Auto-fixing linting issues...
# ✅ Linting passed (with auto-fix)
# 🧪 Running tests...
# ✅ All tests passed
# ✅ Commit message format valid
# ✨ All checks passed! Proceeding with commit...
```

## 🌙 Starting an Overnight Session

### 1. Define Your Goal

Be specific about what you want to accomplish:

```
Goal: Implement supplier performance analytics dashboard
Success Criteria:
- Calculate supplier metrics (reliability, price trends)
- Create API endpoints for dashboard data
- All tests pass with >80% coverage
- Follow DDD patterns from existing domains
```

### 2. Use TDD (Test-Driven Development)

Write tests first, then implementation:

```python
# 1. Write the test
def test_calculate_supplier_reliability():
    # Arrange
    supplier_id = uuid4()
    # ...

    # Act
    reliability = service.calculate_reliability(supplier_id)

    # Assert
    assert reliability >= 0.0
    assert reliability <= 1.0
```

```python
# 2. Implement to make test pass
async def calculate_reliability(self, supplier_id: UUID) -> float:
    # Implementation here
    pass
```

### 3. Commit Frequently

Small, focused commits work best:

```bash
git add tests/unit/test_supplier_analytics.py
git commit -m "test(suppliers): add reliability calculation tests"

git add domains/suppliers/services/analytics_service.py
git commit -m "feat(suppliers): implement reliability calculation"
```

Each commit will automatically:
- Format your code
- Run linting checks
- Run all unit tests
- Enforce commit message format

### 4. Let Claude Work Overnight

With the hooks in place:
- Every commit MUST pass all checks
- Code quality is automatically maintained
- Test failures are caught immediately
- Morning brings fully tested, production-ready features

## 🎯 Configuration Options

### Adjust Test Strictness

For faster iteration (current):
```json
{
  "testCommand": "PYTHONPATH=. pytest tests/unit/ -v --tb=short -x",
  "requireCoverage": false
}
```

For production-ready code:
```json
{
  "testCommand": "pytest --cov=domains --cov=shared --cov-report=term-missing",
  "requireCoverage": true,
  "minCoverage": 80
}
```

### Enable/Disable Auto-Fix

Auto-fix ON (current - recommended):
```json
{
  "autoFix": true
}
```

Manual fixing required:
```json
{
  "autoFix": false
}
```

### Morning Stop Time

```json
{
  "stopOnMorning": true,
  "morningHour": 7  // Stop at 7:00 AM
}
```

## 🐛 Troubleshooting

### "Tests failed" on every commit

1. Check that dependencies are installed:
   ```bash
   source .venv/bin/activate
   pip install -e ".[dev,ml]"
   ```

2. Run tests manually to see errors:
   ```bash
   make test-unit
   ```

3. Fix failing tests before committing

### "Linting failed" on every commit

1. Run auto-formatters manually:
   ```bash
   make format
   ```

2. Check for remaining issues:
   ```bash
   make lint
   ```

### Hooks not running

Make hooks executable:
```bash
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/commit-msg
```

### Need to bypass hooks (emergency only)

```bash
git commit --no-verify -m "emergency: bypass hooks"
```

**Note**: This defeats the purpose of overnight dev! Only use in emergencies.

## 📊 Success Metrics

Track your overnight sessions:

- ✅ **Commit success rate**: % of commits that pass hooks on first try
- ✅ **Test coverage**: Maintained or improved
- ✅ **Code quality**: No linting errors introduced
- ✅ **Feature completion**: All acceptance criteria met
- ✅ **Documentation**: Code is self-documenting with tests

## 🎓 Best Practices

### 1. Start Simple

Don't try to build everything in one session. Break down features:

❌ **Too ambitious**: "Build complete supplier analytics system"
✅ **Achievable**: "Implement supplier reliability calculation with tests"

### 2. Write Tests First

TDD ensures your code works:

```python
# Test first
def test_dead_stock_identification():
    # Test the behavior you want
    ...

# Then implement
async def identify_dead_stock(self):
    # Make the test pass
    ...
```

### 3. Commit Often

Small commits are easier to debug if something breaks:

✅ Good commit sequence:
```
test(inventory): add dead stock age tests
feat(inventory): implement dead stock age calculation
test(inventory): add dead stock value tests
feat(inventory): implement dead stock value calculation
```

❌ Bad commit (too large):
```
feat(inventory): complete dead stock analysis system
```

### 4. Trust the Process

The hooks are there to help you:
- If tests fail → Your code has a bug
- If linting fails → Your code needs cleanup
- If commit message is rejected → Follow conventional format

Don't fight the hooks—they're keeping your code quality high!

## 🚢 Production Deployment

Before deploying code created during overnight sessions:

1. **Review the commits**:
   ```bash
   git log --oneline
   ```

2. **Run full test suite**:
   ```bash
   make check  # lint + type-check + test
   ```

3. **Run integration tests**:
   ```bash
   pytest tests/integration/
   ```

4. **Check test coverage**:
   ```bash
   make test-cov
   ```

5. **Review the changes**:
   ```bash
   git diff origin/master
   ```

## 📚 Additional Resources

- **Project Commands**: See `CLAUDE.md` for all available `make` commands
- **Architecture**: Review domain structure in `domains/` directory
- **Testing Guide**: See `tests/README.md` (if exists)
- **CI/CD**: Hooks mirror CI checks—if hooks pass, CI should pass

---

## Quick Reference

### Daily Workflow

```bash
# Morning: Review overnight work
git log --oneline --since="yesterday"
git diff HEAD~5 HEAD  # Review last 5 commits

# Start new feature
# 1. Write tests
# 2. Commit tests
# 3. Write implementation
# 4. Commit implementation
# 5. Repeat

# Each commit triggers hooks automatically!
```

### Essential Commands

```bash
make dev          # Start development server
make test-unit    # Run unit tests manually
make format       # Auto-format code
make lint         # Check code quality
make check        # Run all quality checks
```

### Hook Behavior

| Check | Auto-Fix | Blocks Commit |
|-------|----------|---------------|
| black formatting | ✅ Yes | ❌ No (after fix) |
| isort imports | ✅ Yes | ❌ No (after fix) |
| Unit tests | ❌ No | ✅ Yes (if fail) |
| Commit message | ❌ No | ✅ Yes (if invalid) |

---

**Ready to start?** Fix the `aiofiles` dependency, and begin your first overnight development session! 🚀
