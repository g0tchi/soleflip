"""
Automated Error Handling Fixer
Fixes common error handling anti-patterns automatically.
"""

import re
import ast
from pathlib import Path
from typing import Dict, List, Set
import logging

class ErrorHandlingFixer:
    def __init__(self):
        self.fixes_applied = {
            "bare_except_fixed": 0,
            "silent_failures_logged": 0,
            "generic_exceptions_specified": 0,
            "print_to_logging_in_except": 0,
            "context_managers_added": 0
        }
        self.files_modified = set()
    
    def fix_directory(self, directory: Path) -> Dict[str, int]:
        """Fix error handling issues in all Python files"""
        python_files = list(directory.rglob("*.py"))
        
        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue
            
            try:
                self.fix_file(file_path)
            except Exception as e:
                logging.error(f"Error fixing {file_path}: {e}")
        
        return self._generate_summary()
    
    def fix_file(self, file_path: Path):
        """Fix error handling issues in a single file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    original_content = f.read()
            except Exception:
                return
        
        modified_content = original_content
        file_changed = False
        
        # Fix bare except clauses
        new_content = self._fix_bare_except(modified_content)
        if new_content != modified_content:
            modified_content = new_content
            file_changed = True
        
        # Fix silent failures in exception handlers
        new_content = self._fix_silent_failures(modified_content, file_path)
        if new_content != modified_content:
            modified_content = new_content
            file_changed = True
        
        # Fix print statements in exception handlers
        new_content = self._fix_print_in_except(modified_content)
        if new_content != modified_content:
            modified_content = new_content
            file_changed = True
        
        # Convert file operations to context managers
        new_content = self._fix_file_operations(modified_content)
        if new_content != modified_content:
            modified_content = new_content
            file_changed = True
        
        # Save if modified
        if file_changed:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(modified_content)
            self.files_modified.add(str(file_path))
            print(f"Fixed error handling in: {file_path.name}")
    
    def _fix_bare_except(self, content: str) -> str:
        """Fix bare except clauses"""
        lines = content.splitlines()
        modified_lines = []
        
        for i, line in enumerate(lines):
            # Match bare except
            if re.match(r'^(\s*)except\s*:\s*$', line):
                indent = len(line) - len(line.lstrip())
                indent_str = " " * indent
                
                # Replace with Exception catch
                modified_lines.append(f"{indent_str}except Exception as e:")
                
                # Add logging if next line is just pass or comment
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line == "pass" or next_line.startswith("#"):
                        # Add logging line
                        modified_lines.append(lines[i + 1])  # Keep the original next line
                        if next_line == "pass":
                            modified_lines[-1] = f"{indent_str}    logging.error(f'Unexpected error: {{e}}')"
                        continue
                
                self.fixes_applied["bare_except_fixed"] += 1
            else:
                modified_lines.append(line)
        
        # Add import logging if we fixed bare excepts and no import exists
        if self.fixes_applied["bare_except_fixed"] > 0 and "import logging" not in content:
            # Find import section
            import_index = 0
            for i, line in enumerate(modified_lines):
                if line.startswith("import ") or line.startswith("from "):
                    import_index = i + 1
                elif line.strip() == "" and import_index > 0:
                    break
            
            modified_lines.insert(import_index, "import logging")
        
        return "\\n".join(modified_lines)
    
    def _fix_silent_failures(self, content: str, file_path: Path) -> str:
        """Fix silent failure patterns in exception handlers"""
        lines = content.splitlines()
        modified_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Look for except handlers
            except_match = re.match(r'^(\\s*)except\\s+([^:]+):\\s*$', line)
            if except_match:
                indent = except_match.group(1)
                exception_type = except_match.group(2)
                modified_lines.append(line)
                
                # Check next lines for silent failure patterns
                j = i + 1
                if j < len(lines):
                    next_line = lines[j]
                    
                    # Silent pass
                    if next_line.strip() == "pass":
                        # Replace pass with logging
                        modified_lines.append(f"{indent}    logging.warning(f'Ignored {exception_type}: {{e}}')")
                        self.fixes_applied["silent_failures_logged"] += 1
                        i = j + 1
                        continue
                    
                    # Comment followed by pass
                    elif next_line.strip().startswith("#") and j + 1 < len(lines) and lines[j + 1].strip() == "pass":
                        modified_lines.append(next_line)  # Keep comment
                        modified_lines.append(f"{indent}    logging.warning(f'Handled {exception_type}: {{e}}')")
                        self.fixes_applied["silent_failures_logged"] += 1
                        i = j + 2
                        continue
            
            modified_lines.append(line)
            i += 1
        
        # Add logging import if needed
        if self.fixes_applied["silent_failures_logged"] > 0 and "import logging" not in content:
            import_index = 0
            for i, line in enumerate(modified_lines):
                if line.startswith("import ") or line.startswith("from "):
                    import_index = i + 1
                elif line.strip() == "" and import_index > 0:
                    break
            
            modified_lines.insert(import_index, "import logging")
        
        return "\\n".join(modified_lines)
    
    def _fix_print_in_except(self, content: str) -> str:
        """Convert print statements in exception handlers to logging"""
        lines = content.splitlines()
        modified_lines = []
        in_except_block = False
        except_indent = 0
        
        for i, line in enumerate(lines):
            # Track if we're in an except block
            if re.match(r'^\\s*except', line):
                in_except_block = True
                except_indent = len(line) - len(line.lstrip())
                modified_lines.append(line)
                continue
            
            # Check if we're still in the except block
            if in_except_block:
                current_indent = len(line) - len(line.lstrip()) if line.strip() else except_indent + 4
                if line.strip() and current_indent <= except_indent:
                    in_except_block = False
            
            # Convert print to logging in except blocks
            if in_except_block and "print(" in line:
                # Extract print content
                print_match = re.search(r"print\\s*\\(([^)]+)\\)", line)
                if print_match:
                    print_content = print_match.group(1)
                    indent = " " * (len(line) - len(line.lstrip()))
                    
                    # Convert to logging.error
                    new_line = line.replace(f"print({print_content})", f"logging.error({print_content})")
                    modified_lines.append(new_line)
                    self.fixes_applied["print_to_logging_in_except"] += 1
                    continue
            
            modified_lines.append(line)
        
        return "\\n".join(modified_lines)
    
    def _fix_file_operations(self, content: str) -> str:
        """Convert file operations to use context managers"""
        lines = content.splitlines()
        modified_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Look for file open without with statement
            open_match = re.match(r'^(\\s*)([\\w_]+)\\s*=\\s*open\\s*\\(([^)]+)\\)', line)
            if open_match and "with " not in line:
                indent = open_match.group(1)
                var_name = open_match.group(2)
                open_args = open_match.group(3)
                
                # Convert to context manager
                modified_lines.append(f"{indent}with open({open_args}) as {var_name}:")
                
                # Indent following lines that use the file variable
                j = i + 1
                while j < len(lines) and j < i + 10:  # Look ahead max 10 lines
                    next_line = lines[j]
                    if var_name in next_line and not next_line.strip().startswith("#"):
                        # Indent this line
                        next_indent = len(next_line) - len(next_line.lstrip())
                        modified_lines.append("    " + next_line)
                    else:
                        modified_lines.append(next_line)
                    j += 1
                
                self.fixes_applied["context_managers_added"] += 1
                i = j
                continue
            
            modified_lines.append(line)
            i += 1
        
        return "\\n".join(modified_lines)
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            "__pycache__", ".git", "venv", "env", ".pytest_cache", "migrations", 
            "alembic", "analyze_", "fix_", "cleanup_"  # Skip our analysis tools
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)
    
    def _generate_summary(self) -> Dict[str, int]:
        """Generate summary of fixes applied"""
        return {
            "files_modified": len(self.files_modified),
            "bare_except_fixed": self.fixes_applied["bare_except_fixed"],
            "silent_failures_logged": self.fixes_applied["silent_failures_logged"],
            "print_to_logging_fixed": self.fixes_applied["print_to_logging_in_except"],
            "context_managers_added": self.fixes_applied["context_managers_added"]
        }

def main():
    fixer = ErrorHandlingFixer()
    current_dir = Path(".")
    
    print("Starting Error Handling Fixes...")
    print("=" * 40)
    
    summary = fixer.fix_directory(current_dir)
    
    print(f"\\nError Handling Fixes Applied:")
    print(f"Files modified: {summary['files_modified']}")
    print(f"Bare except clauses fixed: {summary['bare_except_fixed']}")
    print(f"Silent failures improved: {summary['silent_failures_logged']}")
    print(f"Print statements converted to logging: {summary['print_to_logging_fixed']}")
    print(f"Context managers added: {summary['context_managers_added']}")
    
    if summary["files_modified"] > 0:
        print(f"\\nRecommendation: Review changes and run tests to ensure functionality is preserved.")
        print(f"Consider adding specific exception types where generic Exception was used.")
    
    return summary

if __name__ == "__main__":
    main()