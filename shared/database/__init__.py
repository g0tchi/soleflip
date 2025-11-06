"""
Database Module
===============

Database connection management, models, sessions, and transactions.

Exports:
- connection: Async database engine and connection pooling
- models: SQLAlchemy models for all domains
- session_manager: Database session lifecycle management
- transaction_manager: Transaction handling and context managers
- utils: Database utility functions
"""

from shared.database import connection, models, session_manager, transaction_manager, utils

__all__ = [
    "connection",
    "models",
    "session_manager",
    "transaction_manager",
    "utils",
]
