import flask

from . import lab # Import the Blueprint from __init__.py

import utils
log = utils.get_logger(__name__)


@lab.route("/<test>", methods=['GET'])
def test(test=None):

    if test is None:
        log.warning("missing test in url")
        return flask.jsonify(), 400
    

    return flask.render_template("lab/{}.jinja".format(test))
