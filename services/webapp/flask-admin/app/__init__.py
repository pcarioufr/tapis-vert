from flask import Flask
from ddtrace import tracer

# Import ADMIN Blueprints only
from app.admin import admin_web, admin_api

@tracer.wrap()
def init_admin_app():
    """Initialize the admin-only Flask app (localhost access only)"""
    
    app = Flask(__name__,
                static_url_path="/static",
                static_folder='../static',
                template_folder='../templates')

    app.config.from_object('app.config.Config')

    with app.app_context():
        # Register ADMIN blueprints only
        app.register_blueprint(admin_web, url_prefix="/admin")
        app.register_blueprint(admin_api, url_prefix="/admin/api")

        # Import shared utilities (needed for templates)
        from .routines import render_template

        return app

# For backwards compatibility, provide init_app function  
init_app = init_admin_app
