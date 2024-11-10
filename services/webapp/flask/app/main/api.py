from . import main  # Import the Blueprint from __init__.py

from flask import request, send_file, jsonify

from utils import log
from models import Room, User

import io
import qrcode



@main.route("/api//v1/r/<room_id>", methods=['GET', 'DELETE'])
def room_api(room_id=None):

    if room_id is None:
        log.warning("missing room_id in url")
        return jsonify(), 400

    room = Room(room_id)

    if request.method == 'DELETE':

        room.delete()
        return jsonify(), 204

    if request.method == 'GET':

        return jsonify(room=room.get()), 200




@main.route("/api//v1/r/<room_id>/round", methods=['POST'])
def round_api(room_id=None):

    if room_id is None:
        log.warning("missing room_id in url")
        return jsonify(), 400

    room = Room(room_id)

    # POST

    # Get users list from URL query params
    players = request.args.getlist("user")
    log.debug("players: {}".format(players))

    room.new_round(players)

    return jsonify(room.get())



@main.route("/api//v1/<room_id>/users/<user_id>", methods=['POST', 'DELETE'])
def room_user_id_api(room_id=None, user_id=None):

    if room_id is None:
        log.warning("missing room_id in url")
        return jsonify(), 400

    if user_id is None:
        log.warning("missing user_id in url")
        return jsonify(), 400

    room = Room(room_id)

    # POST
    if request.method == 'POST':
        room.set_user(user_id, "offline")
        return jsonify(), 200

    # DELETE
    if request.method == 'DELETE':
        room.remove_user(user_id)
        return jsonify(), 204



@main.route("/api//v1/users/<user_id>", methods=['POST', 'DELETE', 'GET', 'PUT'])
def user_api(user_id=None):

    if user_id is None:
        log.warning("missing user_id in url")
        return jsonify(), 400


    if request.method == 'POST':
        user = User.create({ "status" : "hello"})
        return jsonify(user=user.to_dict()), 200


    user = User.get(user_id)
    if user is None:
        return jsonify(), 404

    if request.method == 'GET':
        return jsonify(user=user.to_dict()), 200

    if request.method == 'PUT':
        user.status = "world"
        user.save()
        user = User.get(user_id)
        return jsonify(user=user.to_dict()), 200

    if request.method == 'DELETE':
        user.delete()
        return jsonify(), 204


@main.route('/api/v1/qrcode', methods=['GET'])
def qr_code():

    link = request.args.get("link")
    if link is None:
        return jsonify(), 400

    size = request.args.get("size")
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

    return send_file(img_io, mimetype='image/png')
