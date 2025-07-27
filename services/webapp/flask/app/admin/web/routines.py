from ...admin import admin_web

import flask

import utils
log = utils.get_logger(__name__)


@admin_web.before_request
def request_setup():
    
    # 1. Initialize mutable query params from request args
    flask.g.query_params = dict(flask.request.args) 