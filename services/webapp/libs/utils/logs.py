import logging
import os

FORMAT = ('%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] '
          '[dd.service=%(dd.service)s dd.env=%(dd.env)s dd.version=%(dd.version)s dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] '
          '- %(message)s')

logging.basicConfig(format=FORMAT)

# Log level, defaults to INFO
LOG_LEVEL = os.environ.get("LEVEL", "INFO").upper()

logger = logging.getLogger(__name__)
logger.info(f"LOG LEVEL: {LOG_LEVEL}")

def get_logger(name: str):

    logger = logging.getLogger(name)

    if not logger.handlers:  # Avoid adding handlers repeatedly

        if LOG_LEVEL == "DEBUG":
            logger.level = logging.DEBUG
        elif LOG_LEVEL == "INFO":
            logger.level = logging.INFO
        elif LOG_LEVEL == "WARN":
            logger.level = logging.WARN
        elif LOG_LEVEL == "ERROR":
            logger.level = logging.ERROR
        else:
            logger.level = logging.INFO
            logger.warning(f"unknown LOG_LEVEL ({LOG_LEVEL}), expecting DEBUG, INFO, WARN or ERROR. Defaults to INFO")

    return logger