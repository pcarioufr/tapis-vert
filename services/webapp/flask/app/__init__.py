from flask import Flask
from ddtrace import tracer


@tracer.wrap()
def init_app():

    app = Flask(__name__,
                static_url_path="/static",
                template_folder='./templates')
    app.config.from_object('config.Config')


    with app.app_context():

        from .routes import ping, test
        from .routes import room_app, room_api
        from .routes import round_api
        from .routes import room_user_id_api
        from .routes import qr_code

        return app
