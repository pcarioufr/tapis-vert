import os
from core import set_redis_client, create_redis_client

def init_redis_orm():
    """Initialize Redis ORM with the application's Redis configuration.
    
    This should be called from Flask application factories, not during module import.
    """
    client = create_redis_client(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        db=int(os.environ.get("REDIS_DATA_DB", "1")),
        decode_responses=True
    )
    set_redis_client(client)

# Models will be imported after Redis ORM is initialized in Flask app factories
from .models import User, Code, Room
from .models import UserCodes, UsersRooms
