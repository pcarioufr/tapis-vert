import flask

# Initialize the Blueprint
lab = flask.Blueprint("lab", __name__)


# Import routes to register them with the Blueprint
from . import routes 