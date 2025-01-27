from app.admin import admin_api  # Import the Blueprint from __init__.py

import flask 

from models import Room, User, Code, UserCodes

import utils
log = utils.get_logger(__name__)

import redis, os
import fnmatch
redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST"),
    db=os.environ.get("REDIS_DATA_DB"),
    decode_responses=True
)


@admin_api.route("/rooms", methods=['POST'])
@admin_api.route("/rooms/<room_id>", methods=['GET', 'PATCH', 'DELETE'])
def rooms(room_id=None):

    if flask.request.method == 'POST':

        name = flask.request.args.get("name")
        if name is None: 
            log.warning("no name passed, using Change Me")
            name = "Change Me"

        room = Room.create(name=name)
        return flask.jsonify(room.to_dict()), 201

    if room_id is None:
        return flask.jsonify(), 400

    room = Room.get_by_id(room_id)
    if room is None:
        return flask.jsonify(), 404

    if flask.request.method == 'DELETE':
        room.delete()
        return flask.jsonify(), 204

    if flask.request.method == 'GET':
        return flask.jsonify(room.to_dict()), 200

    if flask.request.method == 'PATCH':
        # TODO
        return flask.jsonify(room.to_dict()), 405


@admin_api.route("/users", methods=['POST'])
@admin_api.route("/users/<user_id>", methods=['GET', 'DELETE', 'PATCH'])
def users(user_id=None):

    if flask.request.method == 'POST':

        name = flask.request.args.get("name")
        if name is None: 
            log.warning("no name passed, using Change Me")
            name = "Change Me"

        user = User.create(name=name)
        code = Code.create()
        user.codes().add(code.id, type="login")

        user.save()

        return flask.jsonify(user.to_dict(True)), 201

    if user_id is None:
        return flask.jsonify(), 400

    user = User.get_by_id(user_id)
    if user is None:
        return flask.jsonify(), 404

    if flask.request.method == 'GET':
        user = User.get_by_id(user_id)
        return flask.jsonify(user.to_dict()), 200

    if flask.request.method == 'DELETE':
        user.delete()
        return flask.jsonify(), 204

    if flask.request.method == 'PATCH':
        # TODO
        return flask.jsonify(user.to_dict()), 405



@admin_api.route("/codes", methods=['GET'])
def list_codes():

    codes, cursor = Code.search()
    data = [code.to_dict(True) for code in codes]    
    return flask.jsonify(data), 200


@admin_api.route("/users", methods=['GET'])
def list_users():

    users, cursor = User.search()
    data = {}
    for user in users:
        data.update(user.to_dict(True))

    return flask.jsonify(data), 200


@admin_api.route("/rooms", methods=['GET'])
def list_rooms():

    rooms, cursor = Room.search()
    data = {}
    for room in rooms:
        data.update(room.to_dict(True))

    return flask.jsonify(data), 200


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


@admin_api.route("/delete_fields", methods=["POST"])
def remove_fields_for_keys():

    key_pattern = flask.request.args.get("key_pattern")
    field_pattern = flask.request.args.get("field_pattern")
    if not key_pattern or not field_pattern:
        return flask.jsonify({"error": "Missing key_pattern or field_pattern"}), 400

    matched_keys = list(redis_client.scan_iter(key_pattern))
    total_deleted = 0
    details = {}

    for k in matched_keys:
        fields = redis_client.hkeys(k)
        matching_fields = [f for f in fields if fnmatch.fnmatch(f, field_pattern)]
        if matching_fields:
            deleted = redis_client.hdel(k, *matching_fields)
            total_deleted += deleted
            details[k] = deleted

    return flask.jsonify({"status": "ok", "total_deleted": total_deleted, "details": details}), 200