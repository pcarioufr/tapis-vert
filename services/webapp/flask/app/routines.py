
from flask import current_app as app
import flask

import datetime

from utils import log, LOG_LEVEL
from utils import new_id

from flask_login import current_user

from app.auth import login


def render_template(template, **kwargs):
    """
    Custom render_template wrapper to include layout variables.
    
    Args:
        template (str): Template file to render.
        **kwargs: Additional keyword arguments to pass to the template.
    """

    return flask.render_template(
        template,
        user_id=current_user.id, # returns visitor_id if anonymous
        user_name=current_user.name,
        is_authenticated=current_user.is_authenticated,
        is_anonymous=current_user.is_anonymous,
        level=LOG_LEVEL,
        host=app.config["HOST"],
        clientToken=app.config["DD_CLIENT_TOKEN"],
        applicationId=app.config["DD_APPLICATION_ID"],
        dd_version=app.config["DD_VERSION"],
        dd_env=app.config["DD_ENV"],
        dd_site=app.config["DD_SITE"],
        session=flask.session,
        request_cookies=flask.request.cookies, # Include request cookies for debugging
        **kwargs
    )


def session_management():

    flask.session.permanent = True
    flask.session.modified = True
    app.permanent_session_lifetime = datetime.timedelta(seconds=1800)


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

