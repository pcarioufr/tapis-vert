from app.admin import admin_web  # Import the Blueprint from __init__.py

import flask

from utils import log


@admin_web.route("/list", methods=['GET'])
def list():
    
    return flask.render_template("admin/list.jinja")


@admin_web.route("/redis", methods=['GET'])
def search():
    
    return flask.render_template("admin/redis.jinja")
