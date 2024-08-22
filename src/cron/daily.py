"""This module gets called by cron every day"""

import asyncio
import logging

from database import _db_session
from officers.crud import officer_terms

import github
import google

_logger = logging.getLogger(__name__)

async def update_permissions():
    db_session = _db_session()

    google_permissions = google.current_permissions()
    github_permissions = github.current_permissions()

    one_year_ago = datetime.today() - timedelta(days=365)

    # TODO: for performance, only include officers with recent end-date (1 yr)
    all_officer_terms = await all_officer_terms(db_session)
    for term in all_officer_terms:
        if utils.is_active(term):
            # TODO: if google drive permissions is not active, update them
            # TODO: if github permissions is not active, update them
            pass
        elif utils.end_date <= one_year_ago:
            # ignore old executives
            continue
        else:
            # TODO: if google drive permissions are active, remove them
            # TODO: if github permissions are active, remove them
            pass 

    _logger.info("Complete permissions update")

if __name__ == "__main__":
    asyncio.run(update_permissions())

