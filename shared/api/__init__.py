"""
API Module
==========

Common API utilities, dependencies, and response models.

Exports:
- dependencies: Dependency injection for FastAPI routes
- responses: Standard response models and utilities
"""

from shared.api import dependencies, responses

__all__ = ["dependencies", "responses"]
