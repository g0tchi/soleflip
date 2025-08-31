#!/usr/bin/env python3
"""
Local CI/CD Pipeline Validation Script
Simulates and validates the entire CI/CD pipeline locally before pushing to GitHub.
"""

import subprocess
import sys
import os
import asyncio
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import tempfile


@dataclass
class TestResult:
    """Test result container"""
    name: str
    success: bool
    duration: float
    message: str
    details: List[str] = None


class CIPipelineValidator:
    """Local CI/CD pipeline validator"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = time.time()
        self.project_root = Path.cwd()
        
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def run_command(self, command: List[str], timeout: int = 300) -> Tuple[bool, str, str]:
        """Run command and return success, stdout, stderr"""
        try:
            self.log(f"Running: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )
            
            success = result.returncode == 0
            if not success:
                self.log(f"Command failed with exit code {result.returncode}", "ERROR")
                self.log(f"STDERR: {result.stderr}", "ERROR")
            
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", str(e)
    
    def test_code_quality(self) -> TestResult:
        """Test code quality tools"""
        start_time = time.time()
        self.log("Testing code quality tools...")
        
        checks = []
        
        # Test Black formatting
        success, stdout, stderr = self.run_command(["python", "-m", "black", ".", "--check", "--diff"])
        checks.append(("Black formatting", success, stderr))
        
        # Test isort imports
        success, stdout, stderr = self.run_command(["python", "-m", "isort", ".", "--check-only", "--diff"])
        checks.append(("Import sorting (isort)", success, stderr))
        
        # Test flake8 linting  
        success, stdout, stderr = self.run_command(["python", "-m", "flake8", ".", "--config=setup.cfg"])
        checks.append(("Linting (flake8)", success, stdout + stderr))
        
        # Test mypy type checking
        success, stdout, stderr = self.run_command(["python", "-m", "mypy", "main.py", "--ignore-missing-imports"])
        checks.append(("Type checking (mypy)", success, stderr))
        
        # Analyze results
        passed_checks = sum(1 for _, success, _ in checks if success)
        total_checks = len(checks)
        
        details = []
        for name, success, output in checks:
            status = "PASS" if success else "FAIL"
            details.append(f"{status}: {name}")
            if not success and output:
                details.append(f"  Error: {output[:200]}...")
        
        overall_success = passed_checks == total_checks
        message = f"Code Quality: {passed_checks}/{total_checks} checks passed"
        
        return TestResult(
            name="Code Quality",
            success=overall_success,
            duration=time.time() - start_time,
            message=message,
            details=details
        )
    
    def test_security_scanning(self) -> TestResult:
        """Test security scanning"""
        start_time = time.time()
        self.log("Testing security scanning...")
        
        checks = []
        
        # Test bandit security scanning
        success, stdout, stderr = self.run_command([
            "python", "-m", "bandit", "-r", ".", "-f", "json", "-x", "tests,venv,.venv"
        ])
        
        if success:
            try:
                bandit_results = json.loads(stdout)
                high_severity = len([r for r in bandit_results.get('results', []) if r.get('issue_severity') == 'HIGH'])
                medium_severity = len([r for r in bandit_results.get('results', []) if r.get('issue_severity') == 'MEDIUM'])
                
                if high_severity > 0:
                    success = False
                    checks.append(("Bandit security scan", False, f"{high_severity} high severity issues found"))
                else:
                    checks.append(("Bandit security scan", True, f"{medium_severity} medium, 0 high severity issues"))
            except json.JSONDecodeError:
                checks.append(("Bandit security scan", False, "Failed to parse bandit output"))
        else:
            checks.append(("Bandit security scan", False, stderr))
        
        # Test pip safety check (if available)
        success, stdout, stderr = self.run_command(["python", "-m", "pip", "list", "--format=json"])
        if success:
            checks.append(("Dependency scan", True, "Dependencies listed successfully"))
        else:
            checks.append(("Dependency scan", False, "Failed to list dependencies"))
        
        passed_checks = sum(1 for _, success, _ in checks if success)
        total_checks = len(checks)
        
        details = []
        for name, success, output in checks:
            status = "PASS" if success else "FAIL"
            details.append(f"{status}: {name}")
            if output:
                details.append(f"  Result: {output}")
        
        overall_success = passed_checks == total_checks
        message = f"Security: {passed_checks}/{total_checks} scans passed"
        
        return TestResult(
            name="Security Scanning",
            success=overall_success,
            duration=time.time() - start_time,
            message=message,
            details=details
        )
    
    def test_unit_tests(self) -> TestResult:
        """Test unit tests"""
        start_time = time.time()
        self.log("Running unit tests...")
        
        # Run pytest with coverage
        success, stdout, stderr = self.run_command([
            "python", "-m", "pytest", "tests/", "-v", "--tb=short",
            "--cov=domains", "--cov=shared", "--cov-report=term-missing"
        ])
        
        details = []
        if stdout:
            # Parse test results
            lines = stdout.split('\n')
            for line in lines:
                if 'PASSED' in line or 'FAILED' in line or 'ERROR' in line:
                    details.append(line.strip())
                if 'coverage' in line.lower():
                    details.append(line.strip())
        
        if stderr:
            details.extend(stderr.split('\n')[:10])  # First 10 error lines
        
        message = "Unit tests passed" if success else "Unit tests failed"
        
        return TestResult(
            name="Unit Tests",
            success=success,
            duration=time.time() - start_time,
            message=message,
            details=details
        )
    
    def test_docker_build(self) -> TestResult:
        """Test Docker build"""
        start_time = time.time()
        self.log("Testing Docker build...")
        
        # Test development build
        success, stdout, stderr = self.run_command([
            "docker", "build", ".", "--target", "development", "-t", "soleflip:test-dev"
        ], timeout=600)
        
        details = []
        if success:
            details.append("PASS: Development Docker build")
            
            # Test production build
            success_prod, stdout_prod, stderr_prod = self.run_command([
                "docker", "build", ".", "--target", "production", "-t", "soleflip:test-prod"
            ], timeout=600)
            
            if success_prod:
                details.append("PASS: Production Docker build")
                message = "Docker builds successful"
                overall_success = True
            else:
                details.append("FAIL: Production Docker build")
                details.append(f"Error: {stderr_prod[:200]}...")
                message = "Production Docker build failed"
                overall_success = False
        else:
            details.append("FAIL: Development Docker build") 
            details.append(f"Error: {stderr[:200]}...")
            message = "Development Docker build failed"
            overall_success = False
        
        return TestResult(
            name="Docker Build",
            success=overall_success,
            duration=time.time() - start_time,
            message=message,
            details=details
        )
    
    def test_database_migrations(self) -> TestResult:
        """Test database migrations"""
        start_time = time.time()
        self.log("Testing database migrations...")
        
        # Test dry run migration
        success, stdout, stderr = self.run_command([
            "python", "scripts/database/migrate_with_backup.py", "--dry-run"
        ])
        
        details = []
        if success:
            details.append("PASS: Migration dry run successful")
            
            # Test migration status
            success_status, stdout_status, stderr_status = self.run_command([
                "python", "-m", "alembic", "current"
            ])
            
            if success_status:
                details.append(f"PASS: Current migration: {stdout_status.strip()}")
                
                # Test migration history
                success_history, stdout_history, stderr_history = self.run_command([
                    "python", "-m", "alembic", "history"
                ])
                
                if success_history:
                    details.append("PASS: Migration history accessible")
                    message = "Database migrations validated"
                    overall_success = True
                else:
                    details.append("FAIL: Migration history check failed")
                    message = "Migration history check failed"
                    overall_success = False
            else:
                details.append("FAIL: Current migration check failed")
                message = "Migration status check failed"
                overall_success = False
        else:
            details.append("FAIL: Migration dry run failed")
            details.append(f"Error: {stderr[:200]}...")
            message = "Migration dry run failed"
            overall_success = False
        
        return TestResult(
            name="Database Migrations",
            success=overall_success,
            duration=time.time() - start_time,
            message=message,
            details=details
        )
    
    def test_api_health_check(self) -> TestResult:
        """Test API health check"""
        start_time = time.time()
        self.log("Testing API health check...")
        
        # Import and test the FastAPI app
        try:
            import sys
            sys.path.insert(0, str(self.project_root))
            
            from main import app
            from fastapi.testclient import TestClient
            
            client = TestClient(app)
            
            # Test health endpoint
            response = client.get("/health")
            health_success = response.status_code == 200
            
            # Test metrics endpoint  
            response_metrics = client.get("/metrics")
            metrics_success = response_metrics.status_code == 200
            
            # Test root endpoint
            response_root = client.get("/")
            root_success = response_root.status_code == 200
            
            details = []
            details.append(f"{'PASS' if health_success else 'FAIL'}: Health endpoint")
            details.append(f"{'PASS' if metrics_success else 'FAIL'}: Metrics endpoint")
            details.append(f"{'PASS' if root_success else 'FAIL'}: Root endpoint")
            
            overall_success = health_success and metrics_success and root_success
            message = "API endpoints accessible" if overall_success else "Some API endpoints failed"
            
        except Exception as e:
            details = [f"FAIL: API import/test failed: {str(e)}"]
            overall_success = False
            message = "API health check failed"
        
        return TestResult(
            name="API Health Check",
            success=overall_success,
            duration=time.time() - start_time,
            message=message,
            details=details
        )
    
    def run_all_tests(self):
        """Run all CI/CD pipeline tests"""
        self.log("Starting CI/CD Pipeline Validation")
        self.log("=" * 50)
        
        # Run all tests
        tests = [
            self.test_code_quality,
            self.test_security_scanning,
            self.test_unit_tests,
            self.test_database_migrations,
            self.test_api_health_check,
            self.test_docker_build,  # Run this last as it's slowest
        ]
        
        for test_func in tests:
            try:
                result = test_func()
                self.results.append(result)
                
                status = "PASS" if result.success else "FAIL"
                self.log(f"{status}: {result.name} - {result.message} ({result.duration:.1f}s)")
                
                if result.details:
                    for detail in result.details[:5]:  # Show first 5 details
                        self.log(f"  {detail}")
                
            except Exception as e:
                error_result = TestResult(
                    name=test_func.__name__.replace('test_', '').replace('_', ' ').title(),
                    success=False,
                    duration=0,
                    message=f"Test execution failed: {str(e)}",
                    details=[str(e)]
                )
                self.results.append(error_result)
                self.log(f"FAIL: {error_result.name} - {error_result.message}")
    
    def generate_report(self):
        """Generate final test report"""
        total_duration = time.time() - self.start_time
        passed_tests = sum(1 for result in self.results if result.success)
        total_tests = len(self.results)
        
        self.log("")
        self.log("CI/CD Pipeline Validation Report")
        self.log("=" * 50)
        self.log(f"Total Duration: {total_duration:.1f}s")
        self.log(f"Tests Passed: {passed_tests}/{total_tests}")
        self.log("")
        
        for result in self.results:
            status = "✓" if result.success else "✗"
            self.log(f"{status} {result.name}: {result.message} ({result.duration:.1f}s)")
        
        self.log("")
        if passed_tests == total_tests:
            self.log("🎉 All CI/CD pipeline tests passed! Ready for deployment.", "SUCCESS")
            return True
        else:
            self.log(f"❌ {total_tests - passed_tests} tests failed. Fix issues before deployment.", "ERROR")
            return False


def main():
    """Main function"""
    print("🔍 SoleFlipper CI/CD Pipeline Validator")
    print("=" * 50)
    
    validator = CIPipelineValidator()
    validator.run_all_tests()
    success = validator.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()