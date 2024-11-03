from .mixins import RedisMixin

import os

class User(RedisMixin):

    PREFIX = "user"
    DB_INDEX = os.environ.get("REDIS_ROOMS_DB")
    PARAMS = {"name", "status"}

    # Flask-Login required methods and properties

    def get_id(self) -> str:
        return str(self.id)  # Flask-Login expects get_id to return a string

    @property
    def is_active(self) -> bool:
        return True

    @property
    def is_authenticated(self) -> bool:
        # Flask-Login expects this to return True for authenticated users
        return True

    @property
    def is_anonymous(self) -> bool:
        # Flask-Login expects this to return False for authenticated users
        return False
