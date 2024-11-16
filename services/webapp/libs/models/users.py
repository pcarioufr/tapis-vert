from .mixins import RedisMixin, RedisAssociationMixin, AssociationManager

import os
import utils

class User(RedisMixin):
    '''
    Users:
    * name: public name - appearing in app
    * status: online True/False 
    * code_id: Code for the user to login with
    * rooms: an array of room_id that the user owns or co-owns
    '''

    FIELDS = {"name", "status"}

    def codes(self):
        return AssociationManager(self, "models.UserCode")


    # TODO extend delete method to delete code along with the user
    # def delete(self) -> bool:

    #     # Additional custom logic before deletion

    #     # Call the RedisMixin's delete method
    #     result = super().delete()

    #     # Additional custom logic after deletion, if needed

    #     return result
    

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



class Code(RedisMixin):
    '''
    Code: Magic Code for users to login in
    * user_id: reference to user
    '''

    FIELDS = {}
    ID_GENERATOR = utils.new_sid

    def users(self):
        return AssociationManager(self, "models.UserCode")


class UserCode(RedisAssociationMixin):
    '''
    Association
    User owns Code
    '''

    FIELDS = {"type"}

    L_CLASS = User
    R_CLASS = Code

    NAME    = "user_code_ownership"