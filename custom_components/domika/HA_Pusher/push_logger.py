import logging
_LOGGER = logging.getLogger(__name__)

def log_debug(message):
    print(message)
    _LOGGER.debug(message)

def log_error(message):
    print(message)
    _LOGGER.error(message)
