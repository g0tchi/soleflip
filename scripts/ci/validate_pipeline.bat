@echo off
REM SoleFlipper CI/CD Pipeline Validation Script (Windows Batch)
REM Quick validation of CI/CD pipeline components

echo ============================================
echo SoleFlipper CI/CD Pipeline Validator
echo ============================================

set TESTS_PASSED=0
set TESTS_TOTAL=0

REM Function to run test and track results
goto :main

:run_test
set /a TESTS_TOTAL+=1
echo [%time%] [TEST] %2
%1 >nul 2>&1
if %errorlevel% equ 0 (
    echo [%time%] [PASS] %2
    set /a TESTS_PASSED+=1
) else (
    echo [%time%] [FAIL] %2
)
goto :eof

:main

REM Check Python availability
call :run_test "python --version" "Python availability"

REM Code Quality Tests
echo.
echo === Code Quality Tests ===
call :run_test "python -m black . --check" "Black code formatting"
call :run_test "python -m isort . --check-only" "Import sorting"
call :run_test "python -m flake8 . --extend-ignore=E203,W503" "Python linting"

REM Security Tests  
echo.
echo === Security Tests ===
call :run_test "python -m bandit -r . -x tests,venv,.venv -q" "Security scanning"
call :run_test "python -m pip check" "Dependency security"

REM Database Tests
echo.
echo === Database Tests ===
call :run_test "python scripts/database/migrate_with_backup.py --dry-run" "Migration dry run"
call :run_test "python -m alembic current" "Current migration"

REM API Tests
echo.
echo === API Health Tests ===
echo import sys; sys.path.insert(0, '.'); from main import app; print('FastAPI import successful') | python
if %errorlevel% equ 0 (
    echo [%time%] [PASS] FastAPI application import
    set /a TESTS_PASSED+=1
) else (
    echo [%time%] [FAIL] FastAPI application import
)
set /a TESTS_TOTAL+=1

REM GitHub Workflows
echo.
echo === GitHub Workflows ===
if exist ".github\workflows\ci.yml" (
    echo [%time%] [PASS] CI workflow exists
    set /a TESTS_PASSED+=1
) else (
    echo [%time%] [FAIL] CI workflow missing
)
set /a TESTS_TOTAL+=1

if exist ".github\workflows\deploy.yml" (
    echo [%time%] [PASS] Deploy workflow exists  
    set /a TESTS_PASSED+=1
) else (
    echo [%time%] [FAIL] Deploy workflow missing
)
set /a TESTS_TOTAL+=1

REM Docker Test (optional)
echo.
echo === Docker Tests ===
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [%time%] [INFO] Docker available, testing builds...
    call :run_test "docker build . --target development -t soleflip:test" "Docker development build"
) else (
    echo [%time%] [WARN] Docker not available, skipping build tests
)

REM Summary
echo.
echo ============================================
echo CI/CD Pipeline Validation Summary
echo ============================================
echo Tests Passed: %TESTS_PASSED% / %TESTS_TOTAL%

if %TESTS_PASSED% equ %TESTS_TOTAL% (
    echo.
    echo [SUCCESS] All CI/CD pipeline tests passed! Ready for deployment.
    echo.
    echo Next Steps:
    echo 1. Set up GitHub Secrets: python scripts/deployment/generate_secrets.py
    echo 2. Test deployment: gh workflow run deploy.yml -f environment=staging
    echo 3. Monitor with: gh run list
    exit /b 0
) else (
    set /a TESTS_FAILED=%TESTS_TOTAL%-%TESTS_PASSED%
    echo.
    echo [ERROR] %TESTS_FAILED% tests failed. Fix issues before deployment.
    echo.
    echo Common fixes:
    echo - Code formatting: python -m black . ^&^& python -m isort .
    echo - Install packages: pip install -e .[dev]
    echo - Check errors: python -m flake8 . --show-source
    exit /b 1
)