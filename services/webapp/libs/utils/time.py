from datetime import datetime

import utils
log = utils.get_logger(__name__)

def now():

    return datetime.utcnow().isoformat()