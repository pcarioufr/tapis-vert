import flask
from flask import current_app as app

import redis, json, random

from app.logs import log


redis_client = redis.Redis(
            host=app.config["REDIS_HOST"],
            db=app.config["REDIS_STORE_DB"],
            decode_responses=True
        )

redis_pubsub = redis.Redis(
            host=app.config["REDIS_HOST"],
            db=app.config["REDIS_PUBSUB_DB"],
            decode_responses=True
        )


@app.route("/ping")
def ping():

    log.info("ping successful")
    return flask.jsonify(response="pong"), 200


@app.route("/top10/<room_id>", methods=['GET'])
def top10_app(room_id=None):

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

    if not redis_client.exists(room_id):
        log.warning("room_id {} not found".format(room_id))
        return flask.jsonify(), 404

    # Gets round properties
    round = redis_client.hgetall(room_id)
    cards = json.loads(round['cards'])
    round_id = round['id']

    return flask.render_template(
        "home.jinja",
        user_id=flask.session.get("user_id"),
        round_id=round_id,
        room_id=room_id,
        cards=cards,
        is_anonymous=False,
        clientToken=app.config["DD_CLIENT_TOKEN"],
        applicationId=app.config["DD_APPLICATION_ID"],
        dd_version=app.config["DD_VERSION"],
        dd_env=app.config["DD_ENV"],
        dd_site=app.config["DD_SITE"],
    )


@app.route("/api/top10/<room_id>", methods=['POST', 'DELETE'])
def top10_api(room_id=None):

    if room_id is None:
        log.warning("missing room_id in url")
        return flask.jsonify(), 400

    # DELETE

    if flask.request.method == 'DELETE':
        redis_client.delete(room_id)
        log.info("delete round {}".format(room_id))
        return flask.jsonify(), 204

    # POST

    # Get users list from URL query params
    users = flask.request.args.getlist("user")
    log.debug("users: {}".format(users))

    # Reject new round when too many users 
    if len(users) > 10:
        error = "too many users: max 10"
        log.warning(error)
        return flask.jsonify(error=error), 400

    # Shuffle cards
    values = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    random.shuffle(values)
    cards = {}
    i = 0
    for x in users:
        cards[x] = values[i]
        i = i+1

    # Increment round_id (1 for first round)
    if not redis_client.exists(room_id): 
        round_id = 1
    else:
        round_id = int(redis_client.hgetall(room_id)['id']) + 1

    # Store round properties
    round = {'id': round_id, 'cards': json.dumps(cards)}
    redis_client.hmset(room_id, round)
    redis_client.expire(room_id, 3600)
    log.info("set {} for round {}".format(round, room_id))
    
    # Broadcast new round event
    redis_pubsub.publish(room_id, json.dumps({'room': 'new', 'status': 'test' }))

    return flask.jsonify(room_id=room_id, round=round)
