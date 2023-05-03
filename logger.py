import sys
import time
import logging

# ******************************************************************************************************************
# Logging
# ******************************************************************************************************************

log_level = 'INFO'
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

logging.basicConfig(stream = sys.stdout, level = log_level, format = log_format)

# Set the log to use GMT time zone
logging.Formatter.converter = time.gmtime

# Add milliseconds
logging.Formatter.default_msec_format = '%s.%03d'

# Create
log = logging.getLogger(__name__)
log.debug('Logging started')