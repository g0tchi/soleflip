"""
Integration Repositories
========================

Data access layer for integration domain.

Repositories:
- import_repository: Import batch and record persistence
"""

from domains.integration.repositories import import_repository

__all__ = ["import_repository"]
