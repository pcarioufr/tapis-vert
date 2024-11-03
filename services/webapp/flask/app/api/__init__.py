import flask

# Initialize the Blueprint
api = flask.Blueprint("api", __name__)


# Import routes to register them with the Blueprint
from . import routes 