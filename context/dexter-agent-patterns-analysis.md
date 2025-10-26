# Dexter Agent Patterns Analysis

**Date**: 2025-10-19
**Repository**: https://github.com/virattt/dexter
**Purpose**: Autonomous agent for deep financial research
**Stars**: 1,618 | **Language**: Python | **Status**: Active (created 2025-10-14)

## Overview

Dexter is an autonomous financial research agent that demonstrates advanced LLM-based orchestration patterns. It performs analysis using task planning, self-reflection, and real-time market data - essentially "Claude Code for financial research."

## Core Architecture

### Multi-Agent Pattern
Dexter uses **4 specialized sub-agents**, each with focused responsibilities:

1. **Planning Agent** (`PLANNING_SYSTEM_PROMPT`)
   - Analyzes user queries
   - Breaks down into structured task lists
   - Ensures tasks are SPECIFIC, ATOMIC, SEQUENTIAL, TOOL-ALIGNED
   - Returns empty task list if query is out of scope

2. **Action Agent** (`ACTION_SYSTEM_PROMPT`)
   - Selects appropriate tools for each task
   - Reviews previous outputs to avoid redundancy
   - Decides when no more tools are needed
   - Returns without tool calls when task is complete

3. **Validation Agent** (`VALIDATION_SYSTEM_PROMPT`)
   - Assesses task completion
   - Checks if data is sufficient
   - Distinguishes between "no data" (done) vs "error" (retry)
   - Validates partial vs complete results

4. **Answer Agent** (`ANSWER_SYSTEM_PROMPT`)
   - Synthesizes final answer from collected data
   - Leads with key findings
   - Includes specific numbers with context
   - Uses plain text formatting (no markdown)

### Agent Orchestration Flow

```python
# From agent.py - main loop
def run(self, query: str):
    # 1. Planning Phase
    tasks = self.plan_tasks(query)

    # 2. Execution Phase
    while any(not t.done for t in tasks):
        task = next(t for t in tasks if not t.done)

        # Per-task loop with safety limits
        while per_task_steps < self.max_steps_per_task:
            # 2a. Ask for next action
            ai_message = self.ask_for_actions(task.description, last_outputs)

            # 2b. Execute tools
            for tool_call in ai_message.tool_calls:
                optimized_args = self.optimize_tool_args(...)
                result = self._execute_tool(...)

            # 2c. Validate completion
            if self.ask_if_done(task.description, task_outputs):
                task.done = True
                break

    # 3. Answer Generation Phase
    answer = self._generate_answer(query, session_outputs)
    return answer
```

## Key Patterns & Techniques

### 1. Safety Features ⭐⭐⭐

**Loop Detection**:
```python
# Track last 4 actions
last_actions.append(f"{tool_name}:{optimized_args}")
if len(last_actions) > 4:
    last_actions = last_actions[-4:]

# Detect infinite loops (same action 4x)
if len(set(last_actions)) == 1 and len(last_actions) == 4:
    self.logger._log("Detected repeating action — aborting to avoid loop.")
    return
```

**Step Limits**:
```python
max_steps: int = 20              # Global safety cap
max_steps_per_task: int = 5      # Per-task iteration limit
```

### 2. Tool Argument Optimization ⭐⭐

**Separate optimization step** before tool execution:
```python
def optimize_tool_args(self, tool_name: str, initial_args: dict, task_desc: str) -> dict:
    """Optimize tool arguments based on task requirements."""
    # LLM reviews initial args and task description
    # Returns optimized parameters with proper filtering
    # Falls back to initial args on error
```

**Benefits**:
- Prevents suboptimal API calls
- Adds missing optional parameters
- Improves result quality through better filtering

### 3. Structured Pydantic Schemas ⭐

**Type-safe LLM outputs**:
```python
class Task(BaseModel):
    id: int
    description: str
    done: bool

class TaskList(BaseModel):
    tasks: List[Task]

class IsDone(BaseModel):
    done: bool

class Answer(BaseModel):
    answer: str

class OptimizedToolArgs(BaseModel):
    arguments: Dict[str, Any]
```

**Usage**:
```python
response = call_llm(prompt, system_prompt=PLANNING_SYSTEM_PROMPT, output_schema=TaskList)
tasks = response.tasks  # Type-safe access
```

### 4. Progress Indicators ⭐

**Decorator pattern** for UX feedback:
```python
@show_progress("Planning tasks...", "Tasks planned")
def plan_tasks(self, query: str) -> List[Task]:
    # Long-running operation
    pass

@show_progress("Executing {tool_name}...", "")
def run_tool():
    return tool.run(inp_args)
```

### 5. Comprehensive Logging ⭐

**Structured event logging**:
```python
class Logger:
    def log_user_query(self, query: str)
    def log_task_list(self, task_dicts: List[dict])
    def log_task_start(self, description: str)
    def log_task_done(self, description: str)
    def log_tool_run(self, tool_name: str, result: str)
    def log_summary(self, answer: str)
```

### 6. Fail-Safe Defaults

**Graceful degradation** throughout:
```python
try:
    response = call_llm(...)
    tasks = response.tasks
except Exception as e:
    self.logger._log(f"Planning failed: {e}")
    # Fallback: treat entire query as single task
    tasks = [Task(id=1, description=query, done=False)]
```

## System Prompts Analysis

### Planning Prompt Highlights
- Explicitly defines "Good" vs "Bad" task examples
- Instructs to return EMPTY task list for out-of-scope queries
- Emphasizes SPECIFIC, ATOMIC, SEQUENTIAL, TOOL-ALIGNED tasks
- Includes full tool descriptions for context

### Action Prompt Highlights
- Clear "Decision Process" steps
- "When NOT to call tools" section prevents over-execution
- Tool selection guidelines with parameter usage examples

### Validation Prompt Highlights
- Defines completion criteria with 3 specific conditions
- Defines non-completion criteria (4 specific conditions)
- Distinguishes "no data with reason" (done) vs "empty results" (not done)

### Answer Prompt Highlights
- Structure: Lead with key finding → Specific numbers → Brief analysis
- Formatting: Plain text only, no markdown
- Explicitly says "Don't describe the process of gathering data"

## Technical Stack

```toml
# From pyproject.toml
dependencies = [
    "langchain>=0.3.27",
    "langchain-openai>=0.3.35",
    "openai>=2.2.0",
    "prompt-toolkit>=3.0.0",
    "pydantic>=2.11.10",
    "python-dotenv>=1.1.1",
    "requests>=2.32.5",
]
```

**Notable**:
- Uses **uv** package manager (modern, fast)
- LangChain for LLM orchestration
- Pydantic 2.x for structured outputs
- Minimal dependencies (focused, not bloated)

## Project Structure

```
dexter/
├── src/dexter/
│   ├── agent.py         # Main orchestration (10,938 bytes)
│   ├── prompts.py       # System prompts (7,974 bytes)
│   ├── schemas.py       # Pydantic models (1,094 bytes)
│   ├── model.py         # LLM interface (1,452 bytes)
│   ├── cli.py           # CLI entry (805 bytes)
│   ├── tools/           # Financial data tools
│   └── utils/           # Logger, UI helpers
```

**Observations**:
- Clean, focused architecture
- Small file sizes (good separation of concerns)
- Main logic in agent.py (~300 lines)
- Prompts separated from code

## Adaptable Ideas for SoleFlipper

### ✅ Immediate Implementation (Low-Hanging Fruit)

#### 1. Safety Monitor - Loop Detection
**Where**: `shared/monitoring/loop_detector.py`

```python
class LoopDetector:
    """Prevents infinite loops in background jobs and data processing"""

    def __init__(self, window_size: int = 4):
        self.window_size = window_size
        self.action_history: List[str] = []

    def track_action(self, action_signature: str) -> None:
        """Track an action (e.g., 'fetch_orders:sku=ABC')"""
        self.action_history.append(action_signature)
        if len(self.action_history) > self.window_size:
            self.action_history = self.action_history[-self.window_size:]

    def is_looping(self) -> bool:
        """Detect if same action repeated window_size times"""
        if len(self.action_history) < self.window_size:
            return False
        return len(set(self.action_history)) == 1

    def reset(self) -> None:
        """Reset tracking for new operation"""
        self.action_history.clear()
```

**Use cases**:
- Background job retry logic
- CSV import processing
- StockX API sync loops
- Price update iterations

#### 2. Structured Task Execution
**Where**: `domains/analytics/services/task_executor.py`

```python
from pydantic import BaseModel
from typing import List, Callable, Any

class AnalyticsTask(BaseModel):
    """Structured task for multi-step analytics"""
    id: int
    description: str
    action: str  # Function name to call
    params: dict
    done: bool = False
    result: Any = None
    error: Optional[str] = None

class TaskExecutor:
    """Orchestrates multi-step analytics operations"""

    def __init__(self, max_iterations_per_task: int = 5):
        self.max_iterations_per_task = max_iterations_per_task
        self.loop_detector = LoopDetector()

    async def execute_tasks(
        self,
        tasks: List[AnalyticsTask],
        context: dict
    ) -> List[AnalyticsTask]:
        """Execute tasks sequentially with safety checks"""

        for task in tasks:
            iterations = 0

            while not task.done and iterations < self.max_iterations_per_task:
                # Check for loops
                action_sig = f"{task.action}:{task.params}"
                self.loop_detector.track_action(action_sig)

                if self.loop_detector.is_looping():
                    task.error = "Loop detected - aborting task"
                    break

                try:
                    # Execute task
                    result = await self._execute_task(task, context)
                    task.result = result
                    task.done = True
                except Exception as e:
                    task.error = str(e)
                    iterations += 1

            # Reset loop detector for next task
            self.loop_detector.reset()

        return tasks

    async def _execute_task(self, task: AnalyticsTask, context: dict) -> Any:
        """Execute single task based on action name"""
        # Map action names to actual methods
        # e.g., "fetch_inventory" → self.fetch_inventory(task.params)
        pass
```

**Use cases**:
- Multi-step forecasting workflows
- Complex inventory analysis
- Dead stock identification
- Price optimization pipelines

#### 3. Progress Tracking Decorator
**Where**: `shared/monitoring/progress_tracker.py`

```python
import structlog
from functools import wraps
from contextlib import contextmanager
from typing import Optional

logger = structlog.get_logger(__name__)

def track_progress(
    start_message: str,
    end_message: Optional[str] = None,
    log_result: bool = False
):
    """Decorator for tracking operation progress"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.info("operation_started", message=start_message, function=func.__name__)

            try:
                result = await func(*args, **kwargs)

                final_msg = end_message or f"{start_message} - completed"
                log_data = {"message": final_msg, "function": func.__name__}

                if log_result:
                    log_data["result_preview"] = str(result)[:100]

                logger.info("operation_completed", **log_data)
                return result

            except Exception as e:
                logger.error(
                    "operation_failed",
                    message=f"{start_message} - failed",
                    function=func.__name__,
                    error=str(e),
                    exc_info=True
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.info("operation_started", message=start_message, function=func.__name__)

            try:
                result = func(*args, **kwargs)

                final_msg = end_message or f"{start_message} - completed"
                logger.info("operation_completed", message=final_msg, function=func.__name__)
                return result

            except Exception as e:
                logger.error(
                    "operation_failed",
                    message=f"{start_message} - failed",
                    function=func.__name__,
                    error=str(e),
                    exc_info=True
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator

@contextmanager
def track_operation(description: str):
    """Context manager for tracking code blocks"""
    logger.info("operation_started", description=description)
    try:
        yield
        logger.info("operation_completed", description=description)
    except Exception as e:
        logger.error("operation_failed", description=description, error=str(e))
        raise
```

**Usage examples**:
```python
# As decorator
@track_progress("Generating 12-month forecast", "Forecast ready")
async def generate_forecast(self, product_id: UUID):
    # Long ARIMA calculation
    pass

# As context manager
async def process_large_import(self, file_path: str):
    with track_operation("Processing CSV import"):
        # Multi-step import logic
        await self.validate_csv(file_path)
        await self.transform_data()
        await self.bulk_insert()
```

### 🚀 Medium-Term (Requires LLM Integration)

#### 4. Natural Language Query Interface
**Where**: `domains/analytics/api/query_endpoint.py`

Not implemented yet - requires OpenAI/LangChain integration decision.

#### 5. Autonomous Pricing Agent
**Where**: `domains/pricing/agents/pricing_agent.py`

Not implemented yet - requires LLM integration.

### 🔮 Long-Term (Advanced)

#### 6. Full Autonomous Analytics Agent
Similar to Dexter but for sneaker inventory/pricing data.

## Implementation Priority

1. **✅ NOW**: Safety Monitor (Loop Detection)
   - Critical for background jobs
   - Prevents runaway processes
   - Easy to integrate

2. **✅ NOW**: Progress Tracking
   - Better UX for long operations
   - Improved observability
   - Simple decorator pattern

3. **✅ NOW**: Task Executor
   - Structured multi-step operations
   - Safety built-in
   - Reusable across domains

4. **LATER**: LLM-based features (requires API key decision)

## Key Takeaways

1. **Multi-agent decomposition** makes complex operations manageable
2. **Safety-first design** prevents runaway execution
3. **Structured schemas** ensure type safety with LLMs
4. **Progress feedback** improves user experience
5. **Fail-safe defaults** handle errors gracefully
6. **Small, focused modules** maintain clean architecture

## References

- **Repository**: https://github.com/virattt/dexter
- **Stars**: 1,618
- **Created**: 2025-10-14
- **Last Updated**: 2025-10-18
- **License**: MIT
- **Key Files**:
  - `src/dexter/agent.py` - Main orchestration logic
  - `src/dexter/prompts.py` - System prompts
  - `src/dexter/schemas.py` - Pydantic models

## Notes

- Very clean, minimal codebase (~300 lines main logic)
- Excellent prompt engineering examples
- Strong safety mechanisms
- Production-ready patterns despite being only 5 days old
- Good separation of concerns (prompts, schemas, logic)
