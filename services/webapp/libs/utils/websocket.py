from utils import get_logger
log = get_logger(__name__)

import redis
import os, json


redis_pubsub = redis.Redis(
            host=os.environ.get("REDIS_HOST"),
            db=os.environ.get("REDIS_PUBSUB_DB"),
            decode_responses=True
        )


def publish(room_id, key, value):

    # If value is not a string, we assume it's a more complex structure and JSON-encode it
    if not isinstance(value, str):
        value = json.dumps(value)

    # Create the message with 'key::value' format
    message = f"{key}::{value}"

    # Publish the message to the Redis channel (room_id)
    redis_pubsub.publish(room_id, message)
