"""
Redis caching utilities for Infrastructure Service
"""

import redis
import json
import logging
from typing import Optional, Any, Callable
from functools import wraps
import hashlib

from config import settings

logger = logging.getLogger(__name__)

# Redis client
try:
    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    redis_client.ping()
    logger.info(f"✅ Redis connected: {settings.REDIS_URL}")
except Exception as e:
    logger.warning(f"⚠️ Redis connection failed: {e}. Caching will be disabled.")
    redis_client = None


class Cache:
    """Redis cache wrapper with JSON serialization"""
    
    def __init__(self, client: Optional[redis.Redis] = None):
        self.client = client or redis_client
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.client:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = settings.CACHE_TTL):
        """Set value in cache with TTL"""
        if not self.client:
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str):
        """Delete key from cache"""
        if not self.client:
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def invalidate(self, pattern: str):
        """Invalidate all keys matching pattern"""
        if not self.client:
            return
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache keys matching {pattern}")
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
    
    def flush_all(self):
        """Flush all cache entries (use with caution!)"""
        if not self.client:
            return
        
        try:
            self.client.flushdb()
            logger.info("Cache flushed")
        except Exception as e:
            logger.error(f"Cache flush error: {e}")


# Global cache instance
cache = Cache(redis_client)


def cache_key(*args, **kwargs) -> str:
    """
    Generate cache key from function arguments
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
    
    Returns:
        Cache key string
    """
    # Create a string representation of arguments
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    key_string = ":".join(key_parts)
    
    # Hash for consistent length
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl: int = settings.CACHE_TTL, key_prefix: str = ""):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    
    Usage:
        @cached(ttl=300, key_prefix="stacks")
        async def get_stacks():
            return expensive_operation()
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            func_name = func.__name__
            arg_key = cache_key(*args, **kwargs)
            full_key = f"{key_prefix}:{func_name}:{arg_key}" if key_prefix else f"{func_name}:{arg_key}"
            
            # Try to get from cache
            cached_value = cache.get(full_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {full_key}")
                return cached_value
            
            # Execute function
            logger.debug(f"Cache miss: {full_key}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            cache.set(full_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# TTL constants for different data types
CACHE_TTL = {
    "stacks": 60,  # 1 minute
    "resources": 120,  # 2 minutes
    "drift": 300,  # 5 minutes
    "cost_estimates": 600,  # 10 minutes
    "deployments": 60,  # 1 minute
    "stats": 300,  # 5 minutes
}
