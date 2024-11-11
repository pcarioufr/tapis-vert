from app.main import main_api  # Import the Blueprint from __init__.py

import flask, flask_login

from utils import log
from models import Room, User, Code

import io
import qrcode



@main_api.route("/v1/r/<room_id>", methods=['GET', 'DELETE'])
def room_api(room_id=None):

    if room_id is None:
        log.warning("missing room_id in url")
        return flask.jsonify(), 400

    room = Room(room_id)

    if flask.request.method == 'DELETE':

        room.delete()
        return flask.jsonify(), 204

    if flask.request.method == 'GET':

        return flask.jsonify(room=room.get()), 200




@flask_login.login_required
@main_api.route("/v1/users/<user_id>", methods=['DELETE', 'GET', 'PUT'])
def user_api(user_id=None):

    if user_id is None:
        log.warning("missing user_id in url")
        return flask.jsonify(), 400

    if user_id != flask_login.current_user.id:
        return flask.jsonify(), 403

    user = User.get(user_id)

    if flask.request.method == 'GET':
        return flask.jsonify(user=user.to_dict()), 200

    if flask.request.method == 'PUT':
        user.data = flask.request.args
        user.save()
        user = User.get(user_id)
        return flask.jsonify(user=user.to_dict()), 200

    if flask.request.method == 'DELETE':

        code = Code.get(user.code_id)
        code.delete()

        user.delete()

        return flask.jsonify(), 204




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
