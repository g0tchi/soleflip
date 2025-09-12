"""
JWT Token Blacklist Implementation
Provides server-side token revocation capabilities for enhanced security.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional, Set
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class TokenBlacklist:
    """
    In-memory token blacklist with automatic cleanup.
    In production, this should be backed by Redis or database.
    """
    
    def __init__(self, cleanup_interval: int = 3600):  # 1 hour
        self._blacklisted_tokens: Set[str] = set()
        self._token_expiry: dict[str, float] = {}
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start_cleanup_task(self):
        """Start the background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_tokens())
            logger.info("Token blacklist cleanup task started")
    
    async def stop_cleanup_task(self):
        """Stop the background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Token blacklist cleanup task stopped")
    
    async def blacklist_token(self, token: str, exp_timestamp: float):
        """Add token to blacklist"""
        self._blacklisted_tokens.add(token)
        self._token_expiry[token] = exp_timestamp
        
        logger.info(
            "Token blacklisted",
            token_prefix=token[:20] + "...",
            expires_at=datetime.fromtimestamp(exp_timestamp, timezone.utc).isoformat()
        )
    
    async def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        return token in self._blacklisted_tokens
    
    async def _cleanup_expired_tokens(self):
        """Background task to clean up expired tokens"""
        while True:
            try:
                current_time = time.time()
                expired_tokens = []
                
                for token, exp_time in self._token_expiry.items():
                    if current_time > exp_time:
                        expired_tokens.append(token)
                
                # Remove expired tokens
                for token in expired_tokens:
                    self._blacklisted_tokens.discard(token)
                    self._token_expiry.pop(token, None)
                
                if expired_tokens:
                    logger.debug(f"Cleaned up {len(expired_tokens)} expired blacklisted tokens")
                
                # Sleep until next cleanup
                await asyncio.sleep(self._cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in token cleanup task: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying


class RedisTokenBlacklist:
    """
    Redis-backed token blacklist for distributed systems.
    Better for production environments with multiple instances.
    """
    
    def __init__(self, redis_client=None, key_prefix: str = "blacklist:token:"):
        self.redis_client = redis_client
        self.key_prefix = key_prefix
        self.connected = False
    
    async def connect(self):
        """Connect to Redis"""
        if self.redis_client:
            try:
                await self.redis_client.ping()
                self.connected = True
                logger.info("Redis token blacklist connected")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis for token blacklist: {e}")
    
    async def blacklist_token(self, token: str, exp_timestamp: float):
        """Add token to Redis blacklist"""
        if not self.connected:
            return
        
        try:
            key = f"{self.key_prefix}{token}"
            # Set token with expiration time
            ttl = int(exp_timestamp - time.time())
            if ttl > 0:
                await self.redis_client.setex(key, ttl, "blacklisted")
                logger.info("Token blacklisted in Redis", token_prefix=token[:20] + "...")
        
        except Exception as e:
            logger.error(f"Failed to blacklist token in Redis: {e}")
    
    async def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted in Redis"""
        if not self.connected:
            return False
        
        try:
            key = f"{self.key_prefix}{token}"
            result = await self.redis_client.exists(key)
            return result > 0
        
        except Exception as e:
            logger.error(f"Failed to check token blacklist in Redis: {e}")
            return False


class HybridTokenBlacklist:
    """
    Hybrid blacklist using both in-memory and Redis for best performance.
    Falls back to in-memory if Redis is unavailable.
    """
    
    def __init__(self, redis_client=None):
        self.memory_blacklist = TokenBlacklist()
        self.redis_blacklist = RedisTokenBlacklist(redis_client)
        self.use_redis = False
    
    async def initialize(self):
        """Initialize the hybrid blacklist"""
        await self.memory_blacklist.start_cleanup_task()
        await self.redis_blacklist.connect()
        self.use_redis = self.redis_blacklist.connected
        
        if self.use_redis:
            logger.info("Using hybrid token blacklist (Redis + Memory)")
        else:
            logger.info("Using in-memory token blacklist (Redis unavailable)")
    
    async def shutdown(self):
        """Shutdown the hybrid blacklist"""
        await self.memory_blacklist.stop_cleanup_task()
    
    async def blacklist_token(self, token: str, exp_timestamp: float):
        """Add token to both blacklists"""
        # Always add to memory blacklist
        await self.memory_blacklist.blacklist_token(token, exp_timestamp)
        
        # Add to Redis if available
        if self.use_redis:
            await self.redis_blacklist.blacklist_token(token, exp_timestamp)
    
    async def is_blacklisted(self, token: str) -> bool:
        """Check both blacklists"""
        # Check memory first (fastest)
        if await self.memory_blacklist.is_blacklisted(token):
            return True
        
        # Check Redis if available
        if self.use_redis:
            return await self.redis_blacklist.is_blacklisted(token)
        
        return False


# Global blacklist instance
_token_blacklist: Optional[HybridTokenBlacklist] = None


async def initialize_token_blacklist(redis_client=None):
    """Initialize the global token blacklist"""
    global _token_blacklist
    _token_blacklist = HybridTokenBlacklist(redis_client)
    await _token_blacklist.initialize()


async def shutdown_token_blacklist():
    """Shutdown the global token blacklist"""
    global _token_blacklist
    if _token_blacklist:
        await _token_blacklist.shutdown()


def get_token_blacklist() -> HybridTokenBlacklist:
    """Get the global token blacklist instance"""
    global _token_blacklist
    if _token_blacklist is None:
        raise RuntimeError("Token blacklist not initialized. Call initialize_token_blacklist() first.")
    return _token_blacklist


async def blacklist_token(token: str, exp_timestamp: float):
    """Convenience function to blacklist a token"""
    blacklist = get_token_blacklist()
    await blacklist.blacklist_token(token, exp_timestamp)


async def is_token_blacklisted(token: str) -> bool:
    """Convenience function to check if token is blacklisted"""
    try:
        blacklist = get_token_blacklist()
        return await blacklist.is_blacklisted(token)
    except RuntimeError:
        # Blacklist not initialized - assume token is not blacklisted
        return False