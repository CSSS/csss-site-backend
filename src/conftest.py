# Configuration of Pytest

import logging

import pytest


@pytest.fixture(scope="session", autouse=True)
def suppress_sqlalchemy_logs():
    # Suppress SQLAlchemy logs while testing
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
