from app.admin import admin_web  # Import the Blueprint from __init__.py
from app.routines import render_template

import flask

import utils
log = utils.get_logger(__name__)


@admin_web.route("/list", methods=['GET'])
def list():
    
    return render_template("admin/list.jinja")


@admin_web.route("/redis", methods=['GET'])
def search():
    
    return render_template("admin/redis.jinja")
