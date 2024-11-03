import flask, flask_login

from . import auth  # Import the Blueprint from __init__.py

from models import User

@auth.route("/login", methods=["POST"])
def auth_login():
    """Logs in the current user."""

    user_id = flask.request.args.get("user_id")
    if user_id is None: 
        return flask.jsonify(), 404

    user = User.get(user_id)

    if user is not None:
        flask_login.login_user(user)  # Mark the user as logged in
        return flask.jsonify({"success": True, "message": "Login successful"})
    else:
        return flask.jsonify({"success": False, "message": "Login failed"}), 403


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