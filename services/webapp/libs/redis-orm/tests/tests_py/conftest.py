"""
Pytest configuration for Redis ORM tests.
Uses real Redis instance for all testing.
"""

import os
import pytest
import redis
from core import set_redis_client, reset_connection


def pytest_configure():
    """Configure pytest to use real Redis."""
    # Require REDIS_HOST to be set for all tests
    if not os.environ.get('REDIS_HOST'):
        pytest.exit("Tests require REDIS_HOST environment variable. Use Docker: ./test.sh")


@pytest.fixture(scope="function")
def redis_client():
    """Provide a real Redis client for each test."""
    host = os.environ.get('REDIS_HOST', 'localhost')
    port = int(os.environ.get('REDIS_PORT', '6379'))
    db = int(os.environ.get('REDIS_DATA_DB', '1'))
    
    # Create real Redis client
    client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
    
    # Test connection
    try:
        client.ping()
    except redis.ConnectionError:
        pytest.exit(f"Cannot connect to Redis at {host}:{port}. Is Redis running?")
    
    # Set as global client
    set_redis_client(client)
    
    yield client
    
    # Clean up after test
    client.flushdb()
    reset_connection()


@pytest.fixture(scope="function")
def clean_redis(redis_client):
    """Ensure clean Redis state for each test."""
    redis_client.flushdb()
    yield redis_client
    redis_client.flushdb() 