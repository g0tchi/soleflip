"""
Structured Logging Configuration
Replaces primitive logging with production-ready structured logging
"""
import structlog
import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import os
import json

class JSONRenderer:
    """Custom JSON renderer for structured logs"""
    
    def __call__(self, logger, method_name, event_dict):
        """Render log entry as JSON"""
        # Add standard fields
        event_dict['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        event_dict['level'] = method_name.upper()
        
        # Add request context if available
        if hasattr(structlog.contextvars, 'get_context'):
            context = structlog.contextvars.get_context()
            if context:
                event_dict.update(context)
        
        return json.dumps(event_dict, default=str)

class DatabaseLogHandler(logging.Handler):
    """Log handler that writes to database"""
    
    def __init__(self):
        super().__init__()
        self.db_session = None
    
    def emit(self, record):
        """Emit log record to database"""
        try:
            # Only log WARNING and above to database to avoid spam
            if record.levelno < logging.WARNING:
                return
            
            # Parse structured log data
            if hasattr(record, 'msg') and isinstance(record.msg, dict):
                log_data = record.msg
            else:
                log_data = {'message': str(record.msg)}
            
            # Extract standard fields
            level = record.levelname
            component = log_data.get('component', 'UNKNOWN')
            message = log_data.get('message', str(record.msg))
            details = {k: v for k, v in log_data.items() 
                      if k not in ['message', 'component']}
            
            # Write to database asynchronously
            self._write_to_database(level, component, message, details)
            
        except Exception:
            # Never let logging errors crash the application
            pass
    
    def _write_to_database(self, level: str, component: str, message: str, details: Dict[str, Any]):
        """Write log entry to database (async)"""
        import asyncio
        
        async def write_log():
            try:
                from shared.database.connection import get_db_session
                from shared.database.models import SystemLog
                
                async with get_db_session() as db:
                    log_entry = SystemLog(
                        level=level,
                        component=component,
                        message=message,
                        details=details or None
                    )
                    db.add(log_entry)
                    await db.commit()
            except Exception:
                # Silent fail to prevent logging loops
                pass
        
        # Run in background
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(write_log())
            else:
                asyncio.run(write_log())
        except Exception:
            pass

def setup_logging(
    log_level: str = "INFO",
    enable_database_logging: bool = True,
    enable_json_output: bool = None
) -> structlog.BoundLogger:
    """Setup structured logging configuration"""
    
    # Determine if we should use JSON output
    if enable_json_output is None:
        enable_json_output = os.getenv("LOG_FORMAT", "").lower() == "json"
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Setup structlog processors
    processors = [
        # Add log level
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Process stack info
        structlog.processors.StackInfoRenderer(),
        # Process exceptions
        structlog.processors.format_exc_info,
        # Handle unicode
        structlog.processors.UnicodeDecoder(),
        # Add context variables
        structlog.contextvars.merge_contextvars,
    ]
    
    # Add appropriate renderer
    if enable_json_output:
        processors.append(JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback
            )
        )
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Setup database logging if enabled
    if enable_database_logging:
        root_logger = logging.getLogger()
        db_handler = DatabaseLogHandler()
        root_logger.addHandler(db_handler)
    
    # Return configured logger
    return structlog.get_logger("soleflip")

class LoggingMixin:
    """Mixin to add structured logging to classes"""
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.logger = structlog.get_logger(f"{cls.__module__}.{cls.__name__}")
    
    def log_info(self, message: str, **kwargs):
        """Log info message with context"""
        self.logger.info(message, **kwargs)
    
    def log_warning(self, message: str, **kwargs):
        """Log warning message with context"""
        self.logger.warning(message, **kwargs)
    
    def log_error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message with context"""
        if error:
            kwargs['error'] = str(error)
            kwargs['error_type'] = type(error).__name__
        self.logger.error(message, **kwargs)
    
    def log_debug(self, message: str, **kwargs):
        """Log debug message with context"""
        self.logger.debug(message, **kwargs)

class RequestLoggingMiddleware:
    """Middleware for request/response logging"""
    
    def __init__(self, app):
        self.app = app
        self.logger = structlog.get_logger("middleware.request")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        import time
        from uuid import uuid4
        
        # Generate request ID
        request_id = str(uuid4())
        
        # Add request context
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=scope["method"],
            path=scope["path"],
            query_string=scope.get("query_string", b"").decode(),
        )
        
        start_time = time.time()
        
        # Log request start
        self.logger.info(
            "Request started",
            request_id=request_id,
            method=scope["method"],
            path=scope["path"],
            user_agent=dict(scope.get("headers", {})).get(b"user-agent", b"").decode()
        )
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Calculate response time
                response_time = time.time() - start_time
                
                # Log response
                self.logger.info(
                    "Request completed",
                    request_id=request_id,
                    status_code=message["status"],
                    response_time_ms=round(response_time * 1000, 2)
                )
            
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            # Log request error
            response_time = time.time() - start_time
            self.logger.error(
                "Request failed",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__,
                response_time_ms=round(response_time * 1000, 2)
            )
            raise
        finally:
            # Clear request context
            structlog.contextvars.clear_contextvars()

# Context managers for logging
class LogContext:
    """Context manager for adding log context"""
    
    def __init__(self, **kwargs):
        self.context = kwargs
    
    def __enter__(self):
        structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for key in self.context.keys():
            structlog.contextvars.unbind_contextvars(key)

def log_function_call(func):
    """Decorator to log function entry/exit"""
    import functools
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = structlog.get_logger(f"{func.__module__}.{func.__name__}")
        
        logger.debug(
            "Function called",
            function=func.__name__,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys())
        )
        
        try:
            result = await func(*args, **kwargs)
            logger.debug("Function completed", function=func.__name__)
            return result
        except Exception as e:
            logger.error(
                "Function failed",
                function=func.__name__,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = structlog.get_logger(f"{func.__module__}.{func.__name__}")
        
        logger.debug(
            "Function called",
            function=func.__name__,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys())
        )
        
        try:
            result = func(*args, **kwargs)
            logger.debug("Function completed", function=func.__name__)
            return result
        except Exception as e:
            logger.error(
                "Function failed",
                function=func.__name__,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

# Export main logger
logger = setup_logging()