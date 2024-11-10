import flask, flask_login

from . import auth  # Import the Blueprint from __init__.py

from models import User, MagicCode
from utils import log

@auth.route("/login", methods=["POST"])
def auth_login():
    """Logs in the current user."""

    code_id = flask.request.args.get("code_id")
    if code_id is None: 
        return flask.jsonify({"success": False}), 404

    code = MagicCode.get(code_id)
    if code is None:
        return flask.jsonify({"success": False}), 403
    
    log.info(f'{code}')

    user_id = code.user_id
    user = User.get(user_id)
    user_name = user.name

    if user is not None:
        flask_login.login_user(user)
        log.info(f"user {user_id}:{user_name} logged in")
        return flask.jsonify({"success": True, "user": user.to_dict() })
    else:
        log.warning(f"login with code for invalid user_id {user_id}")
        return flask.jsonify({"success": False}), 403


@auth.route("/logout", methods=["POST"])
@flask_login.login_required
def auth_logout():
    """Logs out the current user."""
    flask_login.logout_user()  # Flask-Login function to clear the session
    return flask.jsonify({"success": True, "message": "Logout successful"})


@auth.route("/test", methods=["GET"])
@flask_login.login_required
def auth_ping():
    """Tests login mechanism."""
    return flask.jsonify({"message": "pong"}), 200