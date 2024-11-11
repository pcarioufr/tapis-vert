import redis
import os
import uuid

from typing import Union

from utils import log, new_id
from datetime import datetime


REDIS_CLIENT = redis.Redis(
    host=os.environ.get("REDIS_HOST"),
    db=os.environ.get("REDIS_DATA_DB"),
    decode_responses=True
)


class RedisMixin:
    """A Redis ORM Mixin that manipulates hash map (HSET) objects"""

    ID_GENERATOR    = new_id    # The ID generator to use for the class
    FIELDS          = None      # An allowlist of fields to consider in the hash map values

    def __init__(self, id: str, data: dict):
        self.id = id 
        self.data = data

    def __getattr__(self, name):
        """Intercepts attribute access for keys in FIELDS."""

        if name in self.FIELDS:
            return self.data.get(name, None)  # Return None if the key is missing
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        """Intercepts attribute setting for keys in FIELDS."""

        if name in {"id", "data", "FIELDS"}:
            # Set known attributes normally
            super().__setattr__(name, value)
        elif name in self.FIELDS:
            # If name is in FIELDS, update self.data instead
            self.data[name] = value
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        
    @classmethod
    def _prefix(cls):
        """Returns the lowercased class name to use as key prefix."""
        return cls.__name__.lower()

    @classmethod
    def _key(cls, id: str) -> str:
        """Returns the Redis key of an object"""
        return f"{cls._prefix()}:{id}"

    @classmethod
    def create(cls, data: dict) -> "RedisMixin":
        """Creates the object in Redis."""
        while True:
            id = str(cls.ID_GENERATOR())
            if not REDIS_CLIENT.exists(cls._key(id)):
                break  # Unique ID found

        instance = cls(id=id, data=data)
        instance.save()

        log.info(f"{cls.__name__} with ID {id} created")

        return instance

    @classmethod
    def get(cls, id: str) -> Union["RedisMixin",  None]:
        """Retrives the object from Redis."""
        data = REDIS_CLIENT.hgetall(cls._key(id))
        if not data:
            return None
        return cls(id=id, data=data)

    @classmethod
    def exist(cls, id: str) -> bool:
        """Assesses whether the object exists."""
        return REDIS_CLIENT.exists(cls._key(id))

    def save(self) -> "RedisMixin":
        """Saves the object current state into Redis."""

        params = {k: v for k, v in self.data.items() if k in self.FIELDS}
        REDIS_CLIENT.hset(self._key(self.id), mapping=params)


        log.info(f"{self.__class__.__name__} with ID {self.id} updated: {params}")

        return self

    def delete(self) -> bool:
        """Deletes the object from Redis."""
        REDIS_CLIENT.delete(self._key(self.id))

        log.info(f"{self.__class__.__name__} with ID {self.id} deleted.")

        return True

    def to_dict(self):
        """Converts the object to a dictionary for JSON serialization."""
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
        for key in REDIS_CLIENT.scan_iter(f"{cls._prefix()}:*"):
            data = REDIS_CLIENT.hgetall(key)
            id = key.split(":")[1]  # Extract the id from the key
            instances.append(cls(id=id, data=data))
        
        return instances





class RedisAssociation:
    """A simplified association class for managing n:m relationships."""

    L_CLASS = None   # left hand side class (e.g., "User")
    R_CLASS = None   # right hand side class (e.g., "Code")
    NAME    = "a"    # name of the association (e.g. ownership)

    @classmethod
    def _L_prefix(cls):
        """Returns the lowercased class name to use as left key prefix."""
        return cls.L_CLASS.__name__.lower()

    @classmethod
    def _R_prefix(cls):
        """Returns the lowercased class name to use as right key prefix."""
        return cls.R_CLASS.__name__.lower()

    @classmethod
    def add_association(cls, left_id: str, right_id: str, metadata: dict = None):

        """Add an association between the left and right objects with optional metadata."""
        key = f"{cls.NAME}::{cls._L_prefix()}:{left_id}::{cls._R_prefix()}:{right_id}"

        # Set metadata, including timestamp if not provided
        metadata = metadata or {}
        metadata.setdefault("created_at", datetime.utcnow().isoformat())
        
        # Store metadata as a hash
        REDIS_CLIENT.hset(key, mapping=metadata)
        
        log.info(f"Association added: {cls._L_prefix()} {left_id} <-> {cls._R_prefix()} {right_id} with metadata {metadata}")

    @classmethod
    def get_left_ids_for_right(cls, right_id: str) -> list:
        """Retrieve all left-side object IDs associated with a given right-side object."""

        left_ids = []
        
        # Pattern to match all left-right associations for the given right_id
        pattern = f"{cls.NAME}::{cls._L_prefix()}:*::{cls._R_prefix()}:{right_id}"
        
        for key in REDIS_CLIENT.scan_iter(pattern):
            left_id = key.split("::")[1].split(":")[1]  # Extract the left_id from the key
            metadata = REDIS_CLIENT.hgetall(key)  # Retrieve metadata
            left_ids.append({
                f"{cls.L_CLASS.__name__.lower()}_id": left_id,
                "metadata": metadata
            })

        return left_ids

    @classmethod
    def get_right_ids_for_left(cls, left_id: str) -> list:
        """Retrieve all right-side object IDs associated with a given left-side object."""

        right_ids = []
        
        # Pattern to match all right-left associations for the given left_id
        pattern = f"{cls.NAME}::{cls._L_prefix()}:{left_id}::{cls._R_prefix()}:*"
        
        for key in REDIS_CLIENT.scan_iter(pattern):
            right_id = key.split("::")[2].split(":")[1]  # Extract the right_id from the key
            metadata = REDIS_CLIENT.hgetall(key)  # Retrieve metadata
            right_ids.append({
                f"{cls.R_CLASS.__name__.lower()}_id": right_id,
                "metadata": metadata
            })

        return right_ids

    @classmethod
    def remove_association(cls, left_id: str, right_id: str):
        """Remove the association between the left and right objects."""

        key = f"{cls.NAME}::{cls._L_prefix()}:{left_id}::{cls._R_prefix()}:{right_id}"
        
        # Delete the association
        REDIS_CLIENT.delete(key)
        log.info(f"Association removed: {cls._L_prefix()} {left_id} <-> {cls._L_prefix()}")


    @classmethod
    def list_all_associations(cls) -> list:
        """Lists all associations with metadata as JSON-serializable dictionaries."""

        associations = []

        # Pattern to match all association keys
        pattern = f"{cls.NAME}::{cls._L_prefix()}:*::{cls._R_prefix()}:*"
        for key in REDIS_CLIENT.scan_iter(pattern):
            # Extract IDs from the key pattern
            parts = key.split(":")
            left_id = parts[2]
            right_id = parts[4]

            # Retrieve metadata
            metadata = REDIS_CLIENT.hgetall(key)

            # Add association with metadata to the list
            associations.append({
                f"{cls._L_prefix()}_id": left_id,
                f"{cls._R_prefix()}_id": right_id,
                "metadata": metadata
            })

        return associations
