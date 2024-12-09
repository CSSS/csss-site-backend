"""This module gets called by cron every day"""

import asyncio
import logging

import github
import google_api
import utils
from database import _db_session
from officers.crud import all_officer_data, get_user_by_username

_logger = logging.getLogger(__name__)

async def update_google_permissions(db_session):
    # TODO: implement this function
    # google_permissions = google_api.all_permissions()
    # one_year_ago = datetime.today() - timedelta(days=365)

    # TODO: for performance, only include officers with recent end-date (1 yr)
    # but measure performance first
    for term in await all_officer_data(db_session):
        if utils.is_active(term):
            # TODO: if google drive permission is not active, update them
            pass
        else:
            # TODO: if google drive permissions are active, remove them
            pass

    _logger.info("updated google permissions")

async def update_github_permissions(db_session):
    github_permissions, team_id_map = github.all_permissions()

    for term in await all_officer_data(db_session):
        new_teams = (
            # move all active officers to their respective teams
            github.officer_teams(term.position)
            if utils.is_active(term)
            # move all inactive officers to the past_officers github organization
            else ["past_officers"]
        )
        if term.username not in github_permissions:
            user = get_user_by_username(term.username)
            github.invite_user(
                user.id,
                [team_id_map[team] for team in new_teams],
            )
        else:
            github.set_user_teams(
                term.username,
                github_permissions[term.username].teams,
                new_teams
            )

    _logger.info("updated github permissions")

async def update_permissions():
    db_session = _db_session()

    update_google_permissions(db_session)
    db_session.commit()
    update_github_permissions(db_session)
    db_session.commit()

    _logger.info("all permissions updated")

if __name__ == "__main__":
    asyncio.run(update_permissions())

