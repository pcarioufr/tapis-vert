from ...admin import admin_api  # Import the Blueprint from __init__.py

import flask 

from models import Room, User, Code, UserCodes

import utils
log = utils.get_logger(__name__)


@admin_api.route("/ping", methods=['GET'])
def ping():
    """Admin API health check endpoint"""
    log.info("admin ping successful")
    return flask.jsonify(response="pong", service="admin"), 200

import redis, os
redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST"),
    db=os.environ.get("REDIS_DATA_DB"),
    decode_responses=True
)


@admin_api.route("/flush", methods=['POST'])
def flush_redis():
    """Flush (clear) the entire Redis database"""
    try:
        # Get count before flushing for logging
        current_db = redis_client.connection_pool.connection_kwargs.get('db', 0)
        key_count = redis_client.dbsize()  # Much simpler way to get key count
        
        # Flush the current database
        redis_client.flushdb()
        
        # Verify it's empty
        remaining_keys = redis_client.dbsize()
        
        log.info(f"Redis database flushed: {key_count} keys deleted, {remaining_keys} remaining")
        
        return flask.jsonify({
            "status": "ok", 
            "message": "Redis database flushed successfully",
            "keys_deleted": key_count,
            "remaining_keys": remaining_keys
        }), 200
        
    except Exception as e:
        log.error(f"Failed to flush Redis database: {str(e)}")
        return flask.jsonify({
            "status": "error", 
            "message": f"Failed to flush Redis database: {str(e)}"
        }), 500


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