import flask, flask_login

# Initialize the Blueprint
auth = flask.Blueprint("auth", __name__)

from models import User

# Initialize the LoginManager
login = flask_login.LoginManager()
login.session_protection = "strong"
# login.login_view = "auth.login" TODO

from names_generator import generate_name

class AnonymousWebUser(flask_login.AnonymousUserMixin):

    def __init__(self, id=None):
        self.id = id

    @property
    def name(self):
        return generate_name(seed=self.id, style='capital')


login.anonymous_user = AnonymousWebUser


# Import routes to register them with the Blueprint
from . import api 


@login.user_loader
def user_loader(user_id):

    return User.get(user_id)
    
