"""
Code Style Consistency Analyzer
Analyzes Python files for formatting, naming conventions, and style inconsistencies.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Any
from dataclasses import dataclass
import logging

@dataclass
class StyleIssue:
    file_path: str
    line_number: int
    issue_type: str
    description: str
    severity: str  # 'low', 'medium', 'high'

class CodeStyleAnalyzer:
    def __init__(self):
        self.issues: List[StyleIssue] = []
        self.stats = {
            "files_analyzed": 0,
            "total_issues": 0,
            "naming_issues": 0,
            "formatting_issues": 0,
            "convention_issues": 0
        }

        # Naming convention patterns
        self.snake_case_pattern = re.compile(r"^[a-z_][a-z0-9_]*$")
        self.pascal_case_pattern = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
        self.constant_pattern = re.compile(r"^[A-Z][A-Z0-9_]*$")

    def analyze_directory(self, directory: Path) -> Dict[str, Any]:
        """Analyze all Python files in directory for style issues"""
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
        """Analyze a single Python file for style issues"""
        self.stats["files_analyzed"] += 1

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
                    lines = content.splitlines()
            except Exception:
                return

        # Parse AST for structural analysis
        try:
            tree = ast.parse(content)
            self._analyze_ast(tree, file_path, lines)
        except SyntaxError:
            self._add_issue(str(file_path), 1, 'syntax_error', 'File contains syntax errors', 'high')

        # Line-by-line analysis
        self._analyze_lines(lines, file_path)

    def _analyze_ast(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Analyze AST for naming and structure issues"""

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._check_function_naming(node, file_path)
                self._check_function_complexity(node, file_path, lines)

            elif isinstance(node, ast.ClassDef):
                self._check_class_naming(node, file_path)

            elif isinstance(node, ast.Assign):
                self._check_variable_naming(node, file_path)

            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                self._check_import_style(node, file_path)

    def _analyze_lines(self, lines: List[str], file_path: Path):
        """Analyze individual lines for formatting issues"""

        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 120:
                self._add_issue(str(file_path), i, "line_length",
                              f'Line too long ({len(line)} characters)', 'medium')

            # Check trailing whitespace
            if line.rstrip() != line:
                self._add_issue(str(file_path), i, "trailing_whitespace",
                              'Trailing whitespace found', 'low')

            # Check inconsistent indentation
            if line.strip() and not line.startswith((' ' * 4, '\t')):
                leading_spaces = len(line) - len(line.lstrip(" "))
                if leading_spaces > 0 and leading_spaces % 4 != 0:
                    self._add_issue(str(file_path), i, "indentation",
                                  'Inconsistent indentation (not multiple of 4)', 'medium')

            # Check for print statements (should use logging)
            if 'print(' in line and not line.strip().startswith('#'):
                self._add_issue(str(file_path), i, "print_statement",
                              'Use logging instead of print statements', 'medium')

            # Check string quotes consistency
            if "'" in line and '"' in line:
                # Complex check for mixed quotes in same line
                single_quotes = line.count("'") - line.count("\\'")
                double_quotes = line.count('"') - line.count('\\"')
                if single_quotes > 0 and double_quotes > 0:
                    self._add_issue(str(file_path), i, "quote_consistency",
                                  'Mixed quote styles in same line', 'low')

    def _check_function_naming(self, node: ast.FunctionDef, file_path: Path):
        """Check function naming conventions"""
        if not self.snake_case_pattern.match(node.name):
            if not node.name.startswith("_"):  # Allow private methods
                self._add_issue(str(file_path), node.lineno, "naming_convention",
                              f'Function name "{node.name}" should use snake_case', 'medium')

    def _check_class_naming(self, node: ast.ClassDef, file_path: Path):
        """Check class naming conventions"""
        if not self.pascal_case_pattern.match(node.name):
            self._add_issue(str(file_path), node.lineno, "naming_convention",
                          f'Class name "{node.name}" should use PascalCase', 'medium')

    def _check_variable_naming(self, node: ast.Assign, file_path: Path):
        """Check variable naming conventions"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                # Skip constants (all uppercase)
                if name.isupper():
                    if not self.constant_pattern.match(name):
                        self._add_issue(str(file_path), node.lineno, "naming_convention",
                                      f'Constant "{name}" should use UPPER_CASE', 'low')
                else:
                    if not self.snake_case_pattern.match(name) and not name.startswith("_"):
                        self._add_issue(str(file_path), node.lineno, "naming_convention",
                                      f'Variable "{name}" should use snake_case', 'low')

    def _check_function_complexity(self, node: ast.FunctionDef, file_path: Path, lines: List[str]):
        """Check function complexity and length"""
        # Count lines in function
        if hasattr(node, "end_lineno") and node.end_lineno:
            func_lines = node.end_lineno - node.lineno + 1
            if func_lines > 50:
                self._add_issue(str(file_path), node.lineno, "function_length",
                              f'Function "{node.name}" is too long ({func_lines} lines)', 'high')

        # Count nested levels
        max_depth = self._calculate_nesting_depth(node)
        if max_depth > 4:
            self._add_issue(str(file_path), node.lineno, "complexity",
                          f'Function "{node.name}" has deep nesting (depth {max_depth})', 'high')

    def _check_import_style(self, node: ast.AST, file_path: Path):
        """Check import statement style"""
        if isinstance(node, ast.Import):
            if len(node.names) > 1:
                self._add_issue(str(file_path), node.lineno, "import_style",
                              'Multiple imports on single line', 'low')

    def _calculate_nesting_depth(self, node: ast.AST, depth: int = 0) -> int:
        """Calculate maximum nesting depth in AST node"""
        max_depth = depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._calculate_nesting_depth(child, depth)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def _add_issue(self, file_path: str, line_number: int, issue_type: str, description: str, severity: str):
        """Add a style issue to the list"""
        issue = StyleIssue(file_path, line_number, issue_type, description, severity)
        self.issues.append(issue)
        self.stats["total_issues"] += 1

        if issue_type in ["naming_convention"]:
            self.stats["naming_issues"] += 1
        elif issue_type in ['line_length', 'trailing_whitespace', 'indentation', 'quote_consistency']:
            self.stats["formatting_issues"] += 1
        else:
            self.stats["convention_issues"] += 1

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            "__pycache__",
            ".git",
            "venv",
            "env",
            ".pytest_cache",
            "migrations",
            "alembic"
        ]

        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)

    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive style analysis report"""

        # Group issues by type
        issues_by_type = {}
        for issue in self.issues:
            if issue.issue_type not in issues_by_type:
                issues_by_type[issue.issue_type] = []
            issues_by_type[issue.issue_type].append(issue)

        # Group issues by severity
        issues_by_severity = {'high': [], 'medium': [], 'low': []}
        for issue in self.issues:
            issues_by_severity[issue.severity].append(issue)

        # Top problematic files
        file_issue_counts = {}
        for issue in self.issues:
            if issue.file_path not in file_issue_counts:
                file_issue_counts[issue.file_path] = 0
            file_issue_counts[issue.file_path] += 1

        top_files = sorted(file_issue_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "statistics": self.stats,
            "issues_by_type": {k: len(v) for k, v in issues_by_type.items()},
            "issues_by_severity": {k: len(v) for k, v in issues_by_severity.items()},
            "top_problematic_files": top_files,
            "detailed_issues": self.issues[:50],  # First 50 for review
            "recommendations": self._generate_recommendations(issues_by_type)
        }

    def _generate_recommendations(self, issues_by_type: Dict[str, List[StyleIssue]]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if "print_statement" in issues_by_type:
            count = len(issues_by_type["print_statement"])
            recommendations.append(f"Replace {count} print statements with proper logging")

        if "function_length" in issues_by_type:
            count = len(issues_by_type["function_length"])
            recommendations.append(f"Refactor {count} overly long functions into smaller units")

        if "naming_convention" in issues_by_type:
            count = len(issues_by_type["naming_convention"])
            recommendations.append(f"Fix {count} naming convention violations")

        if "line_length" in issues_by_type:
            count = len(issues_by_type["line_length"])
            recommendations.append(f"Wrap {count} overly long lines")

        return recommendations

def main():
    analyzer = CodeStyleAnalyzer()
    current_dir = Path(".")

    print("Starting Code Style Consistency Analysis...")
    print("=" * 60)

    report = analyzer.analyze_directory(current_dir)

    print(f"\nCode Style Analysis Results:")
    print(f"Files analyzed: {report['statistics']['files_analyzed']}")
    print(f"Total issues found: {report['statistics']['total_issues']}")
    print(f"- Naming issues: {report['statistics']['naming_issues']}")
    print(f"- Formatting issues: {report['statistics']['formatting_issues']}")
    print(f"- Convention issues: {report['statistics']['convention_issues']}")

    print(f"\nIssues by Severity:")
    for severity, count in report["issues_by_severity"].items():
        print(f"- {severity.title()}: {count}")

    print(f"\nIssues by Type:")
    for issue_type, count in report["issues_by_type"].items():
        print(f"- {issue_type}: {count}")

    print(f"\nTop 10 Files with Most Issues:")
    for file_path, count in report["top_problematic_files"]:
        relative_path = Path(file_path).name
        print(f"- {relative_path}: {count} issues")

    print(f"\nKey Recommendations:")
    for rec in report["recommendations"]:
        print(f"- {rec}")

    print(f"\nFirst 10 Critical Issues:")
    high_priority = [issue for issue in report["detailed_issues"]
                    if issue.severity in ['high', 'medium']][:10]

    for issue in high_priority:
        file_name = Path(issue.file_path).name
        print(f"- {file_name}:{issue.line_number} [{issue.severity}] {issue.description}")

    return report

if __name__ == "__main__":
    main()