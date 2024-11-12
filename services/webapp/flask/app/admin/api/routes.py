from app.admin import admin_api  # Import the Blueprint from __init__.py

import flask 

from utils import log
from models import Room, User, Code, UserCode



@admin_api.route("/v1/invite", methods=['POST'])
def invite():

    name = flask.request.args.get("name")
    if name is None: 
        name = "Change Me"

    user = User.create({ "name": name })

    code = Code.create({ "user_id": user.id })
    user.code_id = code.id
    user.save()

    UserCode.create(user.id, code.id)

    return flask.jsonify(code.to_dict()), 201



@admin_api.route("/v1/rooms/<room_id>", methods=['GET', 'DELETE'])
def rooms(room_id):

    if room_id is None:

        return flask.jsonify({"error": "missing code_id: /api/v1/rooms/<room_id>"}), 400


    if flask.request.method == 'DELETE':

        room = Room.get(room_id)
        room.delete()

        return flask.jsonify(), 204


    if flask.request.method == 'GET':

        room = User.get(room_id)
        return flask.jsonify(room.to_dict()), 200


@admin_api.route("/v1/user_codes/<user_id>", methods=['GET'])
def user_codes(user_id):

    if user_id is None:

        return flask.jsonify({"error": "missing code_id: /api/v1/users/<user_id>/codes"}), 400

    codes = UserCode.get_right_for_left(user_id)
    return flask.jsonify(codes)




@admin_api.route("/v1/users/<user_id>", methods=['GET', 'DELETE'])
def users(user_id):


    if user_id is None:

        return flask.jsonify({"error": "missing code_id: /api/v1/users/<user_id>"}), 400


    if flask.request.method == 'DELETE':

        user = User.get(user_id)
        code = Code.get(user.code_id)

        code.delete()
        user.delete()

        return flask.jsonify(), 204


    if flask.request.method == 'GET':

        user = User.get(user_id)
        return flask.jsonify(user.to_dict()), 200



@admin_api.route("/v1/codes/<code_id>", methods=['GET', 'DELETE'])
def codes(code_id):


    if code_id is None:

        return flask.jsonify({"error": "missing code_id: /api/v1/codes/<code_id>"}), 400


    if flask.request.method == 'DELETE':

        code = Code.get(code_id)
        user = User.get(code.user_id)

        user.delete()
        code.delete()

        return flask.jsonify(), 204


    if flask.request.method == 'GET':

        code = Code.get(code_id)
        return flask.jsonify(code.to_dict()), 200



@admin_api.route("/v1/codes", methods=['GET'])
def list_codes():

    codes = Code.scan_all()
    data = [code.to_dict() for code in codes]    
    return flask.jsonify(data), 200


@admin_api.route("/v1/users", methods=['GET'])
def list_users():

    users = User.scan_all()
    data = [user.to_dict() for user in users]    
    return flask.jsonify(data), 200


@admin_api.route("/v1/rooms", methods=['GET'])
def list_rooms():

    rooms = Room.scan_all()
    data = [room.to_dict() for room in rooms]
    return flask.jsonify(data), 200

@admin_api.route("/v1/user_codes", methods=['GET'])
def list_user_magiccode_associations():
    associations = UserCode.list_all_associations()
    return flask.jsonify(associations), 200



import redis, os

redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST"),
    db=os.environ.get("REDIS_DATA_DB"),
    decode_responses=True
)
    

@admin_api.route('/search', methods=['GET'])
def search_keys():

    # Get the key pattern from the query parameters
    key_pattern = flask.request.args.get('pattern', '*')
    max_results = 100
    results = []

    # Use SCAN to fetch keys matching the pattern, with a limit of max_results
    for key in redis_client.scan_iter(key_pattern, count=100):
        # Retrieve the hashmap associated with each key
        hashmap = redis_client.hgetall(key)
        # Append the key and its hashmap to the results
        results.append({
            'key': key,
            'hashmap': str(hashmap)  # Convert hashmap to string for simplicity
        })
        # Stop if we've reached the max_results cap
        if len(results) >= max_results:
            break

    return flask.jsonify(results), 200



@admin_api.route('/users/<user_id>/codes', methods=['GET'])
def user_to_codes(user_id=None):

    codes = UserCode.get_right_ids_for_left(user_id)

    return flask.jsonify(codes), 200


@admin_api.route('/codes/<code_id>/users', methods=['GET'])
def code_to_users(code_id=None):

    users = UserCode.get_left_ids_for_right(code_id)

    return flask.jsonify(users), 200
