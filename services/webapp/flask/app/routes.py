import flask
from flask import current_app as app

import redis, json, random
from utils import log
from models import Room



@app.route("/ping")
def ping():

    log.info("ping successful")
    return flask.jsonify(response="pong"), 200


@app.route("/r/<room_id>", methods=['GET'])
def room_app(room_id=None):

    # USER AUTHENTICATION

    # Login when user_id is injected as a URL param 
    if flask.request.args.get("user") is not None:

        user_id = flask.request.args.get("user")
        flask.session["user_id"] = user_id
        log.info("user {} logged in".format(user_id))

    # Reject login if no user specifified and no session cookie
    elif flask.session.get("user_id") is None:

        return flask.jsonify(), 401

    # Recognizes an existing user (through session cookie)
    else:
        user_id = flask.session.get("user_id")


    # Checks if the room exists
    if room_id is None:
        return flask.jsonify(), 404


    return flask.render_template(
        "room.jinja",
        user_id=flask.session.get("user_id"),        
        is_anonymous=False,
        room_id=room_id,
        clientToken=app.config["DD_CLIENT_TOKEN"],
        applicationId=app.config["DD_APPLICATION_ID"],
        dd_version=app.config["DD_VERSION"],
        dd_env=app.config["DD_ENV"],
        dd_site=app.config["DD_SITE"],
    )


@app.route("/api/v1/r/<room_id>", methods=['GET', 'DELETE'])
def room_api(room_id=None):

    if room_id is None:
        log.warning("missing room_id in url")
        return flask.jsonify(), 400

    room = Room(room_id)

    if flask.request.method == 'DELETE':

        room.delete()
        return flask.jsonify(), 204

    if flask.request.method == 'GET':

        return flask.jsonify(room=room.get()), 200




@app.route("/api/v1/r/<room_id>/round", methods=['POST'])
def round_api(room_id=None):

    if room_id is None:
        log.warning("missing room_id in url")
        return flask.jsonify(), 400

    room = Room(room_id)

    # POST

    # Get users list from URL query params
    players = flask.request.args.getlist("user")
    log.debug("players: {}".format(players))

    room.new_round(players)
    

    return flask.jsonify(room=room.get())



@app.route("/api/v1/<room_id>/users/<user_id>", methods=['POST', 'DELETE'])
def room_user_id_api(room_id=None, user_id=None):

    if room_id is None:
        log.warning("missing room_id in url")
        return flask.jsonify(), 400

    if user_id is None:
        log.warning("missing user_id in url")
        return flask.jsonify(), 400

    room = Room(room_id)

    # POST
    if flask.request.method == 'POST':
        room.set_user(user_id, "offline")
        return flask.jsonify(), 200

    # DELETE
    if flask.request.method == 'DELETE':
        room.remove_user(user_id)
        return flask.jsonify(), 204
