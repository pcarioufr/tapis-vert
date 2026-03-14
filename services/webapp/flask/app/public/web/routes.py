from ...public import public_web

import flask, flask_login

from ...routines import render_template

from models import Room
import utils
log = utils.get_logger(__name__)


@public_web.route("/", methods=['GET'])
def home():
    rooms = []
    if flask_login.current_user.is_authenticated:
        user = flask_login.current_user
        for room_id in user.rooms().all():
            room = Room.get_by_id(room_id)
            if room:
                rooms.append({"id": room.id, "name": room.name})
    return render_template("public/home.jinja", rooms=rooms)


@public_web.route("/r/<room_id>", methods=['GET'])
def room_app(room_id=None):

    # Checks if the room exists
    if room_id is None:
        return render_template("public/404.jinja"), 404

    room = Room.get_by_id(room_id)
    if room is None:
        return render_template("public/404.jinja"), 404

    return render_template (
        "public/room.jinja",
        room=room
    )

