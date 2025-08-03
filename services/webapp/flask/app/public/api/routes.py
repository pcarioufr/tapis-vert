from ...public import public_api  # Import the Blueprint from __init__.py

import io, qrcode
import flask, flask_login

from models import Room, User, Code
from auth import code_auth  # Import from auth library

import utils, json
log = utils.get_logger(__name__)


@public_api.route("/v1/rooms/<room_id>", methods=['GET'])
def room_get(room_id=None):
    '''Access rooms details'''

    if room_id is None:
        return flask.jsonify(), 400

    room = Room.get_by_id(room_id)
    if room is None:
        return flask.jsonify(), 404

    return flask.jsonify(room.to_dict(True)), 200


@public_api.route("/v1/rooms/<room_id>/round", methods=['POST'])
# @flask_login.login_required
def round_new(room_id=None):
    '''Start a new round in room'''

    if room_id is None:
        return flask.jsonify(), 400

    room = Room.get_by_id(room_id)
    if room is None:
        return flask.jsonify(), 404

    round, cards = room.new_round()

    utils.publish(room_id, "round:new", round)

    return flask.jsonify(room=room.to_dict()), 200


@public_api.route("/v1/rooms/<room_id>/join", methods=['POST'])
@flask_login.login_required
def room_join(room_id=None):
    '''Join a room'''

    if room_id is None:
        return flask.jsonify(), 400

    room = Room.get_by_id(room_id)
    if room is None:
        return flask.jsonify(), 404

    user_id = flask_login.current_user.id

    if room.users().exists(user_id):
        log.debug(f'user {user_id} already member of room {room_id}')
    else:
        log.info(f'adding user {user_id} to room {room_id}')
        room.users().add(user_id, role="watcher")
        utils.publish(room_id, "user:joined", user_id)

    return flask.jsonify(room=room.to_dict()), 200


@public_api.route("/v1/rooms/<room_id>/message", methods=['POST'])
@flask_login.login_required
def room_message(room_id=None):
    log.info(f"🔧 MESSAGE DEBUG: Starting message endpoint for room_id={room_id}")
    
    room = Room.get_by_id(room_id)
    if room is None:
        log.info(f"🔧 MESSAGE DEBUG: Room {room_id} not found")
        return flask.jsonify({"error": "room does not exist"}), 404

    timestamp = utils.now(False)
    content = flask.request.json.get("content")
    user_id = flask_login.current_user.id

    log.info(f"🔧 MESSAGE DEBUG: Room {room_id} before message - data keys: {list(room.data.keys())}")
    log.info(f"🔧 MESSAGE DEBUG: Room {room_id} before message - cards preview: {str(room.cards)[:100]}...")
    log.info(f"🔧 MESSAGE DEBUG: Room {room_id} before message - messages: {room.messages}")

    message_obj = {"timestamp": timestamp, "content": content, "author": user_id}

    # Get current messages array and append new message
    messages = json.loads(room.messages or "[]")
    log.info(f"🔧 MESSAGE DEBUG: Existing messages count: {len(messages)}")
    
    messages.append(message_obj)
    log.info(f"🔧 MESSAGE DEBUG: New messages count: {len(messages)}")
    
    # Update room with new messages JSON blob
    room.messages = json.dumps(messages)
    log.info(f"🔧 MESSAGE DEBUG: Room {room_id} after message update - data keys: {list(room.data.keys())}")
    log.info(f"🔧 MESSAGE DEBUG: Room {room_id} after message update - cards preview: {str(room.cards)[:100]}...")
    log.info(f"🔧 MESSAGE DEBUG: Room {room_id} messages field length: {len(room.messages)} chars")
    
    log.info(f"🔧 MESSAGE DEBUG: About to save room {room_id}")
    
    # DETAILED METHOD INTROSPECTION TO DEBUG SAVE ISSUE
    log.info(f"🚨 SAVE INTROSPECTION: room.save = {room.save}")
    log.info(f"🚨 SAVE INTROSPECTION: room.save.__qualname__ = {getattr(room.save, '__qualname__', 'NO_QUALNAME')}")
    log.info(f"🚨 SAVE INTROSPECTION: room.save.__module__ = {getattr(room.save, '__module__', 'NO_MODULE')}")
    log.info(f"🚨 SAVE INTROSPECTION: room.save.__func__ = {getattr(room.save, '__func__', 'NO_FUNC')}")
    log.info(f"🚨 SAVE INTROSPECTION: type(room) = {type(room)}")
    log.info(f"🚨 SAVE INTROSPECTION: room.__class__.__mro__ = {room.__class__.__mro__}")
    
    try:
        room.save()
        log.info(f"🔧 MESSAGE DEBUG: room.save() completed without exception")
    except Exception as e:
        log.error(f"🚨 SAVE EXCEPTION: {e}")
        log.error(f"🚨 SAVE EXCEPTION TYPE: {type(e)}")
        raise
    # Note: "saved successfully" log should only come from save() method itself

    # Publish message for WebSocket (keep as JSON string for compatibility)
    message_json = json.dumps(message_obj)
    utils.publish(room_id, f"message:new", message_json)

    return flask.jsonify(), 200


@public_api.route("/v1/rooms/<room_id>", methods=['PATCH'])
@flask_login.login_required
def room_patch(room_id=None):
    '''Join a room'''

    if room_id is None:
        return flask.jsonify(), 400

    room = Room.get_by_id(room_id)
    if room is None:
        return flask.jsonify(), 404

    user_id = flask_login.current_user.id

    if not room.users().exists(user_id):
        return flask.jsonify(), 401

    for k,v in flask.request.args.items():

        log.debug(f'patching room {room_id} with {k}={v}')

        path = k.split(':')
        
        if path[0] != "cards":
            return flask.jsonify(), 400
        else: 
            if path[1] not in room.cards:
                log.debug(f'invalid card {path[1]}')
                return flask.jsonify(), 404
            if path[2] not in ["flipped", "peeked"]:
                log.debug(f'invalid card property {path[2]}')
                return flask.jsonify(), 400
            if path[2] == "peeked":
                if path[3] != user_id:
                    log.debug(f'peeked card {path[3]} != user {user_id}')
                    return flask.jsonify(), 401

        Room.patch(room_id, k, v)

        utils.publish(room_id, f"{k}", v)

    return flask.jsonify(), 200


@public_api.route("/v1/rooms/<room_id>/user/<user_id>", methods=['PATCH'])
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

@public_api.route('/v1/qrcode', methods=['GET'])
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



@public_api.route("/auth/login", methods=["POST"])
def auth_login():
    """Logs in the current user."""

    code_id = flask.request.args.get("code_id")
    if code_id is None: 
        return flask.jsonify({"success": False}), 404

    user = code_auth(code_id)

    return flask.jsonify({"success": True, "user": user.to_dict(True) })


@public_api.route("/auth/me", methods=["GET"])
@flask_login.login_required
def me():
    """Logs in the current user."""

    user = flask_login.current_user

    return flask.jsonify( user.to_dict(True) )


@public_api.route("/auth/logout", methods=["POST"])
@flask_login.login_required
def auth_logout():
    """Logs out the current user."""
    flask_login.logout_user()  # Flask-Login function to clear the session
    return flask.jsonify({"success": True, "message": "Logout successful"})


@public_api.route("/auth/test", methods=["GET"])
@flask_login.login_required
def auth_ping():
    """Tests login mechanism."""
    return flask.jsonify({"message": "pong"}), 200