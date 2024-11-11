import flask

# Initialize the Blueprint
admin_web = flask.Blueprint("admin_web", __name__)
admin_api = flask.Blueprint("admin_api", __name__)

# Import routes to register them with the Blueprint
from .api import routes
from .web import routes