from ...admin import admin_web  # Import the Blueprint from __init__.py
from ...routines import render_template

import flask

import utils
log = utils.get_logger(__name__)


@admin_web.route("/list", methods=['GET'])
def list():
    
    return render_template("admin/list.jinja")
