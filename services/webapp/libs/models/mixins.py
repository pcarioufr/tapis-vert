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

# After how many seconds objects set for deletion actually get deleted
DEL_EXPIRE = 60 # 1 min

class ConflictError(Exception):
    """Exception raised when a concurrent modification is detected during save."""
    pass


class RedisMixin():
    """A Redis ORM Mixin that manipulates hash map (HSET) objects"""

    FIELDS          = {}

    META_FIELDS     = {"_created", "_edited", "_version"}  # metadata fields


    def __init__(self, key: str, data: dict, meta: dict):

        if type(self) is RedisMixin:
            raise TypeError("RedisMixin.__init__() is abstract. Call subclass' instead.")

        self.key = key

        self.data = {}
        for field in self.FIELDS:
            self.__setattr__(field, data.get(field, None))

        self.meta = {}
        for field in self.META_FIELDS:
            self.__setattr__(field, meta.get(field, None))


    def __getattr__(self, field):
        """Intercepts attribute access for keys in FIELDS & META_FIELDS."""

        if field in self.FIELDS:
            return self.data.get(field)

        elif field in self.META_FIELDS:
            return self.meta.get(field)

        else:
            raise AttributeError(f"{self.__class__.__name__}.{field} does not exist.")

    def __setattr__(self, field, value):
        """Intercepts attribute setting for keys in FIELDS & META_FIELDS."""

        if field in self.FIELDS:
            self.data[field] = value

        elif field in self.META_FIELDS:
            self.meta[field] = value

        elif field in {"key", "data", "meta"}:
            return super().__setattr__(field, value)

        else:
            raise AttributeError(f"{self.__class__.__name__}.{field} does not exist.")

    @classmethod
    @tracer.wrap("RedisMixin.create")
    def create(cls, key, **kwargs) -> "RedisMixin":
        """
        Creates a new instance in Redis using keyword arguments for data fields.
        Args:
            - key: The Redis key to use - should not already exist
            - kwargs: field (withing FIELDS) to update with their values
        Returns:
            - The created object
        """

        log.info(f"Creating {cls.__name__} with kwargs {kwargs}")

        # Check for invalid fields
        invalid_fields = {k for k in kwargs if k not in cls.FIELDS }
        if invalid_fields:
            raise AttributeError(f"Invalid fields for {cls.__name__}: {invalid_fields}")


        instance = cls(key=key, data=dict(kwargs), meta={})
        instance._created = utils.now()
        instance._version = -1

        if REDIS_CLIENT.exists(key):
            raise ConflictError(f"{cls.__name__}.create: {key} already exists")

        instance.save()

        return instance

    @classmethod
    @tracer.wrap("RedisMixin.exist")
    def exists(cls, key: str) -> bool:
        """Assesses whether the instance with key exists, or isn't mark for deletion."""

        with REDIS_CLIENT.pipeline() as pipe:

            pipe.exists(key)
            pipe.hget(key, "_deleted")

            test_exists, test_deleted = pipe.execute()

        return bool(test_exists) and not test_deleted

    @classmethod
    @tracer.wrap("RedisMixin.get")
    def get(cls, key: str) -> "RedisMixin":
        """
        Retrieves the object from Redis.
        Args
            - key: The Redis key of the object to retrive
        Returns:
            - The object, or None
        """

        # retrieve data
        raw = REDIS_CLIENT.hgetall(key)
        
        # check if object (still) exists
        if not raw:
            log.warning(f"No match for {cls.__name__} with key {key}")
            return None
        if raw.get("_deleted"):
            log.warning(f"{cls.__name__} with key {key} marked for deletion. Returning None")
            return None

        # retrieve data
        data = {}

        for field, value in raw.items() :

            data.update(utils.unflatten({k: v for k, v in raw.items() if k not in cls.META_FIELDS}))


        meta = {k: v for k, v in raw.items() if k in cls.META_FIELDS }

        return cls(key=key, data=data, meta=meta)
    
    @tracer.wrap("RedisMixin.save")
    def save(self) -> "RedisMixin":
        """
        Saves the instance (data and metadata fields) to Redis using optimistic locking.
        Raises an exception if concurrent edits have been made (version change), or are being made (watch) 
        """

        try:

            with REDIS_CLIENT.pipeline() as pipe:

                # watch for concurrent edits
                pipe.watch(self.key)

                pipe.multi()

                # fetch current version within the pipeline
                version_ref = REDIS_CLIENT.hget(self.key, "_version")
                version_ref = int(version_ref) if version_ref else -1
                version_self = int(self._version)

                if version_ref != version_self:
                    raise ConflictError(f"Version mismatch: on server {version_ref}{type(version_ref)}, on instance {version_self}{type(version_self)}.")

                # flush existing fields - specifically matters for dictionary values
                existing_fields = REDIS_CLIENT.hkeys(self.key)
                for field in self.FIELDS:
                    subkeys = [k for k in existing_fields if k.startswith(f"{field}.")]
                    if subkeys:
                        pipe.hdel(self.key, *subkeys)


                # data & metadata update
                mapping = {}

                # prepare data
                flattened = utils.flatten(self.data)
                for k, v in flattened.items():
                     mapping[k] = '' if v is None else v

                # prepare metadata
                self._edited = utils.now()
                self._version = int(self._version) + 1
                mapping.update(self.meta)

                pipe.hset(self.key, mapping=mapping)

                # push the update
                pipe.execute()

        except redis.WatchError:
            log.error(f"Concurrent edit detected for key {self.key}, aborting.")
            raise ConflictError("Concurrent edit detected, aborting.")

        log.info(f"{self.__class__.__name__} with key {self.key} saved: {self.data} (metadata {self.meta})")
        return self.get(self.key)

    @tracer.wrap("RedisMixin.delete")
    def delete(self) -> bool:
        """
        Deletes the object and all its related relations from Redis using a pipeline.
        Soft delete, to absorb concurrent changes (that would revive they Redis key otherwise)
        Hard delete after a buffer period of time (through Redis Expire), when no concurrent changes may happen anymore 
        """

        with REDIS_CLIENT.pipeline() as pipe:
            pipe.expire(self.key, DEL_EXPIRE)
            pipe.hset(self.key, "_deleted", utils.now())
            pipe.execute()

        log.info(f"{self.__class__.__name__} with key {self.key} and all related relations deleted.")
        return True

    @classmethod
    @tracer.wrap("RedisMixin.patch")
    def patch(cls, key: str, field: str, value) -> bool:
        """
        Lower-latency update, targetting a single FIELD values.
        No conflict prevention (the last update wins), although will never revive a deleted subkey
        Args:
            - key: The Redis key of the object to patch
            - field: field to update  
              for dictionary fields, use nested syntax: field.subkey, field.subkey.subsubkey, etc.
            - value: updated value to set. 

        Returns:
            - The True/False, whether the object was patched or not
              TODO: return object instead
        """

        if not RedisMixin.exists.__func__(cls, key):
            log.warning(f"{cls.__class__} > {key} deleted, skipping patch") 
            return False


        with REDIS_CLIENT.pipeline() as pipe:

            pipe.multi()

            if REDIS_CLIENT.hexists(key, field):
                pipe.hset(key, field, value)
            else:
                raise ConflictError(f"'{cls.__name__}' object has no attribute '{field}'")

            pipe.hincrby(key, "_version", 1)
            pipe.hset(key, "_edited", utils.now())
            pipe.execute()

            log.info(f"Patched {field}:{value} for {key}")

        return True


    @classmethod
    @tracer.wrap("ObjectMixin.search")
    def search(cls, pattern="*", cursor=0, count=1000) -> tuple[list["ObjectMixin"], int]:
        """
        Retrieves a batch of objects matching key pattern, using pagination.
        Args:
            - pattern: The search pattern for Redis keys
            - cursor: The starting cursor for the SCAN operation. Pass 0 to start from the beginning.
            - count: How many results to retrieve in search
        Returns:
            - A list of ObjectMixins in the current batch.
            - The cursor for the next batch (0 if all results have been retrieved).
        """

        if type(cls) is ObjectMixin:
            raise TypeError("ObjectMixin.search() is abstract. Call subclass' instead.")

        instances = []

        cursor, keys = REDIS_CLIENT.scan(cursor=cursor, match=pattern, count=1000)

        for key in keys:
            raw = REDIS_CLIENT.hgetall(key)

            if not raw:
                log.warning(f"No match for {cls.__name__} with key {key}")
                continue

            if raw.get("_deleted"):
                log.warning(f"{cls.__name__} with key {key} marked for deletion. Returning None")
                continue

            data = {k: v for k, v in raw.items() if k in cls.FIELDS}
            meta = {k: v for k, v in raw.items() if k in cls.META_FIELDS}

            instances.append(cls(key, data, meta))

        return instances, cursor

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


class ObjectMixin(RedisMixin, metaclass=ObjectMixinMeta):
    """
    An extension of RedisMixin which 
        - introduces relationships (left objects, and right objects) through RelationManagers
        - wraps Redis keys in the form of simple object IDs - see _key() method
    """

    # To be defined in subclasses
    ID_GENERATOR    = utils.new_id  # The ID generator to use for the class

    LEFTS           = {}            # Leftwards relations {"relation_name": "relation_class_path", ...}
    RIGHTS          = {}            # Rightwards relations {"relation_name": "relation_class_path", ...}

    ## HELPERS ##### ##### ##### ##### ##### 

    @classmethod
    def _prefix(cls) -> str:
        """Returns the Redis key of an object given its id"""
        return f"{cls.__name__.lower()}:"
    
    @classmethod
    def _key(cls, id: str) -> str:
        """Returns the Redis key of an object given its id"""
        return f"{cls._prefix()}{id}"

    def __getattr__(self, name):
        """Intercepts attribute access for id."""
        if name == "id":
            return self.key[len(self._prefix()):]
        else:
            return super().__getattr__(name)

    @classmethod
    @tracer.wrap("ObjectMixin.create")
    def create(cls, **kwargs) -> "ObjectMixin":

        # Generate a unique ID and create the instance
        while True:
            id = cls.ID_GENERATOR()
            if not REDIS_CLIENT.exists(cls._key(id)):
                break  # Unique ID found

        return super().create(cls._key(id), **kwargs)

    @classmethod
    def exists(cls, id: str) -> bool:
        return super().exists( cls._key(id) )

    @classmethod
    def get_by_id(cls, id: str) -> "ObjectMixin":
        """
        Retrieves the object from Redis.
        Args
            - id: The ID of the object to retrive
        Returns:
            - The object, or None
        """
        return super().get( cls._key(id) )

    @tracer.wrap("ObjectMixin.delete")
    def delete(self) -> bool:
        """Deletes the object and all its related relations from Redis using a pipeline."""
        # TODO delete relations and objects in the same Redis transaction

        # Delete all left-relations
        if self.LEFTS:

            log.info(f"Deleting relations for {self.__class__.__name__} with ID {self.id}")
            for relation_name, relation_class in self.LEFTS.items():

                manager =LeftwardsRelationManager(self, relation_class)
                manager.remove_all()

        # Delete all right-relations
        if self.RIGHTS:

            log.info(f"Deleting relations for {self.__class__.__name__} with ID {self.id}")
            for relation_name, relation_class in self.RIGHTS.items():

                manager = RightwardsRelationManager(self, relation_class)
                manager.remove_all()

        return super().delete()

    @classmethod
    def patch(cls, id: str, field, value) -> bool:
        return super().patch(cls._key(id), field, value)

    @tracer.wrap("ObjectMixin.to_dict")
    def to_dict(self, include_related=False):
        """Converts the object to a dictionary for JSON serialization."""

        base = { **self.data, **self.meta }

        if include_related:
            
            if self.LEFTS:
                for relation_name, relation_class in self.LEFTS.items():
                    manager = LeftwardsRelationManager(self, relation_class)
                    
                    lefts = manager.all()
                    if lefts is not None:
                        base[relation_name] = {
                            k: v
                            for relation in lefts.values()
                            for k, v in relation.left_to_dict().items()
                        }
                    else:
                        base[relation_name] = {}

            if self.RIGHTS:
                for relation_name, relation_class in self.RIGHTS.items():
                    manager = RightwardsRelationManager(self, relation_class)

                    rights = manager.all()
                    if rights is not None:
                        base[relation_name] = {
                            k: v
                            for relation in rights.values()
                            for k, v in relation.right_to_dict().items()
                        }
                    else:
                        base[relation_name] = {}

        return { str(self.id): base }

    @classmethod
    def search(cls, cursor=0, count=1000):
        return super().search(f"{cls._prefix()}*", cursor, count)


## ASSOCIATIONS ###### ###### ###### ###### ###### ###### ###### ###### ###### ######


class RelationMixin(RedisMixin):
    """
    A class for managing n:m relationships with data fields and metadata in Redis.
    Assumes no more than one relation can exist between 2 instances
    """

    RELATION_TYPE = "many_to_many"  # or "one_to_many"

    L_CLASS = None   # Left-side class (e.g., Room)
    R_CLASS = None   # Right-side class (e.g., User)
    NAME = "left:linksto:right"  # Name of the relation for key generation


    ## HELPERS ##### ##### ##### ##### ##### 

    @classmethod
    def _L_prefix(cls):
        """Returns the lowercased class name for the left-side class."""
        return f"{cls.L_CLASS.__name__.lower()}:"

    @classmethod
    def _R_prefix(cls):
        """Returns the lowercased class name for the right-side class."""
        return f"{cls.R_CLASS.__name__.lower()}:"

    @classmethod
    def _key(cls, left_id: str, right_id: str) -> str:
        """Generate the Redis key for a relation between two objects (used in one-to-many)."""
        return f"{cls.NAME}::{cls._L_prefix()}{left_id}::{cls._R_prefix()}{right_id}"
    
    @classmethod
    def _exist_parent(cls, right_id: str) -> "RelationMixin":
        """Retrieve the relation for a given right-side object (used in one-to-many)."""
        pattern = f"{cls.NAME}::*::{cls._R_prefix()}{right_id}"

        for key in REDIS_CLIENT.scan_iter(pattern):
            raw = REDIS_CLIENT.hgetall(key)
            if raw:
                return True
        return False

    def __getattr__(self, name):
        """Intercepts attribute access for id."""

        if name == "left_id":

            parts = self.key.split("::")
            left_id = parts[1].split(":")[1]
            return left_id

        elif name == "right_id":

            parts = self.key.split("::")
            right_id = parts[2].split(":")[1]        
            return right_id

        else:
            return super().__getattr__(name)

    ## ##### ##### ##### ##### ##### #####

    @classmethod
    @tracer.wrap("RelationMixin.create")
    def create(cls, left_id: str, right_id: str, **kwargs) -> "RelationMixin":

        """Creates a relation instance."""
        log.info(f"Creating relation between {cls.L_CLASS.__name__}:{left_id} and {cls.R_CLASS.__name__}:{right_id} with kwargs {kwargs}")

        if cls.L_CLASS.get_by_id(left_id) is None:
            raise ValueError(f"{cls.L_CLASS.__name__}:{left_id} does not exist.")
        
        if cls.R_CLASS.get_by_id(right_id) is None:
            raise ValueError(f"{cls.R_CLASS.__name__}:{right_id} does not exist.")

        # Enforce cardinality constraints
        if cls.RELATION_TYPE == "one_to_many":
            # Ensure the right-side object is not already linked

            if cls._exist_parent(right_id):
                raise ValueError(
                    f"{cls.R_CLASS.__name__}:{right_id} is already linked to a {cls.L_CLASS.__name__} - skipping association"
                )

        return super().create(cls._key(left_id, right_id), **kwargs)


    @classmethod
    def exists(cls, left_id: str, right_id: str) -> bool:
        return super().exists( cls._key(left_id, right_id) )

    @classmethod
    def get_by_ids(cls, left_id: str, right_id: str) -> "RelationMixin":
        """
        Retrieves the object from Redis.
        Args
            - left_id: The ID of the left-hand side object of the Relation
            - right_id: The ID of the right-hand side object of the Relation
        Returns:
            - The created object, or None
        """
        return super().get( cls._key(left_id, right_id) )
    
    @classmethod
    def patch(cls, left_id: str, right_id: str, field, value) -> bool:
        return super().patch( cls._key(left_id, right_id), field, value)

    @classmethod
    def search(cls, cursor=0, count=1000):
        pattern = f"{cls.NAME}::{cls._L_prefix()}*::{cls._R_prefix()}*"
        return super().search(pattern, cursor, count)
    

    @tracer.wrap("RelationMixin.left")
    def left(self):
        """Returns the left-side object of the relation"""

        return self.L_CLASS.get_by_id(self.left_id)

    @tracer.wrap("RelationMixin.right")
    def right(self):
        """Returns the right-side object of the relation"""

        return self.R_CLASS.get_by_id(self.right_id)
    
    @tracer.wrap("RelationMixin.left_to_dict")
    def left_to_dict(self):
        """Returns the relation alongside its left-side object for JSON serialization."""

        result = self.left().to_dict(False)
        result[str(self.left_id)]["relation"] = self.meta | self.data
    
        return result

    @tracer.wrap("RelationMixin.right_to_dict")
    def right_to_dict(self):
        """Returns the relation alongside its right-side object for JSON serialization."""

        result = self.right().to_dict(False)
        result[str(self.right_id)]["relation"] = self.meta | self.data
        
        return result

    @classmethod
    @tracer.wrap("RelationMixin.lefts")
    def lefts(cls, right_id: str) -> dict[str, "RelationMixin"]:
        """
        Retrieve all leftwards relations with a given right-side object.
        Indexed by the left-side object ID.
        """

        lefts = {}

        pattern = f"{cls.NAME}::{cls._L_prefix()}*::{cls._R_prefix()}{right_id}"
        for key in REDIS_CLIENT.scan_iter(pattern):

            # Fetch raw data from Redis
            raw = REDIS_CLIENT.hgetall(key)
            if not raw:
                log.warning(f"No match for {cls.__name__} with key {key}")
                continue

            if raw.get("_deleted"):
                log.warning(f"{cls.__name__} with key {key} marked for deletion. Returning None")
                return None

            # Extract relation attributes
            data   = {k: v for k, v in raw.items() if k in cls.FIELDS}
            meta   = {k: v for k, v in raw.items() if k in cls.META_FIELDS}
            relation = cls(key, data=data, meta=meta)

            # Store left-side object along with relation attributes
            left_id = key.split("::")[1].split(":")[1]
            lefts[left_id] = relation

        return lefts

    @classmethod
    @tracer.wrap("RelationMixin.rights")
    def rights(cls, left_id: str) -> dict[str, "RelationMixin"]:
        """
        Retrieve all rightwards relations with a given left-side object.
        Indexed by the right-side object ID.
        """

        rights = {}

        pattern = f"{cls.NAME}::{cls._L_prefix()}{left_id}::{cls._R_prefix()}*"
        for key in REDIS_CLIENT.scan_iter(pattern):

            # Fetch raw data from Redis
            raw = REDIS_CLIENT.hgetall(key)
            if not raw:
                log.warning(f"No match for {cls.__name__} with key {key}")
                continue

            if raw.get("_deleted"):
                log.warning(f"{cls.__name__} with key {key} marked for deletion. Returning None")
                continue

            # Extract relation attributes
            data    = {k: v for k, v in raw.items() if k in cls.FIELDS}
            meta    = {k: v for k, v in raw.items() if k in cls.META_FIELDS}
            relation  = cls(key, data=data, meta=meta)

            # Store left-side object along with relation attributes
            right_id = key.split("::")[2].split(":")[1]
            rights[right_id] = relation

        return rights


class RelationManager():
    """An abstract manager for handling relations between two ObjectMixin classes."""

    def __init__(self, instance, relation_class):

        if type(self) is RelationManager:
            raise TypeError("RelationManager cannot be instantiated directly. Call subclass' instead.")

        self.instance = instance

        module_name, class_name = relation_class.rsplit(".", 1)
        module = importlib.import_module(module_name)
        self.relation_class = getattr(module, class_name)


    def all(self) -> dict[str, RelationMixin]:
        """Retrieves all relations for the instance, indexed with their object ID"""

        if type(self) is RelationManager:
            raise TypeError("RelationManager.all() is abstract. Call subclass' instead.")


    def add(self, related_id: str, **data) -> ObjectMixin:
        """Adds a relation between the instance and a related object."""

        if type(self) is RelationManager:
            raise TypeError("RelationManager.add() is abstract. Call subclass' instead.")

    def remove(self, related_id: str) -> ObjectMixin:
        """Removes the relation the instance and a related object."""

        if type(self) is RelationManager:
            raise TypeError("RelationManager.remove() is abstract. Call subclass' instead.")

    @tracer.wrap("RelationManager.remove_all")
    def remove_all(self) -> ObjectMixin:
        """Removes all relations for the instance."""

        log.info(f"Removing all relations for {self.instance.__class__.__name__} with ID {self.instance.id}")
        related = self.all()

        for related_id in related:
            self.remove(related_id)

        return self.instance

    def get_by_id(self, related_id: str) -> tuple[ObjectMixin, RelationMixin] :
        """ Retrieves a related object and its relation to the instance by its ID."""

        if type(self) is RelationManager:
            raise TypeError("RelationManager.get_by_id() is abstract. Call subclass' instead.")

    def exists(self, related_id: str) -> bool :
        """ Retrieves if a relation exists between instance with related object"""

        if type(self) is RelationManager:
            raise TypeError("RelationManager.exists() is abstract. Call subclass' instead.")

    def first(self) -> tuple[ObjectMixin, RelationMixin] :
        """ Retrieves the first related object and its relation to the instance by its ID."""

        if type(self) is RelationManager:
            raise TypeError("RelationManager.remove() is abstract. Call subclass' instead.")

    @tracer.wrap("RelationManager.set")
    def set(self, related_id: str, **kwargs) -> tuple[ObjectMixin, RelationMixin] :
        """ Sets properties of the relation of with related object."""

        obj, rel = self.get_by_id(related_id)
        if rel:
            for key, value in kwargs.items():
                rel.__setattr__(key, value)
                log.debug(f"setting {key}:{value}")
            rel.save()

        return obj, rel            


class RightwardsRelationManager(RelationManager):
    """Manages relations where the instance is the left-side object."""

    def __init__(self, instance, relation_class):

        log.debug(f"Initializing RightwardsRelationManager with instance {instance.key} and relation_class {relation_class}")
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
        relation = self.relation_class.get_by_ids(self.instance.id, related_id)
        if relation:
            relation.delete()
        return self.instance

    @tracer.wrap("RightwardsRelationManager.get")
    def get_by_id(self, related_id) :
        
        if self.exists(related_id) :
            rel = self.relation_class.get_by_ids(self.instance.id, related_id)
            obj = self.relation_class.R_CLASS.get_by_id(related_id)
            return obj, rel
        else: 
            return None, None

    @tracer.wrap("RightwardsRelationManager.exist")
    def exists(self, related_id: str):

        return self.relation_class.exists(self.instance.id, related_id)

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
        relation = self.relation_class.get_by_ids(related_id, self.instance.id)
        if relation:
            relation.delete()
        return self.instance

    @tracer.wrap("LeftwardsRelationManager.get")
    def get_by_id(self, related_id) :
        
        if self.exists(related_id):
            rel = self.relation_class.get_by_ids(related_id, self.instance.id)
            obj = self.relation_class.L_CLASS.get_by_id(related_id)
            return obj, rel
        else: 
            return None, None

    @tracer.wrap("RightwardsRelationManager.exist")
    def exists(self, related_id: str):

        return self.relation_class.exists(related_id, self.instance.id)

    @tracer.wrap("LeftwardsRelationManager.first")
    def first(self):
        
        for related_id, relation in self.all().items():
            return relation.left(), relation