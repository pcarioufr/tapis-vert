from .mixins import RedisMixin

import os

class User(RedisMixin):

    PREFIX = "user"
    DB_INDEX = os.environ.get("REDIS_ROOMS_DB")
    PARAMS = {"name", "status"}
