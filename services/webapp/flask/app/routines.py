from flask import current_app as app
import flask

import datetime

import utils
log = utils.get_logger(__name__)

# Import login system (needed for public routes)
from .auth import login


def render_template(template, **kwargs):
    """
    Custom render_template wrapper to include layout variables.
    
    Args:
        template (str): Template file to render.
        **kwargs: Additional keyword arguments to pass to the template.
    """

    return flask.render_template(
        template,
        level=utils.LOG_LEVEL,
        host=app.config["HOST"],
        clientToken=app.config["DD_CLIENT_TOKEN"],
        applicationId=app.config["DD_APPLICATION_ID"],
        dd_version=app.config["DD_VERSION"],
        dd_env=app.config["DD_ENV"],
        dd_site=app.config["DD_SITE"],
        mp_token=app.config["MP_TOKEN"],
        session=flask.session,
        request_cookies=flask.request.cookies, # Include request cookies for debugging
        **kwargs
    ) 