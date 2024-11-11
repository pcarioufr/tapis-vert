import redis
import os
import uuid

from typing import Union

from utils import log

from utils import new_id


REDIS_CLIENT = redis.Redis(
    host=os.environ.get("REDIS_HOST"),
    db=os.environ.get("REDIS_DATA_DB"),
    decode_responses=True
)
    

class RedisMixin:
    """A Redis ORM Mixin that manipulates hash map (HSET) objects"""

    ID_GENERATOR    = new_id    # The ID generator to use for the class
    PREFIX          = None      # The prefix to be used in Redis keys ("prefix:id")
    FIELDS          = None      # An allowlist of fields to consider in the hash map values

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
    def key(cls, id: str) -> str:
        """Returns the Redis key of an object"""
        return f"{cls.PREFIX}:{id}"


    @classmethod
    def create(cls, data: dict) -> "RedisMixin":
        """Creates the object in Redis."""
        while True:
            id = str(cls.ID_GENERATOR())
            if not REDIS_CLIENT.exists(cls.key(id)):
                break  # Unique ID found

        instance = cls(id=id, data=data)
        instance.save()

        log.info(f"{cls.__name__} with ID {id} created")

        return instance


    @classmethod
    def get(cls, id: str) -> Union["RedisMixin",  None]:
        """Retrives the object from Redis."""
        data = REDIS_CLIENT.hgetall(cls.key(id))
        if not data:
            return None
        return cls(id=id, data=data)

    @classmethod
    def exist(cls, id: str) -> bool:
        """Assess whether the object exists."""
        return REDIS_CLIENT.exists(cls.key(id))


    def save(self) -> "RedisMixin":
        """Saves the object current state into Redis."""

        params = {k: v for k, v in self.data.items() if k in self.FIELDS}
        REDIS_CLIENT.hset(self.key(self.id), mapping=params)


        log.info(f"{self.__class__.__name__} with ID {self.id} updated: {params}")

        return self


    def delete(self) -> bool:
        """Deletes the object from Redis."""
        REDIS_CLIENT.delete(self.key(self.id))

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
        
        instances = []
        
        # Iterate over keys using scan_iter to avoid blocking
        for key in REDIS_CLIENT.scan_iter(f"{cls.PREFIX}:*"):
            data = REDIS_CLIENT.hgetall(key)
            id = key.split(":")[1]  # Extract the id from the key
            instances.append(cls(id=id, data=data))
        
        return instances



import redis
import os
from utils import log
import redis
import os
from utils import log
from datetime import datetime


class RedisAssociation:
    """A simplified association class for managing relationships with metadata in Redis."""

    DB_INDEX = None           # Redis DB index to use
    LEFT_PREFIX = None        # Prefix for the left-side class (e.g., "user")
    RIGHT_PREFIX = None       # Prefix for the right-side class (e.g., "code")


    @classmethod
    def add_association(cls, left_id: str, right_id: str, metadata: dict = None):

        """Add an association between the left and right objects with optional metadata."""
        key = f"a:{cls.LEFT_PREFIX}:{left_id}:{cls.RIGHT_PREFIX}:{right_id}"

        # Set metadata, including timestamp if not provided
        metadata = metadata or {}
        metadata.setdefault("created_at", datetime.utcnow().isoformat())
        
        # Store metadata as a hash
        REDIS_CLIENT.hset(key, mapping=metadata)
        
        log.info(f"Association added: {cls.LEFT_PREFIX.capitalize()} {left_id} <-> {cls.RIGHT_PREFIX.capitalize()} {right_id} with metadata {metadata}")

    @classmethod
    def get_association(cls, left_id: str, right_id: str) -> dict:
        """Retrieve the association between two objects, including metadata."""

        key = f"a:{cls.LEFT_PREFIX}:{left_id}:{cls.RIGHT_PREFIX}:{right_id}"
        
        # Retrieve metadata as a dictionary
        metadata = REDIS_CLIENT.hgetall(key)
        if not metadata:
            return None

        # Return a dictionary with both IDs and the associated metadata
        return {
            f"{cls.LEFT_PREFIX}_id": left_id,
            f"{cls.RIGHT_PREFIX}_id": right_id,
            "metadata": metadata
        }

    @classmethod
    def remove_association(cls, left_id: str, right_id: str):
        """Remove the association between the left and right objects."""

        key = f"a:{cls.LEFT_PREFIX}:{left_id}:{cls.RIGHT_PREFIX}:{right_id}"
        
        # Delete the association
        REDIS_CLIENT.delete(key)
        log.info(f"Association removed: {cls.LEFT_PREFIX.capitalize()} {left_id} <-> {cls.RIGHT_PREFIX.capitalize()}")

    @classmethod
    def list_all_associations(cls) -> list:
        """Lists all associations with metadata as JSON-serializable dictionaries."""

        associations = []

        # Pattern to match all association keys
        pattern = f"a:{cls.LEFT_PREFIX}:*:{cls.RIGHT_PREFIX}:*"
        for key in REDIS_CLIENT.scan_iter(pattern):
            # Extract IDs from the key pattern
            parts = key.split(":")
            left_id = parts[2]
            right_id = parts[4]

            # Retrieve metadata
            metadata = REDIS_CLIENT.hgetall(key)

            # Add association with metadata to the list
            associations.append({
                f"{cls.LEFT_PREFIX}_id": left_id,
                f"{cls.RIGHT_PREFIX}_id": right_id,
                "metadata": metadata
            })

        return associations
