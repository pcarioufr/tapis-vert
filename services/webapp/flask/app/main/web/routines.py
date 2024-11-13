from app.main import main_web

import datetime
import flask

from utils import get_logger
log = get_logger(__name__)

from utils import new_id

from flask_login import current_user

from app.auth import login


@main_web.before_request
def session_management():

    flask.session.permanent = True
    flask.session.modified = True
    main_web.permanent_session_lifetime = datetime.timedelta(seconds=1800)

@main_web.before_request
def visitor_id():
    
    # Ensure Session a Visitor ID
    if 'visitor_id' not in flask.session:

        visitor_id = f"v-{new_id()}"
        flask.session['visitor_id'] = visitor_id
        log.info(f"assign a visitor_id {visitor_id}")

    # Assign Visitor ID has Anonymous User ID
    if not current_user.is_authenticated:
    
        visitor_id = flask.session['visitor_id']
        current_user.id = visitor_id

