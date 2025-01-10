import flask

# Initialize Blueprints for API and Pages
room_api = flask.Blueprint("room_api", __name__)
room_web = flask.Blueprint("room_web", __name__)

# Import the routes from submodules
from .api import routes
from .web import routes, routines
