"""
Structured Task Execution Module

Provides orchestration for multi-step analytics operations with built-in safety.
Inspired by Dexter's task planning and execution pattern.

Usage:
    tasks = [
        AnalyticsTask(id=1, description="Fetch inventory", action="fetch_inventory"),
        AnalyticsTask(id=2, description="Calculate aging", action="calculate_aging"),
        AnalyticsTask(id=3, description="Generate report", action="generate_report"),
    ]

    executor = TaskExecutor()
    results = await executor.execute_tasks(tasks, context={"product_id": uuid})
"""

import structlog
from typing import List, Dict, Any, Optional, Callable, Awaitable
from pydantic import BaseModel, Field

from shared.monitoring.loop_detector import SafetyLimiter
from shared.monitoring.progress_tracker import ProgressTracker

logger = structlog.get_logger(__name__)


class AnalyticsTask(BaseModel):
    """
    Represents a single task in a multi-step analytics operation.

    Similar to Dexter's Task schema but tailored for analytics workflows.
    """

    id: int = Field(..., description="Unique task identifier")
    description: str = Field(..., description="Human-readable task description")
    action: str = Field(..., description="Action/function name to execute")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the action"
    )
    dependencies: List[int] = Field(
        default_factory=list, description="IDs of tasks that must complete first"
    )
    done: bool = Field(default=False, description="Whether task is completed")
    result: Optional[Any] = Field(default=None, description="Task execution result")
    error: Optional[str] = Field(default=None, description="Error message if task failed")

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class TaskExecutionError(Exception):
    """Raised when task execution fails."""

    pass


class TaskExecutor:
    """
    Orchestrates multi-step analytics operations with safety mechanisms.

    Features:
    - Sequential task execution with dependency management
    - Loop detection to prevent infinite retry cycles
    - Iteration limits (global and per-task)
    - Progress tracking with structured logging
    - Graceful error handling with detailed error reporting

    Example:
        executor = TaskExecutor(max_iterations_per_task=5)

        tasks = [
            AnalyticsTask(
                id=1,
                description="Fetch product data",
                action="fetch_products",
                params={"brand": "Nike"}
            ),
            AnalyticsTask(
                id=2,
                description="Calculate margins",
                action="calculate_margins",
                dependencies=[1]  # Depends on task 1
            ),
        ]

        results = await executor.execute_tasks(tasks)
    """

    def __init__(
        self,
        max_global_iterations: int = 20,
        max_iterations_per_task: int = 5,
        enable_loop_detection: bool = True,
    ) -> None:
        """
        Initialize task executor.

        Args:
            max_global_iterations: Maximum total iterations across all tasks
            max_iterations_per_task: Maximum iterations for a single task
            enable_loop_detection: Whether to enable loop detection
        """
        self.safety_limiter = SafetyLimiter(
            max_iterations=max_global_iterations,
            max_iterations_per_task=max_iterations_per_task,
            enable_loop_detection=enable_loop_detection,
        )

        self.action_registry: Dict[str, Callable[..., Awaitable[Any]]] = {}

        logger.info(
            "task_executor_initialized",
            max_global_iterations=max_global_iterations,
            max_iterations_per_task=max_iterations_per_task,
            loop_detection_enabled=enable_loop_detection,
        )

    def register_action(
        self, action_name: str, handler: Callable[..., Awaitable[Any]]
    ) -> None:
        """
        Register an action handler.

        Args:
            action_name: Name of the action (matches AnalyticsTask.action)
            handler: Async function to handle the action
        """
        self.action_registry[action_name] = handler
        logger.debug("action_registered", action=action_name)

    async def execute_tasks(
        self,
        tasks: List[AnalyticsTask],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[AnalyticsTask]:
        """
        Execute a list of tasks sequentially with safety checks.

        Args:
            tasks: List of tasks to execute
            context: Shared context available to all tasks

        Returns:
            List of tasks with results and status updated

        Raises:
            TaskExecutionError: If critical error occurs
        """
        context = context or {}
        tracker = ProgressTracker(
            "Analytics Task Execution",
            total_steps=len(tasks),
            task_count=len(tasks),
        )

        try:
            for task in tasks:
                # Check dependencies
                if not self._dependencies_met(task, tasks):
                    task.error = "Dependencies not met - skipping task"
                    logger.warning(
                        "task_skipped_dependencies",
                        task_id=task.id,
                        description=task.description,
                        dependencies=task.dependencies,
                    )
                    tracker.step(f"Skipped: {task.description}", task_id=task.id)
                    continue

                # Execute task with retries and safety checks
                await self._execute_single_task(task, context, tracker)

                # Reset task-specific safety limits for next task
                self.safety_limiter.reset_task(str(task.id))

            tracker.complete("All tasks processed")
            return tasks

        except Exception as e:
            tracker.fail(e)
            logger.error(
                "task_execution_failed",
                error=str(e),
                completed_tasks=[t.id for t in tasks if t.done],
                failed_tasks=[t.id for t in tasks if t.error],
            )
            raise TaskExecutionError(f"Task execution failed: {e}") from e

    async def _execute_single_task(
        self,
        task: AnalyticsTask,
        context: Dict[str, Any],
        tracker: ProgressTracker,
    ) -> None:
        """
        Execute a single task with retry logic and safety checks.

        Args:
            task: Task to execute
            context: Execution context
            tracker: Progress tracker
        """
        task_id_str = str(task.id)
        iterations = 0

        logger.info(
            "task_started",
            task_id=task.id,
            description=task.description,
            action=task.action,
        )

        tracker.step(f"Executing: {task.description}", task_id=task.id)

        while not task.done and iterations < self.safety_limiter.max_iterations_per_task:
            # Create action signature for loop detection
            action_sig = f"{task.action}:{task.params}"

            # Safety check
            if self.safety_limiter.should_stop(task_id_str, action_sig):
                task.error = "Safety limit exceeded (max iterations or loop detected)"
                logger.error(
                    "task_safety_limit_exceeded",
                    task_id=task.id,
                    description=task.description,
                    iterations=iterations,
                )
                break

            try:
                # Execute the task action
                result = await self._execute_action(task, context)

                # Mark as done and store result
                task.result = result
                task.done = True

                logger.info(
                    "task_completed",
                    task_id=task.id,
                    description=task.description,
                    iterations=iterations + 1,
                )

            except Exception as e:
                iterations += 1
                self.safety_limiter.increment(task_id_str)

                error_msg = f"{type(e).__name__}: {str(e)}"

                logger.warning(
                    "task_iteration_failed",
                    task_id=task.id,
                    description=task.description,
                    iteration=iterations,
                    error=error_msg,
                )

                # If max iterations reached, mark as failed
                if iterations >= self.safety_limiter.max_iterations_per_task:
                    task.error = f"Failed after {iterations} attempts: {error_msg}"
                    logger.error(
                        "task_failed",
                        task_id=task.id,
                        description=task.description,
                        final_error=error_msg,
                        attempts=iterations,
                    )
                    break

                # Otherwise continue to next iteration (retry)
                task.error = f"Attempt {iterations} failed: {error_msg}"

    async def _execute_action(
        self, task: AnalyticsTask, context: Dict[str, Any]
    ) -> Any:
        """
        Execute the task's action using registered handler.

        Args:
            task: Task to execute
            context: Execution context

        Returns:
            Result from action handler

        Raises:
            ValueError: If action not registered
            Exception: Any exception from action handler
        """
        if task.action not in self.action_registry:
            raise ValueError(f"Action '{task.action}' not registered")

        handler = self.action_registry[task.action]

        # Merge task params with context
        execution_params = {**context, **task.params}

        logger.debug(
            "action_executing",
            task_id=task.id,
            action=task.action,
            params=execution_params,
        )

        # Execute handler
        result = await handler(**execution_params)

        return result

    def _dependencies_met(
        self, task: AnalyticsTask, all_tasks: List[AnalyticsTask]
    ) -> bool:
        """
        Check if all task dependencies are satisfied.

        Args:
            task: Task to check
            all_tasks: List of all tasks

        Returns:
            True if all dependencies are met, False otherwise
        """
        if not task.dependencies:
            return True

        for dep_id in task.dependencies:
            dep_task = next((t for t in all_tasks if t.id == dep_id), None)

            if not dep_task:
                logger.warning(
                    "dependency_not_found",
                    task_id=task.id,
                    missing_dependency=dep_id,
                )
                return False

            if not dep_task.done:
                logger.debug(
                    "dependency_not_complete",
                    task_id=task.id,
                    waiting_for=dep_id,
                )
                return False

        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Dictionary with execution stats
        """
        return {
            **self.safety_limiter.get_stats(),
            "registered_actions": list(self.action_registry.keys()),
        }


# Convenience function for simple task execution
async def execute_analytics_workflow(
    tasks: List[AnalyticsTask],
    action_handlers: Dict[str, Callable[..., Awaitable[Any]]],
    context: Optional[Dict[str, Any]] = None,
) -> List[AnalyticsTask]:
    """
    Convenience function for executing analytics workflows.

    Args:
        tasks: List of tasks to execute
        action_handlers: Dictionary mapping action names to handler functions
        context: Optional shared context

    Returns:
        List of completed tasks

    Example:
        tasks = [
            AnalyticsTask(id=1, description="Fetch data", action="fetch"),
            AnalyticsTask(id=2, description="Process", action="process"),
        ]

        async def fetch(**kwargs):
            return await db.fetch_data()

        async def process(**kwargs):
            return calculate_results()

        results = await execute_analytics_workflow(
            tasks=tasks,
            action_handlers={"fetch": fetch, "process": process}
        )
    """
    executor = TaskExecutor()

    # Register all handlers
    for action_name, handler in action_handlers.items():
        executor.register_action(action_name, handler)

    # Execute tasks
    return await executor.execute_tasks(tasks, context)
