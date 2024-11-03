import flask, flask_login

# Initialize the Blueprint
auth = flask.Blueprint("auth", __name__)

from models import User

# Initialize the LoginManager
login = flask_login.LoginManager()
login.session_protection = "strong"
# login.login_view = "auth.login" TODO


class AnonymousWebUser(flask_login.AnonymousUserMixin):
    pass

login.anonymous_user = AnonymousWebUser


# Import routes to register them with the Blueprint
from . import routes 


@login.user_loader
def user_loader(user_id):

    return User.get(user_id)
    
