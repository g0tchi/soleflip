"""
Documentation Analysis Tool
Analyzes Python files for documentation quality, missing docstrings, and comment patterns.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass
import logging

@dataclass
class DocumentationIssue:
    file_path: str
    line_number: int
    issue_type: str
    description: str
    severity: str  # 'low', 'medium', 'high'
    suggestion: str
    element_name: str = ""

class DocumentationAnalyzer:
    def __init__(self):
        self.issues: List[DocumentationIssue] = []
        self.stats = {
            "files_analyzed": 0,
            "total_functions": 0,
            "documented_functions": 0,
            "total_classes": 0,
            "documented_classes": 0,
            "total_modules": 0,
            "documented_modules": 0,
            "total_issues": 0
        }
    
    def analyze_directory(self, directory: Path) -> Dict[str, Any]:
        """Analyze all Python files for documentation quality"""
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
        """Analyze a single file for documentation issues"""
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
        
        # Check module-level documentation
        self._check_module_documentation(tree, file_path, lines)
    
    def _analyze_ast(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Analyze AST for documentation patterns"""
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._analyze_function_documentation(node, file_path, lines)
            elif isinstance(node, ast.AsyncFunctionDef):
                self._analyze_function_documentation(node, file_path, lines)
            elif isinstance(node, ast.ClassDef):
                self._analyze_class_documentation(node, file_path, lines)
    
    def _check_module_documentation(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Check module-level documentation"""
        self.stats["total_modules"] += 1
        
        # Check for module docstring
        if isinstance(tree.body[0] if tree.body else None, ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
            if isinstance(tree.body[0].value.value, str):
                docstring = tree.body[0].value.value.strip()
                if len(docstring) > 10:  # Reasonable docstring length
                    self.stats["documented_modules"] += 1
                    return
        
        # No module docstring found
        file_name = file_path.name
        if not file_name.startswith('__') and file_name != 'conftest.py':  # Skip __init__.py and conftest.py
            self._add_issue(
                str(file_path), 1, "missing_module_docstring",
                "Module missing docstring", "medium",
                "Add module-level docstring describing the module's purpose",
                file_name
            )
    
    def _analyze_function_documentation(self, node: ast.FunctionDef, file_path: Path, lines: List[str]):
        """Analyze function documentation"""
        self.stats["total_functions"] += 1
        
        # Skip private methods and test functions for basic checks
        if node.name.startswith('_') and not node.name.startswith('__'):
            return
        if node.name.startswith('test_'):
            return
        
        # Check for docstring
        docstring = self._get_docstring(node)
        
        if not docstring:
            self._add_issue(
                str(file_path), node.lineno, "missing_function_docstring",
                f"Function '{node.name}' missing docstring", "medium",
                "Add docstring describing function purpose, parameters, and return value",
                node.name
            )
            return
        
        self.stats["documented_functions"] += 1
        
        # Analyze docstring quality
        self._analyze_docstring_quality(docstring, node, file_path, "function")
    
    def _analyze_class_documentation(self, node: ast.ClassDef, file_path: Path, lines: List[str]):
        """Analyze class documentation"""
        self.stats["total_classes"] += 1
        
        # Check for docstring
        docstring = self._get_docstring(node)
        
        if not docstring:
            self._add_issue(
                str(file_path), node.lineno, "missing_class_docstring",
                f"Class '{node.name}' missing docstring", "high",
                "Add class docstring describing purpose and usage",
                node.name
            )
            return
        
        self.stats["documented_classes"] += 1
        
        # Analyze docstring quality
        self._analyze_docstring_quality(docstring, node, file_path, "class")
        
        # Check methods within class
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Public methods should have docstrings
                if not item.name.startswith('_') or item.name == '__init__':
                    method_docstring = self._get_docstring(item)
                    if not method_docstring:
                        self._add_issue(
                            str(file_path), item.lineno, "missing_method_docstring",
                            f"Method '{item.name}' in class '{node.name}' missing docstring",
                            "medium",
                            "Add method docstring describing purpose and parameters",
                            f"{node.name}.{item.name}"
                        )
    
    def _analyze_docstring_quality(self, docstring: str, node: ast.AST, file_path: Path, element_type: str):
        """Analyze the quality of a docstring"""
        
        # Check docstring length
        if len(docstring.strip()) < 20:
            self._add_issue(
                str(file_path), node.lineno, "short_docstring",
                f"{element_type.title()} '{node.name}' has very short docstring",
                "low", "Expand docstring with more detailed description",
                node.name
            )
        
        # For functions, check if parameters are documented
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.args.args:
            param_names = [arg.arg for arg in node.args.args if arg.arg != 'self']
            
            if param_names and not any(param in docstring.lower() for param in param_names):
                self._add_issue(
                    str(file_path), node.lineno, "undocumented_parameters",
                    f"Function '{node.name}' parameters not documented in docstring",
                    "medium", "Add parameter descriptions to docstring",
                    node.name
                )
        
        # Check for return value documentation
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            has_return = any(isinstance(child, ast.Return) for child in ast.walk(node) if isinstance(child, ast.Return) and child.value is not None)
            if has_return and 'return' not in docstring.lower():
                self._add_issue(
                    str(file_path), node.lineno, "undocumented_return",
                    f"Function '{node.name}' return value not documented",
                    "low", "Add return value description to docstring",
                    node.name
                )
    
    def _get_docstring(self, node: ast.AST) -> Optional[str]:
        """Extract docstring from AST node"""
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            return node.body[0].value.value.strip()
        return None
    
    def _add_issue(self, file_path: str, line_number: int, issue_type: str, 
                  description: str, severity: str, suggestion: str, element_name: str = ""):
        """Add a documentation issue"""
        issue = DocumentationIssue(file_path, line_number, issue_type, description, 
                                  severity, suggestion, element_name)
        self.issues.append(issue)
        self.stats["total_issues"] += 1
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            "__pycache__", ".git", "venv", "env", ".pytest_cache", "migrations", 
            "alembic", "analyze_", "fix_", "cleanup_"  # Skip our analysis tools
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive documentation report"""
        
        # Calculate coverage percentages
        function_coverage = (self.stats["documented_functions"] / max(self.stats["total_functions"], 1)) * 100
        class_coverage = (self.stats["documented_classes"] / max(self.stats["total_classes"], 1)) * 100
        module_coverage = (self.stats["documented_modules"] / max(self.stats["total_modules"], 1)) * 100
        
        # Group issues by type and severity
        issues_by_type = {}
        issues_by_severity = {"high": [], "medium": [], "low": []}
        
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
        
        # Calculate overall documentation score
        doc_score = self._calculate_documentation_score(function_coverage, class_coverage, module_coverage)
        
        return {
            "statistics": self.stats,
            "coverage": {
                "function_coverage": round(function_coverage, 1),
                "class_coverage": round(class_coverage, 1),
                "module_coverage": round(module_coverage, 1),
                "overall_score": doc_score
            },
            "issues_by_type": {k: len(v) for k, v in issues_by_type.items()},
            "issues_by_severity": {k: len(v) for k, v in issues_by_severity.items()},
            "top_problematic_files": top_files,
            "high_priority_issues": [issue for issue in self.issues if issue.severity == "high"][:10],
            "recommendations": self._generate_recommendations(issues_by_type, function_coverage, class_coverage),
            "sample_fixes": self._generate_sample_fixes(issues_by_type)
        }
    
    def _calculate_documentation_score(self, func_cov: float, class_cov: float, module_cov: float) -> float:
        """Calculate overall documentation quality score"""
        # Weighted average: functions 40%, classes 35%, modules 25%
        score = (func_cov * 0.4) + (class_cov * 0.35) + (module_cov * 0.25)
        return round(score, 1)
    
    def _generate_recommendations(self, issues_by_type: Dict, func_cov: float, class_cov: float) -> List[str]:
        """Generate actionable documentation recommendations"""
        recommendations = []
        
        if func_cov < 60:
            recommendations.append(f"Function documentation coverage is low ({func_cov:.1f}%) - prioritize documenting public functions")
        
        if class_cov < 70:
            recommendations.append(f"Class documentation coverage is low ({class_cov:.1f}%) - all classes should have docstrings")
        
        if "missing_function_docstring" in issues_by_type:
            count = len(issues_by_type["missing_function_docstring"])
            recommendations.append(f"Add docstrings to {count} undocumented functions")
        
        if "missing_class_docstring" in issues_by_type:
            count = len(issues_by_type["missing_class_docstring"])
            recommendations.append(f"Add docstrings to {count} undocumented classes")
        
        if "missing_module_docstring" in issues_by_type:
            count = len(issues_by_type["missing_module_docstring"])
            recommendations.append(f"Add module docstrings to {count} files")
        
        return recommendations
    
    def _generate_sample_fixes(self, issues_by_type: Dict) -> List[Dict[str, str]]:
        """Generate sample documentation fixes"""
        fixes = []
        
        if "missing_function_docstring" in issues_by_type:
            fixes.append({
                "type": "Function Docstring",
                "before": "def calculate_price(base_price, discount):",
                "after": '''def calculate_price(base_price, discount):
    """
    Calculate final price after applying discount.
    
    Args:
        base_price (float): Original price before discount
        discount (float): Discount percentage (0-100)
        
    Returns:
        float: Final price after discount
    """'''
            })
        
        if "missing_class_docstring" in issues_by_type:
            fixes.append({
                "type": "Class Docstring", 
                "before": "class ProductManager:",
                "after": '''class ProductManager:
    """
    Manages product data and operations.
    
    This class handles CRUD operations for products,
    including validation and business logic.
    """'''
            })
        
        return fixes

def main():
    analyzer = DocumentationAnalyzer()
    current_dir = Path(".")
    
    print("Starting Documentation Analysis...")
    print("=" * 50)
    
    report = analyzer.analyze_directory(current_dir)
    
    print(f"\nDocumentation Analysis Results:")
    print(f"Files analyzed: {report['statistics']['files_analyzed']}")
    print(f"Overall Documentation Score: {report['coverage']['overall_score']}/100")
    
    print(f"\nCoverage Statistics:")
    print(f"Function Coverage: {report['coverage']['function_coverage']}% ({report['statistics']['documented_functions']}/{report['statistics']['total_functions']})")
    print(f"Class Coverage: {report['coverage']['class_coverage']}% ({report['statistics']['documented_classes']}/{report['statistics']['total_classes']})")
    print(f"Module Coverage: {report['coverage']['module_coverage']}% ({report['statistics']['documented_modules']}/{report['statistics']['total_modules']})")
    
    print(f"\nIssues by Severity:")
    for severity, count in report["issues_by_severity"].items():
        if count > 0:
            print(f"- {severity.title()}: {count}")
    
    print(f"\nIssue Types:")
    for issue_type, count in report["issues_by_type"].items():
        print(f"- {issue_type}: {count}")
    
    print(f"\nTop 5 Files Needing Documentation:")
    for file_path, count in report["top_problematic_files"][:5]:
        file_name = Path(file_path).name
        print(f"- {file_name}: {count} issues")
    
    print(f"\nHigh Priority Issues:")
    for issue in report["high_priority_issues"][:5]:
        file_name = Path(issue.file_path).name
        print(f"- {file_name}: {issue.description}")
    
    print(f"\nKey Recommendations:")
    for rec in report["recommendations"]:
        print(f"- {rec}")
    
    print(f"\nSample Documentation Fixes:")
    for fix in report["sample_fixes"]:
        print(f"\n{fix['type']}:")
        print(f"Before:\n{fix['before']}")
        print(f"After:\n{fix['after']}")
    
    return report

if __name__ == "__main__":
    main()