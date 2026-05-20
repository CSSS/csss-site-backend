import logging
import os

os.environ["ENV"] = "test"


def pytest_configure(config):
    loggers = ["sqlalchemy.engine.Engine", "httpx"]
    for logger in loggers:
        logging.getLogger(logger).setLevel(logging.WARNING)
