from app.main import main_web

import flask

from app.routines import render_template
from utils import log


@main_web.route("/r/<room_id>", methods=['GET'])
def room_app(room_id=None):


    # Checks if the room exists
    if room_id is None:
        return flask.jsonify(), 404


    return render_template (
        "main/r.jinja",
        room_id=room_id
    )

    # return flask.render_template(
    #     "r.jinja",
    #     user_id=flask.session.get("user_id"),        
    #     is_anonymous=False,
    #     host=app.config["HOST"],
    #     room_id=room_id,
    #     clientToken=app.config["DD_CLIENT_TOKEN"],
    #     applicationId=app.config["DD_APPLICATION_ID"],
    #     dd_version=app.config["DD_VERSION"],
    #     dd_env=app.config["DD_ENV"],
    #     dd_site=app.config["DD_SITE"],
    # )

