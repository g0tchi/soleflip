"""
Progress Tracking Module

Provides decorators and context managers for tracking operation progress.
Inspired by Dexter's @show_progress decorator pattern.

Usage:
    # As decorator
    @track_progress("Generating forecast", "Forecast complete")
    async def generate_forecast(self):
        # Long operation
        pass

    # As context manager
    with track_operation("Processing import"):
        # Multi-step operation
        process_data()
"""

import asyncio
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


def track_progress(
    start_message: str,
    end_message: Optional[str] = None,
    log_result: bool = False,
    log_duration: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for tracking operation progress with structured logging.

    Args:
        start_message: Message to log when operation starts
        end_message: Optional message to log when operation completes
                    (defaults to "{start_message} - completed")
        log_result: Whether to include result preview in completion log
        log_duration: Whether to log operation duration

    Returns:
        Decorated function that logs progress

    Example:
        @track_progress("Calculating metrics", "Metrics ready")
        async def calculate_metrics(self):
            # Long calculation
            return results
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()

            logger.info(
                "operation_started",
                message=start_message,
                function=func.__name__,
                module=func.__module__,
            )

            try:
                result = await func(*args, **kwargs)

                duration = time.time() - start_time
                final_msg = end_message or f"{start_message} - completed"

                log_data: dict[str, Any] = {
                    "message": final_msg,
                    "function": func.__name__,
                    "module": func.__module__,
                }

                if log_duration:
                    log_data["duration_seconds"] = round(duration, 2)

                if log_result and result is not None:
                    # Include preview of result (first 100 chars)
                    result_preview = str(result)[:100]
                    if len(str(result)) > 100:
                        result_preview += "..."
                    log_data["result_preview"] = result_preview

                logger.info("operation_completed", **log_data)
                return result

            except Exception as e:
                duration = time.time() - start_time

                logger.error(
                    "operation_failed",
                    message=f"{start_message} - failed",
                    function=func.__name__,
                    module=func.__module__,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_seconds=round(duration, 2),
                    exc_info=True,
                )
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()

            logger.info(
                "operation_started",
                message=start_message,
                function=func.__name__,
                module=func.__module__,
            )

            try:
                result = func(*args, **kwargs)

                duration = time.time() - start_time
                final_msg = end_message or f"{start_message} - completed"

                log_data: dict[str, Any] = {
                    "message": final_msg,
                    "function": func.__name__,
                    "module": func.__module__,
                }

                if log_duration:
                    log_data["duration_seconds"] = round(duration, 2)

                if log_result and result is not None:
                    result_preview = str(result)[:100]
                    if len(str(result)) > 100:
                        result_preview += "..."
                    log_data["result_preview"] = result_preview

                logger.info("operation_completed", **log_data)
                return result

            except Exception as e:
                duration = time.time() - start_time

                logger.error(
                    "operation_failed",
                    message=f"{start_message} - failed",
                    function=func.__name__,
                    module=func.__module__,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_seconds=round(duration, 2),
                    exc_info=True,
                )
                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        return cast(Callable[..., T], sync_wrapper)

    return decorator


@contextmanager
def track_operation(
    description: str,
    log_duration: bool = True,
    **extra_context: Any,
):
    """
    Context manager for tracking code blocks with progress logging.

    Args:
        description: Description of the operation
        log_duration: Whether to log operation duration
        **extra_context: Additional context to include in logs

    Yields:
        None

    Example:
        with track_operation("Processing CSV import", file_name="data.csv"):
            validate_csv()
            transform_data()
            bulk_insert()
    """
    start_time = time.time()

    log_data: dict[str, Any] = {
        "description": description,
        **extra_context,
    }

    logger.info("operation_started", **log_data)

    try:
        yield

        duration = time.time() - start_time

        completion_data = log_data.copy()
        if log_duration:
            completion_data["duration_seconds"] = round(duration, 2)

        logger.info("operation_completed", **completion_data)

    except Exception as e:
        duration = time.time() - start_time

        error_data = log_data.copy()
        error_data.update(
            {
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_seconds": round(duration, 2),
            }
        )

        logger.error("operation_failed", exc_info=True, **error_data)
        raise


class ProgressTracker:
    """
    Stateful progress tracker for multi-step operations.

    Useful for tracking progress through a series of steps where
    you want to report incremental progress.

    Example:
        tracker = ProgressTracker("Data import", total_steps=5)

        tracker.step("Validating CSV")
        validate()

        tracker.step("Transforming data")
        transform()

        tracker.step("Inserting records")
        insert()

        tracker.complete("Import successful")
    """

    def __init__(
        self,
        operation_name: str,
        total_steps: Optional[int] = None,
        **context: Any,
    ) -> None:
        """
        Initialize progress tracker.

        Args:
            operation_name: Name of the operation being tracked
            total_steps: Optional total number of steps
            **context: Additional context to include in all logs
        """
        self.operation_name = operation_name
        self.total_steps = total_steps
        self.context = context
        self.current_step = 0
        self.start_time = time.time()
        self.step_times: list[tuple[str, float]] = []

        logger.info(
            "operation_started",
            operation=operation_name,
            total_steps=total_steps,
            **context,
        )

    def step(self, step_description: str, **step_context: Any) -> None:
        """
        Log progress for a step.

        Args:
            step_description: Description of the current step
            **step_context: Additional context for this step
        """
        self.current_step += 1
        step_time = time.time()

        # Calculate duration since last step
        if self.step_times:
            step_duration = step_time - self.step_times[-1][1]
        else:
            step_duration = step_time - self.start_time

        self.step_times.append((step_description, step_time))

        log_data: dict[str, Any] = {
            "operation": self.operation_name,
            "step": self.current_step,
            "step_description": step_description,
            "step_duration_seconds": round(step_duration, 2),
            **self.context,
            **step_context,
        }

        if self.total_steps:
            log_data["total_steps"] = self.total_steps
            log_data["progress_percent"] = round((self.current_step / self.total_steps) * 100, 1)

        logger.info("operation_step", **log_data)

    def complete(self, completion_message: Optional[str] = None, **final_context: Any) -> None:
        """
        Mark operation as complete.

        Args:
            completion_message: Optional completion message
            **final_context: Additional context for completion
        """
        total_duration = time.time() - self.start_time

        log_data: dict[str, Any] = {
            "operation": self.operation_name,
            "total_steps": self.current_step,
            "total_duration_seconds": round(total_duration, 2),
            **self.context,
            **final_context,
        }

        if completion_message:
            log_data["message"] = completion_message

        # Calculate average step duration
        if self.step_times:
            avg_step_duration = total_duration / len(self.step_times)
            log_data["avg_step_duration_seconds"] = round(avg_step_duration, 2)

        logger.info("operation_completed", **log_data)

    def fail(self, error: Exception, **error_context: Any) -> None:
        """
        Mark operation as failed.

        Args:
            error: The exception that caused failure
            **error_context: Additional error context
        """
        total_duration = time.time() - self.start_time

        log_data: dict[str, Any] = {
            "operation": self.operation_name,
            "completed_steps": self.current_step,
            "total_duration_seconds": round(total_duration, 2),
            "error": str(error),
            "error_type": type(error).__name__,
            **self.context,
            **error_context,
        }

        logger.error("operation_failed", exc_info=True, **log_data)

    def get_stats(self) -> dict[str, Any]:
        """
        Get current progress statistics.

        Returns:
            Dictionary with progress statistics
        """
        return {
            "operation": self.operation_name,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "elapsed_seconds": round(time.time() - self.start_time, 2),
            "steps_completed": [desc for desc, _ in self.step_times],
        }
