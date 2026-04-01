import logging
from datetime import date, datetime

import sqlalchemy
from sqlalchemy import func

import database
from announcements.models import Announcements

async def create_new_entry(
    db_session: database.DBSession,
    title: str,
    content: str,
    computing_id: str,
    date_created: date,
):
    """To create a new announcement entry"""

    # TODO: Implement the logic to create a new announcement entry in the database
    pass