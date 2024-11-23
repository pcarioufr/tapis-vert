from .mixins import ObjectMixin, RelationMixin

import os
from utils import get_logger, new_sid
from ddtrace import tracer

log = get_logger(__name__)

class User(ObjectMixin):
    '''
    Users:
    * name: public name - appearing in app
    * status: online True/False 
    * codes: the Magic Links that the user can log in with
    '''

    FIELDS = {"name", "status"}
    RIGHTS = {"codes": "models.UserCode"}

    @tracer.wrap()
    def delete(self) -> bool:
        """Deletes the user and all associated codes."""
        log.info(f"Deleting all codes associated with User ID {self.id}")

        # Iterate over codes associated with this user
        for code_id, association in self.codes().all().items():
            try:
                code_instance = Code.get(code_id)
                if code_instance:
                    code_instance.delete()
                    log.info(f"Deleted Code with ID {code_id} associated with User ID {self.id}")
            except Exception as e:
                log.error(f"Failed to delete Code with ID {code_id} for User ID {self.id}: {e}")

        # Delete the user and its associations
        super().delete()
        return True

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



class Code(ObjectMixin):
    '''
    Code: Magic Code for users to login in
    * user: reference to user
    '''

    FIELDS = {"test"}
    ID_GENERATOR = new_sid
    LEFTS = {"user": "models.UserCode"}


class UserCode(RelationMixin):
    '''
    Association
    User owns Codes
    '''

    FIELDS = {"type"}

    L_CLASS = User
    R_CLASS = Code

    NAME    = "user_code_ownership"
    RELATION_TYPE = "one_to_many"