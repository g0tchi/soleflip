"""
Automated Code Style Fixer
Fixes common formatting and style issues automatically.
"""

import re
from pathlib import Path
from typing import List, Dict, Set

class CodeStyleFixer:
    def __init__(self):
        self.fixes_applied = {
            "trailing_whitespace": 0,
            "print_to_logging": 0,
            "quote_consistency": 0,
            "line_breaks": 0
        }
        self.files_modified = set()

    def fix_directory(self, directory: Path) -> Dict[str, int]:
        """Fix style issues in all Python files in directory"""
        python_files = list(directory.rglob("*.py"))

        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue

            try:
                self.fix_file(file_path)
            except Exception as e:
                logger.error(f"Error fixing {file_path}: {e}")

        return self._generate_summary()

    def fix_file(self, file_path: Path):
        """Fix style issues in a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    original_content = f.read()
            except Exception:
                return

        modified_content = original_content
        file_changed = False

        # Fix trailing whitespace
        new_content = self._fix_trailing_whitespace(modified_content)
        if new_content != modified_content:
            modified_content = new_content
            file_changed = True
            self.fixes_applied['trailing_whitespace'] += modified_content.count('\n')

        # Fix print statements to logging (selective)
        new_content = self._fix_print_statements(modified_content, file_path)
        if new_content != modified_content:
            modified_content = new_content
            file_changed = True

        # Fix quote consistency
        new_content = self._fix_quote_consistency(modified_content)
        if new_content != modified_content:
            modified_content = new_content
            file_changed = True

        # Save if modified
        if file_changed:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            self.files_modified.add(str(file_path))
            print(f"Fixed: {file_path.name}")

    def _fix_trailing_whitespace(self, content: str) -> str:
        """Remove trailing whitespace from all lines"""
        lines = content.splitlines()
        fixed_lines = [line.rstrip() for line in lines]
        return "\n".join(fixed_lines)

    def _fix_print_statements(self, content: str, file_path: Path) -> str:
        """Convert simple print statements to logging (selective approach)"""

        # Skip certain files where print is intentional
        skip_files = ['cli.py', 'test_', 'setup.py', 'manage.py']
        if any(skip in str(file_path) for skip in skip_files):
            return content

        lines = content.splitlines()
        modified_lines = []
        needs_logging_import = False
        has_logging_import = 'import logging' in content or 'import structlog' in content

        for line in lines:
            original_line = line

            # Simple print statement conversion
            if re.match(r'^\s*print\s*\(', line.strip()) and not line.strip().startswith('#'):
                indent = len(line) - len(line.lstrip())
                indent_str = " " * indent

                # Extract print content
                print_match = re.search(r"print\s*\((.*)\)", line)
                if print_match:
                    print_content = print_match.group(1)

                    # Simple conversions for status messages
                    if any(keyword in print_content.lower() for keyword in ['success', 'completed', 'finished']):
                        if "structlog" in content:
                            line = f"{indent_str}logger.info({print_content})"
                        else:
                            line = f"{indent_str}logging.info({print_content})"
                        needs_logging_import = True
                        self.fixes_applied["print_to_logging"] += 1

                    elif any(keyword in print_content.lower() for keyword in ['error', 'failed', 'exception']):
                        if "structlog" in content:
                            line = f"{indent_str}logger.error({print_content})"
                        else:
                            line = f"{indent_str}logging.error({print_content})"
                        needs_logging_import = True
                        self.fixes_applied["print_to_logging"] += 1

                    elif any(keyword in print_content.lower() for keyword in ['warning', 'warn']):
                        if "structlog" in content:
                            line = f"{indent_str}logger.warning({print_content})"
                        else:
                            line = f"{indent_str}logging.warning({print_content})"
                        needs_logging_import = True
                        self.fixes_applied["print_to_logging"] += 1

            modified_lines.append(line)

        # Add logging import if needed and not present
        if needs_logging_import and not has_logging_import:
            # Find import section
            import_index = 0
            for i, line in enumerate(modified_lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_index = i + 1
                elif line.strip() == "" and import_index > 0:
                    break

            if "structlog" not in content:
                modified_lines.insert(import_index, "import logging")

        return "\n".join(modified_lines)

    def _fix_quote_consistency(self, content: str) -> str:
        """Standardize to double quotes for strings"""

        # This is a simple approach - in practice you'd want more sophisticated parsing
        lines = content.splitlines()
        modified_lines = []

        for line in lines:
            # Skip lines with mixed quotes that might be intentional
            if line.count("'") == 2 and line.count('"') == 0:
                # Simple single-quoted string
                if not line.strip().startswith("#"):
                    # Replace simple cases
                    line = re.sub(r"'([^']*)'", r'"\1"', line)
                    self.fixes_applied["quote_consistency"] += 1

            modified_lines.append(line)

        return "\n".join(modified_lines)

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

    def _generate_summary(self) -> Dict[str, int]:
        """Generate summary of fixes applied"""
        return {
            "files_modified": len(self.files_modified),
            'trailing_whitespace_fixed': self.fixes_applied['trailing_whitespace'],
            'prints_converted': self.fixes_applied['print_to_logging'],
            'quotes_standardized': self.fixes_applied['quote_consistency']
        }

def main():
    fixer = CodeStyleFixer()
    current_dir = Path(".")

    print("Starting Automated Code Style Fixes...")
    print("=" * 50)

    summary = fixer.fix_directory(current_dir)

    print(f"\nCode Style Fixes Applied:")
    print(f"Files modified: {summary['files_modified']}")
    print(f"Trailing whitespace removed: {summary['trailing_whitespace_fixed']} lines")
    print(f"Print statements converted: {summary['prints_converted']}")
    print(f"Quote styles standardized: {summary['quotes_standardized']}")

    if summary["files_modified"] > 0:
        print(f"\nRecommendation: Review the changes and run tests to ensure functionality is preserved.")

    return summary

if __name__ == "__main__":
    main()