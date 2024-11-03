from .mixins import RedisMixin

import os

class User(RedisMixin):

    PREFIX = "user"
    DB_INDEX = os.environ.get("REDIS_ROOMS_DB")
    PARAMS = {"name", "status"}


    # Flask-Login required methods and properties

    def get_id(self) -> str:
        # Return the ID from the wrapped User instance
        return str(self._user.id)  # Flask-Login expects get_id to return a string

    @property
    def is_active(self) -> bool:
        # Example: Return active status from the wrapped User instance (if applicable)
        return getattr(self._user, "is_active", True)

    @property
    def is_authenticated(self) -> bool:
        # Flask-Login expects this to return True for authenticated users
        return True

    @property
    def is_anonymous(self) -> bool:
        # Flask-Login expects this to return False for authenticated users
        return False
