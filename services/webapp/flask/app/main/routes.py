from . import main  # Import the Blueprint from __init__.py

import flask
from flask import request, send_file, jsonify

from utils import log

from app.routines import render_template


from flask_login import login_required



@main.route("/r/<room_id>", methods=['GET'])
def room_app(room_id=None):

    # USER AUTHENTICATION

    # Login when user_id is injected as a URL param 
    if request.args.get("user") is not None:

        user_id = request.args.get("user")
        flask.session["user_id"] = user_id
        log.info("user {} logged in".format(user_id))

    # Reject login if no user specifified and no session cookie
    elif flask.session.get("user_id") is None:

        return jsonify(), 401

    # Recognizes an existing user (through session cookie)
    else:
        user_id = flask.session.get("user_id")


    # Checks if the room exists
    if room_id is None:
        return jsonify(), 404


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

