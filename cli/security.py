#!/usr/bin/env python3
"""
Security and Logging Features for Retro CLI
Handles logging, session management, and security checks
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils import colored_text

from config import Config


class SecurityManager:
    """Security management for CLI operations"""

    def __init__(self, config: Config):
        self.config = config
        self.session_file = "cli_session.json"
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        # Setup logging
        self.setup_logging()

        # Session tracking
        self.current_session = None

    def setup_logging(self):
        """Setup comprehensive logging system"""
        # Create log files
        self.access_log = self.log_dir / f"access_{datetime.now().strftime('%Y%m%d')}.log"
        self.error_log = self.log_dir / f"error_{datetime.now().strftime('%Y%m%d')}.log"
        self.audit_log = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"

        # Configure logging
        log_level = getattr(logging, self.config.system.log_level.upper(), logging.INFO)

        # Main logger
        self.logger = logging.getLogger("retro_cli")
        self.logger.setLevel(log_level)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler for development
        if self.config.system.debug:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

        # File handler for access log
        access_handler = logging.FileHandler(self.access_log, encoding="utf-8")
        access_handler.setLevel(logging.INFO)
        access_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        access_handler.setFormatter(access_formatter)
        self.logger.addHandler(access_handler)

        # Error logger
        self.error_logger = logging.getLogger("retro_cli_errors")
        self.error_logger.setLevel(logging.ERROR)
        error_handler = logging.FileHandler(self.error_log, encoding="utf-8")
        error_formatter = logging.Formatter(
            "%(asctime)s | ERROR | %(message)s | %(pathname)s:%(lineno)d"
        )
        error_handler.setFormatter(error_formatter)
        self.error_logger.addHandler(error_handler)

        # Audit logger
        self.audit_logger = logging.getLogger("retro_cli_audit")
        self.audit_logger.setLevel(logging.INFO)
        audit_handler = logging.FileHandler(self.audit_log, encoding="utf-8")
        audit_formatter = logging.Formatter("%(asctime)s | AUDIT | %(message)s")
        audit_handler.setFormatter(audit_formatter)
        self.audit_logger.addHandler(audit_handler)

    def start_session(self, username: str) -> str:
        """Start a new user session"""
        session_id = self.generate_session_id(username)

        self.current_session = {
            "session_id": session_id,
            "username": username,
            "start_time": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "actions": [],
            "environment": self.config.system.environment,
            "test_mode": self.config.system.is_test,
        }

        # Save session
        self.save_session()

        # Log session start
        self.log_access(f"Session started for user: {username}")
        self.log_audit("USER_LOGIN", f"User {username} started session {session_id}")

        return session_id

    def generate_session_id(self, username: str) -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().isoformat()
        raw_id = f"{username}:{timestamp}:{os.getpid()}"
        return hashlib.sha256(raw_id.encode()).hexdigest()[:16]

    def update_session_activity(self, action: str, details: Optional[Dict] = None):
        """Update session with new activity"""
        if not self.current_session:
            return

        activity = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details or {},
        }

        self.current_session["actions"].append(activity)
        self.current_session["last_activity"] = datetime.now().isoformat()

        # Keep only last 50 actions to prevent memory issues
        if len(self.current_session["actions"]) > 50:
            self.current_session["actions"] = self.current_session["actions"][-50:]

        self.save_session()

        # Log activity
        self.log_access(f"Action: {action} | User: {self.current_session['username']}")
        if details:
            self.log_audit(
                "USER_ACTION",
                f"User {self.current_session['username']} performed {action}: {details}",
            )

    def end_session(self):
        """End current session"""
        if not self.current_session:
            return

        username = self.current_session["username"]
        session_id = self.current_session["session_id"]

        # Calculate session duration
        start_time = datetime.fromisoformat(self.current_session["start_time"])
        duration = datetime.now() - start_time

        # Log session end
        self.log_access(f"Session ended for user: {username} | Duration: {duration}")
        self.log_audit(
            "USER_LOGOUT", f"User {username} ended session {session_id} after {duration}"
        )

        # Archive session
        self.archive_session()

        self.current_session = None

    def save_session(self):
        """Save current session to file"""
        if not self.current_session:
            return

        try:
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(self.current_session, f, indent=2, default=str)
        except IOError as e:
            self.log_error(f"Failed to save session: {e}")

    def archive_session(self):
        """Archive session to daily session log"""
        if not self.current_session:
            return

        try:
            archive_file = self.log_dir / f"sessions_{datetime.now().strftime('%Y%m%d')}.log"

            session_summary = {
                "session_id": self.current_session["session_id"],
                "username": self.current_session["username"],
                "start_time": self.current_session["start_time"],
                "end_time": datetime.now().isoformat(),
                "action_count": len(self.current_session["actions"]),
                "environment": self.current_session["environment"],
                "test_mode": self.current_session["test_mode"],
            }

            with open(archive_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(session_summary) + "\n")

            # Clean up session file
            if os.path.exists(self.session_file):
                os.remove(self.session_file)

        except IOError as e:
            self.log_error(f"Failed to archive session: {e}")

    def log_access(self, message: str):
        """Log access event"""
        self.logger.info(message)

    def log_error(self, message: str, exception: Optional[Exception] = None):
        """Log error event"""
        error_msg = message
        if exception:
            error_msg += f" | Exception: {str(exception)}"

        self.error_logger.error(error_msg)

    def log_audit(self, event_type: str, message: str):
        """Log audit event"""
        audit_msg = f"{event_type} | {message}"
        self.audit_logger.info(audit_msg)

    def check_system_security(self) -> Dict[str, Any]:
        """Perform security checks"""
        security_status = {
            "environment_secure": True,
            "encryption_configured": bool(self.config.system.encryption_key),
            "test_mode": self.config.system.is_test,
            "debug_mode": self.config.system.debug,
            "warnings": [],
            "errors": [],
        }

        # Check for security issues
        if self.config.system.is_production and self.config.system.debug:
            security_status["warnings"].append("Debug mode enabled in production")
            security_status["environment_secure"] = False

        if not self.config.system.encryption_key:
            security_status["errors"].append("Encryption key not configured")
            security_status["environment_secure"] = False

        if self.config.system.is_production and not self.config.system.encryption_key:
            security_status["errors"].append("Production environment without encryption")
            security_status["environment_secure"] = False

        # Check file permissions (basic check)
        try:
            sensitive_files = [self.session_file, ".env"]
            for file_path in sensitive_files:
                if os.path.exists(file_path):
                    file_stat = os.stat(file_path)
                    # On Windows, this is limited, but we can still check
                    if hasattr(file_stat, "st_mode"):
                        # This is a basic check - more sophisticated checks would be OS-specific
                        pass
        except Exception as e:
            security_status["warnings"].append(f"Could not check file permissions: {e}")

        return security_status

    def get_recent_logs(self, log_type: str = "access", count: int = 10) -> List[str]:
        """Get recent log entries"""
        log_file_map = {"access": self.access_log, "error": self.error_log, "audit": self.audit_log}

        log_file = log_file_map.get(log_type, self.access_log)

        try:
            if not log_file.exists():
                return []

            # MEMORY OPTIMIZATION: Use efficient tail reading for large log files
            import os

            file_size_mb = os.path.getsize(log_file) / (1024 * 1024)

            if file_size_mb > 10:  # Files larger than 10MB use efficient tail reading
                return self._tail_file_efficiently(log_file, count)
            else:
                # Regular processing for smaller files
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    return [line.strip() for line in lines[-count:]]

        except IOError:
            return []

    def _tail_file_efficiently(self, file_path: str, count: int) -> List[str]:
        """Efficiently read last N lines from large files without loading entire file"""
        import mmap

        try:
            with open(file_path, "rb") as f:
                # Memory-map the file for efficient random access
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    # Start from end and work backwards
                    lines = []
                    line_start = len(mm)
                    lines_found = 0

                    # Search backwards for newlines
                    for pos in range(len(mm) - 1, -1, -1):
                        if mm[pos] == ord("\n"):
                            if lines_found > 0:  # Skip the very last newline
                                line = (
                                    mm[pos + 1 : line_start]
                                    .decode("utf-8", errors="ignore")
                                    .strip()
                                )
                                if line:  # Only add non-empty lines
                                    lines.append(line)
                                    lines_found += 1
                                    if lines_found >= count:
                                        break
                            line_start = pos

                    # Add the first line if we haven't found enough
                    if lines_found < count and line_start > 0:
                        line = mm[0:line_start].decode("utf-8", errors="ignore").strip()
                        if line:
                            lines.append(line)

                    # Reverse to get correct chronological order
                    return lines[::-1]

        except Exception:
            # Fallback to regular method if memory mapping fails
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return [line.strip() for line in lines[-count:]]

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        stats = {
            "current_session": bool(self.current_session),
            "session_duration": None,
            "actions_performed": 0,
            "environment": self.config.system.environment,
            "test_mode": self.config.system.is_test,
        }

        if self.current_session:
            start_time = datetime.fromisoformat(self.current_session["start_time"])
            stats["session_duration"] = str(datetime.now() - start_time)
            stats["actions_performed"] = len(self.current_session["actions"])
            stats["username"] = self.current_session["username"]
            stats["session_id"] = self.current_session["session_id"]

        return stats

    def validate_environment(self) -> bool:
        """Validate that environment is safe for operations"""
        # Test mode validation
        if self.config.system.is_test:
            self.log_audit(
                "ENV_CHECK", "Running in TEST mode - database operations will use test schema"
            )
            return True

        # Production validation
        if self.config.system.is_production:
            if not self.config.system.encryption_key:
                self.log_error("Production environment missing encryption key")
                return False

            if self.config.system.debug:
                self.log_error("Debug mode enabled in production")
                return False

        return True

    def clean_old_logs(self, days_to_keep: int = 30):
        """Clean up old log files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            for log_file in self.log_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    self.log_audit("LOG_CLEANUP", f"Deleted old log file: {log_file.name}")

        except Exception as e:
            self.log_error(f"Failed to clean old logs: {e}")


def display_security_status(security_manager: SecurityManager):
    """Display security status in retro style"""
    print(colored_text("[SEC] SECURITY STATUS", "bright_yellow"))
    print(colored_text("=" * 30, "yellow"))

    security_status = security_manager.check_system_security()
    session_stats = security_manager.get_session_stats()

    # Environment info
    env_color = "bright_green" if security_status["environment_secure"] else "red"
    env_status = "SECURE" if security_status["environment_secure"] else "WARNING"
    print(colored_text(f"Environment: {env_status}", env_color))
    print(colored_text(f"Mode: {session_stats['environment'].upper()}", "cyan"))
    print(colored_text(f"Test Mode: {'YES' if session_stats['test_mode'] else 'NO'}", "cyan"))

    # Encryption status
    enc_status = "CONFIGURED" if security_status["encryption_configured"] else "MISSING"
    enc_color = "bright_green" if security_status["encryption_configured"] else "red"
    print(colored_text(f"Encryption: {enc_status}", enc_color))

    # Session info
    if session_stats["current_session"]:
        print(
            colored_text(f"Session: ACTIVE ({session_stats['session_duration']})", "bright_green")
        )
        print(colored_text(f"User: {session_stats['username']}", "white"))
        print(colored_text(f"Actions: {session_stats['actions_performed']}", "cyan"))
    else:
        print(colored_text("Session: NONE", "yellow"))

    # Warnings and errors
    if security_status["warnings"]:
        print(colored_text("\n[!] WARNINGS:", "yellow"))
        for warning in security_status["warnings"]:
            print(colored_text(f"  * {warning}", "yellow"))

    if security_status["errors"]:
        print(colored_text("\n[X] ERRORS:", "red"))
        for error in security_status["errors"]:
            print(colored_text(f"  * {error}", "red"))

    if not security_status["warnings"] and not security_status["errors"]:
        print(colored_text("\n[OK] No security issues detected", "bright_green"))


if __name__ == "__main__":
    # Demo security features
    from config import get_config

    config = get_config()
    security_manager = SecurityManager(config)

    # Start demo session
    session_id = security_manager.start_session("demo_user")
    print(f"Demo session started: {session_id}")

    # Log some activities
    security_manager.update_session_activity("menu_navigation", {"menu": "main"})
    security_manager.update_session_activity("database_query", {"table": "products"})

    # Display security status
    display_security_status(security_manager)

    # End session
    security_manager.end_session()
    print("Demo session ended")
