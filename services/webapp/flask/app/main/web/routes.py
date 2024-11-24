from app.main import main_web

import flask

from app.routines import render_template
from utils import get_logger
log = get_logger(__name__)


@main_web.route("/r/<room_id>", methods=['GET'])
def room_app(room_id=None):


    # Checks if the room exists
    if room_id is None:
        return flask.jsonify(), 404


    return render_template (
        "main/r.jinja",
        room_id=room_id
    )

