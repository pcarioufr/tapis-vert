"""
Custom exceptions for Redis ORM.
"""

from .utils import get_logger

log = get_logger(__name__)

class RedisORMError(Exception):
    """Base exception for Redis ORM errors."""
    pass

class ConflictError(RedisORMError):
    """Exception raised when a concurrent modification is detected during save."""
    def __init__(self, message):
        super().__init__(message)
        log.error(f"🚨 CONFLICT ERROR: {message}")

class ValidationError(RedisORMError):
    """Exception raised when validation fails."""
    pass

class RelationError(RedisORMError):
    """Exception raised when relationship operations fail."""
    pass 