from . import admin  # Import the Blueprint from __init__.py

from flask import request, send_file, jsonify

from utils import log
from models import Room, User, MagicCode



@admin.route("/api/v1/codes", defaults={'code_id': None}, methods=['POST'])
@admin.route("/api/v1/codes/<code_id>", methods=['GET', 'DELETE'])
def code(code_id):


    if request.method == 'POST':
        
        user = User.create({ "name": "Change Me" })
        code = MagicCode.create({ "user_id": user.id })

        return jsonify(code.to_dict()), 201


    if code_id is None:

        return jsonify({"error": "missing code_id: /api/v1/codes/<code_id>"}), 400


    if request.method == 'DELETE':

        code = MagicCode.get(code_id)
        user = User.get(code.data.user_id)

        User.get(user.id).delete()
        MagicCode.get(code_id).delete()

        return jsonify(), 204


    if request.method == 'GET':

        code = MagicCode.get(code_id)
        return jsonify(code.to_dict()), 200


    return jsonify({"error": "unexpected request"}), 400



@admin.route("/api/v1/codes", methods=['GET'])
def list_codes():

    codes = MagicCode.scan_all()
    data = [code.to_dict() for code in codes]    
    return jsonify(data), 200


@admin.route("/api/v1/users", methods=['GET'])
def list_users():

    users = User.scan_all()
    data = [user.to_dict() for user in users]    
    return jsonify(data), 200


@admin.route("/api/v1/room", methods=['GET'])
def list_rooms():

    rooms = Room.scan_all()
    data = [room.to_dict() for room in rooms]
    return jsonify(data), 200
