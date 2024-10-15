import redis
import os
import uuid

from typing import Union

class RedisMixin:
    
    DB_INDEX = None   # The DB to use for the Redis Client
    PREFIX   = None   # The prefix to be used in Redis keys ("prefix:id")
    PARAMS   = None   # An allowlist of fields to consider in the HSET values

    _redis_client = None


    def __init__(self, id: str, data: dict):
        self.id = id 
        self.data = data


    @classmethod
    def redis_client(cls):
        if cls._redis_client is None:
            cls._redis_client = redis.Redis(
                host=os.environ.get("REDIS_HOST"),
                db=cls.DB_INDEX,  # Use the subclass's DB_INDEX
                decode_responses=True
            )

        return cls._redis_client


    @classmethod
    def key(cls, id: str) -> str:
        return f"{cls.PREFIX}:{id}"


    @classmethod
    def create(cls, data: dict) -> "RedisMixin":
        while True:
            id = str(uuid.uuid4())
            if not cls.redis_client().exists(cls.key(id)):
                break  # Unique ID found

        instance = cls(id=id, data=data)
        instance.save()
        return instance


    @classmethod
    def get(cls, id: str) -> Union["RedisMixin",  None]:
        data = cls.redis_client().hgetall(cls.key(id))
        if not data:
            return None
        return cls(id=id, data=data)


    def save(self) -> "RedisMixin":
        params = {k: v for k, v in self.data.items() if k in self.PARAMS}
        self.redis_client().hset(self.key(self.id), mapping=params)
        return self


    def delete(self) -> bool:
        self.redis_client().delete(self.key(self.id))
        return True


    def to_dict(self):
        """Convert the User object to a dictionary for JSON serialization."""
        return {
            "id": self.id,
            **self.data  # Expand the contents of data dictionary
        }