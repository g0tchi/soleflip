#!/usr/bin/env python3
"""
Quick CI/CD Pipeline Validation
Fast validation of key CI/CD components without running time-intensive tests.
"""

import subprocess
import sys
import time
from pathlib import Path


def log(message, status="INFO"):
    """Log with timestamp and status"""
    timestamp = time.strftime("%H:%M:%S")
    colors = {
        "PASS": "\033[92m",  # Green
        "FAIL": "\033[91m",  # Red
        "INFO": "\033[94m",  # Blue
        "WARN": "\033[93m",  # Yellow
        "END": "\033[0m",  # Reset
    }

    color = colors.get(status, colors["INFO"])
    print(f"[{timestamp}] [{status}] {color}{message}{colors['END']}")


def run_command_check(command, name):
    """Run command and return True if successful"""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            log(f"{name}: PASS", "PASS")
            return True
        else:
            log(f"{name}: FAIL - {result.stderr[:100]}", "FAIL")
            return False
    except subprocess.TimeoutExpired:
        log(f"{name}: FAIL - Timeout", "FAIL")
        return False
    except FileNotFoundError:
        log(f"{name}: FAIL - Command not found", "FAIL")
        return False
    except Exception as e:
        log(f"{name}: FAIL - {str(e)}", "FAIL")
        return False


def check_file_exists(filepath, name):
    """Check if file exists"""
    if Path(filepath).exists():
        log(f"{name}: PASS", "PASS")
        return True
    else:
        log(f"{name}: FAIL - File missing", "FAIL")
        return False


def main():
    """Run quick validation checks"""
    log("Quick CI/CD Pipeline Validation", "INFO")
    log("=" * 50, "INFO")

    passed = 0
    total = 0

    # Check Python and core dependencies
    checks = [
        # Python environment
        (lambda: run_command_check(["python", "--version"], "Python installation"), "Python"),
        (lambda: run_command_check(["python", "-m", "pip", "list"], "Pip package manager"), "Pip"),
        # Code quality tools
        (
            lambda: run_command_check(["python", "-m", "black", "--version"], "Black formatter"),
            "Black",
        ),
        (
            lambda: run_command_check(
                ["python", "-m", "isort", "--version"], "isort import sorter"
            ),
            "isort",
        ),
        (
            lambda: run_command_check(["python", "-m", "flake8", "--version"], "Flake8 linter"),
            "Flake8",
        ),
        # Testing tools
        (
            lambda: run_command_check(
                ["python", "-m", "pytest", "--version"], "Pytest test framework"
            ),
            "Pytest",
        ),
        # Database tools
        (
            lambda: run_command_check(
                ["python", "-m", "alembic", "--version"], "Alembic migrations"
            ),
            "Alembic",
        ),
        # FastAPI import test
        (
            lambda: run_command_check(
                ["python", "-c", "from main import app; print('FastAPI OK')"], "FastAPI application"
            ),
            "FastAPI",
        ),
        # GitHub workflows
        (lambda: check_file_exists(".github/workflows/ci.yml", "CI workflow"), "CI Workflow"),
        (
            lambda: check_file_exists(".github/workflows/deploy.yml", "Deploy workflow"),
            "Deploy Workflow",
        ),
        (
            lambda: check_file_exists(
                ".github/workflows/dependencies.yml", "Dependencies workflow"
            ),
            "Deps Workflow",
        ),
        # Key configuration files
        (lambda: check_file_exists(".pre-commit-config.yaml", "Pre-commit config"), "Pre-commit"),
        (lambda: check_file_exists("Dockerfile", "Docker configuration"), "Dockerfile"),
        (lambda: check_file_exists("pyproject.toml", "Python project config"), "pyproject.toml"),
        # Migration files
        (
            lambda: check_file_exists(
                "migrations/versions/2025_08_30_1000_add_performance_indexes.py",
                "Performance indexes migration",
            ),
            "Performance Migration",
        ),
        (
            lambda: check_file_exists(
                "migrations/versions/2025_08_30_1030_create_auth_schema.py", "Auth schema migration"
            ),
            "Auth Migration",
        ),
        # Auth system
        (lambda: check_file_exists("shared/auth/models.py", "Auth models"), "Auth Models"),
        (lambda: check_file_exists("shared/auth/jwt_handler.py", "JWT handler"), "JWT Handler"),
        (lambda: check_file_exists("domains/auth/api/router.py", "Auth API router"), "Auth API"),
        # Deployment scripts
        (
            lambda: check_file_exists(
                "scripts/deployment/generate_secrets.py", "Secrets generator"
            ),
            "Secrets Script",
        ),
        (
            lambda: check_file_exists(
                "scripts/database/migrate_with_backup.py", "Migration script"
            ),
            "Migration Script",
        ),
    ]

    log(f"Running {len(checks)} validation checks...", "INFO")
    log("")

    for check_func, name in checks:
        total += 1
        if check_func():
            passed += 1

    # Summary
    log("", "INFO")
    log("Quick Validation Summary", "INFO")
    log("=" * 30, "INFO")
    log(f"Checks Passed: {passed}/{total}", "INFO")

    if passed == total:
        log("", "INFO")
        log("[OK] All quick validation checks passed!", "PASS")
        log("", "INFO")
        log("Ready for:", "INFO")
        log("- GitHub Secrets setup: python scripts/deployment/generate_secrets.py", "INFO")
        log("- Full CI testing: gh workflow run ci.yml", "INFO")
        log("- Staging deployment: gh workflow run deploy.yml -f environment=staging", "INFO")
        return True
    else:
        failed = total - passed
        log("", "INFO")
        log(f"[ERROR] {failed} validation checks failed", "FAIL")
        log("", "INFO")
        log("Next steps:", "WARN")
        log("- Install missing dependencies: pip install -e .[dev]", "WARN")
        log("- Fix code formatting: python -m black . && python -m isort .", "WARN")
        log("- Check detailed errors with full validation script", "WARN")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
