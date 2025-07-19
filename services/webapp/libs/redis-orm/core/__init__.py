"""
Redis ORM - A lightweight Redis-based ORM with relationship support.

This package provides ObjectMixin and RelationMixin classes for building
Redis-backed models with automatic key management, optimistic locking,
and relationship handling.

Example usage:

    from core import ObjectMixin, RelationMixin, set_redis_client
    import fakeredis
    
    # For testing
    set_redis_client(fakeredis.FakeRedis(decode_responses=True))
    
    class User(ObjectMixin):
        FIELDS = {"name", "email"}
        RIGHTS = {"posts": "myapp.UserPosts"}
    
    class Post(ObjectMixin):
        FIELDS = {"title", "content"}
        LEFTS = {"author": "myapp.UserPosts"}
    
    class UserPosts(RelationMixin):
        FIELDS = {"role"}
        L_CLASS = User
        R_CLASS = Post
        NAME = "user:posts"
    
    # Create and use models
    user = User.create(name="Alice", email="alice@example.com")
    post = Post.create(title="Hello World", content="...")
    user.posts().add(post.id, role="author")
"""

from .mixins import (
    ObjectMixin,
    RelationMixin,
    RedisMixin,
    RelationManager,
    RightwardsRelationManager,
    LeftwardsRelationManager,
)

from .exceptions import (
    RedisORMError,
    ConflictError,
    ValidationError,
    RelationError,
)

from .connection import (
    get_redis_client,
    set_redis_client,
    create_redis_client,
    reset_connection,
)

from .utils import (
    new_id,
    now,
    flatten,
    unflatten,
)

__version__ = "0.1.0"
__author__ = "Pierre Cariou"

__all__ = [
    # Core mixins
    "ObjectMixin",
    "RelationMixin", 
    "RedisMixin",
    
    # Relation managers
    "RelationManager",
    "RightwardsRelationManager",
    "LeftwardsRelationManager",
    
    # Exceptions
    "RedisORMError",
    "ConflictError",
    "ValidationError",
    "RelationError",
    
    # Connection management
    "get_redis_client",
    "set_redis_client", 
    "create_redis_client",
    "reset_connection",
    
    # Utilities
    "new_id",
    "now",
    "flatten",
    "unflatten",
] 