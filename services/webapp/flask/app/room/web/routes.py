from ...room import room_web

import flask, flask_login

from ...routines import render_template

from models import Room
import utils
log = utils.get_logger(__name__)


@room_web.route("/r/<room_id>", methods=['GET'])
def room_app(room_id=None):


    # Checks if the room exists
    if room_id is None:
        return flask.jsonify(), 400

    room = Room.get_by_id(room_id)
    if room is None:
        return flask.jsonify(), 404


    return render_template (
        "_room.jinja",
        user=flask_login.current_user,
        room=room
    )

