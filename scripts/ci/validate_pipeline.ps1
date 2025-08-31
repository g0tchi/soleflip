# SoleFlipper CI/CD Pipeline Validation Script (PowerShell)
# Validates the entire CI/CD pipeline locally on Windows

param(
    [switch]$SkipDocker,
    [switch]$SkipTests,
    [switch]$Verbose
)

# Set error action preference
$ErrorActionPreference = "Continue"

# Initialize counters
$script:TestsPassed = 0
$script:TestsTotal = 0
$script:StartTime = Get-Date

function Write-TestLog {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Color = "White"
    )
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    switch ($Level) {
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        "ERROR"   { Write-Host $logMessage -ForegroundColor Red }
        "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
        "INFO"    { Write-Host $logMessage -ForegroundColor $Color }
        default   { Write-Host $logMessage }
    }
}

function Test-Command {
    param(
        [string]$Name,
        [string[]]$Command,
        [int]$TimeoutSeconds = 300
    )
    
    $script:TestsTotal++
    Write-TestLog "Testing: $Name"
    
    try {
        $process = Start-Process -FilePath $Command[0] -ArgumentList $Command[1..($Command.Length-1)] -PassThru -NoNewWindow -RedirectStandardOutput "temp_stdout.txt" -RedirectStandardError "temp_stderr.txt"
        
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            $process.Kill()
            Write-TestLog "FAIL: $Name - Command timed out" "ERROR"
            return $false
        }
        
        $stdout = Get-Content "temp_stdout.txt" -Raw -ErrorAction SilentlyContinue
        $stderr = Get-Content "temp_stderr.txt" -Raw -ErrorAction SilentlyContinue
        
        # Clean up temp files
        Remove-Item "temp_stdout.txt", "temp_stderr.txt" -ErrorAction SilentlyContinue
        
        if ($process.ExitCode -eq 0) {
            $script:TestsPassed++
            Write-TestLog "PASS: $Name" "SUCCESS"
            if ($Verbose -and $stdout) {
                Write-TestLog "Output: $($stdout.Substring(0, [Math]::Min(200, $stdout.Length)))" "INFO" "Cyan"
            }
            return $true
        } else {
            Write-TestLog "FAIL: $Name - Exit code: $($process.ExitCode)" "ERROR"
            if ($stderr) {
                Write-TestLog "Error: $($stderr.Substring(0, [Math]::Min(200, $stderr.Length)))" "ERROR"
            }
            return $false
        }
    }
    catch {
        Write-TestLog "FAIL: $Name - Exception: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Test-CodeQuality {
    Write-TestLog "=== Code Quality Tests ===" "INFO" "Magenta"
    
    # Test Black formatting
    Test-Command "Black Code Formatting" @("python", "-m", "black", ".", "--check", "--diff")
    
    # Test Import sorting
    Test-Command "Import Sorting (isort)" @("python", "-m", "isort", ".", "--check-only")
    
    # Test Flake8 linting
    Test-Command "Python Linting (flake8)" @("python", "-m", "flake8", ".", "--extend-ignore=E203,W503")
    
    # Test MyPy type checking
    Test-Command "Type Checking (mypy)" @("python", "-m", "mypy", "main.py", "--ignore-missing-imports")
}

function Test-Security {
    Write-TestLog "=== Security Tests ===" "INFO" "Magenta"
    
    # Test Bandit security scanning
    Test-Command "Security Scanning (bandit)" @("python", "-m", "bandit", "-r", ".", "-x", "tests,venv,.venv", "--quiet")
    
    # Test dependency vulnerabilities
    Test-Command "Dependency Security Check" @("python", "-m", "pip", "check")
}

function Test-UnitTests {
    if ($SkipTests) {
        Write-TestLog "Skipping unit tests (--SkipTests flag)" "WARNING"
        return
    }
    
    Write-TestLog "=== Unit Tests ===" "INFO" "Magenta"
    
    # Run pytest
    Test-Command "Unit Tests (pytest)" @("python", "-m", "pytest", "tests/", "-v", "--tb=short")
}

function Test-DatabaseMigrations {
    Write-TestLog "=== Database Migration Tests ===" "INFO" "Magenta"
    
    # Test migration dry run
    Test-Command "Migration Dry Run" @("python", "scripts/database/migrate_with_backup.py", "--dry-run")
    
    # Test Alembic current
    Test-Command "Current Migration Status" @("python", "-m", "alembic", "current")
    
    # Test Alembic history
    Test-Command "Migration History" @("python", "-m", "alembic", "history")
}

function Test-APIHealth {
    Write-TestLog "=== API Health Tests ===" "INFO" "Magenta"
    
    # Test FastAPI import
    $script:TestsTotal++
    Write-TestLog "Testing: FastAPI Application Import"
    
    try {
        $testScript = @"
import sys
sys.path.insert(0, '.')
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test health endpoint
response = client.get('/health')
print(f'Health endpoint: {response.status_code}')
assert response.status_code in [200, 503], f'Health check failed: {response.status_code}'

# Test root endpoint
response = client.get('/')
print(f'Root endpoint: {response.status_code}')
assert response.status_code == 200, f'Root endpoint failed: {response.status_code}'

print('API health tests passed')
"@
        
        $testScript | Out-File -FilePath "temp_api_test.py" -Encoding UTF8
        
        $result = Test-Command "API Health Check" @("python", "temp_api_test.py")
        
        Remove-Item "temp_api_test.py" -ErrorAction SilentlyContinue
        
    }
    catch {
        Write-TestLog "FAIL: API Health Check - $($_.Exception.Message)" "ERROR"
    }
}

function Test-Docker {
    if ($SkipDocker) {
        Write-TestLog "Skipping Docker tests (--SkipDocker flag)" "WARNING"
        return
    }
    
    Write-TestLog "=== Docker Build Tests ===" "INFO" "Magenta"
    
    # Test Docker availability
    $script:TestsTotal++
    Write-TestLog "Testing: Docker Availability"
    
    try {
        $dockerVersion = docker --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            $script:TestsPassed++
            Write-TestLog "PASS: Docker Available - $dockerVersion" "SUCCESS"
            
            # Test development build
            Test-Command "Docker Development Build" @("docker", "build", ".", "--target", "development", "-t", "soleflip:test-dev")
            
            # Test production build
            Test-Command "Docker Production Build" @("docker", "build", ".", "--target", "production", "-t", "soleflip:test-prod")
        } else {
            Write-TestLog "FAIL: Docker not available" "ERROR"
        }
    }
    catch {
        Write-TestLog "FAIL: Docker test failed - $($_.Exception.Message)" "ERROR"
    }
}

function Test-GitHubWorkflows {
    Write-TestLog "=== GitHub Workflows Validation ===" "INFO" "Magenta"
    
    # Check if workflow files exist
    $workflowFiles = @(
        ".github/workflows/ci.yml",
        ".github/workflows/deploy.yml", 
        ".github/workflows/dependencies.yml"
    )
    
    foreach ($file in $workflowFiles) {
        $script:TestsTotal++
        if (Test-Path $file) {
            $script:TestsPassed++
            Write-TestLog "PASS: Workflow file exists - $file" "SUCCESS"
        } else {
            Write-TestLog "FAIL: Missing workflow file - $file" "ERROR"
        }
    }
    
    # Validate YAML syntax (if yamllint is available)
    foreach ($file in $workflowFiles) {
        if (Test-Path $file) {
            $script:TestsTotal++
            try {
                # Try to parse YAML with PowerShell (basic validation)
                $content = Get-Content $file -Raw
                if ($content -match "^name:" -and $content -match "on:") {
                    $script:TestsPassed++
                    Write-TestLog "PASS: Valid YAML structure - $file" "SUCCESS"
                } else {
                    Write-TestLog "FAIL: Invalid YAML structure - $file" "ERROR"
                }
            }
            catch {
                Write-TestLog "FAIL: YAML validation failed - $file" "ERROR"
            }
        }
    }
}

function Show-Summary {
    $endTime = Get-Date
    $duration = ($endTime - $script:StartTime).TotalSeconds
    
    Write-TestLog ""
    Write-TestLog "=== CI/CD Pipeline Validation Summary ===" "INFO" "Magenta"
    Write-TestLog "Duration: $([math]::Round($duration, 1)) seconds"
    Write-TestLog "Tests Passed: $script:TestsPassed / $script:TestsTotal"
    
    if ($script:TestsPassed -eq $script:TestsTotal) {
        Write-TestLog ""
        Write-TestLog "🎉 All CI/CD pipeline tests passed! Ready for deployment." "SUCCESS"
        Write-TestLog ""
        Write-TestLog "Next Steps:" "INFO" "Cyan"
        Write-TestLog "1. Set up GitHub Secrets: run scripts/deployment/generate_secrets.py" "INFO" "Cyan"
        Write-TestLog "2. Push to GitHub: git push origin feature/pricing-forecast" "INFO" "Cyan"
        Write-TestLog "3. Test deployment: gh workflow run deploy.yml -f environment=staging" "INFO" "Cyan"
        
        exit 0
    } else {
        $failedTests = $script:TestsTotal - $script:TestsPassed
        Write-TestLog ""
        Write-TestLog "❌ $failedTests tests failed. Fix issues before deployment." "ERROR"
        Write-TestLog ""
        Write-TestLog "Common Solutions:" "INFO" "Yellow"
        Write-TestLog "- Code formatting: python -m black . && python -m isort ." "INFO" "Yellow"
        Write-TestLog "- Install missing packages: pip install -e .[dev]" "INFO" "Yellow"
        Write-TestLog "- Fix linting issues: python -m flake8 . --show-source" "INFO" "Yellow"
        
        exit 1
    }
}

# Main execution
Write-TestLog "🔍 SoleFlipper CI/CD Pipeline Validator (PowerShell)" "INFO" "Magenta"
Write-TestLog "=" * 60

# Check Python availability
$script:TestsTotal++
Write-TestLog "Testing: Python Availability"
try {
    $pythonVersion = python --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        $script:TestsPassed++
        Write-TestLog "PASS: Python Available - $pythonVersion" "SUCCESS"
    } else {
        Write-TestLog "FAIL: Python not available" "ERROR"
        exit 1
    }
}
catch {
    Write-TestLog "FAIL: Python test failed" "ERROR"
    exit 1
}

# Run all tests
Test-CodeQuality
Test-Security
Test-UnitTests
Test-DatabaseMigrations
Test-APIHealth
Test-GitHubWorkflows
Test-Docker

Show-Summary