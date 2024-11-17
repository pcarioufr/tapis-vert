import flask

# Initialize the Blueprint
test_web = flask.Blueprint("test_web", __name__)
test_api = flask.Blueprint("test_api", __name__)

# Import routes to register them with the Blueprint
from .api import routes
from .web import routes