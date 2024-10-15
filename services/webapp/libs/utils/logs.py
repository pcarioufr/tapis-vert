import logging
import os 

FORMAT = ('%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] '
          '[dd.service=%(dd.service)s dd.env=%(dd.env)s dd.version=%(dd.version)s dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] '
          '- %(message)s')

logging.basicConfig(format=FORMAT)
log = logging.getLogger(__name__)

# Log level, defaults to INFO
LOG_LEVEL = os.environ.get("LEVEL", "INFO").upper()  
log.level = getattr(logging, LOG_LEVEL, logging.INFO)
