"""
Services Module
===============

Shared services used across multiple domains.

Exports:
- payment_provider: Payment integration abstraction
"""

from shared.services import payment_provider

__all__ = ["payment_provider"]
