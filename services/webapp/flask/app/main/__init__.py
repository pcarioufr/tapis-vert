import flask

# Initialize the Blueprint
main = flask.Blueprint("main", __name__)


# Import routes to register them with the Blueprint
from . import web
from . import api