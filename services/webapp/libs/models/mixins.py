import os
import redis
import importlib
from datetime import datetime

from typing import Union
from ddtrace import tracer

from utils import get_logger, new_id
log = get_logger(__name__)


REDIS_CLIENT = redis.Redis(
    host=os.environ.get("REDIS_HOST"),
    db=os.environ.get("REDIS_DATA_DB"),
    decode_responses=True
)


class RedisMixinMeta(type):
    """Metaclass to dynamically generate association methods for RedisMixin subclasses."""

    def __new__(cls, name, bases, dct):

        # Create the new class
        new_cls = super().__new__(cls, name, bases, dct)

        # Add association methods based on RELATED
        related = dct.get("RELATED", {}) or {}

        log.debug(f"Processing class {name} with RELATED: {related}")

        for relation_name, association_class_path in related.items():
            def make_named_manager(relation_name, association_class_path):
                def named_manager(self):
                    return AssociationManager(self, association_class_path)
                named_manager.__name__ = relation_name
                named_manager.__doc__ = f"Returns a manager for the {relation_name} association."
                return named_manager

            # Add the generated method to the class
            setattr(new_cls, relation_name, make_named_manager(relation_name, association_class_path))

        return new_cls


class RedisMixin(metaclass=RedisMixinMeta):
    """A Redis ORM Mixin that manipulates hash map (HSET) objects"""

    # To be defined in subclasses
    ID_GENERATOR    = new_id    # The ID generator to use for the class
    FIELDS          = {}        # An allowlist of fields to consider in the hash map values
    RELATED         = {}        # {"relation_name": "association_class_path", ...}

    _META_FIELDS = {"last_edited"}  # Known metadata fields

    def __init__(self, id: str, data: dict, meta: dict = None):
        self.id = id 
        self.data = data      # Object data (allowed fields)
        self._meta = meta or {}  # Object metadata (private attribute)

    def __getattr__(self, name):
        """Intercepts attribute access for keys in FIELDS."""

        if name in self.FIELDS:
            return self.data.get(name, None)
        else:
            log.warning(f"'{self.__class__.__name__}' object has no attribute '{name}'")
            return None

    def __setattr__(self, name, value):
        """Intercepts attribute setting for keys in FIELDS."""

        if name in {"id", "data", "_meta", "FIELDS", "_META_FIELDS"}:
            super().__setattr__(name, value)
        elif name in self.FIELDS:
            self.data[name] = value
        else:
            log.warning(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    @classmethod
    def _prefix(cls):
        """Returns the lowercased class name to use as key prefix."""
        return cls.__name__.lower()

    @classmethod
    def _key(cls, id: str) -> str:
        """Returns the Redis key of an object"""
        return f"{cls._prefix()}:{id}"

    @classmethod
    @tracer.wrap()
    def create(cls, **kwargs) -> "RedisMixin":
        """Creates the object in Redis using keyword arguments for data fields."""
        log.info(f"Creating {cls.__name__} with kwargs {kwargs}")

        # Separate valid and invalid fields
        data = {k: v for k, v in kwargs.items() if k in cls.FIELDS}
        invalid_fields = set(kwargs.keys()) - set(cls.FIELDS)

        # Log a warning for invalid fields
        if invalid_fields:
            log.warning(
                f"Invalid fields for {cls.__name__}: {invalid_fields}. "
                f"Allowed fields are: {cls.FIELDS}"
            )

        # Generate a unique ID and create the instance
        while True:
            id = str(cls.ID_GENERATOR())
            if not REDIS_CLIENT.exists(cls._key(id)):
                break  # Unique ID found

        instance = cls(id=id, data=data)
        instance.save()

        return instance

    @classmethod
    @tracer.wrap()
    def get(cls, id: str) -> Union["RedisMixin",  None]:
        """Retrieves the object from Redis, splitting data and meta."""
        key = cls._key(id)
        raw = REDIS_CLIENT.hgetall(key)
        
        if not raw:
            return None

        # Separate data and meta based on known fields and metadata fields
        data = {k: v for k, v in raw.items() if k in cls.FIELDS}
        meta = {k: v for k, v in raw.items() if k in cls._META_FIELDS}

        return cls(id=id, data=data, meta=meta)
    
    @classmethod
    def exist(cls, id: str) -> bool:
        """Assesses whether the object exists."""
        return REDIS_CLIENT.exists(cls._key(id))

    @tracer.wrap()
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

    @tracer.wrap()
    def delete(self) -> bool:
        """Deletes the object and all its related associations from Redis using a pipeline."""

        # Delete all related associations
        if self.RELATED:

            log.info(f"Deleting associations for {self.__class__.__name__} with ID {self.id}")
            for relation_name, association_class in self.RELATED.items():

                manager = AssociationManager(self, association_class)
                manager.remove_all()

        # Delete the object itself
        REDIS_CLIENT.delete(self._key(self.id))

        log.info(f"{self.__class__.__name__} with ID {self.id} and all related associations deleted.")
        return True

    def to_dict(self, include_related=False):
        """Converts the object to a dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "data": self.data,
            "metadata": self._meta,
        }

        if include_related and self.RELATED:
            result["relations"] = {}
            for relation_name, association_class in self.RELATED.items():
                manager = AssociationManager(self, association_class)
                result["relations"][relation_name] = manager.get()

        return result

    @classmethod
    @tracer.wrap()
    def all(cls) -> list:
        """Scans and lists all objects. """

        instances = []

        for key in REDIS_CLIENT.scan_iter(f"{cls._prefix()}:*"):
            raw = REDIS_CLIENT.hgetall(key)
            id = key.split(":")[1]  # Extract the id from the key

            # Separate data and metadata
            data = {k: v for k, v in raw.items() if k in cls.FIELDS}
            meta = {k: v for k, v in raw.items() if k in cls._META_FIELDS}

            instances.append(cls(id=id, data=data, meta=meta))

        return instances


class ManyToManyAssociationMixin:
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

    def __getattr__(self, name):
        """Intercepts attribute access for keys in FIELDS."""

        if name in self.FIELDS:
            return self.data.get(name, None)
        else:
            log.warning(f"'{self.__class__.__name__}' object has no attribute '{name}'")
            return None

    def __setattr__(self, name, value):
        """Intercepts attribute setting for keys in FIELDS."""

        if name in {"key", "data", "_meta", "FIELDS", "_META_FIELDS"}:
            super().__setattr__(name, value)
        elif name in self.FIELDS:
            self.data[name] = value
        else:
            log.warning(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    @classmethod
    @tracer.wrap()
    def create(cls, left_id: str, right_id: str, **kwargs) -> "ManyToManyAssociationMixin":
        """Creates an association instance."""
        log.info(f"Creating association between {cls.L_CLASS.__name__}:{left_id} and {cls.R_CLASS.__name__}:{right_id} with kwargs {kwargs}")

        # Separate valid and invalid fields
        data = {k: v for k, v in kwargs.items() if k in cls.FIELDS}
        invalid_fields = set(kwargs.keys()) - set(cls.FIELDS)

        if invalid_fields:
            log.warning(
                f"Invalid fields for association between {cls.L_CLASS.__name__}:{left_id} and {cls.R_CLASS.__name__}:{right_id}: {invalid_fields}. "
                f"Allowed fields are: {cls.FIELDS}"
            )

        # Create the association
        key = cls._key(left_id, right_id)
        instance = cls(key, data=data)
        instance.save()

        return instance


    @classmethod
    @tracer.wrap()
    def get(cls, left_id: str, right_id: str) -> Union["ManyToManyAssociationMixin", None]:
        """Retrieves the association, splitting fields and metadata."""
        key = cls._key(left_id, right_id)
        raw = REDIS_CLIENT.hgetall(key)

        if not raw:
            return None

        # Split combined_data into fields and metadata
        data = {k: v for k, v in raw.items() if k in cls.FIELDS}
        meta = {k: v for k, v in raw.items() if k in cls._META_FIELDS}

        return cls(key=key, data=data, meta=meta)

    @tracer.wrap()
    def save(self):

        """Saves the association's data fields and metadata to Redis."""
        self._meta["last_edited"] = datetime.utcnow().isoformat()

        # Combine data and metadata for storage
        combined_data = {**self.data, **self._meta}
        REDIS_CLIENT.hset(self.key, mapping=combined_data)

        log.info(f"Association with key {self.key} saved with data {self.data} and metadata {self._meta}")
        return self

    @tracer.wrap()
    def delete(self) -> bool:
        """Deletes the association from Redis."""
        REDIS_CLIENT.delete(self.key)
        log.info(f"Association removed: {self.key}")
        return True

    @classmethod
    @tracer.wrap()
    def all(cls) -> list:
        """Lists all associations with data fields and metadata as JSON-serializable dictionaries."""
        associations = []
        pattern = f"{cls.NAME}::{cls._L_prefix()}:*::{cls._R_prefix()}:*"

        for key in REDIS_CLIENT.scan_iter(pattern):
            raw = REDIS_CLIENT.hgetall(key)
            parts = key.split("::")
            left_id = parts[1].split(":")[1]
            right_id = parts[2].split(":")[1]

            # Separate data fields and metadata
            data = {k: v for k, v in raw.items() if k in cls.FIELDS}
            meta = {k: v for k, v in raw.items() if k in cls._META_FIELDS}

            association = cls(cls._key(left_id, right_id), data=data, meta=meta)

            associations.append( association.to_dict() )

        return associations

    @classmethod
    def all_lefts(cls, right_id: str) -> list:
        """Retrieve all left-side objects associated with a given right-side object."""

        lefts = {}
        pattern = f"{cls.NAME}::*::{cls._R_prefix()}:{right_id}"
        
        for key in REDIS_CLIENT.scan_iter(pattern):

            left_id = key.split("::")[1].split(":")[1]

            # Fetch raw data from Redis
            raw_a = REDIS_CLIENT.hgetall(key)
            if not raw_a:
                log.warning(f"No data found for key {key}")
                continue

            # Extract association attributes
            data   = {k: v for k, v in raw_a.items() if k in cls.FIELDS}
            meta   = {k: v for k, v in raw_a.items() if k in cls._META_FIELDS}
            association = cls(key, data=data, meta=meta)

            # Store left-side object along with association attributes
            lefts[left_id] = association

        return lefts

    @classmethod
    def all_rights(cls, left_id: str) -> list:
        """Retrieve all right-side object IDs associated with a given left-side object."""

        rights = {}
        pattern = f"{cls.NAME}::{cls._L_prefix()}:{left_id}::{cls._R_prefix()}:*"
        
        for key in REDIS_CLIENT.scan_iter(pattern):

            right_id = key.split("::")[2].split(":")[1]

            # Fetch raw data from Redis
            raw = REDIS_CLIENT.hgetall(key)
            if not raw:
                log.warning(f"No data found for key {key}")
                continue

            # Extract association attributes
            data    = {k: v for k, v in raw.items() if k in cls.FIELDS}
            meta    = {k: v for k, v in raw.items() if k in cls._META_FIELDS}
            association  = cls(key, data=data, meta=meta)

            # Store left-side object along with association attributes
            rights[right_id] = association

        return rights

    def to_dict(self):
        """Converts the association to a dictionary for JSON serialization."""
        left_id, right_id = self.key.split("::")[1].split(":")[1], self.key.split("::")[2].split(":")[1]
        return {
            "ids": 
            {
                f"{self._L_prefix()}_id": left_id,
                f"{self._R_prefix()}_id": right_id
            },
            "data": self.data,
            "metadata": self._meta
        }


class OneToManyAssociationMixin(ManyToManyAssociationMixin):
    """Adds logic to handle 1(left):many(right) associations"""

    @classmethod
    @tracer.wrap()
    def create(cls, left_id: str, right_id: str, **kwargs) -> "ManyToManyAssociationMixin":
        """Creates an association instance, enforcing 1:n relationship"""

        existing = cls.all_lefts(right_id)
        if existing:
            raise ValueError(f"{cls.R_CLASS.__name__} with ID {right_id} is already associated with {cls.L_CLASS.__name__} with ID {existing[0]['id']}.")

        return super().create(left_id, right_id, **kwargs)


class AssociationManager:
    """An abstract manager for handling associations between two RedisMixin classes."""

    def __init__(self, instance, association_class):
        """
        Initializes the manager for handling associations.

        Args:
            instance: The instance of the calling object (e.g., User or Code).
            association_class: The association class that defines the relationship (e.g., UserCode).
        """
        self.instance = instance
        self.association_class = self._resolve_class(association_class)

        # Determine the related class based on _L_CLASS and _R_CLASS
        if isinstance(instance, self.association_class.L_CLASS):
            self.side = 'left'
            self.related_class = self.association_class.R_CLASS
            self.all_related = self.association_class.all_rights
        elif isinstance(instance, self.association_class.R_CLASS):
            self.side = 'right'
            self.related_class = self.association_class.L_CLASS
            self.all_related = self.association_class.all_lefts
        else:
            raise ValueError(f"{instance.__class__.__name__} is not valid for this association.")

    def _resolve_class(self, class_ref):
        """Resolve a class reference given as a string or class object."""
        if isinstance(class_ref, str):
            module_name, class_name = class_ref.rsplit(".", 1)
            module = importlib.import_module(module_name)
            return getattr(module, class_name)
        return class_ref

    @tracer.wrap()
    def add(self, related_id: str, **data):
        """Adds an association between the instance and a related object."""

        if self.side == 'left':
            self.association_class.create(self.instance.id, related_id, **data)
        else:
            self.association_class.create(related_id, self.instance.id, **data)
        
        return self.instance

    @tracer.wrap()
    def remove(self, related_id: str):
        """Removes the association between the left instance and an related object."""
        if self.side == 'left':
            association = self.association_class.get(self.instance.id, related_id)
        else:
            association = self.association_class.get(related_id, self.instance.id)

        if association:
            association.delete()

        return self.instance

    @tracer.wrap()
    def remove_all(self):
        """
        Removes all associations for the instance.
        """

        log.info(f"Removing all associations for {self.instance.__class__.__name__} with ID {self.instance.id}")
        associations = self.all()

        for related_id in associations:
            self.remove(related_id)

        return self.instance

    @tracer.wrap()
    def all(self) -> list:
        """Retrieves all associations for the left instance."""

        return self.all_related(self.instance.id)

    @tracer.wrap()
    def get(self, key):
        """
        Retrieves an associated object by ID.

        Args:
            key: The ID of the associated object to retrieve.
            default: The value to return if the key doesn't exist.

        Returns:
            A tuple (object, association) if found, or the default value if not.
        """

        associations = self.all()
        try:
            return self.related_class.get(key), associations[key]
        except KeyError:
            log.debug(
                f"Key {key} not found in associations for {self.instance.id}. "
                f"Available keys: {list(associations.keys())}"
            )
            return None, None
