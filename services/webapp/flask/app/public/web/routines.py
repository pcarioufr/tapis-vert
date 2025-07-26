from ...public import public_web
from auth import code_auth

import flask, flask_login
import datetime

import utils
import nanoid
log = utils.get_logger(__name__)



@public_web.before_request
def request_setup():
    
    # 1. Initialize mutable query params from request args
    flask.g.query_params = dict(flask.request.args)
    
    # 2. Handle code-based authentication (QR code login)
    if flask.request.args.get("code_id"):
        log.info(f"attempting code login...")
        code_id = flask.request.args.get("code_id")
        user = code_auth(code_id)
        
        # Remove code_id from URL after successful authentication
        if 'code_id' in flask.g.query_params:
            del flask.g.query_params['code_id']
            log.info(f"removed code_id from URL params after login")
    
    # 3. Session management
    flask.session.permanent = True
    flask.session.modified = True
    public_web.permanent_session_lifetime = datetime.timedelta(seconds=3600)
    
    # 4. Visitor ID management
    # Ensure Session has a Visitor ID
    if 'visitor_id' not in flask.session:
        # Generate simple visitor ID (shorter than game IDs)
        def generate_visitor_id():
            return f"v-{nanoid.non_secure_generate('0123456789abcdef', 8)}"
            
        visitor_id = generate_visitor_id()
        flask.session['visitor_id'] = visitor_id
        log.info(f"assign a visitor_id {visitor_id}")

    # Assign Visitor ID as Anonymous User ID
    if not flask_login.current_user.is_authenticated:
        visitor_id = flask.session['visitor_id']
        flask_login.current_user.id = visitor_id

