from flask import Flask
from ddtrace import tracer


# Import Blueprints
from app.auth   import auth, login
from app.lab    import lab
from app.main   import main
from app.admin  import admin


@tracer.wrap()
def init_app():

    app = Flask(__name__,
                static_url_path="/static",
                template_folder='./templates')
    app.config.from_object('config.Config')

    login.init_app(app)

    with app.app_context():

        app.register_blueprint(main, url_prefix="/")
        app.register_blueprint(auth, url_prefix="/auth")
        app.register_blueprint(lab,  url_prefix="/lab")
        app.register_blueprint(admin, url_prefix="/admin")

        from .api import ping

        return app
