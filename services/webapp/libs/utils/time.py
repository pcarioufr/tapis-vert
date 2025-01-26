from datetime import datetime, timezone

import utils
log = utils.get_logger(__name__)


def now(as_epoch=False):
    current_time = datetime.now(timezone.utc)
    return int(current_time.timestamp() * 1000) if as_epoch else current_time.strftime('%Y-%m-%dT%H:%M:%SZ')