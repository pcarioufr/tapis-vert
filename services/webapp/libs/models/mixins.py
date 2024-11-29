import os
import redis
import importlib

from ddtrace import tracer

import utils
log = utils.get_logger(__name__)


REDIS_CLIENT = redis.Redis(
    host=os.environ.get("REDIS_HOST"),
    db=os.environ.get("REDIS_DATA_DB"),
    decode_responses=True
)


## OBJECTS ###### ###### ###### ###### ###### ###### ###### ###### ###### ######

class ObjectMixinMeta(type):
    """Metaclass to dynamically generate relation methods for ObjectMixin subclasses."""

    def __new__(cls, name, bases, dct):
        log.debug(f"Creating class {name} with ObjectMixinMeta")
        new_cls = super().__new__(cls, name, bases, dct)

        # Add relation methods for LEFTS
        lefts = dct.get("LEFTS", {}) or {}
        for relation_name, relation_class_path in lefts.items():
            log.debug(f"Adding leftwards relation method {relation_name} for class {name}")
            setattr(new_cls, relation_name, cls._create_manager(relation_name, relation_class_path, LeftwardsRelationManager))

        # Add relation methods for RIGHTS
        rights = dct.get("RIGHTS", {}) or {}
        for relation_name, relation_class_path in rights.items():
            log.debug(f"Adding rightwards relation method {relation_name} for class {name}")
            setattr(new_cls, relation_name, cls._create_manager(relation_name, relation_class_path, RightwardsRelationManager))

        return new_cls

    @staticmethod
    def _create_manager(relation_name, relation_class_path, manager_class):
        """Helper to create and return a manager function with captured variables."""
        def named_manager(self):
            return manager_class(self, relation_class_path)
        named_manager.__name__ = relation_name
        named_manager.__doc__ = f"Returns a manager for the {relation_name} relation."
        return named_manager


class ObjectMixin(metaclass=ObjectMixinMeta):
    """A Redis ORM Mixin that manipulates hash map (HSET) objects"""

    # To be defined in subclasses
    ID_GENERATOR    = utils.new_id  # The ID generator to use for the class
    FIELDS          = {}            # An allowlist of fields to consider in the hash map values
    LEFTS           = {}            # Leftwards relations {"relation_name": "relation_class_path", ...}
    RIGHTS          = {}            # Rightwards relations {"relation_name": "relation_class_path", ...}

    META_FIELDS = {"_created", "_edited"}  # Known metadata fields

    def __init__(self, id: str, data: dict, meta: dict = None):
        self.id = id
        self.data = data  # Object data (allowed fields)
        self.meta = meta or {}  # Object metadata (private attribute)

    def __getattr__(self, name):
        """Intercepts attribute access for keys in FIELDS."""

        if name in self.FIELDS:
            return self.data.get(name, None)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        """Intercepts attribute setting for keys in FIELDS."""

        if name in {"id", "data", "meta", "_relation_managers", "FIELDS", "META_FIELDS"}:
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
    @tracer.wrap("ObjectMixin.create")
    def create(cls, **kwargs) -> "ObjectMixin":
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
        instance.meta["_created"] = utils.now()
        instance.save()

        return instance

    @classmethod
    def exist(cls, id: str) -> bool:
        """Assesses whether the object exists."""
        return REDIS_CLIENT.exists(cls._key(id))

    @classmethod
    @tracer.wrap("ObjectMixin.get")
    def get(cls, id: str) -> "ObjectMixin":
        """Retrieves the object from Redis, splitting data and meta."""
        key = cls._key(id)
        raw = REDIS_CLIENT.hgetall(key)
        
        if not raw:
            return None

        # Separate data and meta based on known fields and metadata fields
        data = {k: v for k, v in raw.items() if k in cls.FIELDS}
        meta = {k: v for k, v in raw.items() if k in cls.META_FIELDS}

        return cls(id=id, data=data, meta=meta)
    
    @tracer.wrap("ObjectMixin.save")
    def save(self) -> "ObjectMixin":
        """Saves the object current state into Redis."""

        key = self._key(self.id)

        # Prepare data and metadata for storage
        data = {k: v for k, v in self.data.items() if k in self.FIELDS}
        
        # Update metadata (e.g., timestamp for 'last_edited')
        self.meta["_edited"] = utils.now()

        # Combine data and metadata for saving in Redis
        combined_data = {**data, **self.meta}
        REDIS_CLIENT.hset(key, mapping=combined_data)

        log.info(f"{self.__class__.__name__} with ID {self.id} updated: {data} (metadata {self.meta})")
        return self

    @tracer.wrap("ObjectMixin.delete")
    def delete(self) -> bool:
        """Deletes the object and all its related relations from Redis using a pipeline."""

        # Delete all related relations
        if self.LEFTS:

            log.info(f"Deleting relations for {self.__class__.__name__} with ID {self.id}")
            for relation_name, relation_class in self.LEFTS.items():

                manager =LeftwardsRelationManager(self, relation_class)
                manager.remove_all()

        # Delete all related relations
        if self.RIGHTS:

            log.info(f"Deleting relations for {self.__class__.__name__} with ID {self.id}")
            for relation_name, relation_class in self.RIGHTS.items():

                manager = RightwardsRelationManager(self, relation_class)
                manager.remove_all()


        # Delete the object itself
        REDIS_CLIENT.delete(self._key(self.id))

        log.info(f"{self.__class__.__name__} with ID {self.id} and all related relations deleted.")
        return True

    @tracer.wrap("ObjectMixin.to_dict")
    def to_dict(self, include_related=False):
        """Converts the object to a dictionary for JSON serialization."""
        result = {
            "id": self.id,
            **self.meta,
            **self.data
        }

        if include_related:
            
            if self.LEFTS:

                for relation_name, relation_class in self.LEFTS.items():
                    manager = LeftwardsRelationManager(self, relation_class)
                    
                    lefts = manager.all()
                    result[relation_name] = []

                    for object_id, relation in lefts.items():
                        result[relation_name].append(relation.left_to_dict())


            if self.RIGHTS:
                for relation_name, relation_class in self.RIGHTS.items():
                    manager = RightwardsRelationManager(self, relation_class)

                    rights = manager.all()
                    result[relation_name] = []

                    for object_id, relation in rights.items():
                        result[relation_name].append(relation.right_to_dict())

        return result

    @classmethod
    @tracer.wrap("ObjectMixin.all")
    def all(cls, cursor=0, count=1000) -> tuple[list["ObjectMixin"], int]:
        """
        Retrieves a batch of objects from Redis using pagination.

        Args:
            cursor: The starting cursor for the SCAN operation. Pass 0 to start from the beginning.

        Returns:
            - A list of ObjectMixins in the current batch.
            - The cursor for the next batch (0 if all results have been retrieved).
        """
        instances = []

        pattern = f"{cls._prefix()}:*"
        cursor, keys = REDIS_CLIENT.scan(cursor=cursor, match=pattern, count=1000)

        for key in keys:
            raw = REDIS_CLIENT.hgetall(key)
            id = key.split(":")[1]  # Extract the id from the key

            # Separate data and metadata
            data = {k: v for k, v in raw.items() if k in cls.FIELDS}
            meta = {k: v for k, v in raw.items() if k in cls.META_FIELDS}

            instances.append(cls(id=id, data=data, meta=meta))

        return instances, cursor


## ASSOCIATIONS ###### ###### ###### ###### ###### ###### ###### ###### ###### ######


class RelationMixin():
    """
    A class for managing n:m relationships with data fields and metadata in Redis.
    Assumes no more than one relation can exist between 2 instances
    """

    RELATION_TYPE = "many_to_many"  # or "one_to_many"

    L_CLASS = None   # Left-side class (e.g., Room)
    R_CLASS = None   # Right-side class (e.g., User)
    NAME = "left:linksto:right"  # Name of the relation for key generation

    FIELDS = None    # Relation-specific data fields (e.g., "role")
    META_FIELDS = {"_created", "_edited"}  # Metadata fields only

    def __init__(self, key: str, data: dict, meta: dict = None):

        self.key        = key
        self.data       = data
        self.meta      = meta or {}

    def __getattr__(self, name):
        """Intercepts attribute access for keys in FIELDS."""

        if name in self.FIELDS:
            return self.data.get(name, None)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        """Intercepts attribute setting for keys in FIELDS."""

        if name in {"key", "left_id", "right_id", "data", "meta", "FIELDS", "META_FIELDS"}:
            super().__setattr__(name, value)
        elif name in self.FIELDS:
            self.data[name] = value
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    ## HELPERS ##### ##### ##### ##### ##### 

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
        """Generate the Redis key for a relation between two objects (used in one-to-many)."""
        return f"{cls.NAME}::{cls._L_prefix()}:{left_id}::{cls._R_prefix()}:{right_id}"
    
    @classmethod
    def _exist_parent(cls, right_id: str) -> "RelationMixin":
        """Retrieve the relation for a given right-side object (used in one-to-many)."""
        pattern = f"{cls.NAME}::*::{cls._R_prefix()}:{right_id}"

        for key in REDIS_CLIENT.scan_iter(pattern):
            raw = REDIS_CLIENT.hgetall(key)
            if raw:
                return True
        return False

    ## ##### ##### ##### ##### ##### #####

    @classmethod
    @tracer.wrap("RelationMixin.create")
    def create(cls, left_id: str, right_id: str, **kwargs) -> "RelationMixin":

        """Creates a relation instance."""
        log.info(f"Creating relation between {cls.L_CLASS.__name__}:{left_id} and {cls.R_CLASS.__name__}:{right_id} with kwargs {kwargs}")

        if cls.L_CLASS.get(left_id) is None:
            raise ValueError(f"{cls.L_CLASS}:{left_id} does not exist.")
        
        if cls.R_CLASS.get(right_id) is None:
            raise ValueError(f"{cls.L_CLASS}:{left_id} does not exist.")

        # Enforce cardinality constraints
        if cls.RELATION_TYPE == "one_to_many":
            # Ensure the right-side object is not already linked

            if cls._exist_parent(right_id):
                raise ValueError(
                    f"{cls.R_CLASS.__name__}:{right_id} is already linked to a {cls.L_CLASS.__name__} - skipping association"
                )

        # Separate valid and invalid fields
        data = {k: v for k, v in kwargs.items() if k in cls.FIELDS}
        invalid_fields = set(kwargs.keys()) - set(cls.FIELDS)

        if invalid_fields:
            log.warning(
                f"Invalid fields for relation between {cls.L_CLASS.__name__}:{left_id} and {cls.R_CLASS.__name__}:{right_id}: {invalid_fields}. "
                f"Allowed fields are: {cls.FIELDS}"
            )

        # Create the relation
        key = cls._key(left_id, right_id)
        relation = cls(key, data=data)

        relation.meta["_created"] = utils.now()
        relation.save()

        return relation

    @classmethod
    def exist(cls, left_id: str, right_id: str) -> bool:
        """Assesses whether the relation exists."""

        return REDIS_CLIENT.exists(cls._key(left_id, right_id))

    @classmethod
    @tracer.wrap("RelationMixin.get")
    def get(cls, left_id: str, right_id: str) -> "RelationMixin":
        """Retrieves the relation, splitting fields and metadata."""

        key = cls._key(left_id, right_id)
        raw = REDIS_CLIENT.hgetall(key)

        if not raw:
            log.info(f"No match for relation {cls.__name__} with key {key}")
            return None

        # Split combined_data into fields and metadata
        data = {k: v for k, v in raw.items() if k in cls.FIELDS}
        meta = {k: v for k, v in raw.items() if k in cls.META_FIELDS}

        return cls(key=key, data=data, meta=meta)
    

    @tracer.wrap("RelationMixin.save")
    def save(self) -> "RelationMixin":
        """Saves the relation's data fields and metadata to Redis."""
        self.meta["_edited"] = utils.now()

        # Combine data and metadata for storage
        combined_data = {**self.data, **self.meta}
        REDIS_CLIENT.hset(self.key, mapping=combined_data)

        log.info(f"Relation with key {self.key} saved with data {self.data} and metadata {self.meta}")
        return self

    @tracer.wrap("RelationMixin.delete")
    def delete(self) -> bool:
        """Deletes the relation from Redis."""
        REDIS_CLIENT.delete(self.key)
        log.info(f"Relation removed: {self.key}")
        return True

    @classmethod
    @tracer.wrap("RelationMixin.all")
    def all(cls, cursor=0) -> list["RelationMixin"]:
        """
        Retrieves a batch of relations from Redis using pagination.

        Args:
            cursor: The starting cursor for the SCAN operation. Pass 0 to start from the beginning.

        Returns:
            - A list of ObjectMixins in the current batch.
            - The cursor for the next batch (0 if all results have been retrieved).
        """

        relations = []
        pattern = f"{cls.NAME}::{cls._L_prefix()}:*::{cls._R_prefix()}:*"

        cursor, keys = REDIS_CLIENT.scan(cursor=cursor, match=pattern, count=1000)

        for key in REDIS_CLIENT.scan_iter(pattern):
            raw = REDIS_CLIENT.hgetall(key)
            parts = key.split("::")
            left_id = parts[1].split(":")[1]
            right_id = parts[2].split(":")[1]

            # Separate data fields and metadata
            data = {k: v for k, v in raw.items() if k in cls.FIELDS}
            meta = {k: v for k, v in raw.items() if k in cls.META_FIELDS}

            relation = cls(cls._key(left_id, right_id), data=data, meta=meta)

            relations.append( relation.to_dict() )

        return relations

    @tracer.wrap("RelationMixin.to_dict")
    def to_dict(self):
        """Converts the relation to a dictionary for JSON serialization."""

        left_id, right_id = self.key.split("::")[1].split(":")[1], self.key.split("::")[2].split(":")[1]

        result = {
            f"{self._L_prefix()}": self.L_CLASS.get(left_id).to_dict(False),
            f"{self._R_prefix()}": self.R_CLASS.get(right_id).to_dict(False),
            **self.meta,
            **self.data
        }
    
        return result

    @tracer.wrap("RelationMixin.left")
    def left(self):
        """Returns the left-side object of the relation"""

        left_id = self.key.split("::")[1].split(":")[1]
        return self.L_CLASS.get(left_id)

    @tracer.wrap("RelationMixin.left_to_dict")
    def left_to_dict(self):
        """Returns the relation alongside its left-side object for JSON serialization."""

        left_id = self.key.split("::")[1].split(":")[1]

        result = self.L_CLASS.get(left_id).to_dict(False)
        result ["relation"] = self.meta | self.data
    
        return result

    @tracer.wrap("RelationMixin.right")
    def right(self):
        """Returns the right-side object of the relation"""

        right_id = self.key.split("::")[2].split(":")[1]
        return self.R_CLASS.get(right_id)

    @tracer.wrap("RelationMixin.right_to_dict")
    def right_to_dict(self):
        """Returns the relation alongside its right-side object for JSON serialization."""

        right_id = self.key.split("::")[2].split(":")[1]

        result = self.R_CLASS.get(right_id).to_dict(False)
        result ["relation"] = self.meta | self.data
    
        return result

    @classmethod
    @tracer.wrap("RelationMixin.lefts")
    def lefts(cls, right_id: str) -> dict[str, "RelationMixin"]:
        """Retrieve all leftwards relations with a given right-side object."""

        lefts = {}
        pattern = f"{cls.NAME}::*::{cls._R_prefix()}:{right_id}"
        
        for key in REDIS_CLIENT.scan_iter(pattern):

            left_id = key.split("::")[1].split(":")[1]

            # Fetch raw data from Redis
            raw_a = REDIS_CLIENT.hgetall(key)
            if not raw_a:
                log.warning(f"No data found for key {key}")
                continue

            # Extract relation attributes
            data   = {k: v for k, v in raw_a.items() if k in cls.FIELDS}
            meta   = {k: v for k, v in raw_a.items() if k in cls.META_FIELDS}
            relation = cls(key, data=data, meta=meta)

            # Store left-side object along with relation attributes
            lefts[left_id] = relation

        return lefts

    @classmethod
    @tracer.wrap("RelationMixin.rights")
    def rights(cls, left_id: str) -> dict[str, "RelationMixin"]:
        """Retrieve all rightwards relations with a given left-side object."""

        rights = {}
        pattern = f"{cls.NAME}::{cls._L_prefix()}:{left_id}::{cls._R_prefix()}:*"
        
        for key in REDIS_CLIENT.scan_iter(pattern):

            right_id = key.split("::")[2].split(":")[1]

            # Fetch raw data from Redis
            raw = REDIS_CLIENT.hgetall(key)
            if not raw:
                log.warning(f"No data found for key {key}")
                continue

            # Extract relation attributes
            data    = {k: v for k, v in raw.items() if k in cls.FIELDS}
            meta    = {k: v for k, v in raw.items() if k in cls.META_FIELDS}
            relation  = cls(key, data=data, meta=meta)

            # Store left-side object along with relation attributes
            rights[right_id] = relation

        return rights


class RelationManager():
    """An abstract manager for handling relations between two ObjectMixin classes."""

    def __init__(self, instance, relation_class):

        if type(self) is RelationManager:
            raise TypeError("RelationManager cannot be instantiated directly. Subclass it instead.")

        self.instance = instance

        module_name, class_name = relation_class.rsplit(".", 1)
        module = importlib.import_module(module_name)
        self.relation_class = getattr(module, class_name)


    def all(self) -> dict[str, RelationMixin]:
        """Retrieves all relations for the instance, indexed with their object ID"""

        if type(self) is RelationManager:
            raise TypeError("RelationManager.all() is abstract. Use subclass it instead.")


    def add(self, related_id: str, **data) -> ObjectMixin:
        """Adds a relation between the instance and a related object."""

        if type(self) is RelationManager:
            raise TypeError("RelationManager.add() is abstract. Use subclass it instead.")

    def remove(self, related_id: str) -> ObjectMixin:
        """Removes the relation the instance and a related object."""

        if type(self) is RelationManager:
            raise TypeError("RelationManager.remove() is abstract. Use subclass it instead.")

    @tracer.wrap("RelationManager.remove_all")
    def remove_all(self) -> ObjectMixin:
        """Removes all relations for the instance."""

        log.info(f"Removing all relations for {self.instance.__class__.__name__} with ID {self.instance.id}")
        related = self.all()

        for related_id in related:
            self.remove(related_id)

        return self.instance

    def get(self, related_id: str) -> tuple[ObjectMixin, RelationMixin] :
        """ Retrieves a related object and its relation to the instance by its ID."""

        if type(self) is RelationManager:
            raise TypeError("RelationManager.get() is abstract. Use subclass it instead.")

    def exists(self, related_id: str) -> bool :
        """ Retrieves if a relation exists between instance with related object"""

        if type(self) is RelationManager:
            raise TypeError("RelationManager.exists() is abstract. Use subclass it instead.")

    def first(self) -> tuple[ObjectMixin, RelationMixin] :
        """ Retrieves the first related object and its relation to the instance by its ID."""

        if type(self) is RelationManager:
            raise TypeError("RelationManager.remove() is abstract. Use subclass it instead.")

    @tracer.wrap("RelationManager.set")
    def set(self, related_id: str, **kwargs) -> tuple[ObjectMixin, RelationMixin] :
        """ Sets properties of the relation of with related object."""

        obj, rel = self.get(related_id)
        if rel:
            for key, value in kwargs.items():
                rel.__setattr__(key, value)
                rel.save()

        return obj, rel            


class RightwardsRelationManager(RelationManager):
    """Manages relations where the instance is the left-side object."""

    def __init__(self, instance, relation_class):

        log.debug(f"Initializing RightwardsRelationManager with instance {instance} and relation_class {relation_class}")
        super().__init__(instance, relation_class)

    @tracer.wrap("RightwardsRelationManager.all")
    def all(self):
        return self.relation_class.rights(self.instance.id)

    @tracer.wrap("RightwardsRelationManager.add")
    def add(self, related_id: str, **data):
        self.relation_class.create(self.instance.id, related_id, **data)
        return self.instance

    @tracer.wrap("RightwardsRelationManager.remove")
    def remove(self, related_id: str):
        relation = self.relation_class.get(self.instance.id, related_id)
        if relation:
            relation.delete()
        return self.instance

    @tracer.wrap("RightwardsRelationManager.get")
    def get(self, related_id) :
        
        bool = self.relation_class.exist(self.instance.id, related_id)
        if bool:
            rel = self.relation_class.get(self.instance.id, related_id)
            obj = self.relation_class.R_CLASS.get(related_id)
            return obj, rel
        else: 
            return None, None

    @tracer.wrap("RightwardsRelationManager.exist")
    def exist(self, related_id: str, **data):

        bool = self.relation_class.exist(self.instance.id, related_id)
        return bool

    @tracer.wrap("RightwardsRelationManager.first")
    def first(self) :
        
        for related_id, relation in self.all().items():
            return relation.right(), relation


class LeftwardsRelationManager(RelationManager):
    """Manages relations where the instance is the right-side object."""

    def __init__(self, instance, relation_class):

        log.debug(f"Initializing LeftwardsRelationManager with instance {instance} and relation_class {relation_class}")
        super().__init__(instance, relation_class)

    @tracer.wrap("LeftwardsRelationManager.all")
    def all(self):
        return self.relation_class.lefts(self.instance.id)

    @tracer.wrap("LeftwardsRelationManager.add")
    def add(self, related_id: str, **data):
        self.relation_class.create(related_id, self.instance.id, **data)
        return self.instance

    @tracer.wrap("LeftwardsRelationManager.remove")
    def remove(self, related_id: str):
        relation = self.relation_class.get(related_id, self.instance.id)
        if relation:
            relation.delete()
        return self.instance

    @tracer.wrap("LeftwardsRelationManager.get")
    def get(self, related_id) :
        
        bool = self.relation_class.exist(related_id, self.instance.id)
        if bool:
            rel = self.relation_class.get(related_id, self.instance.id)
            obj = self.relation_class.L_CLASS.get(related_id)
            return obj, rel
        else: 
            return None, None

    @tracer.wrap("RightwardsRelationManager.exist")
    def exist(self, related_id: str, **data):

        bool = self.relation_class.exist(related_id, self.instance.id)
        return bool

    @tracer.wrap("LeftwardsRelationManager.first")
    def first(self):
        
        for related_id, relation in self.all().items():
            return relation.left(), relation