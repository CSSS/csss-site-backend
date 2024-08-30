"""This module gets called by cron every day"""

import asyncio
import logging

from database import _db_session
from officers.crud import officer_terms
from officers.constants import OfficerPosition

import github
import google

_logger = logging.getLogger(__name__)

async def update_google_permissions(db_session):
    google_permissions = google.current_permissions()
    #one_year_ago = datetime.today() - timedelta(days=365)

    # TODO: for performance, only include officers with recent end-date (1 yr)
    # but measure performance first
    all_officer_terms = await all_officer_terms(db_session)
    for term in all_officer_terms:
        if utils.is_active(term):
            # TODO: if google drive permission is not active, update them
            pass
        else:
            # TODO: if google drive permissions are active, remove them
            pass

    _logger.info("updated google permissions")

async def update_github_permissions(db_session):
    github_permissions = github.current_permissions()
    #one_year_ago = datetime.today() - timedelta(days=365)

    # TODO: for performance, only include officers with recent end-date (1 yr)
    # but measure performance first
    all_officer_terms = await all_officer_terms(db_session)
    for term in all_officer_terms:
        if term.username not in github_permissions:
            # will wait another day until giving a person their required permissions
            # TODO: setup a hook or something?
            github.invite_user(term.username)
            continue

        if utils.is_active(term):
            # move all active officers to their respective teams
            if term.position == OfficerPosition.DIRECTOR_OF_ARCHIVES:
                github.set_user_teams(
                    term.username,
                    github_permissions[term.username].teams,
                    ["doa", "officers"]
                )
            elif term.position == OfficerPosition.ELECTION_OFFICER:
                github.set_user_teams(
                    term.username,
                    github_permissions[term.username].teams,
                    ["election_officer", "officers"]
                )
            else:
                github.set_user_teams(
                    term.username,
                    github_permissions[term.username].teams,
                    ["officers"]
                )

        else:
            # move all inactive officers to the past_officers github organization
            github.set_user_teams(
                term.username,
                github_permissions[term.username].teams,
                ["past_officers"]
            )

    _logger.info("updated github permissions")

async def update_permissions():
    db_session = _db_session()

    update google_permissions(db_session)
    db_session.commit()

    update_github_permissions(db_session)
    db_session.commit()

    _logger.info("all permissions updated")

if __name__ == "__main__":
    asyncio.run(update_permissions())

