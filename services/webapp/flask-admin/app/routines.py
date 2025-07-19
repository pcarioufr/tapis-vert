
from flask import current_app as app
import flask

import utils
log = utils.get_logger(__name__)


def render_template(template, **kwargs):
    """
    Custom render_template wrapper for admin templates.
    
    Args:
        template (str): Template file to render.
        **kwargs: Additional keyword arguments to pass to the template.
    """

    return flask.render_template(
        template,
        level=utils.LOG_LEVEL,
        host=app.config["HOST"],
        # Admin doesn't need client-side analytics
        session=flask.session,
        request_cookies=flask.request.cookies, # Include request cookies for debugging
        **kwargs
    )

