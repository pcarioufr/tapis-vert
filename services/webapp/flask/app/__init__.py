from flask import Flask
from ddtrace import tracer


# Import Blueprints
from app.room   import room_web, room_api
from app.auth   import auth, login

from app.test  import test_web, test_api

from app.admin  import admin_web, admin_api


@tracer.wrap()
def init_app():

    app = Flask(__name__,
                static_url_path="/static",
                template_folder='/flask/templates/')

    app.config.from_object('app.config.Config')

    login.init_app(app)

    with app.app_context():

        app.register_blueprint(room_web, url_prefix="/")
        app.register_blueprint(room_api, url_prefix="/api")
        app.register_blueprint(auth, url_prefix="/auth")

        app.register_blueprint(admin_web, url_prefix="/admin")
        app.register_blueprint(admin_api, url_prefix="/admin/api")

        app.register_blueprint(test_web, url_prefix="/test")
        app.register_blueprint(test_api, url_prefix="/test/api")

        from .api import ping

        from .routines import render_template


        return app
