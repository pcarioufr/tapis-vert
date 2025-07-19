import flask, flask_login

# Initialize the Blueprint
auth = flask.Blueprint("auth", __name__)

from models import User

# Initialize the LoginManager
login = flask_login.LoginManager()
login.session_protection = "strong"
# login.login_view = "auth.login" TODO

import random

# Anonymous user name generation
colors = [
    "Almond", "Amethyst", "Apricot", "Aqua", "Azure", "Beige", "Black", "Blue", 
    "Bronze", "Brown", "Burgundy", "Byzantine", "Cerulean", "Champagne", 
    "Charcoal", "Cherry", "Cobalt", "Coral", "Crimson", "Cyan", "Emerald", 
    "Fuchsia", "Gold", "Gray", "Green", "Indigo", "Ivory", "Jade", "Lavender", 
    "Lemon", "Lilac", "Lime", "Magenta", "Maroon", "Mint", "Navy", "Olive", 
    "Orange", "Peach", "Periwinkle", "Pink", "Plum", "Purple", "Red", 
    "Rose", "Ruby", "Salmon", "Sapphire", "Silver", "Teal", "Yellow"
]

animals = [
    "Aardvark", "Albatross", "Alligator", "Antelope", "Armadillo", "Badger", 
    "Bat", "Beaver", "Bison", "Buffalo", "Camel", "Capybara", "Caribou", 
    "Chameleon", "Cheetah", "Chipmunk", "Cobra", "Cougar", "Coyote", "Crab", 
    "Crocodile", "Deer", "Dingo", "Dolphin", "Dragonfly", "Eagle", "Elephant", 
    "Elk", "Ferret", "Flamingo", "Fox", "Frog", "Gazelle", "Giraffe", "Goat", 
    "Gorilla", "Grasshopper", "Hamster", "Hedgehog", "Heron", "Hippo", 
    "Horse", "Hyena", "Iguana", "Jaguar", "Jellyfish", "Kangaroo", "Koala", 
    "Lemur", "Leopard"
]

def new_name(seed: str):
    random.seed(seed)
    return f"{random.choice(colors)} {random.choice(animals)}"

class AnonymousWebUser(flask_login.AnonymousUserMixin):

    def __init__(self, id=None):
        self.id = id

    @property
    def name(self):
        return new_name(self.id)

login.anonymous_user = AnonymousWebUser

@login.user_loader
def user_loader(user_id):

    return User.get_by_id(user_id)


# Import routes to register them with the Blueprint
from .routines import code_auth
from . import api 
