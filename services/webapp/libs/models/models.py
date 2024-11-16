from .mixins import ObjectMixin, RelationMixin

import os
from utils import get_logger, new_sid
from ddtrace import tracer

import random, json

log = get_logger(__name__)

class User(ObjectMixin):
    '''
    Users:
    * name: public name - appearing in app
    * status: online True/False 
    * codes: the Magic Links that the user can log in with
    '''

    FIELDS  = {"name", "status"}

    RIGHTS  = {
        "codes": "models.UserCodes",
        "rooms": "models.UsersRooms"
    }
    LEFTS   = {}

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

    LEFTS = {
        "user": "models.UserCodes"
    }


class UserCodes(RelationMixin):
    '''
    Association
    User owns Codes
    '''

    FIELDS = {"type"}

    L_CLASS = User
    R_CLASS = Code

    NAME    = "user_code_ownership"
    RELATION_TYPE = "one_to_many"



class Room(ObjectMixin):
    '''
    '''

    FIELDS = {"name", "round"}

    RIGHTS = {} 
    LEFTS = {
        "users": "models.UsersRooms"
    }


    @tracer.wrap("Room.new_round")
    def new_round(self, players: list[str]):

        if len(players) > 10:
            raise Exception("too many users ({}): max 10".format(len(players)))

        # Define Round

        values = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
        random.shuffle(values)

        cards = {}

        i = 0
        for x in players:
            cards[x] = values[i]
            i = i+1

        self.round = json.dumps( {"cards": cards} )
        self.save()


class UsersRooms(RelationMixin):
    '''
    '''

    FIELDS = {"role"}

    L_CLASS = User
    R_CLASS = Room

    NAME    = "round_room"
    RELATION_TYPE = "many_to_many"
