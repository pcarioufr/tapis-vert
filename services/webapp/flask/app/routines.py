
from flask import current_app as app
import flask

import datetime

from utils import log, LOG_LEVEL



def render_template(template, **kwargs):
    """
    Custom render_template wrapper to include layout variables.
    
    Args:
        template (str): Template file to render.
        **kwargs: Additional keyword arguments to pass to the template.
    """

    return flask.render_template(
        template,
        user_id=flask.session.get("user_id"),        
        is_anonymous=False,
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



# @app.before_request
# def before_request():

#     flask.session.permanent = True
#     flask.session.modified = True
#     app.permanent_session_lifetime = datetime.timedelta(seconds=1800)

#     # check master cookie accounting for cookie acceptance 
#     ok_cookie = request.cookies.get("ok_cookie")
#     if ok_cookie is None:
#         flask.g.ok_cookie = "false"
#     else:
#         flask.g.ok_cookie = ok_cookie
