from flask import Flask
from ddtrace import tracer


from app.auth import auth, login
from app.lab import lab

@tracer.wrap()
def init_app():

    app = Flask(__name__,
                static_url_path="/static",
                template_folder='./templates')
    app.config.from_object('config.Config')

    login.init_app(app)

    with app.app_context():

        from .routes import ping
        from .routes import room_app, room_api
        from .routes import round_api
        from .routes import room_user_id_api
        from .routes import user_api
        from .routes import qr_code

        app.register_blueprint(auth, url_prefix="/auth")
        app.register_blueprint(lab,  url_prefix="/lab")

        return app
