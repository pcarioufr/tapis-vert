import flask
from flask import current_app as app

from utils import get_logger
log = get_logger(__name__)

@app.route("/ping")
def ping():

    log.info("ping successful")
    return flask.jsonify(response="pong"), 200
