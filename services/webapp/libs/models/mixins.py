import redis
import os
import uuid

from typing import Union

from utils import log

from utils import new_id


class RedisMixin:
    """A Redis ORM Mixin that manipulates hash map (HSET) objects"""

    DB_INDEX        = None      # The DB to use for the Redis client
    ID_GENERATOR    = new_id    # The ID generator to use for the class
    PREFIX          = None      # The prefix to be used in Redis keys ("prefix:id")
    FIELDS          = None      # An allowlist of fields to consider in the hash map values

    _redis_client = None        # The Redis Client to use


    def __init__(self, id: str, data: dict):
        self.id = id 
        self.data = data


    def __getattr__(self, name):
        """Intercept attribute access for keys in FIELDS."""

        if name in self.FIELDS:
            return self.data.get(name, None)  # Return None if the key is missing
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        """Intercept attribute setting for keys in FIELDS."""

        if name in {"id", "data", "PREFIX", "DB_INDEX", "FIELDS"}:
            # Set known attributes normally
            super().__setattr__(name, value)
        elif name in self.FIELDS:
            # If name is in FIELDS, update self.data instead
            self.data[name] = value
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        

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
            id = str(cls.ID_GENERATOR())
            if not cls.redis_client().exists(cls.key(id)):
                break  # Unique ID found

        instance = cls(id=id, data=data)
        instance.save()

        log.info(f"{cls.__name__} with ID {id} created")

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

        params = {k: v for k, v in self.data.items() if k in self.FIELDS}
        self.redis_client().hset(self.key(self.id), mapping=params)


        log.info(f"{self.__class__.__name__} with ID {self.id} updated: {params}")

        return self


    def delete(self) -> bool:
        """Deletes the object from Redis."""
        self.redis_client().delete(self.key(self.id))

        log.info(f"{self.__class__.__name__} with ID {self.id} deleted.")

        return True


    def to_dict(self):
        """Convert the object to a dictionary for JSON serialization."""
        return {
            "id": self.id,
            **self.data  # Expand the contents of data dictionary
        }
    
    @classmethod
    def scan_all(cls) -> list:
        """Scans and lists all objects. """
        """This method is suited for large datasets (millions of entries)."""
        client = cls.redis_client()
        instances = []
        
        # Iterate over keys using scan_iter to avoid blocking
        for key in client.scan_iter(f"{cls.PREFIX}:*"):
            data = client.hgetall(key)
            id = key.split(":")[1]  # Extract the id from the key
            instances.append(cls(id=id, data=data))
        
        return instances
