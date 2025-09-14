"""
Common Utility Functions and Helpers
DRY principle implementation with reusable components
"""

import asyncio
import hashlib
import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from functools import wraps
from typing import Any, Dict, List, Optional, TypeVar, Union
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)

# PERFORMANCE OPTIMIZATION: Pre-compiled regex patterns
_DIGITS_ONLY_PATTERN = re.compile(r"[^\d]")
_CAMEL_TO_SNAKE_1_PATTERN = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_TO_SNAKE_2_PATTERN = re.compile(r"([a-z0-9])([A-Z])")
_SLUG_CLEAN_PATTERN = re.compile(r"[^\w\s-]")
_SLUG_HYPHEN_PATTERN = re.compile(r"[-\s]+")

T = TypeVar("T")


class ValidationHelper:
    """Common validation utilities"""

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email address format"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Validate phone number format"""
        # Remove all non-digits using compiled regex
        digits_only = _DIGITS_ONLY_PATTERN.sub("", phone)
        # Should be 10-15 digits
        return 10 <= len(digits_only) <= 15

    @staticmethod
    def is_valid_uuid(uuid_string: str) -> bool:
        """Validate UUID format"""
        try:
            UUID(uuid_string)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_valid_sku(sku: str) -> bool:
        """Validate SKU format (alphanumeric with hyphens/underscores)"""
        pattern = r"^[A-Za-z0-9_-]+$"
        return bool(re.match(pattern, sku)) and 3 <= len(sku) <= 100

    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            value = str(value)

        # Remove control characters
        value = "".join(char for char in value if ord(char) >= 32 or char in "\n\r\t")

        # Trim whitespace
        value = value.strip()

        # Limit length
        if len(value) > max_length:
            value = value[:max_length]

        return value

    @staticmethod
    def validate_price(price: Union[str, int, float, Decimal]) -> Decimal:
        """Validate and normalize price"""
        try:
            decimal_price = Decimal(str(price))
            if decimal_price < 0:
                raise ValueError("Price cannot be negative")
            if decimal_price > Decimal("999999.99"):
                raise ValueError("Price too large")
            return decimal_price.quantize(Decimal("0.01"))
        except (ValueError, TypeError, ArithmeticError) as e:
            raise ValueError(f"Invalid price format: {e}")


class DateTimeHelper:
    """Common datetime utilities"""

    @staticmethod
    def utc_now() -> datetime:
        """Get current UTC datetime"""
        return datetime.now(timezone.utc)

    @staticmethod
    def to_iso_string(dt: datetime) -> str:
        """Convert datetime to ISO string"""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    @staticmethod
    def from_iso_string(iso_string: str) -> datetime:
        """Parse ISO string to datetime"""
        try:
            return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid ISO datetime format: {e}")

    @staticmethod
    def days_ago(days: int) -> datetime:
        """Get datetime N days ago"""
        from datetime import timedelta

        return DateTimeHelper.utc_now() - timedelta(days=days)

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 1:
            return f"{seconds*1000:.1f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"


class StringHelper:
    """Common string utilities"""

    @staticmethod
    def to_snake_case(camel_str: str) -> str:
        """Convert CamelCase to snake_case using compiled regex"""
        s1 = _CAMEL_TO_SNAKE_1_PATTERN.sub(r"\1_\2", camel_str)
        return _CAMEL_TO_SNAKE_2_PATTERN.sub(r"\1_\2", s1).lower()

    @staticmethod
    def to_camel_case(snake_str: str) -> str:
        """Convert snake_case to camelCase"""
        components = snake_str.split("_")
        return components[0] + "".join(x.capitalize() for x in components[1:])

    @staticmethod
    def slugify(text: str) -> str:
        """Convert text to URL-friendly slug using compiled regex"""
        # Convert to lowercase and replace spaces/special chars with hyphens
        text = _SLUG_CLEAN_PATTERN.sub("", text.lower())
        text = _SLUG_HYPHEN_PATTERN.sub("-", text)
        return text.strip("-")

    @staticmethod
    def truncate(text: str, length: int, suffix: str = "...") -> str:
        """Truncate text to specified length"""
        if len(text) <= length:
            return text
        return text[: length - len(suffix)] + suffix

    @staticmethod
    def mask_sensitive(text: str, visible_chars: int = 4) -> str:
        """Mask sensitive data showing only first/last chars"""
        if not text or len(text) <= visible_chars * 2:
            return "*" * len(text) if text else ""

        visible_start = text[:visible_chars]
        visible_end = text[-visible_chars:]
        masked_middle = "*" * (len(text) - visible_chars * 2)
        return f"{visible_start}{masked_middle}{visible_end}"


class SecurityHelper:
    """Security-related utilities"""

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)

        # Use PBKDF2 for password hashing
        import hashlib

        key = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        )  # 100k iterations

        return key.hex(), salt

    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """Verify password against hash"""
        expected_hash, _ = SecurityHelper.hash_password(password, salt)
        return secrets.compare_digest(hashed, expected_hash)

    @staticmethod
    def generate_api_key() -> str:
        """Generate API key"""
        return f"sf_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()


class DataHelper:
    """Data manipulation utilities"""

    @staticmethod
    def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DataHelper.deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
        """Flatten nested dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(DataHelper.flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def chunk_list(lst: List[T], chunk_size: int) -> List[List[T]]:
        """Split list into chunks"""
        return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]

    @staticmethod
    def remove_none_values(d: Dict[str, Any]) -> Dict[str, Any]:
        """Remove keys with None values from dictionary"""
        return {k: v for k, v in d.items() if v is not None}

    @staticmethod
    def safe_get(d: Dict[str, Any], path: str, default: Any = None) -> Any:
        """Safely get nested dictionary value using dot notation"""
        keys = path.split(".")
        value = d
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError, IndexError):
            return default


class PerformanceHelper:
    """Performance monitoring utilities"""

    @staticmethod
    def measure_execution_time(func):
        """Decorator to measure function execution time"""

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            import time

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.debug(
                    "Function execution time",
                    function=func.__name__,
                    execution_time_ms=round(execution_time * 1000, 2),
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    "Function execution failed",
                    function=func.__name__,
                    execution_time_ms=round(execution_time * 1000, 2),
                    error=str(e),
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.debug(
                    "Function execution time",
                    function=func.__name__,
                    execution_time_ms=round(execution_time * 1000, 2),
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    "Function execution failed",
                    function=func.__name__,
                    execution_time_ms=round(execution_time * 1000, 2),
                    error=str(e),
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    @staticmethod
    def memory_usage():
        """Get current memory usage"""
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            }
        except ImportError:
            return {"error": "psutil not available"}


class RetryHelper:
    """Retry mechanism utilities"""

    @staticmethod
    def retry_on_exception(
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,),
    ):
        """Decorator for retrying functions on specific exceptions"""

        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_attempts - 1:
                            logger.error(
                                "Function failed after all retries",
                                function=func.__name__,
                                attempts=max_attempts,
                                error=str(e),
                            )
                            raise

                        wait_time = delay * (backoff_factor**attempt)
                        logger.warning(
                            "Function failed, retrying",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            wait_time=wait_time,
                            error=str(e),
                        )
                        await asyncio.sleep(wait_time)

                raise last_exception

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                import time

                last_exception = None
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_attempts - 1:
                            logger.error(
                                "Function failed after all retries",
                                function=func.__name__,
                                attempts=max_attempts,
                                error=str(e),
                            )
                            raise

                        wait_time = delay * (backoff_factor**attempt)
                        logger.warning(
                            "Function failed, retrying",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            wait_time=wait_time,
                            error=str(e),
                        )
                        time.sleep(wait_time)

                raise last_exception

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator


class CacheHelper:
    """Simple in-memory cache implementation"""

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self._cache:
            return None

        import time

        entry = self._cache[key]
        if time.time() - entry["timestamp"] > self.ttl:
            self._remove(key)
            return None

        self._access_times[key] = time.time()
        return entry["value"]

    def set(self, key: str, value: Any):
        """Set value in cache"""
        import time

        # Remove oldest entries if cache is full
        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        timestamp = time.time()
        self._cache[key] = {"value": value, "timestamp": timestamp}
        self._access_times[key] = timestamp

    def _remove(self, key: str):
        """Remove key from cache"""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)

    def _evict_oldest(self):
        """Evict least recently used items"""
        if not self._access_times:
            return

        # Remove oldest 10% of entries
        num_to_remove = max(1, len(self._cache) // 10)
        oldest_keys = sorted(self._access_times.keys(), key=lambda k: self._access_times[k])

        for key in oldest_keys[:num_to_remove]:
            self._remove(key)

    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
        self._access_times.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {"size": len(self._cache), "max_size": self.max_size, "ttl": self.ttl}


# Global cache instance
_global_cache = CacheHelper()


def cached(ttl: int = 300):
    """Decorator for caching function results"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"

            # Try to get from cache
            result = _global_cache.get(key)
            if result is not None:
                return result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            _global_cache.set(key, result)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"

            # Try to get from cache
            result = _global_cache.get(key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            _global_cache.set(key, result)
            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
