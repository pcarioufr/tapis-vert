# Import from the redis-orm core package
from core import ObjectMixin, RelationMixin

import random, json
import nanoid
from ddtrace import tracer

from utils import get_logger
from topics import topic as get_topic

log = get_logger(__name__)

# ID generators for models
S_ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
def new_sid() -> str:
    '''Generates Random ID, suited for Secret IDs'''
    return nanoid.generate(S_ALPHABET, 24)

ALPHABET = '0123456789abcdef'
def new_id(size=10) -> str:
    '''Generates Random ID, suited for Internal Object IDs'''
    return nanoid.non_secure_generate(ALPHABET, size)

class User(ObjectMixin):
    '''
    Users:
    * name: public name - appearing in app
    * status: online True/False 
    * codes: the Magic Links that the user can log in with
    '''

    FIELDS  = {"name"}

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
                code_instance = Code.get_by_id(code_id)
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
    Room model with messages as nested dict.
    '''

    FIELDS = {"name", "round", "cards", "messages"}

    RIGHTS = {} 
    LEFTS = {
        "users": "models.UsersRooms"
    }

    @tracer.wrap("Room.new_round")
    def new_round(self):
        users = self.users().all()

        round_id = new_id()
        round_topic = get_topic()
        round = {"id": round_id, "topic": round_topic}
        self.round = round

        cards = {}
        values = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
        random.shuffle(values)

        i = 0
        for user_id, relation in users.items():

            player = User.get_by_id(user_id)
            
            card_ids = []
            if relation.role == "player":

                while True:
                    card_id = new_id(4)
                    if card_id not in card_ids:
                        break
                card_ids.append(card_id)

                cards[card_id] = { 
                    "flipped": "True", 
                    "player_id": player.id, 
                    "peeked": {u_id: "False" for u_id in users.keys()},
                    "value": values[i] 
                }

            i = i+1

        # Clear old messages when starting new round
        self.messages = {}
        self.cards = cards
        self.save()

        return round, cards


class UsersRooms(RelationMixin):
    '''
    role:   { watcher, player, master }
    status: { offline, online }
    '''

    FIELDS = {"role", "status"}

    L_CLASS = User
    R_CLASS = Room

    NAME    = "member"
    RELATION_TYPE = "many_to_many"
