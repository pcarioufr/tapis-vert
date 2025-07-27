from ...public import public_web
from ...auth import code_auth

import flask, flask_login
import datetime

import utils
import nanoid
log = utils.get_logger(__name__)



@public_web.before_request
def code_authentication():

    if flask.request.args.get("code_id"):
        log.info(f"attempting code login...")

        code_id = flask.request.args.get("code_id")
        user = code_auth(code_id)


@public_web.before_request
def session_management():

    flask.session.permanent = True
    flask.session.modified = True
    public_web.permanent_session_lifetime = datetime.timedelta(seconds=3600)


@public_web.before_request
def visitor_id():
    
    # Ensure Session a Visitor ID
    if 'visitor_id' not in flask.session:

        # Generate simple visitor ID (shorter than game IDs)
        def generate_visitor_id():
            return f"v-{nanoid.non_secure_generate('0123456789abcdef', 8)}"
            
        visitor_id = generate_visitor_id()
        flask.session['visitor_id'] = visitor_id
        log.info(f"assign a visitor_id {visitor_id}")

    # Assign Visitor ID has Anonymous User ID
    if not flask_login.current_user.is_authenticated:
    
        visitor_id = flask.session['visitor_id']
        flask_login.current_user.id = visitor_id

