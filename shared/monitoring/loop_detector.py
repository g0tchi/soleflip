"""
Loop Detection Module

Prevents infinite loops in background jobs, data processing, and automated operations.
Inspired by Dexter's safety mechanisms (github.com/virattt/dexter).

Usage:
    detector = LoopDetector(window_size=4)

    for operation in operations:
        detector.track_action(f"fetch_orders:{sku}")

        if detector.is_looping():
            raise LoopDetectionError("Infinite loop detected")

        perform_operation()
"""

from typing import List, Optional

import structlog

logger = structlog.get_logger(__name__)


class LoopDetectionError(Exception):
    """Raised when an infinite loop is detected."""

    pass


class LoopDetector:
    """
    Detects infinite loops in automated operations.

    Tracks recent actions and identifies when the same action is repeated
    consecutively, indicating a potential infinite loop.

    Attributes:
        window_size: Number of recent actions to track (default: 4)
        action_history: List of recent action signatures
    """

    def __init__(self, window_size: int = 4) -> None:
        """
        Initialize the loop detector.

        Args:
            window_size: Number of actions to track for loop detection.
                        If same action appears window_size times consecutively,
                        it's considered a loop. Default is 4 (same as Dexter).
        """
        if window_size < 2:
            raise ValueError("window_size must be at least 2")

        self.window_size = window_size
        self.action_history: List[str] = []
        self._loop_count = 0

    def track_action(self, action_signature: str) -> None:
        """
        Track an action in the history.

        Args:
            action_signature: String identifier for the action.
                            Format: "action_name:param1=value1,param2=value2"
                            Example: "fetch_orders:platform=stockx,days=7"
        """
        self.action_history.append(action_signature)

        # Keep only the last window_size actions
        if len(self.action_history) > self.window_size:
            self.action_history = self.action_history[-self.window_size :]

        logger.debug(
            "action_tracked",
            action=action_signature,
            history_size=len(self.action_history),
            window_size=self.window_size,
        )

    def is_looping(self) -> bool:
        """
        Check if a loop has been detected.

        A loop is detected when:
        1. The action history is full (length == window_size)
        2. All actions in the window are identical

        Returns:
            True if loop detected, False otherwise
        """
        # Need full window to detect loop
        if len(self.action_history) < self.window_size:
            return False

        # Check if all actions in window are the same
        unique_actions = set(self.action_history)

        if len(unique_actions) == 1:
            self._loop_count += 1
            logger.warning(
                "loop_detected",
                repeated_action=self.action_history[0],
                window_size=self.window_size,
                loop_count=self._loop_count,
            )
            return True

        return False

    def reset(self) -> None:
        """
        Reset the action history.

        Call this between different operations or when starting a new task
        to avoid false positives from previous operations.
        """
        previous_size = len(self.action_history)
        self.action_history.clear()
        self._loop_count = 0

        logger.debug(
            "loop_detector_reset",
            previous_history_size=previous_size,
        )

    def get_current_action(self) -> Optional[str]:
        """
        Get the most recent action tracked.

        Returns:
            The last action signature, or None if no actions tracked
        """
        return self.action_history[-1] if self.action_history else None

    def get_history(self) -> List[str]:
        """
        Get the current action history.

        Returns:
            List of recent action signatures
        """
        return self.action_history.copy()

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"LoopDetector(window_size={self.window_size}, "
            f"history_size={len(self.action_history)}, "
            f"is_looping={self.is_looping()})"
        )


class SafetyLimiter:
    """
    Enforces iteration limits to prevent runaway processes.

    Combines loop detection with hard iteration limits for comprehensive safety.

    Usage:
        limiter = SafetyLimiter(max_iterations=20, max_per_task=5)

        for task in tasks:
            task_limiter = limiter.for_task(task.id)

            while not task.done:
                if task_limiter.should_stop():
                    raise MaxIterationsExceeded()

                task_limiter.increment()
                process_task()
    """

    def __init__(
        self,
        max_iterations: int = 20,
        max_iterations_per_task: int = 5,
        enable_loop_detection: bool = True,
    ) -> None:
        """
        Initialize the safety limiter.

        Args:
            max_iterations: Global maximum iterations across all tasks
            max_iterations_per_task: Maximum iterations for a single task
            enable_loop_detection: Whether to enable loop detection
        """
        self.max_iterations = max_iterations
        self.max_iterations_per_task = max_iterations_per_task
        self.enable_loop_detection = enable_loop_detection

        self._global_count = 0
        self._task_counts: dict[str, int] = {}
        self._loop_detectors: dict[str, LoopDetector] = {}

        logger.info(
            "safety_limiter_initialized",
            max_iterations=max_iterations,
            max_iterations_per_task=max_iterations_per_task,
            loop_detection_enabled=enable_loop_detection,
        )

    def increment(self, task_id: Optional[str] = None) -> None:
        """
        Increment iteration counters.

        Args:
            task_id: Optional task identifier for per-task tracking
        """
        self._global_count += 1

        if task_id:
            self._task_counts[task_id] = self._task_counts.get(task_id, 0) + 1

    def should_stop(
        self,
        task_id: Optional[str] = None,
        action_signature: Optional[str] = None,
    ) -> bool:
        """
        Check if execution should stop due to safety limits.

        Args:
            task_id: Optional task identifier
            action_signature: Optional action signature for loop detection

        Returns:
            True if any safety limit is exceeded, False otherwise
        """
        # Check global limit
        if self._global_count >= self.max_iterations:
            logger.warning(
                "global_iteration_limit_reached",
                count=self._global_count,
                limit=self.max_iterations,
            )
            return True

        # Check per-task limit
        if task_id:
            task_count = self._task_counts.get(task_id, 0)
            if task_count >= self.max_iterations_per_task:
                logger.warning(
                    "task_iteration_limit_reached",
                    task_id=task_id,
                    count=task_count,
                    limit=self.max_iterations_per_task,
                )
                return True

            # Check for loops if enabled
            if self.enable_loop_detection and action_signature:
                if task_id not in self._loop_detectors:
                    self._loop_detectors[task_id] = LoopDetector()

                detector = self._loop_detectors[task_id]
                detector.track_action(action_signature)

                if detector.is_looping():
                    logger.error(
                        "loop_detected_stopping",
                        task_id=task_id,
                        repeated_action=action_signature,
                    )
                    return True

        return False

    def reset_task(self, task_id: str) -> None:
        """
        Reset counters for a specific task.

        Args:
            task_id: Task identifier to reset
        """
        if task_id in self._task_counts:
            del self._task_counts[task_id]

        if task_id in self._loop_detectors:
            self._loop_detectors[task_id].reset()

        logger.debug("task_counters_reset", task_id=task_id)

    def reset_all(self) -> None:
        """Reset all counters and detectors."""
        self._global_count = 0
        self._task_counts.clear()
        self._loop_detectors.clear()

        logger.info("safety_limiter_reset_all")

    def get_stats(self) -> dict:
        """
        Get current statistics.

        Returns:
            Dictionary with iteration counts and loop detection info
        """
        return {
            "global_count": self._global_count,
            "global_limit": self.max_iterations,
            "task_counts": self._task_counts.copy(),
            "per_task_limit": self.max_iterations_per_task,
            "active_tasks": len(self._task_counts),
            "loop_detection_enabled": self.enable_loop_detection,
        }
