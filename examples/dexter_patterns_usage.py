"""
Example Usage of Dexter-Inspired Patterns

Demonstrates how to use the new safety, progress tracking, and task execution
modules inspired by the Dexter autonomous agent.
"""

import asyncio
from uuid import uuid4

# Example 1: Loop Detection
from shared.monitoring.loop_detector import LoopDetector, SafetyLimiter


def example_loop_detection():
    """Example: Basic loop detection."""
    print("\n=== Example 1: Loop Detection ===\n")

    detector = LoopDetector(window_size=4)

    # Simulate some operations
    operations = [
        "fetch_orders:platform=stockx",
        "fetch_orders:platform=ebay",
        "fetch_orders:platform=goat",
        "fetch_orders:platform=stockx",  # Different action
        "update_price:sku=ABC",
        "update_price:sku=ABC",  # Repeated
        "update_price:sku=ABC",  # Repeated
        "update_price:sku=ABC",  # Repeated - will trigger loop detection
    ]

    for action in operations:
        detector.track_action(action)
        print(f"Action: {action}")

        if detector.is_looping():
            print(f"⚠️  LOOP DETECTED! Repeated action: {action}")
            print(f"   History: {detector.get_history()}")
            break

        print(f"   History: {detector.get_history()}")


def example_safety_limiter():
    """Example: Safety limiter with multiple tasks."""
    print("\n=== Example 2: Safety Limiter ===\n")

    limiter = SafetyLimiter(
        max_iterations=10,
        max_iterations_per_task=3,
        enable_loop_detection=True,
    )

    # Simulate processing multiple tasks
    tasks = ["task_a", "task_b", "task_c"]

    for task_id in tasks:
        print(f"\nProcessing {task_id}:")
        iteration = 0

        while iteration < 5:  # Try 5 times
            action_sig = f"process:{task_id}:iteration={iteration}"

            if limiter.should_stop(task_id=task_id, action_signature=action_sig):
                print(f"  ❌ Stopped due to safety limits")
                break

            limiter.increment(task_id)
            iteration += 1
            print(f"  ✓ Iteration {iteration} completed")

    print(f"\nFinal stats: {limiter.get_stats()}")


# Example 2: Progress Tracking
from shared.monitoring.progress_tracker import (
    track_progress,
    track_operation,
    ProgressTracker,
)


@track_progress("Fetching inventory data", "Inventory data loaded")
async def fetch_inventory_with_progress():
    """Example: Using decorator for progress tracking."""
    await asyncio.sleep(0.5)  # Simulate API call
    return {"products": 150, "total_value": 45000}


async def example_progress_decorator():
    """Example: Progress tracking with decorator."""
    print("\n=== Example 3: Progress Tracking (Decorator) ===\n")

    result = await fetch_inventory_with_progress()
    print(f"Result: {result}")


def example_progress_context_manager():
    """Example: Progress tracking with context manager."""
    print("\n=== Example 4: Progress Tracking (Context Manager) ===\n")

    with track_operation("Importing CSV data", file_name="sales_2024.csv"):
        print("  - Validating CSV structure...")
        print("  - Transforming data...")
        print("  - Bulk inserting records...")
    print("Done!")


def example_progress_tracker():
    """Example: Multi-step progress tracker."""
    print("\n=== Example 5: Multi-Step Progress Tracker ===\n")

    tracker = ProgressTracker("Dead Stock Analysis", total_steps=4)

    tracker.step("Fetching inventory older than 90 days", count=120)
    tracker.step("Calculating profit margins", avg_margin=-0.05)
    tracker.step("Identifying low-velocity products", velocity_threshold=0.1)
    tracker.step("Generating recommendations", actions=15)

    tracker.complete("Analysis complete", total_dead_stock_value=12500)

    print(f"\nStats: {tracker.get_stats()}")


# Example 3: Task Execution
from domains.analytics.services.task_executor import (
    AnalyticsTask,
    TaskExecutor,
    execute_analytics_workflow,
)


async def fetch_products_handler(**kwargs):
    """Mock handler: Fetch products."""
    brand = kwargs.get("brand", "Unknown")
    print(f"  → Fetching products for brand: {brand}")
    await asyncio.sleep(0.3)
    return {"products": [{"id": 1, "brand": brand, "price": 150}]}


async def calculate_margins_handler(**kwargs):
    """Mock handler: Calculate margins."""
    print("  → Calculating profit margins")
    await asyncio.sleep(0.2)
    return {"avg_margin": 0.22, "products_analyzed": 1}


async def generate_report_handler(**kwargs):
    """Mock handler: Generate report."""
    print("  → Generating report")
    await asyncio.sleep(0.1)
    return {"report_url": "/reports/analysis_123.pdf"}


async def example_task_executor():
    """Example: Structured task execution."""
    print("\n=== Example 6: Structured Task Execution ===\n")

    # Define tasks
    tasks = [
        AnalyticsTask(
            id=1,
            description="Fetch product data",
            action="fetch_products",
            params={"brand": "Nike"},
        ),
        AnalyticsTask(
            id=2,
            description="Calculate profit margins",
            action="calculate_margins",
            dependencies=[1],  # Depends on task 1
        ),
        AnalyticsTask(
            id=3,
            description="Generate analysis report",
            action="generate_report",
            dependencies=[2],  # Depends on task 2
        ),
    ]

    # Execute workflow
    results = await execute_analytics_workflow(
        tasks=tasks,
        action_handlers={
            "fetch_products": fetch_products_handler,
            "calculate_margins": calculate_margins_handler,
            "generate_report": generate_report_handler,
        },
        context={"user_id": uuid4()},
    )

    # Display results
    print("\n=== Task Results ===\n")
    for task in results:
        status = "✓ Done" if task.done else "❌ Failed"
        print(f"Task {task.id}: {status}")
        print(f"  Description: {task.description}")
        if task.result:
            print(f"  Result: {task.result}")
        if task.error:
            print(f"  Error: {task.error}")


async def example_task_executor_with_failure():
    """Example: Task execution with retry logic."""
    print("\n=== Example 7: Task Execution with Retries ===\n")

    # Handler that fails first 2 times, then succeeds
    attempt_count = 0

    async def flaky_handler(**kwargs):
        nonlocal attempt_count
        attempt_count += 1
        print(f"  → Attempt {attempt_count}")

        if attempt_count < 3:
            raise ValueError(f"Simulated failure (attempt {attempt_count})")

        return {"status": "success", "attempts": attempt_count}

    executor = TaskExecutor(max_iterations_per_task=5)
    executor.register_action("flaky_operation", flaky_handler)

    tasks = [
        AnalyticsTask(
            id=1,
            description="Flaky operation (will retry)",
            action="flaky_operation",
        ),
    ]

    results = await executor.execute_tasks(tasks)

    task = results[0]
    print(f"\nFinal status: {'✓ Success' if task.done else '❌ Failed'}")
    if task.result:
        print(f"Result: {task.result}")


# Main execution
async def main():
    """Run all examples."""
    print("=" * 60)
    print("Dexter-Inspired Patterns - Usage Examples")
    print("=" * 60)

    # Synchronous examples
    example_loop_detection()
    example_safety_limiter()
    example_progress_context_manager()
    example_progress_tracker()

    # Asynchronous examples
    await example_progress_decorator()
    await example_task_executor()
    await example_task_executor_with_failure()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
