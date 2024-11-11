import flask

# Initialize Blueprints for API and Pages
main_api = flask.Blueprint("main_api", __name__)
main_web = flask.Blueprint("main_web", __name__)

# Import the routes from submodules
from .api import routes
from .web import routes, routines
