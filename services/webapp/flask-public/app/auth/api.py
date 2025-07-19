import flask, flask_login

from . import auth, code_auth  # Import the Blueprint from __init__.py

from models import User, Code
import utils
log = utils.get_logger(__name__)


@auth.route("/login", methods=["POST"])
def auth_login():
    """Logs in the current user."""

    code_id = flask.request.args.get("code_id")
    if code_id is None: 
        return flask.jsonify({"success": False}), 404

    user = code_auth(code_id)

    return flask.jsonify({"success": True, "user": user.to_dict(True) })


@auth.route("/me", methods=["GET"])
@flask_login.login_required
def me():
    """Logs in the current user."""

    user = flask_login.current_user

    return flask.jsonify( user.to_dict(True) )


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