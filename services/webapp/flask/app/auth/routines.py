import flask, flask_login
import models

import utils
log = utils.get_logger(__name__)


def code_auth(code_id):

    code = models.Code.get_by_id(code_id)
    if code is None:
        return flask.jsonify({"success": False}), 403
    
    user, user_code = code.user().first()

    if user is None:
        log.error(f"login with code for invalid user {user.id}")
        return flask.jsonify({"success": False}), 403

    flask_login.login_user(user)
    log.info(f"user {user.id}:{user.name} logged in")

    return user
