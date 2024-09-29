import os

class Config:

    # FLASK ###############
    SECRET_KEY = os.environ.get("FLASK_SECRET")

    # REDIS ###############
    REDIS_HOST = os.environ.get("REDIS_HOST")
    REDIS_ROUNDS_DB = os.environ.get("REDIS_ROUNDS_DB")
    REDIS_USERS_DB = os.environ.get("REDIS_USERS_DB")
    REDIS_PUBSUB_DB = os.environ.get("REDIS_PUBSUB_DB")

    # DATADOG ###############
    DD_CLIENT_TOKEN = os.environ.get("DD_CLIENT_TOKEN")
    DD_APPLICATION_ID = os.environ.get("DD_APPLICATION_ID")
    DD_VERSION = os.environ.get("DD_VERSION")
    DD_ENV = os.environ.get("DD_ENV")
    DD_SITE = os.environ.get("DD_SITE")
