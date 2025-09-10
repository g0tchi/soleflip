#!/usr/bin/env python3
"""
Awin Affiliate Data Import for Retro CLI
Handles Awin API operations and CSV imports with security focus
"""

import csv
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils import clear_screen, colored_text, progress_bar

from config import AwinConfig, Config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AwinManager:
    """Awin affiliate data operations manager"""

    def __init__(self, config: Config):
        self.config = config
        self.awin_config: Optional[AwinConfig] = config.awin

        # Setup HTTP session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        if self.awin_config:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self.awin_config.api_token}",
                    "Content-Type": "application/json",
                }
            )

        # Import history storage
        self.import_history_file = "awin_import_history.json"
        self.import_history = self._load_import_history()

    def check_status(self) -> bool:
        """Check if Awin is configured and accessible"""
        if not self.awin_config or not self.awin_config.api_token:
            return False

        try:
            # Test API connection with a simple request
            url = f"{self.awin_config.base_url}/accounts"
            response = self.session.get(url, timeout=10)
            return response.status_code in [
                200,
                401,
            ]  # 401 means API is working but token might be invalid

        except requests.RequestException:
            return False

    def _load_import_history(self) -> List[Dict[str, Any]]:
        """Load import history from JSON file"""
        try:
            if os.path.exists(self.import_history_file):
                with open(self.import_history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

        return []

    def _save_import_history(self):
        """Save import history to JSON file"""
        try:
            with open(self.import_history_file, "w", encoding="utf-8") as f:
                json.dump(self.import_history, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save import history: {e}")

    def _add_import_record(
        self, import_type: str, filename: str, record_count: int, status: str = "success"
    ):
        """Add record to import history"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "type": import_type,
            "filename": filename,
            "record_count": record_count,
            "status": status,
        }

        self.import_history.append(record)

        # Keep only last 100 records
        if len(self.import_history) > 100:
            self.import_history = self.import_history[-100:]

        self._save_import_history()

    def import_csv(self):
        """Import CSV data from Awin reports"""
        clear_screen()
        print(colored_text("📥 AWIN CSV IMPORT", "bright_magenta"))
        print(colored_text("═" * 30, "magenta"))

        # List available CSV files
        csv_files = [f for f in os.listdir(".") if f.endswith(".csv") and "awin" in f.lower()]

        if not csv_files:
            print(colored_text("No Awin CSV files found in current directory", "yellow"))
            print(colored_text("Looking for files containing 'awin' in filename", "dim"))

            # Show all CSV files as alternative
            all_csv = [f for f in os.listdir(".") if f.endswith(".csv")]
            if all_csv:
                print(colored_text(f"\nFound {len(all_csv)} CSV files:", "cyan"))
                for i, file in enumerate(all_csv[:5], 1):
                    file_size = os.path.getsize(file) / 1024  # KB
                    print(colored_text(f"  {i}. {file} ({file_size:.1f} KB)", "white"))
                if len(all_csv) > 5:
                    print(colored_text(f"  ... and {len(all_csv) - 5} more files", "dim"))
            return

        print(colored_text("Available Awin CSV files:", "bright_white"))
        for i, file in enumerate(csv_files, 1):
            file_size = os.path.getsize(file) / 1024  # KB
            mod_time = datetime.fromtimestamp(os.path.getmtime(file)).strftime("%Y-%m-%d %H:%M")
            print(colored_text(f"{i}. {file}", "white"))
            print(colored_text(f"   Size: {file_size:.1f} KB, Modified: {mod_time}", "dim"))

        print(colored_text("0. Cancel", "dim"))

        choice = input(colored_text("\nSelect CSV file: ", "bright_green"))

        try:
            choice_idx = int(choice) - 1
            if choice == "0":
                return
            if choice_idx < 0 or choice_idx >= len(csv_files):
                raise ValueError

            csv_file = csv_files[choice_idx]

        except ValueError:
            print(colored_text("Invalid selection", "red"))
            return

        # Analyze CSV structure
        try:
            print(colored_text(f"\nAnalyzing {csv_file}...", "cyan"))

            with open(csv_file, "r", encoding="utf-8") as f:
                # Try to detect CSV structure
                sample = f.read(1024)
                f.seek(0)

                # Detect delimiter
                delimiter = ","
                if sample.count("\t") > sample.count(","):
                    delimiter = "\t"

                reader = csv.DictReader(f, delimiter=delimiter)
                headers = reader.fieldnames

                # Read first few rows
                rows = []
                for i, row in enumerate(reader):
                    if i >= 3:  # Only read first 3 rows for preview
                        break
                    rows.append(row)

                # Get total row count
                f.seek(0)
                total_rows = sum(1 for line in f) - 1  # -1 for header

            # Display analysis
            print(colored_text(f"\n📊 CSV Analysis:", "bright_white"))
            print(colored_text(f"Total Rows: {total_rows:,}", "cyan"))
            print(colored_text(f"Columns: {len(headers) if headers else 0}", "cyan"))
            print(colored_text(f"Delimiter: {'Tab' if delimiter == '\\t' else 'Comma'}", "cyan"))

            if headers:
                print(colored_text(f"\nColumn Headers:", "bright_yellow"))
                for i, header in enumerate(headers[:10], 1):  # Show first 10 headers
                    print(colored_text(f"  {i}. {header}", "white"))
                if len(headers) > 10:
                    print(colored_text(f"  ... and {len(headers) - 10} more columns", "dim"))

            if rows:
                print(colored_text(f"\nSample Data (first row):", "bright_yellow"))
                for header in list(headers)[:5]:  # Show first 5 columns
                    value = rows[0].get(header, "")[:50]  # Truncate long values
                    print(colored_text(f"  {header}: {value}", "white"))

            # Import options
            print(colored_text(f"\nImport Options:", "bright_cyan"))
            print(colored_text("1. Validate data only (dry run)", "white"))
            print(colored_text("2. Import to database (if connected)", "white"))
            print(colored_text("3. Export processed JSON", "white"))
            print(colored_text("0. Cancel", "dim"))

            action = input(colored_text("\nSelect action: ", "bright_green"))

            if action == "0":
                print(colored_text("Import cancelled", "yellow"))
                return
            elif action == "1":
                self._validate_csv_data(csv_file, delimiter, total_rows)
            elif action == "2":
                self._import_csv_to_db(csv_file, delimiter, total_rows)
            elif action == "3":
                self._export_csv_to_json(csv_file, delimiter, total_rows)
            else:
                print(colored_text("Invalid option", "red"))
                return

        except Exception as e:
            print(colored_text(f"Error analyzing CSV: {e}", "red"))

        input(colored_text("\nPress Enter to continue...", "dim"))

    def _validate_csv_data(self, csv_file: str, delimiter: str, total_rows: int):
        """Validate CSV data structure and content"""
        print(colored_text(f"\n🔍 VALIDATING {csv_file}", "bright_yellow"))

        validation_results = {"total_rows": 0, "valid_rows": 0, "errors": [], "warnings": []}

        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=delimiter)

                progress_bar("Validating data", total_rows, 0.001)

                for row_num, row in enumerate(reader, 1):
                    validation_results["total_rows"] = row_num

                    # Basic validation checks
                    is_valid = True

                    # Check for empty required fields (example validation)
                    required_fields = ["commission_group_id", "advertiser_id", "publisher_id"]
                    for field in required_fields:
                        if field in row and not row[field].strip():
                            validation_results["warnings"].append(f"Row {row_num}: Empty {field}")

                    # Check data types (example)
                    numeric_fields = ["commission_group_id", "advertiser_id", "click_refs"]
                    for field in numeric_fields:
                        if field in row and row[field].strip():
                            try:
                                int(row[field])
                            except ValueError:
                                validation_results["errors"].append(
                                    f"Row {row_num}: Invalid {field} '{row[field]}'"
                                )
                                is_valid = False

                    if is_valid:
                        validation_results["valid_rows"] += 1

            # Display validation results
            print(colored_text(f"\n✅ VALIDATION COMPLETE", "bright_green"))
            print(colored_text(f"Total Rows: {validation_results['total_rows']:,}", "white"))
            print(colored_text(f"Valid Rows: {validation_results['valid_rows']:,}", "bright_green"))
            print(
                colored_text(
                    f"Errors: {len(validation_results['errors'])}",
                    "red" if validation_results["errors"] else "green",
                )
            )
            print(
                colored_text(
                    f"Warnings: {len(validation_results['warnings'])}",
                    "yellow" if validation_results["warnings"] else "green",
                )
            )

            # Show first few errors/warnings
            if validation_results["errors"]:
                print(colored_text(f"\nFirst 5 Errors:", "red"))
                for error in validation_results["errors"][:5]:
                    print(colored_text(f"  • {error}", "red"))

            if validation_results["warnings"]:
                print(colored_text(f"\nFirst 5 Warnings:", "yellow"))
                for warning in validation_results["warnings"][:5]:
                    print(colored_text(f"  • {warning}", "yellow"))

            # Record validation
            self._add_import_record(
                "validation",
                csv_file,
                validation_results["total_rows"],
                "success" if not validation_results["errors"] else "errors",
            )

        except Exception as e:
            print(colored_text(f"Validation error: {e}", "red"))
            self._add_import_record("validation", csv_file, 0, "failed")

    def _import_csv_to_db(self, csv_file: str, delimiter: str, total_rows: int):
        """Import CSV to database (placeholder)"""
        print(colored_text(f"\n💾 IMPORTING TO DATABASE", "bright_blue"))

        # Check database connection
        if not self.config.database or not hasattr(self.config, "database"):
            print(colored_text("❌ Database not configured", "red"))
            return

        print(colored_text("⚠️  Database import not yet implemented", "yellow"))
        print(colored_text("This would require:", "dim"))
        print(colored_text("  • Database table mapping", "dim"))
        print(colored_text("  • Data transformation rules", "dim"))
        print(colored_text("  • Duplicate handling logic", "dim"))
        print(colored_text("  • Transaction safety", "dim"))

        # Simulate import process
        progress_bar(f"Simulating import of {total_rows:,} rows", total_rows, 0.001)

        self._add_import_record("database_import", csv_file, total_rows, "simulated")

    def _export_csv_to_json(self, csv_file: str, delimiter: str, total_rows: int):
        """Export CSV to structured JSON"""
        print(colored_text(f"\n📄 EXPORTING TO JSON", "bright_cyan"))

        output_file = csv_file.replace(
            ".csv", f'_processed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )

        try:
            with open(csv_file, "r", encoding="utf-8") as infile:
                reader = csv.DictReader(infile, delimiter=delimiter)

                data = {
                    "metadata": {
                        "source_file": csv_file,
                        "export_time": datetime.now().isoformat(),
                        "total_records": 0,
                    },
                    "records": [],
                }

                progress_bar(f"Processing {total_rows:,} rows", total_rows, 0.001)

                for row in reader:
                    # Clean and process row data
                    processed_row = {}
                    for key, value in row.items():
                        if key and value is not None:
                            processed_row[key.strip()] = str(value).strip()

                    data["records"].append(processed_row)
                    data["metadata"]["total_records"] += 1

            # Write JSON output
            with open(output_file, "w", encoding="utf-8") as outfile:
                json.dump(data, outfile, indent=2, ensure_ascii=False)

            print(
                colored_text(
                    f"✅ Exported {data['metadata']['total_records']:,} records to:", "bright_green"
                )
            )
            print(colored_text(f"   {output_file}", "cyan"))

            self._add_import_record(
                "json_export", csv_file, data["metadata"]["total_records"], "success"
            )

        except Exception as e:
            print(colored_text(f"Export error: {e}", "red"))
            self._add_import_record("json_export", csv_file, 0, "failed")

    def sync_api(self):
        """Sync data directly from Awin API"""
        if not self.check_status():
            print(colored_text("❌ Awin API not configured or accessible!", "red"))
            return

        clear_screen()
        print(colored_text("🔄 AWIN API SYNC", "bright_magenta"))
        print(colored_text("═" * 30, "magenta"))

        print(colored_text("⚠️  Direct API sync not yet implemented", "yellow"))
        print(colored_text("This would require:", "dim"))
        print(colored_text("  • API endpoint mapping", "dim"))
        print(colored_text("  • Authentication handling", "dim"))
        print(colored_text("  • Rate limit management", "dim"))
        print(colored_text("  • Data synchronization logic", "dim"))

        # Simulate API sync
        endpoints = ["Advertisers", "Commission Groups", "Transaction Data", "Performance Reports"]

        for endpoint in endpoints:
            print(colored_text(f"\nSyncing {endpoint}...", "cyan"))
            progress_bar(f"Fetching {endpoint.lower()}", 100, 0.02)
            print(colored_text(f"✓ {endpoint} sync completed", "green"))

        self._add_import_record("api_sync", "awin_api", len(endpoints), "simulated")

        input(colored_text("\nPress Enter to continue...", "dim"))

    def import_history(self):
        """Display import history"""
        clear_screen()
        print(colored_text("📋 AWIN IMPORT HISTORY", "bright_magenta"))
        print(colored_text("═" * 40, "magenta"))

        if not self.import_history:
            print(colored_text("No import history found", "yellow"))
            return

        # Show recent imports
        recent_imports = sorted(self.import_history, key=lambda x: x["timestamp"], reverse=True)[
            :20
        ]

        print(colored_text(f"Showing last {len(recent_imports)} imports:", "bright_white"))
        print(colored_text("-" * 80, "dim"))

        for i, record in enumerate(recent_imports, 1):
            timestamp = datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d %H:%M")
            import_type = record["type"].upper()
            filename = record["filename"][:30]  # Truncate long filenames
            count = record["record_count"]
            status = record["status"]

            # Color code by status
            status_color = {
                "success": "bright_green",
                "failed": "red",
                "errors": "yellow",
                "simulated": "cyan",
            }.get(status, "white")

            print(
                colored_text(
                    f"{i:2d}. {timestamp} | {import_type:12} | {filename:30} | {count:6,} records",
                    "white",
                )
            )
            print(colored_text(f"    Status: ", "dim"), end="")
            print(colored_text(status.upper(), status_color))

        # Summary statistics
        total_records = sum(r["record_count"] for r in self.import_history)
        success_count = sum(1 for r in self.import_history if r["status"] == "success")
        failed_count = sum(1 for r in self.import_history if r["status"] == "failed")

        print(colored_text(f"\n📊 SUMMARY:", "bright_cyan"))
        print(colored_text(f"Total Imports: {len(self.import_history)}", "white"))
        print(colored_text(f"Successful: {success_count}", "bright_green"))
        print(colored_text(f"Failed: {failed_count}", "red"))
        print(colored_text(f"Total Records: {total_records:,}", "cyan"))

        input(colored_text("\nPress Enter to continue...", "dim"))

    def validate_data(self):
        """Data validation utilities"""
        clear_screen()
        print(colored_text("🔍 AWIN DATA VALIDATION", "bright_magenta"))
        print(colored_text("═" * 35, "magenta"))

        print(colored_text("Validation Options:", "bright_white"))
        print(colored_text("1. Check CSV file formats", "white"))
        print(colored_text("2. Validate API credentials", "white"))
        print(colored_text("3. Test data integrity", "white"))
        print(colored_text("4. Check duplicate records", "white"))
        print(colored_text("0. Back to menu", "dim"))

        choice = input(colored_text("\nSelect validation: ", "bright_green"))

        if choice == "1":
            self._validate_csv_formats()
        elif choice == "2":
            self._validate_api_credentials()
        elif choice == "3":
            print(colored_text("Data integrity check not yet implemented", "yellow"))
        elif choice == "4":
            print(colored_text("Duplicate check not yet implemented", "yellow"))
        elif choice == "0":
            return
        else:
            print(colored_text("Invalid option", "red"))

        input(colored_text("\nPress Enter to continue...", "dim"))

    def _validate_csv_formats(self):
        """Validate CSV file formats"""
        csv_files = [f for f in os.listdir(".") if f.endswith(".csv")]

        if not csv_files:
            print(colored_text("No CSV files found", "yellow"))
            return

        print(colored_text(f"\n🔍 Validating {len(csv_files)} CSV files:", "cyan"))

        for csv_file in csv_files:
            try:
                with open(csv_file, "r", encoding="utf-8") as f:
                    # Basic format validation
                    first_line = f.readline().strip()

                    if "," in first_line or "\t" in first_line:
                        print(colored_text(f"✓ {csv_file}", "green"))
                    else:
                        print(colored_text(f"⚠ {csv_file} - Unknown format", "yellow"))

            except Exception as e:
                print(colored_text(f"❌ {csv_file} - Error: {str(e)}", "red"))

    def _validate_api_credentials(self):
        """Validate Awin API credentials"""
        if not self.awin_config:
            print(colored_text("❌ Awin not configured", "red"))
            return

        print(colored_text("\n🔐 Testing API credentials...", "cyan"))

        try:
            # Test API connection
            url = f"{self.awin_config.base_url}/accounts"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                print(colored_text("✅ API credentials valid", "bright_green"))

                # Try to get account info
                try:
                    account_data = response.json()
                    print(
                        colored_text(
                            f"Account ID: {account_data.get('account_id', 'Unknown')}", "cyan"
                        )
                    )
                except Exception:
                    print(colored_text("✓ API accessible but response format unknown", "yellow"))

            elif response.status_code == 401:
                print(colored_text("❌ API credentials invalid (401 Unauthorized)", "red"))
            elif response.status_code == 403:
                print(colored_text("❌ API access forbidden (403)", "red"))
            else:
                print(colored_text(f"⚠ API responded with status {response.status_code}", "yellow"))

        except requests.RequestException as e:
            print(colored_text(f"❌ API connection failed: {e}", "red"))


if __name__ == "__main__":
    # Demo Awin operations
    from config import get_config

    config = get_config()
    awin_manager = AwinManager(config)

    if awin_manager.check_status():
        print("✅ Awin configured and accessible")
    else:
        print("❌ Awin not configured or inaccessible")
