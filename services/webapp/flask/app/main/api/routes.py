from app.main import main_api  # Import the Blueprint from __init__.py

import io, qrcode
import flask, flask_login

from models import Room, User, Code

import utils
log = utils.get_logger(__name__)


@main_api.route("/v1/rooms/<room_id>", methods=['GET'])
def room_get(room_id=None):
    '''Access rooms details'''

    if room_id is None:
        return flask.jsonify(), 400

    room = Room.get_by_id(room_id)
    if room is None:
        return flask.jsonify(), 404

    return flask.jsonify(room.to_dict(True)), 200


@main_api.route("/v1/rooms/<room_id>/round", methods=['POST'])
# @flask_login.login_required
def round_new(room_id=None):
    '''Start a new round in room'''

    if room_id is None:
        return flask.jsonify(), 400

    room = Room.get_by_id(room_id)
    if room is None:
        return flask.jsonify(), 404

    room.new_round()

    utils.publish(room_id, "round", "new")

    return flask.jsonify(room=room.to_dict()), 200


@main_api.route("/v1/rooms/<room_id>/join", methods=['POST'])
@flask_login.login_required
def room_join(room_id=None):
    '''Join a room'''

    if room_id is None:
        return flask.jsonify(), 400

    room = Room.get_by_id(room_id)
    if room is None:
        return flask.jsonify(), 404

    user_id = flask_login.current_user.id

    if room.users().exist(user_id):
        log.debug(f'user {user_id} already member of room {room_id}')
    else:
        log.info(f'adding user {user_id} to room {room_id}')
        room.users().add(user_id, role="watcher")
        utils.publish(room_id, "user:joined", user_id)

    return flask.jsonify(room=room.to_dict()), 200


@main_api.route("/v1/rooms/<room_id>/user/<user_id>", methods=['PATCH'])
@flask_login.login_required
def room_user(room_id=None, user_id=None):
    '''Changes properties of user in a room'''

    if room_id is None:
        return flask.jsonify(), 400

    room = Room.get_by_id(room_id)
    if room is None:
        return flask.jsonify(), 404

    if user_id is None:
        return flask.jsonify(), 400

    user = User.get_by_id(user_id)
    if user is None:
        return flask.jsonify(), 404

    users = room.users().all()

    if user_id not in users:
        return flask.jsonify(), 404

    if flask_login.current_user.id not in users:
        return flask.jsonify(), 403

    room.users().set(user_id, **flask.request.args)

    if "role" in flask.request.args:
        role = flask.request.args.get("role")
        room, rel = user.rooms().get_by_id(room_id)
        utils.publish(room_id, f"user:{rel.role}", user_id )

    return flask.jsonify(room=room.to_dict()), 200

@main_api.route('/v1/qrcode', methods=['GET'])
@flask_login.login_required
def qr_code():
    '''QR code generator'''

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
