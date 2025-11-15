from ...public import public_api  # Import the Blueprint from __init__.py

import io, qrcode
import flask, flask_login

from models import Room, User, Code, new_id
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

    # ORM automatically unflattens messages from Redis
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

    # ORM automatically unflattens all fields including messages (empty after new_round)
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

    # ORM automatically unflattens all fields including messages
    return flask.jsonify(room=room.to_dict()), 200


@public_api.route("/v1/rooms/<room_id>/message", methods=['POST'])
@flask_login.login_required
def room_message(room_id=None):
    room = Room.get_by_id(room_id)
    if room is None:
        return flask.jsonify({"error": "room does not exist"}), 404

    timestamp = utils.now(False)
    content = flask.request.json.get("content")
    user_id = flask_login.current_user.id
    
    # Generate unique message ID
    message_id = new_id(8)

    # Add message using atomic patch operations
    # ORM will flatten: messages:{msg_id}:content, messages:{msg_id}:timestamp, etc.
    Room.patch(room_id, f"messages:{message_id}:id", message_id, add=True)
    Room.patch(room_id, f"messages:{message_id}:timestamp", str(timestamp), add=True)
    Room.patch(room_id, f"messages:{message_id}:content", content, add=True)
    Room.patch(room_id, f"messages:{message_id}:author", user_id, add=True)
    
    # Build message object for WebSocket broadcast
    message_obj = {
        "id": message_id,
        "timestamp": timestamp, 
        "content": content, 
        "author": user_id,
        "reactions": {}
    }

    # Publish message for WebSocket
    message_json = json.dumps(message_obj)
    utils.publish(room_id, f"message:new", message_json)

    return flask.jsonify(), 200


@public_api.route("/v1/rooms/<room_id>/messages/<message_id>/react", methods=['PATCH'])
@flask_login.login_required
def message_react(room_id=None, message_id=None):
    """Add or remove a reaction to a message"""
    
    room = Room.get_by_id(room_id)
    if room is None:
        return flask.jsonify({"error": "room does not exist"}), 404
    
    user_id = flask_login.current_user.id
    
    # Check user is member of room
    if not room.users().exists(user_id):
        return flask.jsonify({"error": "user not in room"}), 403
    
    # Get request data
    emoji = flask.request.json.get("emoji")
    action = flask.request.json.get("action")
    
    # Log emoji details for debugging
    log.debug(f"Received emoji: {repr(emoji)}, len: {len(emoji) if emoji else 'None'}, bytes: {emoji.encode('utf-8') if emoji else 'None'}")
    
    # Validate emoji exists and is reasonable length
    # Allow up to 10 characters to support compound emojis (e.g., ❤️ with variation selector)
    if not emoji or len(emoji) > 10:
        log.warning(f"Invalid emoji validation: emoji={repr(emoji)}, len={len(emoji) if emoji else 'None'}")
        return flask.jsonify({"error": "emoji must be a single emoji character"}), 400
    
    # Validate action
    if action not in ["add", "remove"]:
        return flask.jsonify({"error": "action must be 'add' or 'remove'"}), 400
    
    # Verify message exists in messages dict
    if not room.messages or message_id not in room.messages:
        return flask.jsonify({"error": "message not found"}), 404
    
    # Add or remove reaction using atomic patch operation
    # ORM flattens: messages:{msg_id}:reactions:{emoji}:{user_id} = "True"
    reaction_key = f"messages:{message_id}:reactions:{emoji}:{user_id}"
    
    if action == "add":
        Room.patch(room_id, reaction_key, "True", add=True)
    elif action == "remove":
        Room.delete_field(room_id, reaction_key)
    
    # Publish WebSocket event for real-time updates
    reaction_event = {
        "message_id": message_id,
        "emoji": emoji,
        "action": action,
        "user_id": user_id
    }
    utils.publish(room_id, "message:reaction", json.dumps(reaction_event))
    
    log.info(f"Reaction {action}: user={user_id}, emoji={repr(emoji)}, message={message_id}, room={room_id}")
    return flask.jsonify({"success": True}), 200


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

    # ORM automatically unflattens all fields including messages
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