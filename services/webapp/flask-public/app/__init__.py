from flask import Flask
from ddtrace import tracer

# Import PUBLIC Blueprints only
from app.room import room_web, room_api
from app.auth import auth, login


@tracer.wrap()
def init_public_app():
    """Initialize the public-facing Flask app (no admin routes)"""
    
    app = Flask(__name__,
                static_url_path="/static", 
                static_folder='../static',
                template_folder='../templates')

    app.config.from_object('app.config.Config')

    # Initialize Redis ORM with app configuration
    from models import init_redis_orm
    init_redis_orm()

    login.init_app(app)

    with app.app_context():
        # Register PUBLIC blueprints only
        app.register_blueprint(room_web, url_prefix="/")
        app.register_blueprint(room_api, url_prefix="/api")
        app.register_blueprint(auth, url_prefix="/auth")
        


        # Import shared utilities
        from .api import ping
        from .routines import render_template

        return app

# For backwards compatibility, provide init_app function
init_app = init_public_app
