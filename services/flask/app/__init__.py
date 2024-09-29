from flask import Flask
from ddtrace import tracer


@tracer.wrap()
def init_app():

    app = Flask(__name__,
                static_url_path="/static",
                static_folder="./static",
                template_folder='./templates')
    app.config.from_object('config.Config')


    with app.app_context():

        from .routes import ping
        from .routes import room_app, room_api
        from .routes import room_user_api, room_user_api_get

        return app
