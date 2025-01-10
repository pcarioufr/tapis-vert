from app.room import room_web
from app.auth import code_auth

import flask, flask_login
import datetime

import utils
log = utils.get_logger(__name__)



@room_web.before_request
def code_authentication():

    if flask.request.args.get("code_id"):
        log.info(f"attempting code login...")

        code_id = flask.request.args.get("code_id")
        user = code_auth(code_id)


@room_web.before_request
def session_management():

    flask.session.permanent = True
    flask.session.modified = True
    room_web.permanent_session_lifetime = datetime.timedelta(seconds=3600)


@room_web.before_request
def visitor_id():
    
    # Ensure Session a Visitor ID
    if 'visitor_id' not in flask.session:

        visitor_id = f"v-{utils.new_id()}"
        flask.session['visitor_id'] = visitor_id
        log.info(f"assign a visitor_id {visitor_id}")

    # Assign Visitor ID has Anonymous User ID
    if not flask_login.current_user.is_authenticated:
    
        visitor_id = flask.session['visitor_id']
        flask_login.current_user.id = visitor_id

