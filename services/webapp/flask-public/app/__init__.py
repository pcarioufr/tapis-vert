from flask import Flask
from ddtrace import tracer

# Import PUBLIC Blueprints only
from app.room import room_web, room_api
from app.auth import auth, login
from app.test import test_web, test_api

@tracer.wrap()
def init_public_app():
    """Initialize the public-facing Flask app (no admin routes)"""
    
    app = Flask(__name__,
                static_url_path="/static", 
                static_folder='../static',
                template_folder='../templates')

    app.config.from_object('app.config.Config')

    login.init_app(app)

    with app.app_context():
        # Register PUBLIC blueprints only
        app.register_blueprint(room_web, url_prefix="/")
        app.register_blueprint(room_api, url_prefix="/api")
        app.register_blueprint(auth, url_prefix="/auth")
        
        app.register_blueprint(test_web, url_prefix="/test")
        app.register_blueprint(test_api, url_prefix="/test/api")

        # Import shared utilities
        from .api import ping
        from .routines import render_template

        return app

# For backwards compatibility, provide init_app function
init_app = init_public_app
