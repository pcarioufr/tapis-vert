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
    room = Room.get_by_id(room_id)
    if room is None:
        return flask.jsonify({"error": "room does not exist"}), 404

    timestamp = utils.now(False)
    content = flask.request.json.get("content")
    user_id = flask_login.current_user.id
    
    # Generate unique message ID
    message_id = new_id(8)

    message_obj = {
        "id": message_id,
        "timestamp": timestamp, 
        "content": content, 
        "author": user_id,
        "reactions": {}
    }

    # Get current messages array and append new message
    messages = json.loads(room.messages or "[]")
    messages.append(message_obj)
    
    # Update room with new messages JSON blob
    room.messages = json.dumps(messages)
    
    room.save()
    # Note: "saved successfully" log should only come from save() method itself

    # Publish message for WebSocket (keep as JSON string for compatibility)
    message_json = json.dumps(message_obj)
    utils.publish(room_id, f"message:new", message_json)

    return flask.jsonify(), 200


@public_api.route("/v1/rooms/<room_id>/messages/<message_id>/react", methods=['POST'])
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
    
    # Parse messages
    messages = json.loads(room.messages or "[]")
    
    # Find the message
    message = None
    message_index = None
    for i, msg in enumerate(messages):
        if msg.get("id") == message_id:
            message = msg
            message_index = i
            break
    
    if message is None:
        return flask.jsonify({"error": "message not found"}), 404
    
    # Ensure reactions field exists (backward compatibility)
    if "reactions" not in message:
        message["reactions"] = {}
    
    reactions = message["reactions"]
    
    # Add or remove reaction
    if action == "add":
        if emoji not in reactions:
            reactions[emoji] = []
        if user_id not in reactions[emoji]:
            reactions[emoji].append(user_id)
    elif action == "remove":
        if emoji in reactions and user_id in reactions[emoji]:
            reactions[emoji].remove(user_id)
            # Clean up empty emoji lists
            if len(reactions[emoji]) == 0:
                del reactions[emoji]
    
    # Update message in array
    messages[message_index] = message
    
    # Save back to room
    room.messages = json.dumps(messages)
    room.save()
    
    # Publish WebSocket event for real-time updates
    reaction_event = {
        "message_id": message_id,
        "emoji": emoji,
        "action": action,
        "user_id": user_id,
        "reactions": reactions
    }
    utils.publish(room_id, "message:reaction", json.dumps(reaction_event))
    
    log.info(f"Reaction {action}: user={user_id}, emoji={repr(emoji)}, message={message_id}, room={room_id}")
    return flask.jsonify({"success": True, "reactions": reactions}), 200


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