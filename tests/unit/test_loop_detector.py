"""
Tests for Loop Detection Module

Tests the safety mechanisms that prevent infinite loops in automated operations.
"""

import pytest

from shared.monitoring.loop_detector import LoopDetector, SafetyLimiter, LoopDetectionError


class TestLoopDetector:
    """Test cases for LoopDetector class."""

    def test_initialization(self):
        """Test detector initializes with correct defaults."""
        detector = LoopDetector()

        assert detector.window_size == 4
        assert detector.action_history == []
        assert not detector.is_looping()

    def test_initialization_with_custom_window(self):
        """Test detector initializes with custom window size."""
        detector = LoopDetector(window_size=3)

        assert detector.window_size == 3

    def test_initialization_invalid_window_size(self):
        """Test detector raises error for invalid window size."""
        with pytest.raises(ValueError, match="window_size must be at least 2"):
            LoopDetector(window_size=1)

    def test_track_action(self):
        """Test action tracking."""
        detector = LoopDetector(window_size=3)

        detector.track_action("action1")
        assert len(detector.action_history) == 1

        detector.track_action("action2")
        assert len(detector.action_history) == 2

    def test_history_size_limit(self):
        """Test that history is limited to window_size."""
        detector = LoopDetector(window_size=3)

        for i in range(5):
            detector.track_action(f"action{i}")

        # Should only keep last 3 actions
        assert len(detector.action_history) == 3
        assert detector.action_history == ["action2", "action3", "action4"]

    def test_loop_detection_positive(self):
        """Test that loops are detected correctly."""
        detector = LoopDetector(window_size=4)

        # Repeat same action 4 times
        for _ in range(4):
            detector.track_action("same_action:param=value")

        assert detector.is_looping()

    def test_loop_detection_negative_different_actions(self):
        """Test that different actions don't trigger loop detection."""
        detector = LoopDetector(window_size=4)

        detector.track_action("action1")
        detector.track_action("action2")
        detector.track_action("action3")
        detector.track_action("action4")

        assert not detector.is_looping()

    def test_loop_detection_negative_partial_window(self):
        """Test that partial window doesn't trigger loop detection."""
        detector = LoopDetector(window_size=4)

        # Only 3 actions, need 4 for full window
        for _ in range(3):
            detector.track_action("same_action")

        assert not detector.is_looping()

    def test_loop_detection_with_pattern(self):
        """Test loop detection with alternating pattern."""
        detector = LoopDetector(window_size=4)

        detector.track_action("action1")
        detector.track_action("action2")
        detector.track_action("action1")
        detector.track_action("action2")

        # This is NOT a loop (different actions)
        assert not detector.is_looping()

    def test_reset(self):
        """Test that reset clears history."""
        detector = LoopDetector(window_size=3)

        detector.track_action("action1")
        detector.track_action("action2")
        assert len(detector.action_history) == 2

        detector.reset()

        assert len(detector.action_history) == 0
        assert not detector.is_looping()

    def test_get_current_action(self):
        """Test getting current action."""
        detector = LoopDetector()

        assert detector.get_current_action() is None

        detector.track_action("action1")
        assert detector.get_current_action() == "action1"

        detector.track_action("action2")
        assert detector.get_current_action() == "action2"

    def test_get_history(self):
        """Test getting history returns copy."""
        detector = LoopDetector()

        detector.track_action("action1")
        detector.track_action("action2")

        history = detector.get_history()
        assert history == ["action1", "action2"]

        # Modifying returned history shouldn't affect detector
        history.append("action3")
        assert len(detector.action_history) == 2


class TestSafetyLimiter:
    """Test cases for SafetyLimiter class."""

    def test_initialization(self):
        """Test limiter initializes correctly."""
        limiter = SafetyLimiter(
            max_iterations=20,
            max_iterations_per_task=5,
        )

        assert limiter.max_iterations == 20
        assert limiter.max_iterations_per_task == 5

    def test_global_limit_enforcement(self):
        """Test global iteration limit is enforced."""
        limiter = SafetyLimiter(max_iterations=3)

        for i in range(3):
            limiter.increment()
            if i < 2:
                assert not limiter.should_stop()

        # 3rd increment should trigger limit
        assert limiter.should_stop()

    def test_per_task_limit_enforcement(self):
        """Test per-task iteration limit is enforced."""
        limiter = SafetyLimiter(
            max_iterations=100,
            max_iterations_per_task=3,
        )

        task_id = "task1"

        for i in range(3):
            limiter.increment(task_id)
            if i < 2:
                assert not limiter.should_stop(task_id)

        # 3rd iteration should trigger task limit
        assert limiter.should_stop(task_id)

    def test_multiple_tasks(self):
        """Test that different tasks have independent counters."""
        limiter = SafetyLimiter(
            max_iterations=100,
            max_iterations_per_task=3,
        )

        # Task 1: increment 3 times
        for _ in range(3):
            limiter.increment("task1")

        # Task 1 should be at limit
        assert limiter.should_stop("task1")

        # Task 2 should still be ok
        limiter.increment("task2")
        assert not limiter.should_stop("task2")

    def test_loop_detection_integration(self):
        """Test loop detection integration."""
        limiter = SafetyLimiter(
            max_iterations=100,
            max_iterations_per_task=100,
            enable_loop_detection=True,
        )

        task_id = "task1"

        # Repeat same action 3 times (fills window but doesn't trigger)
        for _ in range(3):
            assert not limiter.should_stop(
                task_id=task_id,
                action_signature="same_action:params",
            )

        # 4th time should detect loop (window_size=4)
        assert limiter.should_stop(
            task_id=task_id,
            action_signature="same_action:params",
        )

    def test_loop_detection_disabled(self):
        """Test that loop detection can be disabled."""
        limiter = SafetyLimiter(
            max_iterations=100,
            max_iterations_per_task=100,
            enable_loop_detection=False,
        )

        task_id = "task1"

        # Repeat same action many times
        for _ in range(10):
            result = limiter.should_stop(
                task_id=task_id,
                action_signature="same_action",
            )
            assert not result  # Should never stop due to loop

    def test_reset_task(self):
        """Test resetting task counters."""
        limiter = SafetyLimiter(max_iterations_per_task=3)

        task_id = "task1"

        # Increment to limit
        for _ in range(3):
            limiter.increment(task_id)

        assert limiter.should_stop(task_id)

        # Reset task
        limiter.reset_task(task_id)

        # Should be able to continue
        limiter.increment(task_id)
        assert not limiter.should_stop(task_id)

    def test_reset_all(self):
        """Test resetting all counters."""
        limiter = SafetyLimiter(
            max_iterations=5,
            max_iterations_per_task=3,
        )

        # Increment global and task counters
        limiter.increment("task1")
        limiter.increment("task2")

        # Reset all
        limiter.reset_all()

        # Should be back to zero
        stats = limiter.get_stats()
        assert stats["global_count"] == 0
        assert len(stats["task_counts"]) == 0

    def test_get_stats(self):
        """Test getting statistics."""
        limiter = SafetyLimiter(
            max_iterations=20,
            max_iterations_per_task=5,
        )

        limiter.increment("task1")
        limiter.increment("task1")
        limiter.increment("task2")

        stats = limiter.get_stats()

        assert stats["global_count"] == 3
        assert stats["global_limit"] == 20
        assert stats["task_counts"] == {"task1": 2, "task2": 1}
        assert stats["per_task_limit"] == 5
        assert stats["active_tasks"] == 2
