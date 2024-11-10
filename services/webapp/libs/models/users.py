from .mixins import RedisMixin

import os
import utils

class User(RedisMixin):
    '''
    Users:
    * name: public name - appearing in app
    * status: online True/False 
    '''

    PREFIX = "user"
    DB_INDEX = os.environ.get("REDIS_USERS_DB")
    FIELDS = {"name", "status", "code_id"}

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



class MagicCode(RedisMixin):
    '''
    Magic Codes: for users to login in
    * user_id: reference to user
    '''

    PREFIX = "code"
    DB_INDEX = os.environ.get("REDIS_USERS_DB")
    FIELDS = {"user_id"}

    ID_GENERATOR = utils.new_sid
