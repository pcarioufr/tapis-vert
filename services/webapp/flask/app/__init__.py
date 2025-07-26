from flask import Flask
from ddtrace import tracer

# Import ALL Blueprints (admin + public)
from .admin import admin_web, admin_api
from .room import room_web, room_api
from .auth import auth, login


@tracer.wrap()
def init_app():
    """Initialize the unified Flask app with both admin and public routes"""
    
    app = Flask(__name__,
                static_url_path="/static",
                static_folder='../static',
                template_folder='../templates')

    app.config.from_object('app.config.Config')

    # Initialize Redis ORM with app configuration
    from models import init_redis_orm
    init_redis_orm()

    # Initialize login system (needed for public routes)
    login.init_app(app)

    with app.app_context():
        # Register ALL blueprints in unified app
        # Admin routes (will be protected by nginx)
        app.register_blueprint(admin_web, url_prefix="/admin")
        app.register_blueprint(admin_api, url_prefix="/admin/api")
        
        # Public routes
        app.register_blueprint(room_web, url_prefix="/")
        app.register_blueprint(room_api, url_prefix="/api")
        app.register_blueprint(auth, url_prefix="/auth")

        # Import shared utilities
        from .api import ping
        from .routines import render_template

        return app 