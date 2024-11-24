from datetime import datetime, timezone

import utils
log = utils.get_logger(__name__)

def now():

    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')