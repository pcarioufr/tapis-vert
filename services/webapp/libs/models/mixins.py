import os
import redis
from datetime import datetime
from typing import Union

from utils import get_logger, new_id
log = get_logger(__name__)


REDIS_CLIENT = redis.Redis(
    host=os.environ.get("REDIS_HOST"),
    db=os.environ.get("REDIS_DATA_DB"),
    decode_responses=True
)


class RedisMixin:
    """A Redis ORM Mixin that manipulates hash map (HSET) objects"""

    ID_GENERATOR    = new_id    # The ID generator to use for the class
    FIELDS          = None      # An allowlist of fields to consider in the hash map values

    _META_FIELDS = {"last_edited"}  # Known metadata fields

    def __init__(self, id: str, data: dict, meta: dict = None):
        self.id = id 
        self.data = data      # Object data (allowed fields)
        self._meta = meta or {}  # Object metadata (private attribute)

    def __getattr__(self, name):
        """Intercepts attribute access for keys in FIELDS."""

        if name in self.FIELDS:
            return self.data.get(name, None)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        """Intercepts attribute setting for keys in FIELDS."""

        if name in {"id", "data", "_meta", "FIELDS", "_META_FIELDS"}:
            super().__setattr__(name, value)
        elif name in self.FIELDS:
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
        log.info(f"Creating {cls.__name__} with ID {id}")

        while True:
            id = str(cls.ID_GENERATOR())
            if not REDIS_CLIENT.exists(cls._key(id)):
                break  # Unique ID found

        instance = cls(id=id, data=data)
        instance.save()


        return instance

    @classmethod
    def get(cls, id: str) -> Union["RedisMixin",  None]:
        """Retrieves the object from Redis, splitting data and meta."""
        key = cls._key(id)
        raw_data = REDIS_CLIENT.hgetall(key)
        
        if not raw_data:
            return None

        # Separate data and meta based on known fields and metadata fields
        data = {k: v for k, v in raw_data.items() if k in cls.FIELDS}
        meta = {k: v for k, v in raw_data.items() if k in cls._META_FIELDS}

        return cls(id=id, data=data, meta=meta)
    
    @classmethod
    def exist(cls, id: str) -> bool:
        """Assesses whether the object exists."""
        return REDIS_CLIENT.exists(cls._key(id))


    def save(self) -> "RedisMixin":
        """Saves the object current state into Redis."""

        key = self._key(self.id)

        # Prepare data and metadata for storage
        data = {k: v for k, v in self.data.items() if k in self.FIELDS}
        
        # Update metadata (e.g., timestamp for 'last_edited')
        self._meta["last_edited"] = datetime.utcnow().isoformat()

        # Combine data and metadata for saving in Redis
        combined_data = {**data, **self._meta}
        REDIS_CLIENT.hset(key, mapping=combined_data)

        log.info(f"{self.__class__.__name__} with ID {self.id} updated: {data} (metadata {self._meta})")
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
            **self.data,
            "metadata": self._meta
        }
    
    @classmethod
    def scan_all(cls) -> list:
        """Scans and lists all objects. """

        instances = []

        for key in REDIS_CLIENT.scan_iter(f"{cls._prefix()}:*"):
            raw_data = REDIS_CLIENT.hgetall(key)
            id = key.split(":")[1]  # Extract the id from the key

            # Separate data and metadata
            data = {k: v for k, v in raw_data.items() if k in cls.FIELDS}
            meta = {k: v for k, v in raw_data.items() if k in cls._META_FIELDS}

            instances.append(cls(id=id, data=data, meta=meta))

        return instances


from datetime import datetime
import logging

log = logging.getLogger(__name__)

class RedisAssociationMixin:
    """A class for managing n:m relationships with data fields and metadata in Redis."""

    L_CLASS = None   # Left-side class (e.g., Room)
    R_CLASS = None   # Right-side class (e.g., User)
    NAME = "left:linksto:right"  # Name of the association for key generation

    FIELDS = None    # Association-specific data fields (e.g., "role")
    _META_FIELDS = {"last_edited"}  # Metadata fields only

    def __init__(self, key: str, data: dict, meta: dict = None):
        self.key = key
        self.data = data
        self._meta = meta or {}

    @classmethod
    def _L_prefix(cls):
        """Returns the lowercased class name for the left-side class."""
        return cls.L_CLASS.__name__.lower()

    @classmethod
    def _R_prefix(cls):
        """Returns the lowercased class name for the right-side class."""
        return cls.R_CLASS.__name__.lower()

    @classmethod
    def _key(cls, left_id: str, right_id: str) -> str:
        """Generate the Redis key for an association between two objects."""
        return f"{cls.NAME}::{cls._L_prefix()}:{left_id}::{cls._R_prefix()}:{right_id}"

    @classmethod
    def create(cls, left_id: str, right_id: str, data: dict = None) -> "RedisAssociationMixin":
        """Creates an association instance and saves it, returning the updated instance."""

        log.info(f"Creating Association: {cls._L_prefix()} {left_id} <-> {cls._R_prefix()} {right_id} with data {data} and metadata {instance._meta}")

        data = {k: v for k, v in (data or {}).items() if k in cls.FIELDS}

        # Initialize the instance with data and metadata, then call save to handle Redis storage
        instance = cls(cls._key(left_id, right_id), data=data)
        instance.save()

        return instance

    @classmethod
    def get(cls, left_id: str, right_id: str) -> Union["RedisAssociationMixin", None]:
        """Retrieves the association, splitting fields and metadata."""
        key = cls._key(left_id, right_id)
        combined_data = REDIS_CLIENT.hgetall(key)

        if not combined_data:
            return None

        # Split combined_data into fields and metadata
        data = {k: v for k, v in combined_data.items() if k in cls.FIELDS}
        meta = {k: v for k, v in combined_data.items() if k in cls._META_FIELDS}

        return cls(key=key, data=data, metadata=meta)

    def save(self):

        """Saves the association's data fields and metadata to Redis."""
        self._meta["last_edited"] = datetime.utcnow().isoformat()

        # Combine data and metadata for storage
        combined_data = {**self.data, **self._meta}
        REDIS_CLIENT.hset(self.key, mapping=combined_data)

        log.info(f"Association with key {self.key} saved with data {self.data} and metadata {self._meta}")
        return self


    def delete(self) -> bool:
        """Deletes the association from Redis."""
        REDIS_CLIENT.delete(self.key)
        log.info(f"Association removed: {self.key}")
        return True

    @classmethod
    def scan_all(cls) -> list:
        """Lists all associations with data fields and metadata as JSON-serializable dictionaries."""
        associations = []
        pattern = f"{cls.NAME}::{cls._L_prefix()}:*::{cls._R_prefix()}:*"

        for key in REDIS_CLIENT.scan_iter(pattern):
            combined_data = REDIS_CLIENT.hgetall(key)
            parts = key.split("::")
            left_id = parts[1].split(":")[1]
            right_id = parts[2].split(":")[1]

            # Separate data fields and metadata
            data = {k: v for k, v in combined_data.items() if k in cls.FIELDS}
            meta = {k: v for k, v in combined_data.items() if k in cls._META_FIELDS}

            associations.append({
                f"{cls._L_prefix()}_id": left_id,
                f"{cls._R_prefix()}_id": right_id,
                "data": data,
                "metadata": meta
            })

        return associations

    @classmethod
    def get_left_ids_for_right(cls, right_id: str) -> list:
        """Retrieve all left-side object IDs associated with a given right-side object."""
        left_ids = []
        pattern = f"{cls.NAME}::{cls._L_prefix()}:*::{cls._R_prefix()}:{right_id}"
        
        for key in REDIS_CLIENT.scan_iter(pattern):

            left_id = key.split("::")[1].split(":")[1]  # Extract left_id from the key
            raw_data = REDIS_CLIENT.hgetall(key)  # Retrieve metadata and fields
            
            # Separate fields and metadata
            data = {k: v for k, v in raw_data.items() if k in cls.FIELDS}
            meta = {k: v for k, v in raw_data.items() if k in cls._META_FIELDS}
            
            left_ids.append({
                f"{cls._L_prefix()}_id": left_id,
                "data": data,
                "metadata": meta
            })

        return left_ids

    @classmethod
    def get_right_ids_for_left(cls, left_id: str) -> list:
        """Retrieve all right-side object IDs associated with a given left-side object."""
        right_ids = []
        pattern = f"{cls.NAME}::{cls._L_prefix()}:{left_id}::{cls._R_prefix()}:*"
        
        for key in REDIS_CLIENT.scan_iter(pattern):
            right_id = key.split("::")[2].split(":")[1]  # Extract right_id from the key
            metadata = REDIS_CLIENT.hgetall(key)  # Retrieve metadata and fields
            
            # Separate fields and metadata
            data = {k: v for k, v in metadata.items() if k in cls.FIELDS}
            meta = {k: v for k, v in metadata.items() if k in cls._META_FIELDS}
            
            right_ids.append({
                f"{cls._R_prefix()}_id": right_id,
                "data": data,
                "metadata": meta
            })

        return right_ids

    def to_dict(self):
        """Converts the association to a dictionary for JSON serialization."""
        left_id, right_id = self.key.split("::")[1].split(":")[1], self.key.split("::")[2].split(":")[1]
        return {
            f"{self._L_prefix()}_id": left_id,
            f"{self._R_prefix()}_id": right_id,
            "data": self.data,
            "metadata": self._meta
        }
