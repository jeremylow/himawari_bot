import logging
import logging.handlers

import twitter
import config


def get_api():
    """Returns an authenticated Twitter API instance"""
    logger.info('Getting API')
    api = twitter.Api(
        config.CONSUMER_KEY,
        config.CONSUMER_SECRET,
        config.ACCESS_KEY,
        config.ACCESS_SECRET,
        tweet_mode="extended",
        sleep_on_rate_limit=True)
    logger.debug('Using Api: %s', api)
    return api


def set_up_logging(log_file=None, level=logging.DEBUG):
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(level)

    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=1048576, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
