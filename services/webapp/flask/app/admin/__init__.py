import flask

# Initialize the Blueprint
admin = flask.Blueprint("admin", __name__)


# Import routes to register them with the Blueprint
from . import api
from . import web