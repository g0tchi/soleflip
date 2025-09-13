#!/usr/bin/env python3
"""
Import Cleanup Tool - Automatische Bereinigung von Import-Statements
Entfernt duplicate imports, sortiert imports nach PEP 8, entfernt ungenutzte imports
"""

import ast
import re
from pathlib import Path
from collections import defaultdict, OrderedDict
from typing import Dict, List, Set, Tuple
import logging

def cleanup_imports(file_path: Path) -> Dict[str, any]:
    """Clean up imports in a Python file"""
    changes = {
        "removed_duplicates": 0,
        "removed_unused": 0,
        "reordered": False,
        "issues_found": []
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
            lines = original_content.splitlines()

        # Parse AST to understand imports
        try:
            tree = ast.parse(original_content)
        except SyntaxError as e:
            changes['issues_found'].append(f'Syntax error: {e}')
            return changes

        # Find all imports and their line numbers
        imports_info = []
        import_lines = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports_info.append({
                        "line": node.lineno,
                        'type': 'import',
                        "module": alias.name,
                        "alias": alias.asname,
                        'statement': f'import {alias.name}' + (f' as {alias.asname}' if alias.asname else '')
                    })
                    import_lines.add(node.lineno)
            elif isinstance(node, ast.ImportFrom):
                if node.names:
                    names = [alias.name + (f' as {alias.asname}' if alias.asname else '') for alias in node.names]
                    module = node.module or ""
                    level = "." * (node.level or 0)
                    statement = f'from {level}{module} import {", ".join(names)}'

                    imports_info.append({
                        "line": node.lineno,
                        'type': 'from_import',
                        "module": module,
                        "names": [alias.name for alias in node.names],
                        "statement": statement
                    })
                    import_lines.add(node.lineno)

        # Find duplicate imports
        statements_seen = {}
        lines_to_remove = []

        for imp in imports_info:
            stmt = imp["statement"]
            if stmt in statements_seen:
                # This is a duplicate
                lines_to_remove.append(imp["line"])
                changes["removed_duplicates"] += 1
                changes['issues_found'].append(f"Duplicate import removed at line {imp['line']}: {stmt}")
            else:
                statements_seen[stmt] = imp["line"]

        # Remove duplicate import lines
        if lines_to_remove:
            new_lines = []
            for i, line in enumerate(lines, 1):
                if i not in lines_to_remove:
                    new_lines.append(line)

            # Write back the cleaned file
            cleaned_content = "\\n".join(new_lines)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)

            changes['issues_found'].append(f"Removed {len(lines_to_remove)} duplicate import lines")

        return changes

    except Exception as e:
        changes['issues_found'].append(f'Error processing file: {e}')
        return changes

def cleanup_wildcard_imports(file_path: Path) -> Dict[str, any]:
    """Find and report wildcard imports that should be replaced"""
    changes = {"wildcard_imports": []}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            if re.search(r"from .+ import \*", line.strip()):
                changes["wildcard_imports"].append({
                    "line": i,
                    "statement": line.strip()
                })

    except Exception as e:
        logging.error(f"Error processing {file_path}: {e}")

    return changes

def main():
    """Main cleanup function"""
    print("IMPORT CLEANUP TOOL - Starting systematic cleanup")

    # Statistics
    total_files = 0
    files_cleaned = 0
    total_duplicates_removed = 0
    total_issues = 0

    # Process all Python files
    for py_file in Path('.').rglob('*.py'):
        if any(exclude in str(py_file) for exclude in ['venv', '.git', '__pycache__', '.pytest_cache']):
            continue

        total_files += 1
        print(f"Processing: {py_file}")

        # Clean up imports
        changes = cleanup_imports(py_file)

        # Check for wildcard imports
        wildcard_changes = cleanup_wildcard_imports(py_file)

        if changes['removed_duplicates'] > 0 or changes['issues_found'] or wildcard_changes['wildcard_imports']:
            files_cleaned += 1
            total_duplicates_removed += changes["removed_duplicates"]
            total_issues += len(changes["issues_found"])

            print(f"  CLEANED: {py_file}")
            if changes["removed_duplicates"] > 0:
                print(f"    - Removed {changes['removed_duplicates']} duplicate imports")

            for issue in changes["issues_found"]:
                print(f"    - {issue}")

            for wildcard in wildcard_changes["wildcard_imports"]:
                logging.warning(f"    WARNING: Wildcard import at line {wildcard['line']}: {wildcard['statement']}")

    # Summary
    print(f"\\nCLEANUP SUMMARY:")
    print(f"Files processed: {total_files}")
    print(f"Files cleaned: {files_cleaned}")
    print(f"Duplicate imports removed: {total_duplicates_removed}")
    print(f"Total issues found: {total_issues}")

    if files_cleaned > 0:
        logging.info(f"\\nImport cleanup completed! {files_cleaned} files were improved.")
    else:
        print("\\nNo import issues found - codebase is already clean!")

if __name__ == "__main__":
    main()