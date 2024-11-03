import flask
from flask import current_app as app

from utils import log


@app.route("/ping")
def ping():

    log.info("ping successful")
    return flask.jsonify(response="pong"), 200
