from . import admin  # Import the Blueprint from __init__.py

import flask 

from utils import log
from models import Room, User, MagicCode



@admin.route("/api/v1/invite", methods=['POST'])
def invite():

    name = flask.request.args.get("name")
    if name is None: 
        name = "Change Me"

    user = User.create({ "name": name })

    code = MagicCode.create({ "user_id": user.id })
    user.code_id = code.id
    user.save()

    return flask.jsonify(code.to_dict()), 201



@admin.route("/api/v1/users/<user_id>", methods=['GET', 'DELETE'])
def users(user_id):


    if user_id is None:

        return flask.jsonify({"error": "missing code_id: /api/v1/users/<user_id>"}), 400


    if flask.request.method == 'DELETE':

        user = User.get(user_id)
        code = MagicCode.get(user.data["code_id"])

        code.delete()
        user.delete()

        return flask.jsonify(), 204


    if flask.request.method == 'GET':

        user = User.get(user_id)
        return flask.jsonify(user.to_dict()), 200



@admin.route("/api/v1/codes/<code_id>", methods=['GET', 'DELETE'])
def codes(code_id):


    if code_id is None:

        return flask.jsonify({"error": "missing code_id: /api/v1/codes/<code_id>"}), 400


    if flask.request.method == 'DELETE':

        code = MagicCode.get(code_id)
        user = User.get(code.data["user_id"])

        user.delete()
        code.delete()

        return flask.jsonify(), 204


    if flask.request.method == 'GET':

        code = MagicCode.get(code_id)
        return flask.jsonify(code.to_dict()), 200



@admin.route("/api/v1/codes", methods=['GET'])
def list_codes():

    codes = MagicCode.scan_all()
    data = [code.to_dict() for code in codes]    
    return flask.jsonify(data), 200


@admin.route("/api/v1/users", methods=['GET'])
def list_users():

    users = User.scan_all()
    data = [user.to_dict() for user in users]    
    return flask.jsonify(data), 200


@admin.route("/api/v1/room", methods=['GET'])
def list_rooms():

    rooms = Room.scan_all()
    data = [room.to_dict() for room in rooms]
    return flask.jsonify(data), 200
