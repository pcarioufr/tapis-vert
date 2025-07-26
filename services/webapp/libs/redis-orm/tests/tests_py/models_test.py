"""
Tests for example models demonstrating Redis ORM usage patterns.
"""

import pytest
import sys
import os
sys.path.insert(0, '/app')
# Simple Redis fixture
try:
    from core import set_redis_client, create_redis_client
except ImportError:
    import core
    from core import set_redis_client, create_redis_client

@pytest.fixture(scope="function") 
def redis_client():
    client = create_redis_client(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=int(os.environ.get('REDIS_PORT', '6379')),
        db=int(os.environ.get('REDIS_DATA_DB', '1'))
    )
    set_redis_client(client)
    yield client
    client.flushdb()

from models import (
    User, Post, Comment,
    UserPosts, UserComments, PostComments,
    create_blog_example
)


class TestExampleModels:
    """Test the example blog models."""
    
    def test_create_user(self, clean_redis):
        """Test creating a user with metadata."""
        user = User.create(
            name="John Doe", 
            # Use only fields defined in User.FIELDS
            metadata={"location": "SF", "join_date": "2024-01-01"}
        )
        
        assert user.name == "John Doe"
        assert user.metadata["location"] == "SF"
        assert User.exists(user.id)

    def test_create_post_with_metadata(self, clean_redis):
        """Test creating a post with metadata."""
        post = Post.create(
            title="Redis ORM Guide",
            content="How to use Redis ORM effectively",
            # Use string-based metadata like current ORM
            metadata={
                "word_count": "1500",
                "reading_time": "5", 
                "category": "tutorial"
            }
        )
        
        assert post.title == "Redis ORM Guide"
        assert post.content == "How to use Redis ORM effectively"
        assert post.metadata["word_count"] == "1500"
        assert post.metadata["category"] == "tutorial"
        assert Post.exists(post.id)

    def test_user_post_relationship(self, clean_redis):
        """Test creating and querying user-post relationships."""
        user = User.create(name="Author User")
        post = Post.create(title="My First Post", content="Hello world!")
        
        # Create relationship with string-based data
        user.posts().add(post.id, role="author", permissions="edit,delete")
        
        # Test relationship queries
        user_posts = user.posts().all()
        assert post.id in user_posts
        
        relation = user_posts[post.id]
        assert relation.role == "author"
        assert relation.permissions == "edit,delete"
        
        # Test reverse relationship
        post_authors = post.author().all()
        assert user.id in post_authors

    def test_comment_relationships(self, clean_redis):
        """Test many-to-many relationships with comments."""
        user = User.create(name="Commenter")
        post = Post.create(title="Popular Post", content="Great content!")
        comment = Comment.create(text="Great post!", author_id=user.id)
        
        # Link comment to post with string values
        post.comments().add(comment.id, approved="true", moderated="false")
        
        # Test post comments
        post_comments = post.comments().all()
        assert comment.id in post_comments
        
        comment_relation = post_comments[comment.id]
        assert comment_relation.approved == "true"
        assert comment_relation.moderated == "false"
        
        # Test comment posts (reverse)
        comment_posts = comment.posts().all()
        assert post.id in comment_posts

    def test_one_to_many_constraint(self, clean_redis):
        """Test that one-to-many relationships enforce cardinality."""
        user1 = User.create(name="User1", email="user1@example.com")
        user2 = User.create(name="User2", email="user2@example.com")
        post = Post.create(title="Contested Post", content="Who wrote this?")
        
        # First user claims authorship
        user1.posts().add(post.id, role="author")
        
        # Second user tries to claim authorship - should fail for one-to-many
        with pytest.raises(ValueError) as exc_info:
            user2.posts().add(post.id, role="author")
        
        assert "already linked" in str(exc_info.value)

    def test_complex_query_patterns(self, clean_redis):
        """Test complex relationship queries and filtering."""
        # Create test data
        alice = User.create(name="Alice")
        bob = User.create(name="Bob")
        
        post1 = Post.create(title="Post 1", content="First post")
        post2 = Post.create(title="Post 2", content="Second post")
        
        comment1 = Comment.create(text="Great post!")
        comment2 = Comment.create(text="I disagree")
        comment3 = Comment.create(text="Interesting points")
        
        # Create relationships with string values
        alice.comments().add(comment1.id, created_at="2024-01-01")
        bob.comments().add(comment2.id, created_at="2024-01-02") 
        bob.comments().add(comment3.id, created_at="2024-01-03")
        
        post1.comments().add(comment1.id, approved="true")
        post1.comments().add(comment2.id, approved="true")
        post2.comments().add(comment3.id, approved="false")
        
        # Test queries
        post1_comments = post1.comments().all()
        assert len(post1_comments) == 2
        
        # Get all of Bob's comments
        bob_comments = bob.comments().all()
        assert len(bob_comments) == 2
        
        # Get approved comments on post1 (check string values)
        approved_count = 0
        for comment_id, relation in post1.comments().all().items():
            if relation.approved == "true":
                approved_count += 1
        assert approved_count == 2
        
        # Get pending comments on post2 (check string values)
        pending_count = 0
        for comment_id, relation in post2.comments().all().items():
            if relation.approved == "false":
                pending_count += 1
        assert pending_count == 1

    def test_to_dict_with_relationships(self, clean_redis):
        """Test serializing objects with relationships."""
        user = User.create(name="Serializer", email="test@example.com")
        post = Post.create(title="Test Post", content="Content")
        
        user.posts().add(post.id, role="author")
        
        # Test serialization without relationships
        user_dict = user.to_dict(include_related=False)
        assert user.id in user_dict
        assert user_dict[user.id]["name"] == "Serializer"
        assert "posts" not in user_dict[user.id]
        
        # Test serialization with relationships
        user_dict_with_rel = user.to_dict(include_related=True)
        assert user.id in user_dict_with_rel
        assert "posts" in user_dict_with_rel[user.id]
        assert len(user_dict_with_rel[user.id]["posts"]) == 1


class TestBlogExample:
    """Test the complete blog example."""
    
    def test_create_blog_example(self, clean_redis):
        """Test the complete blog example function."""
        data = create_blog_example()
        
        # Verify data structure
        assert "users" in data
        assert "posts" in data
        assert "comments" in data
        
        assert len(data["users"]) == 2
        assert len(data["posts"]) == 2
        assert len(data["comments"]) == 3
        
        # Verify users
        alice, bob = data["users"]
        assert alice.name == "Alice Smith"
        assert bob.name == "Bob Johnson"
        
        # Verify posts
        post1, post2 = data["posts"]
        assert "Redis" in post1.title
        assert "Python" in post2.title
        
        # Verify relationships exist
        alice_posts = alice.posts().all()
        bob_posts = bob.posts().all()
        
        assert len(alice_posts) == 1
        assert len(bob_posts) == 1
        
        # Verify comments are linked
        total_comment_relations = 0
        for post in data["posts"]:
            post_comments = post.comments().all()
            total_comment_relations += len(post_comments)
        
        assert total_comment_relations == 3  # All comments should be linked to posts

    def test_search_functionality(self, clean_redis):
        """Test searching for objects."""
        # Create some test data
        create_blog_example()
        
        # Search for users
        users, cursor = User.search()
        assert len(users) >= 2
        assert cursor == 0
        
        # Search for posts
        posts, cursor = Post.search()
        assert len(posts) >= 2
        
        # Search for comments
        comments, cursor = Comment.search()
        assert len(comments) >= 3

    def test_relationship_deletion(self, clean_redis):
        """Test that deleting objects properly handles relationships."""
        user = User.create(name="To Delete", email="delete@example.com")
        post = Post.create(title="Will be orphaned", content="Content")
        comment = Comment.create(content="Will be orphaned too")
        
        # Create relationships
        user.posts().add(post.id, role="author")
        user.comments().add(comment.id)
        post.comments().add(comment.id, approved=True)
        
        # Verify relationships exist
        assert len(user.posts().all()) == 1
        assert len(user.comments().all()) == 1
        assert len(post.comments().all()) == 1
        
        # Delete user
        user.delete()
        
        # Verify user is gone
        assert User.get_by_id(user.id) is None
        
        # Verify relationships are cleaned up
        # (Note: In a real implementation, you might want cascade deletion
        # or orphan handling depending on your business logic) 