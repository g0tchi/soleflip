"""
Performance Analyzer for Codebase
Identifies inefficient code patterns, potential bottlenecks, and optimization opportunities.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Set
from dataclasses import dataclass
import logging

@dataclass
class PerformanceIssue:
    file_path: str
    line_number: int
    issue_type: str
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    suggestion: str

class PerformanceAnalyzer:
    def __init__(self):
        self.issues: List[PerformanceIssue] = []
        self.stats = {
            "files_analyzed": 0,
            "total_issues": 0,
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 0,
            "low_issues": 0
        }
        
        # Performance anti-patterns
        self.inefficient_patterns = {
            # Database queries
            "n_plus_one": [r"\.get\(.*\)", r"\.filter\(.*\)\.first\(\)", r"\.query\(.*\)"],
            "missing_indexes": [r"\.filter\(.*==.*\)", r"\.filter_by\(.*\)"],
            "bulk_operations": [r"for.*in.*:", r"session\.add\("],
            
            # List/Dict operations
            "list_append_in_loop": [r"for.*in.*:", r"\.append\("],
            "dict_get_default": [r"\[.*\]\s*=.*", r"if.*in.*:"],
            "inefficient_membership": [r"if.*in.*list", r"for.*in.*list"],
            
            # String operations
            "string_concatenation": [r"\+.*str", r"\".*\"\s*\+"],
            "regex_in_loop": [r"re\.(match|search|findall)", r"for.*in"],
            
            # I/O operations
            "sync_io_in_async": [r"open\(", r"with.*open"],
            "multiple_file_ops": [r"open\(.*\)", r"\.read\(\)", r"\.write\("],
        }
    
    def analyze_directory(self, directory: Path) -> Dict[str, Any]:
        """Analyze all Python files for performance issues"""
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
        """Analyze a single file for performance issues"""
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
            self._analyze_ast(tree, file_path, content)
        except SyntaxError:
            return
        
        # Line-by-line pattern analysis
        self._analyze_patterns(lines, file_path)
    
    def _analyze_ast(self, tree: ast.AST, file_path: Path, content: str):
        """Analyze AST for performance anti-patterns"""
        
        # Track function contexts
        function_contexts = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._analyze_function_performance(node, file_path, content)
                
                # Check for async/await patterns
                if self._is_async_function(node):
                    self._check_async_performance(node, file_path, content)
            
            elif isinstance(node, ast.For):
                self._analyze_loop_performance(node, file_path)
            
            elif isinstance(node, ast.ListComp):
                self._analyze_list_comprehension(node, file_path)
            
            elif isinstance(node, ast.Call):
                self._analyze_function_call(node, file_path)
    
    def _analyze_function_performance(self, node: ast.FunctionDef, file_path: Path, content: str):
        """Analyze function for performance issues"""
        
        # Check function complexity
        complexity = self._calculate_cyclomatic_complexity(node)
        if complexity > 10:
            self._add_issue(
                str(file_path), node.lineno, "high_complexity",
                f"Function '{node.name}' has high cyclomatic complexity ({complexity})",
                "high", "Consider breaking down into smaller functions"
            )
        
        # Check for deep nesting
        max_depth = self._calculate_nesting_depth(node)
        if max_depth > 5:
            self._add_issue(
                str(file_path), node.lineno, "deep_nesting",
                f"Function '{node.name}' has deep nesting (depth {max_depth})",
                "medium", "Refactor to reduce nesting levels"
            )
        
        # Check for database queries in loops
        has_loop = False
        has_query = False
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.While)):
                has_loop = True
            if isinstance(child, ast.Call) and hasattr(child.func, 'attr'):
                if child.func.attr in ['get', 'filter', 'query', 'execute']:
                    has_query = True
        
        if has_loop and has_query:
            self._add_issue(
                str(file_path), node.lineno, "query_in_loop",
                f"Function '{node.name}' may have database queries in loops",
                "critical", "Use bulk operations or prefetch data"
            )
    
    def _analyze_loop_performance(self, node: ast.For, file_path: Path):
        """Analyze loop for performance issues"""
        
        # Check for list operations in loops
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and hasattr(child.func, 'attr'):
                if child.func.attr == 'append':
                    self._add_issue(
                        str(file_path), node.lineno, "list_append_loop",
                        "List.append() in loop - consider list comprehension",
                        "medium", "Use list comprehension or pre-allocate list"
                    )
                elif child.func.attr in ['get', 'pop', 'remove']:
                    self._add_issue(
                        str(file_path), node.lineno, "inefficient_list_ops",
                        f"Inefficient list operation ({child.func.attr}) in loop",
                        "medium", "Consider using collections.deque or different data structure"
                    )
    
    def _analyze_list_comprehension(self, node: ast.ListComp, file_path: Path):
        """Analyze list comprehension for efficiency"""
        
        # Check for nested list comprehensions
        nested_count = 0
        for generator in node.generators:
            if isinstance(generator.iter, ast.ListComp):
                nested_count += 1
        
        if nested_count > 1:
            self._add_issue(
                str(file_path), node.lineno, "nested_comprehension",
                "Deeply nested list comprehension",
                "medium", "Consider breaking into separate steps for readability"
            )
    
    def _analyze_function_call(self, node: ast.Call, file_path: Path):
        """Analyze function calls for performance issues"""
        
        if hasattr(node.func, 'id'):
            func_name = node.func.id
            
            # Check for inefficient built-ins
            if func_name == "len" and len(node.args) == 1:
                # Check if len() is used in condition that could use truthiness
                self._add_issue(
                    str(file_path), node.lineno, "unnecessary_len",
                    "len() used where truthiness check might suffice",
                    "low", "Consider using 'if container:' instead of 'if len(container) > 0:'"
                )
        
        elif hasattr(node.func, 'attr'):
            attr_name = node.func.attr
            
            # Check for string operations that could be optimized
            if attr_name == "join" and isinstance(node.func.value, ast.Str):
                if node.func.value.s == "":
                    self._add_issue(
                        str(file_path), node.lineno, "string_join",
                        "Using ''.join() - good practice for string concatenation",
                        "low", "Confirm this is more efficient than alternatives"
                    )
    
    def _check_async_performance(self, node: ast.FunctionDef, file_path: Path, content: str):
        """Check async function for performance issues"""
        
        # Look for synchronous I/O in async functions
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if hasattr(child.func, 'id') and child.func.id == 'open':
                    self._add_issue(
                        str(file_path), child.lineno, "sync_io_async",
                        "Synchronous I/O in async function",
                        "high", "Use aiofiles or async equivalent"
                    )
                
                # Check for missing await
                if hasattr(child.func, 'attr'):
                    async_methods = ['get', 'post', 'put', 'delete', 'execute', 'commit']
                    if child.func.attr in async_methods:
                        # This is a simplified check - in practice need more context
                        parent = self._get_parent_node(child, node)
                        if not isinstance(parent, ast.Await):
                            self._add_issue(
                                str(file_path), child.lineno, "missing_await",
                                f"Potentially missing await for async operation",
                                "high", "Ensure async operations are properly awaited"
                            )
    
    def _analyze_patterns(self, lines: List[str], file_path: Path):
        """Analyze lines for performance anti-patterns"""
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # String concatenation in loops
            if "for " in line_stripped and ("+" in line_stripped or "+=" in line_stripped):
                if any(quote in line_stripped for quote in ['"', "'"]):
                    self._add_issue(
                        str(file_path), i, "string_concat_loop",
                        "String concatenation in loop",
                        "medium", "Use join() or f-strings for better performance"
                    )
            
            # Multiple database queries pattern
            if ".get(" in line_stripped or ".filter(" in line_stripped:
                if i < len(lines) - 1:
                    next_line = lines[i].strip()
                    if ".get(" in next_line or ".filter(" in next_line:
                        self._add_issue(
                            str(file_path), i, "multiple_queries",
                            "Multiple sequential database queries",
                            "high", "Consider using batch operations or joins"
                        )
            
            # Inefficient dictionary access
            if 'if ' in line_stripped and ' in ' in line_stripped and '[' in line_stripped:
                self._add_issue(
                    str(file_path), i, "dict_key_check",
                    "Potential inefficient dictionary access pattern",
                    "low", "Consider using dict.get() with default value"
                )
            
            # Regular expressions without compilation
            if 're.match(' in line_stripped or 're.search(' in line_stripped:
                self._add_issue(
                    str(file_path), i, "uncompiled_regex",
                    "Regular expression without pre-compilation",
                    "medium", "Compile regex patterns for repeated use"
                )
            
            # Large file operations without chunking
            if ".read()" in line_stripped and "with open" not in line_stripped:
                self._add_issue(
                    str(file_path), i, "large_file_read",
                    "Reading entire file into memory",
                    "medium", "Consider reading in chunks for large files"
                )
    
    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _calculate_nesting_depth(self, node: ast.AST, depth: int = 0) -> int:
        """Calculate maximum nesting depth"""
        max_depth = depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._calculate_nesting_depth(child, depth)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _is_async_function(self, node: ast.FunctionDef) -> bool:
        """Check if function is async"""
        return isinstance(node, ast.AsyncFunctionDef)
    
    def _get_parent_node(self, child: ast.AST, root: ast.AST) -> ast.AST:
        """Get parent node of child (simplified implementation)"""
        for node in ast.walk(root):
            for child_node in ast.iter_child_nodes(node):
                if child_node == child:
                    return node
        return None
    
    def _add_issue(self, file_path: str, line_number: int, issue_type: str, 
                  description: str, severity: str, suggestion: str):
        """Add a performance issue"""
        issue = PerformanceIssue(file_path, line_number, issue_type, description, severity, suggestion)
        self.issues.append(issue)
        self.stats["total_issues"] += 1
        self.stats[f"{severity}_issues"] += 1
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            "__pycache__", ".git", "venv", "env", ".pytest_cache", "migrations", "alembic",
            "test_", "tests"  # Skip test files for performance analysis
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        
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
        
        # Generate recommendations
        recommendations = self._generate_performance_recommendations(issues_by_type)
        
        return {
            "statistics": self.stats,
            "issues_by_type": {k: len(v) for k, v in issues_by_type.items()},
            "issues_by_severity": {k: len(v) for k, v in issues_by_severity.items()},
            "top_problematic_files": top_files,
            "critical_issues": [issue for issue in self.issues if issue.severity == "critical"][:10],
            "high_priority_issues": [issue for issue in self.issues if issue.severity == "high"][:15],
            "recommendations": recommendations,
            "performance_score": self._calculate_performance_score()
        }
    
    def _generate_performance_recommendations(self, issues_by_type: Dict[str, List[PerformanceIssue]]) -> List[str]:
        """Generate actionable performance recommendations"""
        recommendations = []
        
        # Critical issues first
        if "query_in_loop" in issues_by_type:
            count = len(issues_by_type["query_in_loop"])
            recommendations.append(f"CRITICAL: Fix {count} database queries in loops - major performance impact")
        
        if "sync_io_async" in issues_by_type:
            count = len(issues_by_type["sync_io_async"])
            recommendations.append(f"HIGH: Replace {count} synchronous I/O operations in async functions")
        
        if "high_complexity" in issues_by_type:
            count = len(issues_by_type["high_complexity"])
            recommendations.append(f"Refactor {count} highly complex functions to improve maintainability")
        
        if "string_concat_loop" in issues_by_type:
            count = len(issues_by_type["string_concat_loop"])
            recommendations.append(f"Optimize {count} string concatenations in loops")
        
        if "uncompiled_regex" in issues_by_type:
            count = len(issues_by_type["uncompiled_regex"])
            recommendations.append(f"Compile {count} regular expressions for better performance")
        
        return recommendations
    
    def _calculate_performance_score(self) -> float:
        """Calculate overall performance score (0-100)"""
        if self.stats["files_analyzed"] == 0:
            return 100.0
        
        total_weight = (
            self.stats["critical_issues"] * 10 +
            self.stats["high_issues"] * 5 +
            self.stats["medium_issues"] * 2 +
            self.stats["low_issues"] * 1
        )
        
        # Normalize based on file count
        penalty = total_weight / self.stats["files_analyzed"]
        score = max(0, 100 - penalty)
        
        return round(score, 1)

def main():
    analyzer = PerformanceAnalyzer()
    current_dir = Path(".")
    
    print("Starting Performance Analysis...")
    print("=" * 60)
    
    report = analyzer.analyze_directory(current_dir)
    
    print(f"\nPerformance Analysis Results:")
    print(f"Files analyzed: {report['statistics']['files_analyzed']}")
    print(f"Total issues found: {report['statistics']['total_issues']}")
    print(f"Performance Score: {report['performance_score']}/100")
    
    print(f"\nIssues by Severity:")
    for severity, count in report["issues_by_severity"].items():
        if count > 0:
            print(f"- {severity.title()}: {count}")
    
    print(f"\nIssues by Type:")
    for issue_type, count in report["issues_by_type"].items():
        print(f"- {issue_type}: {count}")
    
    print(f"\nTop 5 Files Needing Optimization:")
    for file_path, count in report["top_problematic_files"][:5]:
        file_name = Path(file_path).name
        print(f"- {file_name}: {count} issues")
    
    print(f"\nCritical Performance Issues:")
    for issue in report["critical_issues"]:
        file_name = Path(issue.file_path).name
        print(f"- {file_name}:{issue.line_number} {issue.description}")
        print(f"  Suggestion: {issue.suggestion}")
    
    print(f"\nKey Recommendations:")
    for rec in report["recommendations"]:
        print(f"- {rec}")
    
    return report

if __name__ == "__main__":
    main()