"""
Tests for core Redis ORM functionality.
"""

import pytest
import sys
import os
sys.path.insert(0, '/app')
# Simple Redis fixture instead of complex conf
import redis
from core import ObjectMixin, RelationMixin, ConflictError, ValidationError, set_redis_client, create_redis_client

# Simple Redis client fixture
@pytest.fixture(scope="function")
def redis_client():
    client = create_redis_client(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=int(os.environ.get('REDIS_PORT', '6379')),
        db=int(os.environ.get('REDIS_DATA_DB', '1'))
    )
    set_redis_client(client)
    yield client
    client.flushdb()  # Clean up after each test


class User(ObjectMixin):
    """Test model for basic ObjectMixin functionality."""
    FIELDS = {"name", "email", "age"}
    RIGHTS = {"posts": "tests_py.core_test.UserPosts"}


class Post(ObjectMixin):
    """Test model for relationships."""
    FIELDS = {"title", "content"}
    LEFTS = {"author": "tests_py.core_test.UserPosts"}


class UserPosts(RelationMixin):
    """Test relationship model."""
    FIELDS = {"role", "created_at"}
    RELATION_TYPE = "one_to_many"
    L_CLASS = User
    R_CLASS = Post  
    NAME = "user:posts"


# Note: RIGHTS is now defined within the User class above


class TestObjectMixin:
    """Test ObjectMixin CRUD operations."""
    
    def test_create_object(self, clean_redis):
        """Test creating a new object."""
        user = User.create(name="Alice", email="alice@test.com", age=25)
        
        assert user.name == "Alice"
        assert user.email == "alice@test.com"  
        assert user.age == 25
        assert user.id is not None
        assert user._created is not None
        assert user._version == 0

    def test_create_with_invalid_fields(self, clean_redis):
        """Test that creating with invalid fields raises error."""
        with pytest.raises(AttributeError) as exc_info:
            User.create(name="Alice", invalid_field="value")
        
        assert "Invalid fields" in str(exc_info.value)

    def test_get_by_id(self, clean_redis):
        """Test retrieving object by ID."""
        user = User.create(name="Bob", email="bob@test.com")
        user_id = user.id
        
        retrieved = User.get_by_id(user_id)
        assert retrieved is not None
        assert retrieved.name == "Bob"
        assert retrieved.email == "bob@test.com"
        assert retrieved.id == user_id

    def test_get_nonexistent(self, clean_redis):
        """Test retrieving nonexistent object returns None."""
        result = User.get_by_id("nonexistent")
        assert result is None

    def test_exists(self, clean_redis):
        """Test checking if object exists."""
        user = User.create(name="Charlie")
        
        assert User.exists(user.id) is True
        assert User.exists("nonexistent") is False

    def test_update_and_save(self, clean_redis):
        """Test updating object fields."""
        user = User.create(name="Dave", age="30")  # Use string like current ORM
        original_version = user._version
        
        user.name = "David"
        user.age = "31"  # Use string like current ORM
        updated_user = user.save()
        
        assert updated_user.name == "David"
        assert updated_user.age == "31"  # Expect string like current ORM
        assert updated_user._version == original_version + 1
        
        # Verify persistence
        retrieved = User.get_by_id(user.id)
        assert retrieved.name == "David"
        assert retrieved.age == "31"  # Expect string like current ORM

    def test_optimistic_locking(self, clean_redis):
        """Test that concurrent modifications are detected."""
        user = User.create(name="Eve")
        
        # Simulate concurrent modification by changing version
        user1 = User.get_by_id(user.id)
        user2 = User.get_by_id(user.id)
        
        user1.name = "Eve1"
        user1.save()  # This should succeed
        
        user2.name = "Eve2"
        with pytest.raises(ConflictError) as exc_info:
            user2.save()  # This should fail due to version mismatch
        
        assert "Version mismatch" in str(exc_info.value)

    def test_delete(self, clean_redis):
        """Test deleting an object."""
        user = User.create(name="Frank")
        user_id = user.id
        
        assert User.exists(user_id) is True
        
        user.delete()
        
        # Object should be marked as deleted
        assert User.exists(user_id) is False
        assert User.get_by_id(user_id) is None

    def test_patch(self, clean_redis):
        """Test patching a single field."""
        user = User.create(name="Grace", age="25")  # Use string like current ORM
        
        result = User.patch(user.id, "age", "26")  # Use string like current ORM
        assert result is True
        
        updated = User.get_by_id(user.id)
        assert updated.age == "26"  # Expect string like current ORM
        assert updated.name == "Grace"  # Other fields unchanged

    def test_patch_nonexistent(self, clean_redis):
        """Test patching nonexistent object."""
        result = User.patch("nonexistent", "name", "Test")
        assert result is False

    def test_patch_corruption_prevention(self, clean_redis):
        """Test that patch prevents corruption when mixing simple and nested fields."""
        from core.exceptions import ConflictError
        
        user = User.create(name="Alice", email="alice@test.com")
        
        # This should raise ConflictError - can't patch nested field when base field has content
        with pytest.raises(ConflictError) as exc_info:
            User.patch(user.id, "email:subdomain", "gmail")
        
        assert "Cannot patch nested field" in str(exc_info.value)
        assert "base field 'email' contains data" in str(exc_info.value)

    def test_patch_nested_structure(self, clean_redis):
        """Test that patch can create pure nested structures correctly."""
        user = User.create(name="Bob")  # No email field set
        
        # Should work - creating nested structure from scratch
        result1 = User.patch(user.id, "email:domain", "example.com", add=True)
        result2 = User.patch(user.id, "email:username", "bob", add=True)
        
        assert result1 is True
        assert result2 is True
        
        # Verify the structure is reconstructed correctly
        updated_user = User.get_by_id(user.id)
        assert updated_user.email["domain"] == "example.com"
        assert updated_user.email["username"] == "bob"

    def test_patch_empty_base_field_removal(self, clean_redis):
        """Test that patch removes empty base field markers when adding nested fields."""
        from core import get_redis_client
        
        # Create user and then manually set empty base field (like ORM internal operations might)
        user = User.create(name="Charlie")
        redis_client = get_redis_client()
        
        # Manually create empty base field marker like flatten() would
        redis_client.hset(user.key, "email", "")
        
        # Verify empty base field exists
        raw_data_before = redis_client.hgetall(user.key)
        assert raw_data_before.get("email") == "", "Should have empty base field marker"
        
        # Add nested field - should remove empty base field
        User.patch(user.id, "email:provider", "gmail", add=True)
        
        # Verify empty base field was removed and nested field exists
        raw_data_after = redis_client.hgetall(user.key)
        assert "email" not in raw_data_after or raw_data_after.get("email") != "", "Empty base field should be removed"
        assert "email:provider" in raw_data_after, "Nested field should exist"
        
        # Verify data reconstruction
        updated_user = User.get_by_id(user.id)
        assert updated_user.email["provider"] == "gmail"

    def test_search(self, clean_redis):
        """Test searching for objects."""
        user1 = User.create(name="Alice")
        user2 = User.create(name="Bob") 
        
        results, cursor = User.search()
        
        assert len(results) == 2
        assert cursor == 0  # No more results
        
        names = {user.name for user in results}
        assert names == {"Alice", "Bob"}

    def test_to_dict(self, clean_redis):
        """Test converting object to dictionary."""
        user = User.create(name="Helen", email="helen@test.com", age=28)
        
        user_dict = user.to_dict()
        
        assert user.id in user_dict
        user_data = user_dict[user.id]
        assert user_data["name"] == "Helen"
        assert user_data["email"] == "helen@test.com"
        assert user_data["age"] == 28
        assert "_created" in user_data
        assert "_version" in user_data


class TestRelationMixin:
    """Test RelationMixin functionality."""
    
    def test_create_relation(self, clean_redis):
        """Test creating a relationship."""
        user = User.create(name="Author")
        post = Post.create(title="Test Post", content="Content")
        
        relation = UserPosts.create(
            user.id, 
            post.id, 
            role="author", 
            created_at="2024-01-15"
        )
        
        assert relation.left_id == user.id
        assert relation.right_id == post.id
        assert relation.role == "author"
        assert relation.created_at == "2024-01-15"

    def test_create_relation_nonexistent_objects(self, clean_redis):
        """Test that creating relation with nonexistent objects fails."""
        user = User.create(name="User")
        
        with pytest.raises(ValueError) as exc_info:
            UserPosts.create(user.id, "nonexistent", role="author")
        
        assert "does not exist" in str(exc_info.value)

    def test_get_relation_by_ids(self, clean_redis):
        """Test retrieving relation by left and right IDs."""
        user = User.create(name="User")
        post = Post.create(title="Post")
        
        original = UserPosts.create(user.id, post.id, role="editor")
        
        retrieved = UserPosts.get_by_ids(user.id, post.id)
        assert retrieved is not None
        assert retrieved.role == "editor"
        assert retrieved.left_id == user.id
        assert retrieved.right_id == post.id

    def test_left_and_right_objects(self, clean_redis):
        """Test accessing left and right objects from relation."""
        user = User.create(name="Jane")
        post = Post.create(title="Jane's Post")
        
        relation = UserPosts.create(user.id, post.id, role="author")
        
        left_obj = relation.left()
        right_obj = relation.right()
        
        assert left_obj.id == user.id
        assert left_obj.name == "Jane"
        assert right_obj.id == post.id
        assert right_obj.title == "Jane's Post"

    def test_lefts_and_rights_queries(self, clean_redis):
        """Test querying relations by left/right side."""
        user1 = User.create(name="User1")
        user2 = User.create(name="User2")
        post1 = Post.create(title="Post1")
        post2 = Post.create(title="Post2")
        
        # User1 writes both posts
        UserPosts.create(user1.id, post1.id, role="author")
        UserPosts.create(user1.id, post2.id, role="author")
        
        # User2 edits post1
        UserPosts.create(user2.id, post1.id, role="editor")
        
        # Query user1's posts (rights from user1's perspective)
        user1_posts = UserPosts.rights(user1.id)
        assert len(user1_posts) == 2
        assert post1.id in user1_posts
        assert post2.id in user1_posts
        
        # Query post1's authors (lefts from post1's perspective)
        post1_authors = UserPosts.lefts(post1.id)
        assert len(post1_authors) == 2
        assert user1.id in post1_authors
        assert user2.id in post1_authors


class TestRelationManagers:
    """Test relation manager functionality."""
    
    def test_rightwards_manager_add(self, clean_redis):
        """Test adding relations via rightwards manager."""
        user = User.create(name="Author")
        post = Post.create(title="New Post")
        
        user.posts().add(post.id, role="author", created_at="2024-01-15")
        
        # Check relation was created
        relation = UserPosts.get_by_ids(user.id, post.id)
        assert relation is not None
        assert relation.role == "author"

    def test_rightwards_manager_all(self, clean_redis):
        """Test getting all relations via rightwards manager."""
        user = User.create(name="Prolific Author")
        post1 = Post.create(title="Post 1")
        post2 = Post.create(title="Post 2")
        
        user.posts().add(post1.id, role="author")
        user.posts().add(post2.id, role="author")
        
        posts = user.posts().all()
        assert len(posts) == 2
        assert post1.id in posts
        assert post2.id in posts

    def test_rightwards_manager_get_by_id(self, clean_redis):
        """Test getting specific relation via manager."""
        user = User.create(name="User")
        post = Post.create(title="Post")
        
        user.posts().add(post.id, role="contributor")
        
        obj, relation = user.posts().get_by_id(post.id)
        assert obj.id == post.id
        assert obj.title == "Post"
        assert relation.role == "contributor"

    def test_rightwards_manager_remove(self, clean_redis):
        """Test removing relations via manager."""
        user = User.create(name="User")
        post = Post.create(title="Post")
        
        user.posts().add(post.id, role="author")
        assert UserPosts.exists(user.id, post.id) is True
        
        user.posts().remove(post.id)
        assert UserPosts.exists(user.id, post.id) is False

    def test_rightwards_manager_exists(self, clean_redis):
        """Test checking relation existence via manager."""
        user = User.create(name="User")
        post = Post.create(title="Post")
        
        assert user.posts().exists(post.id) is False
        
        user.posts().add(post.id, role="author")
        assert user.posts().exists(post.id) is True

    def test_leftwards_manager(self, clean_redis):
        """Test leftwards manager functionality."""
        user = User.create(name="Author")
        post = Post.create(title="Post")
        
        # Add relation via rightwards manager
        user.posts().add(post.id, role="author")
        
        # Access via leftwards manager from post
        authors = post.author().all()
        assert len(authors) == 1
        assert user.id in authors
        
        # Get specific author
        author_obj, relation = post.author().get_by_id(user.id)
        assert author_obj.id == user.id
        assert author_obj.name == "Author"
        assert relation.role == "author"

    def test_manager_set_properties(self, clean_redis):
        """Test setting relation properties via manager."""
        user = User.create(name="User")
        post = Post.create(title="Post")
        
        user.posts().add(post.id, role="author")
        
        # Update relation properties
        user.posts().set(post.id, role="editor", created_at="2024-01-20")
        
        obj, relation = user.posts().get_by_id(post.id)
        assert relation.role == "editor"
        assert relation.created_at == "2024-01-20"

    def test_manager_first(self, clean_redis):
        """Test getting first relation via manager."""
        user = User.create(name="User")
        post1 = Post.create(title="First Post")
        post2 = Post.create(title="Second Post")
        
        user.posts().add(post1.id, role="author")
        user.posts().add(post2.id, role="author") 
        
        first_obj, first_relation = user.posts().first()
        assert first_obj is not None
        assert first_relation is not None
        assert first_obj.id in [post1.id, post2.id]


class TestRedisOperations:
    """Test Redis-specific functionality."""
    
    def test_redis_connection_info(self, clean_redis):
        """Test Redis connection and get version info."""
        info = clean_redis.info()
        assert "redis_version" in info
        print(f"✅ Connected to Redis {info['redis_version']}")

    def test_object_persistence_across_connections(self, clean_redis):
        """Test that objects persist across different connections."""
        # Create object with current connection
        user = User.create(
            name="Persistent User",
            email="persist@test.com",
            age=30
        )
        user_id = user.id
        
        # Create new connection and verify object exists
        import os
        new_client = redis.Redis(
            host=os.environ.get('REDIS_HOST', 'localhost'),
            port=int(os.environ.get('REDIS_PORT', '6379')),
            db=int(os.environ.get('REDIS_DATA_DB', '1')),
            decode_responses=True
        )
        from core import set_redis_client
        set_redis_client(new_client)
        
        # Retrieve object with new connection
        retrieved = User.get_by_id(user_id)
        assert retrieved is not None
        assert retrieved.name == "Persistent User"
        assert retrieved.email == "persist@test.com"
        assert retrieved.age == 30

    def test_complex_data_serialization(self, clean_redis):
        """Test nested data structures using current ORM's flatten/unflatten approach."""
        # Use nested data similar to what the current application actually stores
        room_data = {
            "cards": {
                "card1": {"value": "5", "flipped": "True"},
                "card2": {"value": "7", "flipped": "False"}
            },
            "settings": {
                "max_players": "4",
                "round_time": "30"
            }
        }
        
        user = User.create(name="Complex User", email="complex@test.com", age=room_data)
        
        # Verify data persisted correctly using current ORM approach
        retrieved = User.get_by_id(user.id)
        assert retrieved.age == room_data
        assert retrieved.age["cards"]["card1"]["value"] == "5"
        assert retrieved.age["settings"]["max_players"] == "4"
        
        # All values are stored as strings in current ORM
        assert isinstance(retrieved.age["cards"]["card1"]["value"], str)
        assert isinstance(retrieved.age["settings"]["max_players"], str)

    def test_concurrent_operations(self, clean_redis):
        """Test concurrent operations with real Redis."""
        import threading
        import time
        
        user = User.create(name="Concurrent User", email="concurrent@test.com")
        results = []
        errors = []
        
        def update_user(thread_id):
            try:
                from core import ConflictError
                # Get user
                thread_user = User.get_by_id(user.id)
                
                # Simulate some work
                time.sleep(0.1)
                
                # Update user
                thread_user.name = f"Updated by thread {thread_id}"
                updated = thread_user.save()
                results.append((thread_id, updated.name))
                
            except ConflictError as e:
                errors.append((thread_id, str(e)))
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=update_user, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # At least one should succeed, others might get ConflictError
        assert len(results) >= 1
        print(f"✅ Concurrent operations: {len(results)} succeeded, {len(errors)} failed (expected)")

    def test_redis_memory_usage(self, clean_redis):
        """Test Redis memory usage with the ORM."""
        # Get initial memory usage
        info_before = clean_redis.info('memory')
        used_memory_before = info_before['used_memory']
        
        # Create objects
        objects = []
        for i in range(50):
            user = User.create(
                name=f"Memory Test User {i}",
                email=f"memtest{i}@test.com",
                age=i
            )
            objects.append(user)
        
        # Get final memory usage
        info_after = clean_redis.info('memory')
        used_memory_after = info_after['used_memory']
        
        memory_increase = used_memory_after - used_memory_before
        memory_per_object = memory_increase / 50
        
        print(f"✅ Memory usage: {memory_increase} bytes for 50 objects ({memory_per_object:.1f} bytes/object)")
        
        # Basic assertion that memory was used
        assert memory_increase > 0
        assert memory_per_object > 50  # Each object should use at least 50 bytes 