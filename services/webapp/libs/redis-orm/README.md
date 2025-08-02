# Redis ORM

**The perfect balance between relational database structure and Redis low-latency performance.**

Redis ORM provides familiar ORM patterns (models, relationships, migrations) while leveraging Redis's atomic operations and in-memory speed. Ideal for real-time applications where traditional databases are too slow, but you still need structured data relationships.

## Why Redis ORM?

This ORM bridges the gap between traditional database structure and Redis performance:

| Traditional RDBMS | Redis ORM | Pure Redis |
|-------------------|-----------|------------|
| ✅ Structured relationships | ✅ Structured relationships | ❌ Manual key management |
| ✅ ACID transactions | ✅ Atomic operations | ✅ Atomic operations |
| ❌ High latency (10-100ms) | ✅ Low latency (<1ms) | ✅ Low latency (<1ms) |
| ✅ Complex queries | ⚠️ Simple queries only | ❌ No query abstraction |
| ✅ Schema validation | ✅ Field validation | ❌ No validation |

**Perfect for**: Applications that need relational data structure but can't afford database latency.

# User Guide

## Installation & Quick Start

🚀 **Low-Latency Operations**: Sub-millisecond response times for real-time applications  
🔗 **Relational Structure**: Full support for one-to-many and many-to-many relationships  
⚡ **Atomic Operations**: Redis's native concurrency control prevents race conditions  
🔒 **Optimistic Locking**: Version-based conflict resolution for collaborative environments  
🧹 **Automatic Cleanup**: Built-in TTL support for temporary data and soft deletes  
📊 **Real-Time State**: Perfect for live game state, chat systems, collaborative tools

**Use Cases**: Multiplayer games, real-time collaboration, live dashboards, chat applications, any system requiring both structured relationships and millisecond response times.

### Installation

```bash
pip install redis-orm
```

#### Development Installation

```bash
git clone https://github.com/yourusername/redis-orm.git
cd redis-orm
pip install -e ".[dev]"
```

### Basic Usage

```python
from core import ObjectMixin, RelationMixin, set_redis_client
import redis

# Configure Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
set_redis_client(redis_client)

# Define models
class User(ObjectMixin):
    FIELDS = {"name", "email"}
    RIGHTS = {"posts": "myapp.UserPosts"}

class Post(ObjectMixin):
    FIELDS = {"title", "content"}
    LEFTS = {"author": "myapp.UserPosts"}

class UserPosts(RelationMixin):
    FIELDS = {"role"}
    RELATION_TYPE = "one_to_many"  # Each post has one author
    L_CLASS = User
    R_CLASS = Post
    NAME = "user:posts"

# Use the models
user = User.create(name="Alice", email="alice@example.com")
post = Post.create(title="Hello World", content="My first post!")

# Create relationship
user.posts().add(post.id, role="author")

# Query relationships
user_posts = user.posts().all()
author, relation = post.author().first()
```

### Configuration

#### Environment Variables
```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DATA_DB=0
```

#### Programmatic Configuration
```python
from core import create_redis_client, set_redis_client

# Create custom client
client = create_redis_client(
    host="redis.example.com",
    port=6379,
    db=1,
    password="secret"
)
set_redis_client(client)
```

#### Connection Management
```python
from core import get_redis_client, reset_connection

# Get current client
client = get_redis_client()

# Reset connection (useful for testing)
reset_connection()
```

## Testing

This section describes the testing strategy and setup for the Redis ORM package.

### Testing Strategy

All tests use **real Redis instances** for authentic behavior validation. The testing is done via Docker Compose to ensure a consistent, isolated environment.

```bash
# Run all tests with Docker
cd tests/
./run.sh
```

The test suite includes:
- **Core ORM functionality**: Object creation, updates, relationships, optimistic locking
- **Example models**: Blog-style models (User, Post, Comment) with relationships  
- **Redis integration**: Connection management, pipeline operations, error handling
- **Performance edge cases**: Large datasets, concurrent operations

### Test Structure

```
tests/
├── run.sh                    # Main test runner
├── models.py                 # Example models and scenarios
├── docker/
│   ├── run.sh               # Docker orchestration
│   ├── compose.yml          # Redis + Python test environment
│   └── Dockerfile           # Test environment setup
└── tests_py/
    ├── core_test.py         # Core ORM tests
    ├── models_test.py       # Example model tests
    └── conf_test.py         # Test configuration
```

**Why Real Redis**: Tests revealed bugs that fakeredis missed, including the patch method existence check bug and relationship query performance issues.

## Error Handling

```python
from core import ConflictError, ValidationError, RelationError

try:
    # Create object
    user = User.create(name="Alice")
    
    # Create relationship
    user.posts().add(post.id, role="author")
    
    # Update with optimistic locking
    user.name = "Alice Smith"
    user.save()
    
except ConflictError:
    # Handle concurrent modifications or deleted objects
    pass
except ValidationError:
    # Handle validation errors
    pass
except RelationError:
    # Handle relationship errors
    pass
```

## Performance

### Performance Tips

1. **Use patch() for single field updates**:
   ```python
   # Faster than get + save for single fields
   User.patch(user_id, "last_login", timestamp)
   ```

2. **Batch operations with pipelines**:
   ```python
   # For bulk operations, consider using Redis pipelines directly
   client = get_redis_client()
   with client.pipeline() as pipe:
       # Multiple operations
       pipe.execute()
   ```

3. **Optimize relationship queries**:
   ```python
   # Use exists() before get_by_id() if you only need to check existence
   if user.posts().exists(post_id):
       # Do something
   ```

4. **Be aware of relationship query costs**:
   ```python
   # These operations get slower as Redis grows (O(N) keyspace scan)
   user_posts = UserPosts.rights(user.id)  # Consider caching results
   post_authors = UserPosts.lefts(post.id)  # Or use alternative patterns
   ```

### Performance Considerations

#### 1. Redis Pipelining
Multiple operations are batched when possible:

```python
# save(), delete(), and relationship operations use pipelines
with REDIS_CLIENT.pipeline() as pipe:
    pipe.hset(key, field, value)
    pipe.hincrby(key, "_version", 1)
    pipe.hset(key, "_edited", now())
    pipe.execute()
```

#### 2. Relationship Query Performance

**⚠️ Known Performance Issue**: The current `lefts()` and `rights()` methods use Redis SCAN operations that are O(N) where N is the total Redis keyspace:

```python
# Current implementation - scans ALL keys in Redis
def rights(cls, left_id: str) -> dict[str, "RelationMixin"]:
    pattern = f"{cls.NAME}:{left_id}:*"
    # This gets slower as your Redis instance grows!
    cursor, keys = REDIS_CLIENT.scan(0, match=pattern, count=1000)
```

**Impact**: Gets slower as Redis instance grows, regardless of actual number of relations.

**Alternative Approaches** (see Developer Guide):
- Redis Sets for O(1) lookups
- Sorted Sets for ordered relationships
- Hash-based indexes

#### 3. Optimistic vs Pessimistic Locking
- System uses optimistic locking (version checks)
- Better performance than locks in low-contention scenarios
- May require retry logic in high-contention cases

# Developer Guide

## Core Concepts & Features

### ObjectMixin

Base class for Redis-backed models with these key features:

- **ObjectMixin**: Base class for Redis-backed models with automatic ID generation
- **RelationMixin**: Support for one-to-many and many-to-many relationships  
- **Optimistic Locking**: Prevents concurrent modification conflicts using version control
- **Soft Deletes**: Two-phase deletion that prevents zombie updates during grace period
- **Flexible Fields**: Support for complex nested data structures via flatten/unflatten
- **Query Support**: Search and pagination with Redis SCAN
- **Real Redis Testing**: All tests use real Redis instances for authentic behavior
- **Optional Tracing**: Datadog APM integration (optional dependency)

```python
class User(ObjectMixin):
    FIELDS = {"name", "email", "profile"}  # Define allowed fields
    
    # Define relationships (optional)
    RIGHTS = {"posts": "myapp.UserPosts"}   # User has many posts
    LEFTS = {"team": "myapp.TeamUsers"}     # User belongs to team

# Create objects
user = User.create(
    name="John Doe",
    email="john@example.com", 
    profile={"bio": "Developer", "location": "NYC"}
)

# Update objects
user.name = "John Smith"
user = user.save()  # Returns updated object with new version

# Query objects
user = User.get_by_id("some_id")
all_users, cursor = User.search()

# Delete objects (soft delete with 60s TTL)
user.delete()
```

### RelationMixin

Manages relationships between objects:

```python
class UserPosts(RelationMixin):
    FIELDS = {"role", "created_at"}  # Additional relationship data
    RELATION_TYPE = "one_to_many"    # or "many_to_many"
    L_CLASS = User                   # Left side class
    R_CLASS = Post                   # Right side class
    NAME = "user:posts"              # Redis key prefix

# Create relationships
relation = UserPosts.create(user.id, post.id, role="author")

# Query relationships
user_posts = UserPosts.rights(user.id)  # All posts for user
post_authors = UserPosts.lefts(post.id) # All authors for post
```

### Optimistic Locking

Each object maintains a version number to prevent lost updates:

```python
# Get the same object in two places
user1 = User.get_by_id("some_id")
user2 = User.get_by_id("some_id")

# First save succeeds
user1.name = "Updated Name"
user1.save()

# Second save fails with ConflictError
user2.name = "Different Name"
try:
    user2.save()
except ConflictError:
    # Handle conflict - typically reload and retry
    user2 = User.get_by_id("some_id")
    user2.name = "Different Name"
    user2.save()
```

## Advanced Usage

### Complex Data Types

Objects support nested data through automatic flattening:

```python
user = User.create(
    name="Alice",
    profile={
        "preferences": {
            "theme": "dark",
            "notifications": {"email": True, "push": False}
        },
        "metadata": ["tag1", "tag2"]
    }
)
```

### Custom Field Validation

```python
class User(ObjectMixin):
    FIELDS = {"name", "email", "age"}
    
    @classmethod
    def validate_fields(cls, **data):
        if "email" in data and "@" not in data["email"]:
            raise ValidationError("Invalid email format")
        return data
```

### Manual Key Management

For advanced use cases:

```python
# Custom object IDs
user = User.create(id="custom_id", name="Alice")

# Direct Redis operations
from core import get_redis_client
client = get_redis_client()
client.hset("custom:key", "field", "value")
```

## Architecture Overview

The ORM is designed for low-latency operations in collaborative environments with these key architectural decisions:

### Core Modules

- **`connection.py`**: Redis connection management with environment variable support
- **`mixins.py`**: Core ObjectMixin and RelationMixin classes
- **`exceptions.py`**: Custom exception hierarchy for error handling
- **`utils.py`**: Utility functions for ID generation, timestamps, and data serialization

### Design Patterns

**Mixin Architecture**: Instead of traditional inheritance, uses mixins to compose functionality:
```python
class User(ObjectMixin):          # Gets: CRUD, versioning, soft delete
    pass

class UserPosts(RelationMixin):   # Gets: relationship management
    pass
```

**Pipeline Optimization**: Groups related Redis operations:
```python
def save(self):
    with REDIS_CLIENT.pipeline() as pipe:
        pipe.hset(self.key, mapping=self.flatten())
        pipe.hincrby(self.key, "_version", 1)
        pipe.hset(self.key, "_edited", now())
        pipe.execute()
```

**Optimistic Concurrency**: Uses version numbers instead of locks:
```python
# Check version before save
current_version = REDIS_CLIENT.hget(self.key, "_version") 
if current_version != self._version:
    raise ConflictError("Object modified by another process")
```

### Redis Key Structure

Objects and relationships use predictable key patterns:

```
# Objects
object:{class_name}:{object_id}         # User object
  ├── field1: "value1"
  ├── field2: "value2"  
  ├── _version: "3"
  ├── _created: "2024-01-01T12:00:00Z"
  └── _edited: "2024-01-01T12:30:00Z"

# Relationships  
relation:{relation_name}:{left_id}:{right_id}  # UserPosts relation
  ├── role: "author"
  ├── created_at: "2024-01-01T12:00:00Z"
  ├── _version: "1"
  └── _created: "2024-01-01T12:00:00Z"
```

## Known Issues & Future Development

### Known Issues & Test Findings

Based on comprehensive testing, the following issues were identified:

#### 1. Relationship Query Performance Issue ⚠️
**Problem**: `lefts()` and `rights()` methods use O(N) SCAN operations
**Test**: `test_lefts_and_rights_queries` - FAILING
**Impact**: Gets slower as Redis keyspace grows
**Status**: Documented for future optimization

#### 2. Cross-Connection Type Consistency ⚠️
**Problem**: Objects may not maintain exact type consistency across different Redis connections
**Test**: `test_object_persistence_across_connections` - FAILING  
**Impact**: Potential issues in multi-process deployments
**Status**: Under investigation

#### 3. Example Model Inconsistencies
**Tests**: Multiple example-related tests failing
**Reason**: Example models don't match current ORM patterns exactly
**Impact**: Documentation examples only
**Status**: Test artifacts, not production issues

#### 4. patch() vs unflatten() Inconsistency ✅ FIXED
**Problem**: `patch()` method supports nested field syntax but doesn't create empty field markers that `unflatten()` expects
**Example**: `obj.patch(key, "messages:123", "data")` creates Redis field `"messages:123"` but no `"messages": ""` marker
**Impact**: Causes object corruption when reading back - `unflatten()` fails to reconstruct nested structure properly
**Real-world trigger**: Message storage using `room.patch(room_id, f"messages:{timestamp}", message)` corrupted room.cards data
**Root cause**: Inconsistent behavior between flatten/unflatten (creates markers) vs patch() nested syntax (doesn't create markers)
**Fix**: Updated `patch()` method to prevent mixed states and remove empty base field markers when adding nested fields
**Status**: ✅ RESOLVED - patch method now raises ConflictError for invalid mixed states and cleans up empty markers

#### 5. Module Path Configuration Issues ✅ FIXED
**Problem**: Test relationship configurations used inconsistent module paths
**Example**: `RIGHTS = {"posts": "UserPosts"}` instead of `RIGHTS = {"posts": "tests.models.UserPosts"}`
**Impact**: ModuleNotFoundError and ValueError during relationship manager instantiation
**Tests affected**: 12 relationship-related tests failing with import errors
**Fix**: Updated all relationship class paths to use fully qualified module names
**Status**: ✅ RESOLVED - Test coverage improved from 52.5% to 85% (21→34 passing tests)

#### 6. Redis Data Type Serialization ⚠️
**Problem**: Redis only accepts bytes, strings, integers, and floats - not Python lists, dicts, or booleans
**Example**: `DataError: Invalid input of type: 'list'` when trying to save Python lists directly
**Impact**: Affects models that store complex data structures without proper serialization
**Tests affected**: 3 tests failing when trying to save lists/booleans to Redis
**Workaround**: Use JSON serialization for complex types: `json.dumps(data)` before saving
**Status**: Design limitation - requires explicit serialization for complex types

#### 7. Relationship Constraint Enforcement ⚠️
**Problem**: Tests attempting to violate one-to-many constraints
**Example**: `ValueError: Post:xyz is already linked to a User - skipping association`
**Impact**: Test logic error, but demonstrates ORM correctly enforcing relationship constraints
**Tests affected**: 1 test expecting to create duplicate one-to-many relationships
**Status**: Test needs updating - ORM behavior is correct

### Future Work & TODOs

#### Redis-Native Relationships

The current implementation could be optimized using Redis Sets:

##### Current Approach (O(N) keyspace scan)
```python
# Scans ALL keys in Redis to find matches - gets slower as Redis grows
pattern = f"{cls.NAME}:{left_id}:*"
cursor, keys = REDIS_CLIENT.scan(cursor, match=pattern, count=1000)
```

##### Proposed Set-Based Approach (O(1) access + O(M) results)
```python
class SetBasedRelationMixin:
    @classmethod
    def create(cls, left_id, right_id, **data):
        with REDIS_CLIENT.pipeline() as pipe:
            # Store relation data
            key = f"relation:{cls.NAME}:{left_id}:{right_id}"
            pipe.hset(key, mapping=data)
            
            # O(1) bidirectional indexes
            pipe.sadd(f"{cls.L_CLASS.__name__.lower()}:{left_id}:rights", right_id)
            pipe.sadd(f"{cls.R_CLASS.__name__.lower()}:{right_id}:lefts", left_id)
            pipe.execute()
    
    @classmethod
    def rights(cls, left_id):
        # O(1) lookup + O(M) where M = number of relations
        right_ids = REDIS_CLIENT.smembers(f"{cls.L_CLASS.__name__.lower()}:{left_id}:rights")
        # Then batch fetch the relation objects
```

#### Enhanced Query Capabilities
- Add support for field-based queries beyond ID lookup
- Implement Redis Lua scripts for atomic complex operations
- Add support for sorted relationships (using Redis Sorted Sets)

#### Fix patch() / unflatten() Consistency ✅ COMPLETED
- ~~**Option 1**: Update patch() to auto-create empty field markers for nested syntax~~
- ~~**Option 2**: Make unflatten() more tolerant of missing markers~~
- ~~**Option 3**: Deprecate nested syntax in patch(), force users to work with complete objects~~
- ✅ **Implemented**: Added validation to patch() that prevents invalid mixed states and cleans up empty markers
- **Result**: Patch method now raises ConflictError when trying to mix simple fields with nested subfields

#### Performance Optimizations
- Lazy loading for relationship traversal
- Configurable batch sizes for SCAN operations
- Optional caching layer for frequently accessed objects

#### Test Suite Improvements
- ✅ **Module path fixes completed** - Test coverage improved from 52.5% to 85%
- **Remaining data serialization tests** - 3 tests still failing due to Redis type constraints
- **Test documentation** - Add examples of proper JSON serialization for complex types
- **Relationship constraint tests** - Update tests to properly handle one-to-many enforcement

#### Documentation Improvements
- **Version Number Tracking**: Ensure version bumping process updates all references throughout documentation
- **Relationship Type Naming**: Clarify perspective (always from left class perspective) and be consistent about one_to_many vs many_to_one terminology
- **Code Example Completeness**: Make examples completely self-contained or explicitly reference prerequisite sections

## Contributing

We welcome contributions! Here's how to get started:

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/redis-orm.git
   cd redis-orm
   ```

2. **Install in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Run tests**:
   ```bash
   cd tests/
   ./run.sh
   ```

### Contribution Guidelines

- **Tests Required**: All new features must include tests
- **Real Redis**: Tests must pass with real Redis (not fakeredis)
- **Documentation**: Update README for user-facing changes
- **Performance**: Consider Redis operation costs for new features

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Write tests for your changes
4. Ensure all tests pass: `cd tests/ && ./run.sh`
5. Update documentation if needed
6. Submit pull request with clear description

## Publishing to PyPI

This guide explains how to publish the redis-orm package to PyPI.

### Prerequisites

#### 1. PyPI Account Setup
1. **Create accounts** on both:
   - **TestPyPI**: https://test.pypi.org/account/register/ (for testing)
   - **PyPI**: https://pypi.org/account/register/ (for production)

2. **Verify email addresses** for both accounts

3. **Enable 2FA** (required for PyPI publishing)

#### 2. API Tokens
1. Go to Account Settings → API tokens
2. Create a **project-scoped token** for `redis-orm` (recommended)
3. Or create a **global token** (less secure)
4. Save tokens securely - you'll need them for publishing

#### 3. Install Publishing Tools
```bash
pip install build twine
```

### Publishing Process

#### 1. Prepare Release

**Update version in `pyproject.toml`**:
```toml
[project]
name = "redis-orm"
version = "0.2.0"  # Update this
```

**Update CHANGELOG** (recommended):
```markdown
## [0.2.0] - 2024-01-15
### Added
- New feature X
### Fixed  
- Bug Y
```

#### 2. Build Package
```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build source distribution and wheel
python -m build
```

This creates:
- `dist/redis-orm-0.2.0.tar.gz` (source distribution)
- `dist/redis_orm-0.2.0-py3-none-any.whl` (wheel)

#### 3. Test on TestPyPI First

**Upload to TestPyPI**:
```bash
python -m twine upload --repository testpypi dist/*
```

Enter your TestPyPI credentials when prompted.

**Test installation from TestPyPI**:
```bash
# Create fresh virtual environment
python -m venv test-env
source test-env/bin/activate  # Linux/Mac
# test-env\Scripts\activate    # Windows

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ redis-orm
```

#### 4. Publish to Production PyPI

**Upload to PyPI**:
```bash
python -m twine upload dist/*
```

Enter your PyPI credentials when prompted.

#### 5. Verify Publication

**Check package page**:
- Visit https://pypi.org/project/redis-orm/
- Verify version, description, and metadata

**Test installation**:
```bash
pip install redis-orm==0.2.0
```

### Automation Options

#### GitHub Actions (Recommended)

Create `.github/workflows/publish.yml`:
```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.x'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}
```

**Setup**:
1. Add your PyPI API token to GitHub Secrets as `PYPI_API_TOKEN`
2. Create GitHub release to trigger automatic publishing

#### Manual with Token Storage

Store token in `~/.pypirc`:
```ini
[distutils]
index-servers = pypi testpypi

[pypi]
username = __token__
password = pypi-your-api-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-testpypi-token-here
```

Then upload without credential prompts:
```bash
python -m twine upload dist/*
```

### Best Practices

1. **Always test on TestPyPI first**
2. **Use semantic versioning** (MAJOR.MINOR.PATCH)
3. **Tag releases in Git**: `git tag v0.2.0 && git push --tags`
4. **Keep changelogs** for users
5. **Test installation** in clean environment before publishing
6. **Use API tokens** instead of passwords
7. **Automate with CI/CD** for consistency



# License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 