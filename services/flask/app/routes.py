import flask

from flask import current_app as app

import redis
import os

from app.logs import log

import random
import time


redis_client = redis.Redis(
            host=app.config["REDIS_HOST"],
            decode_responses=True
        )

def random_id():
    rid = ''.join((random.choice('1234567890abcdef') for i in range(8)))
    return rid

@app.route("/ping")
def ping():

    log.info("ping successful")
    return flask.jsonify(response="pong"), 200


@app.route("/top10/<round_id>", methods=['GET'])
def top10_app(round_id=None):

    if round_id is None:
        return flask.jsonify(), 404


    # Login when user_id is injected as a URL param 
    if flask.request.args.get("user") is not None:

        user_id = flask.request.args.get("user")
        flask.session["user_id"] = user_id

        log.info("user {} logged in".format(user_id))


    # Login as random user (when session cookie is empty)
    elif flask.session.get("user_id") is None:

        return flask.jsonify(), 401

    # Recognizes an existing user (through session cookie)
    else:
        user_id = flask.session.get("user_id")


    # if not redis_client.exists(round_id):
    #     log.info("round {} not found".format(round_id))
    #     return flask.jsonify(), 404


    cards = redis_client.hgetall(round_id)

    return flask.render_template(
        "home.jinja",
        user_id=flask.session.get("user_id"),
        round_id=round_id,
        cards=cards,
        # user_init_count=user_init_count,
        is_anonymous=False,
        clientToken=app.config["DD_CLIENT_TOKEN"],
        applicationId=app.config["DD_APPLICATION_ID"],
        dd_version=app.config["DD_VERSION"],
        dd_env=app.config["DD_ENV"],
        dd_site=app.config["DD_SITE"],
    )


@app.route("/api/top10/<round_id>", methods=['POST', 'DELETE'])
def top10_api(round_id=None):

    if round_id is None:
        return flask.jsonify(), 404

    if flask.request.method == 'DELETE':
        redis_client.delete(round_id)
        log.info("delete round {}".format(round_id))
        return flask.jsonify(), 204

    users = flask.request.args.getlist("user")
    log.info("users: {}".format(users))

    if len(users) > 10:
        error = "too many users (max 10)"
        log.warning(error)
        return flask.jsonify(error=error), 400

    values = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    random.shuffle(values)
    log.info("values: {}".format(values))

    cards = {}
    i = 0
    for x in users:
        cards[x] = values[i]
        i = i+1

    redis_client.hmset(round_id, cards)
    redis_client.expire(round_id, 3600)
    log.info("set {} for round {}".format(cards, round_id))

    cards = redis_client.hgetall(round_id)

    return flask.jsonify(round_id=round_id, cards=cards)
