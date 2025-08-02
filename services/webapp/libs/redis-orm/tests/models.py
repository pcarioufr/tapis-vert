
"""
Example models demonstrating Redis ORM usage patterns.

These examples show how to:
- Define basic models with ObjectMixin
- Create relationships with RelationMixin
- Use different relationship types (one-to-many, many-to-many)
- Handle complex data fields
"""

from core import ObjectMixin, RelationMixin


class User(ObjectMixin):
    """Example user model demonstrating basic ObjectMixin usage."""
    
    FIELDS = {"name", "email", "profile", "metadata"}
    
    RIGHTS = {
        "posts": "tests.models.UserPosts",
        "comments": "tests.models.UserComments", 
    }


class Post(ObjectMixin):
    """Example post model demonstrating relationships and complex fields."""
    
    FIELDS = {"title", "content", "metadata", "tags"}
    
    LEFTS = {
        "author": "tests.models.UserPosts"
    }
    
    RIGHTS = {
        "comments": "tests.models.PostComments"
    }


class Comment(ObjectMixin):
    """Example comment model demonstrating nested relationships."""
    
    FIELDS = {"content", "text", "created_at", "author_id"}
    
    LEFTS = {
        "author": "tests.models.UserComments",
        "post": "tests.models.PostComments"
    }


# Relationship Models

class UserPosts(RelationMixin):
    """One-to-many relationship: User has many Posts, Post has one author."""
    
    FIELDS = {"role", "permissions"}
    RELATION_TYPE = "one_to_many"  # Each post has only one author
    
    L_CLASS = User
    R_CLASS = Post
    NAME = "user:posts"


class UserComments(RelationMixin):
    """One-to-many relationship: User has many Comments."""
    
    FIELDS = {"created_at"}
    RELATION_TYPE = "one_to_many"
    
    L_CLASS = User  
    R_CLASS = Comment
    NAME = "user:comments"


class PostComments(RelationMixin):
    """One-to-many relationship: Post has many Comments."""
    
    FIELDS = {"approved", "moderated"}
    RELATION_TYPE = "one_to_many"
    
    L_CLASS = Post
    R_CLASS = Comment  
    NAME = "post:comments"


# Example usage functions

def create_blog_example():
    """Create example blog data to demonstrate the ORM."""
    
    # Create users
    alice = User.create(
        name="Alice Smith",
        email="alice@example.com", 
        profile={"bio": "Software developer", "location": "San Francisco"}
    )
    
    bob = User.create(
        name="Bob Johnson",
        email="bob@example.com",
        profile={"bio": "Tech writer", "location": "New York"}
    )
    
    # Create posts
    post1 = Post.create(
        title="Introduction to Redis",
        content="Redis is a powerful in-memory data structure store...",
        metadata={"views": 150, "likes": 23},
        tags=["redis", "database", "tutorial"]
    )
    
    post2 = Post.create(
        title="Python Best Practices", 
        content="Here are some important Python best practices...",
        metadata={"views": 89, "likes": 12},
        tags=["python", "programming", "best-practices"]
    )
    
    # Create relationships: users write posts
    alice.posts().add(post1.id, role="author", permissions=["edit", "delete"])
    bob.posts().add(post2.id, role="author", permissions=["edit", "delete"])
    
    # Create comments
    comment1 = Comment.create(content="Great tutorial! Thanks for sharing.", created_at="2024-01-15")
    comment2 = Comment.create(content="Very helpful examples.", created_at="2024-01-16")
    comment3 = Comment.create(content="Could you add more details about performance?", created_at="2024-01-17")
    
    # Create relationships: users write comments on posts
    bob.comments().add(comment1.id, created_at="2024-01-15")
    alice.comments().add(comment2.id, created_at="2024-01-16") 
    alice.comments().add(comment3.id, created_at="2024-01-17")
    
    post1.comments().add(comment1.id, approved=True, moderated=False)
    post1.comments().add(comment3.id, approved=True, moderated=False)
    post2.comments().add(comment2.id, approved=True, moderated=False)
    
    return {
        "users": [alice, bob],
        "posts": [post1, post2], 
        "comments": [comment1, comment2, comment3]
    }


def query_examples(data):
    """Demonstrate various query patterns."""
    
    alice, bob = data["users"]
    post1, post2 = data["posts"]
    
    # Get user's posts
    alice_posts = alice.posts().all()
    print(f"Alice has {len(alice_posts)} posts")
    
    # Get post's author  
    author, relation = post1.author().first()
    if author:
        print(f"Post '{post1.title}' was written by {author.name}")
        print(f"Author role: {relation.role}")
    
    # Get post's comments
    post1_comments = post1.comments().all()
    print(f"Post 1 has {len(post1_comments)} comments")
    
    # Get user's comments
    alice_comments = alice.comments().all() 
    print(f"Alice has written {len(alice_comments)} comments")
    
    # Convert to dict for JSON serialization
    user_dict = alice.to_dict(include_related=True)
    print(f"Alice full data: {user_dict}")


if __name__ == "__main__":
    import os
    from core import set_redis_client, create_redis_client
    
    # Require Redis environment variables
    if not os.environ.get('REDIS_HOST'):
        print("❌ REDIS_HOST environment variable required")
        print("💡 Run with Docker: ./test.sh")
        print("💡 Or set Redis environment variables:")
        print("   export REDIS_HOST=localhost")
        print("   export REDIS_PORT=6379") 
        print("   export REDIS_DATA_DB=0")
        exit(1)
    
    # Use real Redis from environment
    redis_client = create_redis_client()
    set_redis_client(redis_client)
    print(f"✅ Using Redis at {os.environ.get('REDIS_HOST')}:{os.environ.get('REDIS_PORT', '6379')}")
    
    # Create example data
    print("Creating blog example...")
    data = create_blog_example()
    
    print("\nRunning query examples...")
    query_examples(data)
    
    print("\nExample completed!") 