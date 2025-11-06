"""
Processing Module
=================

Async pipelines, streaming processors, and data processing stages.

Exports:
- async_pipeline: Pipeline abstraction for async processing
- streaming_processor: Large dataset streaming processor
- stages: Data processing stages (retailer, etc.)
"""

from shared.processing import async_pipeline, stages, streaming_processor

__all__ = [
    "async_pipeline",
    "streaming_processor",
    "stages",
]
