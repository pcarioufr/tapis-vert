import redis
import os
import uuid

from typing import Union

class RedisMixin:
    """A Redis ORM Mixin that manipulates hash map (HSET) objects"""

    DB_INDEX = None   # The DB to use for the Redis client
    PREFIX   = None   # The prefix to be used in Redis keys ("prefix:id")
    PARAMS   = None   # An allowlist of fields to consider in the hash map values

    _redis_client = None


    def __init__(self, id: str, data: dict):
        self.id = id 
        self.data = data


    @classmethod
    def redis_client(cls):
        """Returns the appropriate Redis client for the class"""
        if cls._redis_client is None:
            cls._redis_client = redis.Redis(
                host=os.environ.get("REDIS_HOST"),
                db=cls.DB_INDEX,  # Use the subclass's DB_INDEX
                decode_responses=True
            )

        return cls._redis_client


    @classmethod
    def key(cls, id: str) -> str:
        """Returns the Redis key of an object"""
        return f"{cls.PREFIX}:{id}"


    @classmethod
    def create(cls, data: dict) -> "RedisMixin":
        """Creates the object in Redis."""
        while True:
            id = str(uuid.uuid4())
            if not cls.redis_client().exists(cls.key(id)):
                break  # Unique ID found

        instance = cls(id=id, data=data)
        instance.save()
        return instance


    @classmethod
    def get(cls, id: str) -> Union["RedisMixin",  None]:
        """Retrives the object from Redis."""
        data = cls.redis_client().hgetall(cls.key(id))
        if not data:
            return None
        return cls(id=id, data=data)

    @classmethod
    def exist(cls, id: str) -> bool:
        """Assess whether the object exists."""
        return cls.redis_client().exists(cls.key(id))


    def save(self) -> "RedisMixin":
        """Saves the object current state into Redis."""
        params = {k: v for k, v in self.data.items() if k in self.PARAMS}
        self.redis_client().hset(self.key(self.id), mapping=params)
        return self


    def delete(self) -> bool:
        """Deletes the object from Redis."""
        self.redis_client().delete(self.key(self.id))
        return True


    def to_dict(self):
        """Convert the object to a dictionary for JSON serialization."""
        return {
            "id": self.id,
            **self.data  # Expand the contents of data dictionary
        }