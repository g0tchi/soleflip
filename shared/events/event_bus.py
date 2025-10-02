"""
Event Bus Implementation for Domain Communication
Provides publish-subscribe pattern for loose coupling between domains.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional, Type, Union
from uuid import UUID
import weakref

import structlog

from .base_event import BaseEvent

logger = structlog.get_logger(__name__)


class EventHandler:
    """Wrapper for event handlers to support both sync and async functions"""
    
    def __init__(self, handler: Callable, handler_name: str):
        self.handler = handler
        self.handler_name = handler_name
        self.is_async = asyncio.iscoroutinefunction(handler)
    
    async def handle(self, event: BaseEvent) -> Any:
        """Handle event (async wrapper for both sync and async handlers)"""
        try:
            if self.is_async:
                return await self.handler(event)
            else:
                return self.handler(event)
        except Exception as e:
            logger.error(
                "Event handler failed",
                handler_name=self.handler_name,
                event_type=event.event_type,
                event_id=str(event.event_id),
                error=str(e),
                exc_info=True
            )
            raise


class EventBus:
    """
    Central event bus for domain communication.
    Supports both in-memory and persistent event handling.
    """
    
    def __init__(self, enable_persistence: bool = False):
        self.enable_persistence = enable_persistence
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []
        self._middleware: List[Callable[[BaseEvent], BaseEvent]] = []
        
        # Use weak references to avoid circular dependencies
        self._domain_subscribers: Dict[str, weakref.WeakSet] = {}
        
        # Event store for debugging and replay
        self._event_history: List[BaseEvent] = []
        self._max_history_size = 1000
    
    def subscribe(
        self, 
        event_type: Union[str, Type[BaseEvent]], 
        handler: Callable[[BaseEvent], Any],
        handler_name: Optional[str] = None
    ):
        """Subscribe to specific event type"""
        if isinstance(event_type, type) and issubclass(event_type, BaseEvent):
            event_type_str = f"{event_type.model_fields['domain'].default}.{event_type.model_fields['event_type'].default}"
        else:
            event_type_str = str(event_type)
        
        handler_name = handler_name or f"{handler.__module__}.{handler.__name__}"
        event_handler = EventHandler(handler, handler_name)
        
        if event_type_str not in self._handlers:
            self._handlers[event_type_str] = []
        
        self._handlers[event_type_str].append(event_handler)
        
        logger.debug(
            "Event handler subscribed",
            event_type=event_type_str,
            handler_name=handler_name
        )
    
    def subscribe_to_domain(
        self, 
        domain: str, 
        handler: Callable[[BaseEvent], Any],
        handler_name: Optional[str] = None
    ):
        """Subscribe to all events from a specific domain"""
        handler_name = handler_name or f"{handler.__module__}.{handler.__name__}"
        event_handler = EventHandler(handler, handler_name)
        
        domain_pattern = f"{domain}.*"
        if domain_pattern not in self._handlers:
            self._handlers[domain_pattern] = []
        
        self._handlers[domain_pattern].append(event_handler)
        
        logger.debug(
            "Domain handler subscribed",
            domain=domain,
            handler_name=handler_name
        )
    
    def subscribe_global(
        self, 
        handler: Callable[[BaseEvent], Any],
        handler_name: Optional[str] = None
    ):
        """Subscribe to all events (global handler)"""
        handler_name = handler_name or f"{handler.__module__}.{handler.__name__}"
        event_handler = EventHandler(handler, handler_name)
        
        self._global_handlers.append(event_handler)
        
        logger.debug("Global handler subscribed", handler_name=handler_name)
    
    def add_middleware(self, middleware: Callable[[BaseEvent], BaseEvent]):
        """Add middleware to process events before handling"""
        self._middleware.append(middleware)
        logger.debug("Event middleware added", middleware=f"{middleware.__module__}.{middleware.__name__}")
    
    async def publish(self, event: BaseEvent, correlation_id: Optional[UUID] = None):
        """Publish event to all subscribers"""
        # Set correlation ID if provided
        if correlation_id:
            event.correlation_id = correlation_id
        
        # Apply middleware
        for middleware in self._middleware:
            try:
                event = middleware(event)
            except Exception as e:
                logger.error(
                    "Event middleware failed",
                    middleware=f"{middleware.__module__}.{middleware.__name__}",
                    event_id=str(event.event_id),
                    error=str(e)
                )
        
        # Store in history for debugging
        self._add_to_history(event)
        
        logger.info(
            "Publishing event",
            event_type=event.event_name,
            event_id=str(event.event_id),
            aggregate_id=str(event.aggregate_id),
            correlation_id=str(event.correlation_id) if event.correlation_id else None
        )
        
        # Collect all matching handlers
        handlers_to_execute = []
        
        # Exact event type match
        event_name = event.event_name
        if event_name in self._handlers:
            handlers_to_execute.extend(self._handlers[event_name])
        
        # Domain pattern match (domain.*)
        domain_pattern = f"{event.domain}.*"
        if domain_pattern in self._handlers:
            handlers_to_execute.extend(self._handlers[domain_pattern])
        
        # Global handlers
        handlers_to_execute.extend(self._global_handlers)
        
        # Execute all handlers concurrently
        if handlers_to_execute:
            handler_tasks = []
            for handler in handlers_to_execute:
                task = asyncio.create_task(
                    self._execute_handler_safely(handler, event)
                )
                handler_tasks.append(task)
            
            # Wait for all handlers to complete
            results = await asyncio.gather(*handler_tasks, return_exceptions=True)
            
            # Log any handler failures
            failed_handlers = [
                (handler, result) for handler, result in zip(handlers_to_execute, results)
                if isinstance(result, Exception)
            ]
            
            if failed_handlers:
                logger.error(
                    "Some event handlers failed",
                    event_id=str(event.event_id),
                    failed_count=len(failed_handlers),
                    total_handlers=len(handlers_to_execute)
                )
        
        # Persist event if enabled
        if self.enable_persistence:
            await self._persist_event(event)
    
    async def _execute_handler_safely(self, handler: EventHandler, event: BaseEvent):
        """Execute handler with timeout and error handling"""
        try:
            # Add timeout to prevent hanging handlers
            await asyncio.wait_for(handler.handle(event), timeout=30.0)
        except asyncio.TimeoutError:
            logger.error(
                "Event handler timed out",
                handler_name=handler.handler_name,
                event_id=str(event.event_id),
                timeout_seconds=30
            )
        except Exception as e:
            logger.error(
                "Event handler execution failed",
                handler_name=handler.handler_name,
                event_id=str(event.event_id),
                error=str(e),
                exc_info=True
            )
            # Don't re-raise - we want other handlers to continue
    
    def _add_to_history(self, event: BaseEvent):
        """Add event to history with size limit"""
        self._event_history.append(event)
        
        # Trim history if too large
        if len(self._event_history) > self._max_history_size:
            self._event_history = self._event_history[-self._max_history_size:]
    
    async def _persist_event(self, event: BaseEvent):
        """Persist event to database (if enabled)"""
        try:
            from shared.database.connection import get_db_session
            from shared.database.models import EventStore
            
            async with get_db_session() as session:
                event_record = EventStore(
                    event_id=event.event_id,
                    event_type=event.event_name,
                    aggregate_id=event.aggregate_id,
                    event_data=event.model_dump(),
                    correlation_id=event.correlation_id,
                    timestamp=event.timestamp
                )
                session.add(event_record)
                await session.commit()
                
        except Exception as e:
            logger.error(
                "Failed to persist event",
                event_id=str(event.event_id),
                error=str(e)
            )
    
    def get_event_history(self, limit: int = 100) -> List[BaseEvent]:
        """Get recent event history for debugging"""
        return self._event_history[-limit:]
    
    def get_handler_count(self) -> Dict[str, int]:
        """Get count of handlers by event type"""
        counts = {}
        for event_type, handlers in self._handlers.items():
            counts[event_type] = len(handlers)
        counts["global"] = len(self._global_handlers)
        return counts


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus(enable_persistence=True)
    return _event_bus


# Convenience functions
async def publish_event(event: BaseEvent, correlation_id: Optional[UUID] = None):
    """Publish event using global event bus"""
    bus = get_event_bus()
    await bus.publish(event, correlation_id)


def subscribe_to_event(
    event_type: Union[str, Type[BaseEvent]], 
    handler: Callable[[BaseEvent], Any],
    handler_name: Optional[str] = None
):
    """Subscribe to event using global event bus"""
    bus = get_event_bus()
    bus.subscribe(event_type, handler, handler_name)


def subscribe_to_domain_events(
    domain: str, 
    handler: Callable[[BaseEvent], Any],
    handler_name: Optional[str] = None
):
    """Subscribe to domain events using global event bus"""
    bus = get_event_bus()
    bus.subscribe_to_domain(domain, handler, handler_name)