"""
Custom exceptions for Redis ORM.
"""


class RedisORMError(Exception):
    """Base exception for all Redis ORM errors."""
    pass


class ConflictError(RedisORMError):
    """Exception raised when a concurrent modification is detected during save."""
    pass


class ValidationError(RedisORMError):
    """Exception raised when model validation fails."""
    pass


class RelationError(RedisORMError):
    """Exception raised when relationship operations fail."""
    pass 