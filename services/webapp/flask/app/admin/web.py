from . import admin  # Import the Blueprint from __init__.py

import flask

from utils import log


@admin.route("/list", methods=['GET'])
def test():
    

    return flask.render_template("admin/list.jinja")
