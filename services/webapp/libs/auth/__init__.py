"""
Authentication Library

Provides Flask-Login integration and authentication utilities.
"""

import flask_login
import random
from models import User

# Initialize the LoginManager (to be configured by Flask app)
login = flask_login.LoginManager()
login.session_protection = "strong"
# login.login_view = "auth.login" TODO

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
    """Generate a random anonymous name from seed"""
    random.seed(seed)
    return f"{random.choice(colors)} {random.choice(animals)}"

class AnonymousWebUser(flask_login.AnonymousUserMixin):
    """Anonymous user class with generated names"""
    
    def __init__(self, id=None):
        self.id = id

    @property
    def name(self):
        return new_name(self.id)

# Configure login manager
login.anonymous_user = AnonymousWebUser

@login.user_loader
def user_loader(user_id):
    """Load user by ID for Flask-Login"""
    return User.get_by_id(user_id)

# Import authentication functions
from .routines import code_auth

# Export public API
__all__ = ['login', 'code_auth', 'AnonymousWebUser', 'new_name'] 
