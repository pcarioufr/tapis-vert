from app.main import main_api  # Import the Blueprint from __init__.py

import io, qrcode
import flask, flask_login

from models import Room, User, Code

import utils
from utils import get_logger
log = get_logger(__name__)


@main_api.route("/v1/rooms/<room_id>", methods=['GET'])
def room_get(room_id=None):

    if room_id is None:
        return flask.jsonify(), 400

    room = Room.get(room_id)
    if room is None:
        return flask.jsonify(), 404

    return flask.jsonify(room=room.to_dict()), 200


@main_api.route("/v1/rooms/<room_id>/round", methods=['POST'])
# @flask_login.login_required
def round_new(room_id=None):

    if room_id is None:
        return flask.jsonify(), 400

    room = Room.get(room_id)
    if room is None:
        return flask.jsonify(), 404

    PLAYERS = [ "Alice", "Bob", "Charlie", "Dan", "Eve" ]
    room.new_round(PLAYERS)

    utils.publish(room_id, "round", "new")

    return flask.jsonify(room=room.to_dict()), 200


@main_api.route("/v1/rooms/<room_id>/join", methods=['POST'])
@flask_login.login_required
def room_join(room_id=None):

    if room_id is None:
        return flask.jsonify(), 400

    room = Room.get(room_id)

    user_id = flask_login.current_user.id

    utils.publish(room_id, "joined", user_id)

    return flask.jsonify(room=room.to_dict()), 200


@main_api.route('/v1/qrcode', methods=['GET'])
def qr_code():

    link = flask.request.args.get("link")
    if link is None:
        return flask.jsonify(), 400

    size = flask.request.args.get("size")
    if size is None:
        size = 8

    qr = qrcode.QRCode(
            box_size=size, 
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            border=0
        )
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#ece2ce", back_color="#4f3111")
    img.convert('RGB')

    img_io = io.BytesIO()
    img.get_image().save(img_io, 'PNG')
    img_io.seek(0)

    return flask.send_file(img_io, mimetype='image/png')
