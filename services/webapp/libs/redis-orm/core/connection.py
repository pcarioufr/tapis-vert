"""
Redis connection management for Redis ORM.
Supports both real Redis and fakeredis for testing.
"""

import os
from typing import Optional
import redis
from .utils import get_logger

log = get_logger(__name__)

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get the current Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = create_redis_client()
    return _redis_client


def set_redis_client(client: redis.Redis) -> None:
    """Set a custom Redis client (useful for testing with fakeredis)."""
    global _redis_client
    _redis_client = client
    log.info("Custom Redis client configured")


def create_redis_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    db: Optional[int] = None,
    decode_responses: bool = True,
    **kwargs
) -> redis.Redis:
    """
    Create a new Redis client with configuration from environment or parameters.
    
    Args:
        host: Redis host (defaults to REDIS_HOST env var or 'localhost')
        port: Redis port (defaults to REDIS_PORT env var or 6379)
        db: Redis database number (defaults to REDIS_DATA_DB env var or 0)
        decode_responses: Whether to decode Redis responses as strings
        **kwargs: Additional Redis client parameters
    
    Returns:
        Configured Redis client instance
    """
    host = host or os.environ.get("REDIS_HOST", "localhost")
    port = port or int(os.environ.get("REDIS_PORT", "6379"))
    db = db or int(os.environ.get("REDIS_DATA_DB", "0"))
    
    client = redis.Redis(
        host=host,
        port=port,
        db=db,
        decode_responses=decode_responses,
        **kwargs
    )
    
    log.info(f"Redis client created: {host}:{port}/{db}")
    return client


def reset_connection() -> None:
    """Reset the global Redis connection (useful for testing)."""
    global _redis_client
    _redis_client = None
    log.info("Redis connection reset") 