import flask

# Initialize Blueprints for API and Pages
public_api = flask.Blueprint("public_api", __name__)
public_web = flask.Blueprint("public_web", __name__)

# Import the routes from submodules
from .api import routes
from .web import routes, routines
