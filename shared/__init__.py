"""
Shared Package
==============

Cross-cutting concerns and infrastructure utilities shared across all domains.

Modules:
- api: API dependencies, responses, and common utilities
- auth: Authentication, JWT handling, password hashing, token blacklist
- caching: Redis-based caching strategies
- config: Application settings and configuration
- database: Database connection, session management, models, transactions
- decorators: Reusable decorators (error handling, caching, etc.)
- error_handling: Custom exception classes and error handlers
- events: Event-driven architecture (event bus, base events)
- exceptions: Domain-specific exception definitions
- logging: Structured logging with correlation IDs
- middleware: HTTP middleware (compression, ETag, security)
- monitoring: Health checks, metrics, APM, batch monitoring
- performance: Database optimizations, caching strategies
- processing: Async pipelines, streaming processors, data stages
- repositories: Base repository pattern for CRUD operations
- security: Security middleware and API security utilities
- services: Shared services (payment providers, etc.)
- streaming: Response streaming for large datasets
- types: Type definitions (base, domain, API, service types)
- utils: Utility functions (helpers, financial, data transformers, validation)
- validation: Validation utilities (financial validators, etc.)
"""

__all__ = [
    "api",
    "auth",
    "caching",
    "config",
    "database",
    "decorators",
    "error_handling",
    "events",
    "exceptions",
    "logging",
    "middleware",
    "monitoring",
    "performance",
    "processing",
    "repositories",
    "security",
    "services",
    "streaming",
    "types",
    "utils",
    "validation",
]
