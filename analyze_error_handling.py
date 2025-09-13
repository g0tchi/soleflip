"""
Error Handling Analysis and Improvement Tool
Analyzes Python files for error handling patterns and suggests improvements.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Set
from dataclasses import dataclass
import logging

@dataclass
class ErrorHandlingIssue:
    file_path: str
    line_number: int
    issue_type: str
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    suggestion: str
    code_snippet: str = ""

class ErrorHandlingAnalyzer:
    def __init__(self):
        self.issues: List[ErrorHandlingIssue] = []
        self.stats = {
            "files_analyzed": 0,
            "total_issues": 0,
            "bare_except": 0,
            "generic_exceptions": 0,
            "missing_finally": 0,
            "silent_failures": 0,
            "missing_logging": 0,
            "improper_reraise": 0
        }
        
        # Common generic exception types that should be more specific
        self.generic_exceptions = {
            'Exception', 'BaseException', 'RuntimeError', 'ValueError', 'TypeError'
        }
    
    def analyze_directory(self, directory: Path) -> Dict[str, Any]:
        """Analyze all Python files for error handling issues"""
        python_files = list(directory.rglob("*.py"))
        
        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue
                
            try:
                self.analyze_file(file_path)
            except Exception as e:
                logging.error(f"Error analyzing {file_path}: {e}")
        
        return self._generate_report()
    
    def analyze_file(self, file_path: Path):
        """Analyze a single file for error handling issues"""
        self.stats["files_analyzed"] += 1
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    content = f.read()
                    lines = content.splitlines()
            except Exception:
                return
        
        # Parse AST for structural analysis
        try:
            tree = ast.parse(content)
            self._analyze_ast(tree, file_path, lines)
        except SyntaxError:
            return
        
        # Line-by-line analysis for patterns
        self._analyze_patterns(lines, file_path)
    
    def _analyze_ast(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Analyze AST for error handling patterns"""
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                self._analyze_try_except(node, file_path, lines)
            
            elif isinstance(node, ast.ExceptHandler):
                self._analyze_exception_handler(node, file_path, lines)
            
            elif isinstance(node, ast.Raise):
                self._analyze_raise_statement(node, file_path, lines)
            
            elif isinstance(node, ast.With):
                self._analyze_context_manager(node, file_path, lines)
    
    def _analyze_try_except(self, node: ast.Try, file_path: Path, lines: List[str]):
        """Analyze try/except block structure"""
        
        # Check if try block is too large
        if hasattr(node, 'end_lineno'):
            try_size = node.end_lineno - node.lineno
            if try_size > 20:
                self._add_issue(
                    str(file_path), node.lineno, "large_try_block",
                    f"Try block spans {try_size} lines - too large",
                    "medium", "Break down into smaller try blocks",
                    self._get_code_snippet(lines, node.lineno, min(node.lineno + 3, len(lines)))
                )
        
        # Check for missing finally clause when resources are involved
        has_finally = node.finalbody is not None and len(node.finalbody) > 0
        has_resource_usage = self._check_resource_usage_in_try(node)
        
        if has_resource_usage and not has_finally:
            self._add_issue(
                str(file_path), node.lineno, "missing_finally",
                "Try block with resource usage lacks finally clause",
                "medium", "Consider using context managers or adding finally clause",
                self._get_code_snippet(lines, node.lineno, node.lineno + 2)
            )
    
    def _analyze_exception_handler(self, node: ast.ExceptHandler, file_path: Path, lines: List[str]):
        """Analyze exception handler quality"""
        
        # Check for bare except
        if node.type is None:
            self._add_issue(
                str(file_path), node.lineno, "bare_except",
                "Bare except clause catches all exceptions",
                "high", "Specify specific exception types",
                self._get_code_snippet(lines, node.lineno, node.lineno + 1)
            )
            self.stats["bare_except"] += 1
        
        # Check for overly generic exceptions
        elif hasattr(node.type, 'id') and node.type.id in self.generic_exceptions:
            self._add_issue(
                str(file_path), node.lineno, "generic_exception",
                f"Catching generic exception: {node.type.id}",
                "medium", f"Catch specific exceptions instead of {node.type.id}",
                self._get_code_snippet(lines, node.lineno, node.lineno + 1)
            )
            self.stats["generic_exceptions"] += 1
        
        # Check for silent failures (empty except block or just pass)
        if len(node.body) == 0 or (
            len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
        ):
            self._add_issue(
                str(file_path), node.lineno, "silent_failure",
                "Exception handler silently ignores errors",
                "high", "Add proper error logging and handling",
                self._get_code_snippet(lines, node.lineno, node.lineno + 2)
            )
            self.stats["silent_failures"] += 1
        
        # Check for missing logging in exception handlers
        elif not self._has_logging_in_handler(node):
            self._add_issue(
                str(file_path), node.lineno, "missing_logging",
                "Exception handler missing error logging",
                "medium", "Add logging to track exceptions",
                self._get_code_snippet(lines, node.lineno, node.lineno + 2)
            )
            self.stats["missing_logging"] += 1
    
    def _analyze_raise_statement(self, node: ast.Raise, file_path: Path, lines: List[str]):
        """Analyze raise statements"""
        
        # Check for bare raise outside except block
        if node.exc is None:
            # This is a bare raise - check if it's in an except handler context
            # This is a simplified check
            pass
        
        # Check for raising generic exceptions
        elif hasattr(node.exc, 'func') and hasattr(node.exc.func, 'id'):
            if node.exc.func.id in self.generic_exceptions:
                self._add_issue(
                    str(file_path), node.lineno, "generic_raise",
                    f"Raising generic exception: {node.exc.func.id}",
                    "low", "Consider raising more specific custom exceptions",
                    self._get_code_snippet(lines, node.lineno, node.lineno + 1)
                )
    
    def _analyze_context_manager(self, node: ast.With, file_path: Path, lines: List[str]):
        """Analyze context manager usage"""
        
        # Good practice check - context managers are generally good for resource management
        # We can check if files are being opened without context managers elsewhere
        pass
    
    def _analyze_patterns(self, lines: List[str], file_path: Path):
        """Analyze lines for error handling anti-patterns"""
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip().lower()
            
            # Check for file operations without context managers
            if re.search(r'\bopen\s*\(', line) and 'with ' not in line:
                self._add_issue(
                    str(file_path), i, "file_without_context",
                    "File operation without context manager",
                    "medium", "Use 'with open()' for proper resource management",
                    line.strip()
                )
            
            # Check for assertion errors in production code (not test files)
            if 'assert ' in line_stripped and not self._is_test_file(file_path):
                self._add_issue(
                    str(file_path), i, "assertion_in_production",
                    "Assert statement in production code",
                    "low", "Replace with proper exception raising",
                    line.strip()
                )
            
            # Check for print statements in exception handling
            if ('except:' in line_stripped or 'except ' in line_stripped) and i < len(lines):
                next_lines = lines[i:i+3]  # Check next few lines
                for j, next_line in enumerate(next_lines):
                    if 'print(' in next_line.lower():
                        self._add_issue(
                            str(file_path), i + j + 1, "print_in_except",
                            "Using print() in exception handler instead of logging",
                            "medium", "Use logging instead of print for error messages",
                            next_line.strip()
                        )
                        break
    
    def _check_resource_usage_in_try(self, node: ast.Try) -> bool:
        """Check if try block contains resource usage that needs cleanup"""
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if hasattr(child.func, 'id'):
                    if child.func.id in ['open', 'connect', 'socket', 'acquire']:
                        return True
                elif hasattr(child.func, 'attr'):
                    if child.func.attr in ['connect', 'open', 'acquire', 'lock']:
                        return True
        
        return False
    
    def _has_logging_in_handler(self, node: ast.ExceptHandler) -> bool:
        """Check if exception handler contains logging statements"""
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if hasattr(child.func, 'attr'):
                    if child.func.attr in ['error', 'warning', 'exception', 'critical']:
                        return True
                elif hasattr(child.func, 'id'):
                    if child.func.id in ['logging', 'logger']:
                        return True
        
        return False
    
    def _is_test_file(self, file_path: Path) -> bool:
        """Check if file is a test file"""
        path_str = str(file_path).lower()
        return 'test' in path_str or 'tests' in path_str
    
    def _get_code_snippet(self, lines: List[str], start: int, end: int) -> str:
        """Get code snippet for context"""
        if start < 1:
            start = 1
        if end > len(lines):
            end = len(lines)
        
        snippet_lines = lines[start-1:end]
        return '\n'.join(snippet_lines)
    
    def _add_issue(self, file_path: str, line_number: int, issue_type: str, 
                  description: str, severity: str, suggestion: str, code_snippet: str = ""):
        """Add an error handling issue"""
        issue = ErrorHandlingIssue(file_path, line_number, issue_type, description, 
                                  severity, suggestion, code_snippet)
        self.issues.append(issue)
        self.stats["total_issues"] += 1
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            "__pycache__", ".git", "venv", "env", ".pytest_cache", "migrations", "alembic"
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive error handling report"""
        
        # Group issues by type and severity
        issues_by_type = {}
        issues_by_severity = {"critical": [], "high": [], "medium": [], "low": []}
        
        for issue in self.issues:
            # Group by type
            if issue.issue_type not in issues_by_type:
                issues_by_type[issue.issue_type] = []
            issues_by_type[issue.issue_type].append(issue)
            
            # Group by severity
            issues_by_severity[issue.severity].append(issue)
        
        # Find most problematic files
        file_issue_counts = {}
        for issue in self.issues:
            if issue.file_path not in file_issue_counts:
                file_issue_counts[issue.file_path] = 0
            file_issue_counts[issue.file_path] += 1
        
        top_files = sorted(file_issue_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Calculate error handling score
        error_score = self._calculate_error_handling_score()
        
        return {
            "statistics": self.stats,
            "issues_by_type": {k: len(v) for k, v in issues_by_type.items()},
            "issues_by_severity": {k: len(v) for k, v in issues_by_severity.items()},
            "top_problematic_files": top_files,
            "critical_issues": [issue for issue in self.issues if issue.severity == "critical"][:10],
            "high_priority_issues": [issue for issue in self.issues if issue.severity == "high"][:15],
            "recommendations": self._generate_recommendations(issues_by_type),
            "error_handling_score": error_score,
            "detailed_issues": self.issues[:20]  # First 20 for review
        }
    
    def _calculate_error_handling_score(self) -> float:
        """Calculate error handling quality score (0-100)"""
        if self.stats["files_analyzed"] == 0:
            return 100.0
        
        # Weight different issue types
        penalty = (
            self.stats["bare_except"] * 10 +
            self.stats["silent_failures"] * 8 +
            self.stats["generic_exceptions"] * 3 +
            self.stats["missing_logging"] * 2 +
            (self.stats["total_issues"] - sum([
                self.stats["bare_except"],
                self.stats["silent_failures"], 
                self.stats["generic_exceptions"],
                self.stats["missing_logging"]
            ])) * 1
        )
        
        # Normalize by file count
        penalty_per_file = penalty / self.stats["files_analyzed"]
        score = max(0, 100 - penalty_per_file)
        
        return round(score, 1)
    
    def _generate_recommendations(self, issues_by_type: Dict[str, List[ErrorHandlingIssue]]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if "bare_except" in issues_by_type:
            count = len(issues_by_type["bare_except"])
            recommendations.append(f"CRITICAL: Replace {count} bare except clauses with specific exceptions")
        
        if "silent_failure" in issues_by_type:
            count = len(issues_by_type["silent_failure"])
            recommendations.append(f"HIGH: Fix {count} silent failure handlers - add logging and proper handling")
        
        if "missing_logging" in issues_by_type:
            count = len(issues_by_type["missing_logging"])
            recommendations.append(f"Add logging to {count} exception handlers")
        
        if "generic_exception" in issues_by_type:
            count = len(issues_by_type["generic_exception"])
            recommendations.append(f"Replace {count} generic exception catches with specific exceptions")
        
        if "file_without_context" in issues_by_type:
            count = len(issues_by_type["file_without_context"])
            recommendations.append(f"Convert {count} file operations to use context managers")
        
        return recommendations

def main():
    analyzer = ErrorHandlingAnalyzer()
    current_dir = Path(".")
    
    print("Starting Error Handling Analysis...")
    print("=" * 50)
    
    report = analyzer.analyze_directory(current_dir)
    
    print(f"\nError Handling Analysis Results:")
    print(f"Files analyzed: {report['statistics']['files_analyzed']}")
    print(f"Total issues found: {report['statistics']['total_issues']}")
    print(f"Error Handling Score: {report['error_handling_score']}/100")
    
    print(f"\nIssues by Severity:")
    for severity, count in report["issues_by_severity"].items():
        if count > 0:
            print(f"- {severity.title()}: {count}")
    
    print(f"\nIssue Types:")
    for issue_type, count in report["issues_by_type"].items():
        if count > 0:
            print(f"- {issue_type}: {count}")
    
    print(f"\nTop 5 Files Needing Error Handling Improvements:")
    for file_path, count in report["top_problematic_files"][:5]:
        file_name = Path(file_path).name
        print(f"- {file_name}: {count} issues")
    
    print(f"\nHigh Priority Issues (First 10):")
    high_issues = report["high_priority_issues"]
    for issue in high_issues[:10]:
        file_name = Path(issue.file_path).name
        print(f"- {file_name}:{issue.line_number} [{issue.severity}] {issue.description}")
        if issue.code_snippet:
            print(f"  Code: {issue.code_snippet}")
        print(f"  Suggestion: {issue.suggestion}")
    
    print(f"\nKey Recommendations:")
    for rec in report["recommendations"]:
        print(f"- {rec}")
    
    return report

if __name__ == "__main__":
    main()