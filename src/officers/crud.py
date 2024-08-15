import dataclasses
import logging
from datetime import datetime

import database
import sqlalchemy
from auth.models import SiteUser

from officers.constants import OfficerPosition
from officers.tables import OfficerInfo, OfficerTerm
from officers.types import (
    OfficerData,
    OfficerInfoData,
    OfficerPrivateData,
    OfficerTermData,
)

_logger = logging.getLogger(__name__)


async def most_recent_exec_term(db_session: database.DBSession, computing_id: str) -> OfficerTerm | None:
    """
    Returns the most recent OfficerTerm an exec has had
    """

    query = sqlalchemy.select(OfficerTerm)
    query = query.where(OfficerTerm.computing_id == computing_id)
    query = query.order_by(OfficerTerm.start_date.desc())
    query = query.limit(1)

    # TODO: can this be replaced with scalar to improve performance?
    return (await db_session.scalars(query)).first()

# TODO: test this function
async def current_officer_position(db_session: database.DBSession, computing_id: str) -> str | None:
    """
    Returns None if the user is not currently an officer
    """
    query = sqlalchemy.select(OfficerTerm)
    query = query.where(OfficerTerm.computing_id == computing_id)
    # TODO: assert this constraint at the SQL level, so that we don't even have to check it.
    query = query.where(
        # TODO: turn this query into a utility function, so it can be reused
        OfficerTerm.is_filled_in
        and (
            # executives without a specified end_date are considered active
            OfficerTerm.end_date is None
            # check that today's timestamp is before (smaller than) the term's end date
            or (datetime.today() <= OfficerTerm.end_date)
        )
    )
    query = query.limit(1)

    # TODO: can this be replaced with scalar to improve performance?
    return (await db_session.scalars(query)).first()

async def current_executive_team(db_session: database.DBSession, include_private: bool) -> dict[str, list[OfficerData]]:
    """
    Get info about officers that are active. Go through all active & complete officer terms.

    Returns a mapping between officer position and officer terms
    """

    query = sqlalchemy.select(OfficerTerm)
    query = query.where(
        OfficerTerm.is_filled_in
        and (
            # executives without a specified end_date are considered active
            OfficerTerm.end_date is None
            # check that today's timestamp is before (smaller than) the term's end date
            or (datetime.today() <= OfficerTerm.end_date)
        )
    )
    query = query.order_by(OfficerTerm.start_date.desc())

    officer_terms = (await db_session.scalars(query)).all()
    num_officers = {}
    officer_data = {}

    for term in officer_terms:
        # NOTE: improve performance?
        if term.position not in [officer.value for officer in OfficerPosition]:
            _logger.warning(
                f"Unknown OfficerTerm.position={term.position} in database. Ignoring in request."
            )
            continue

        # TODO: improve performance by doing these all in one database request
        officer_info_query = sqlalchemy.select(OfficerInfo)
        officer_info_query = officer_info_query.where(
            OfficerInfo.computing_id == term.computing_id
        )
        officer_info = (await db_session.scalars(officer_info_query)).first()
        if officer_info is None:
            # TODO: make sure there are daily checks that this data actually exists
            continue

        if term.position not in officer_data:
            num_officers[term.position] = 0
            officer_data[term.position] = []

        num_officers[term.position] += 1
        # TODO: move this to a daily cronjob & just ignore any of the extras
        if num_officers[term.position] > OfficerPosition.from_string(term.position).num_active():
            # If there are more active positions than expected, log it to a file
            _logger.warning(
                f"There are more active {term.position} positions in the OfficerTerm than expected "
                f"({num_officers[term.position]} > {OfficerPosition.from_string(term.position).num_active()})"
            )

        officer_data[term.position] += [
            OfficerData(
                is_active = True,

                position = term.position,
                start_date = term.start_date,
                end_date = term.end_date,

                legal_name = officer_info.legal_name,
                nickname = term.nickname,
                discord_name = officer_info.discord_name,
                discord_nickname = officer_info.discord_nickname,

                favourite_course_0 = term.favourite_course_0,
                favourite_course_1 = term.favourite_course_1,
                favourite_language_0 = term.favourite_pl_0,
                favourite_language_1 = term.favourite_pl_1,

                csss_email = OfficerPosition.from_string(term.position).to_email(),
                biography = term.biography,
                photo_url = term.photo_url,

                private_data = OfficerPrivateData(
                    computing_id = term.computing_id,
                    phone_number = officer_info.phone_number,
                    github_username = officer_info.github_username,
                    google_drive_email = officer_info.google_drive_email,
                ) if include_private else None,
            )
        ]

    # validate & warn if there are any data issues
    # TODO: decide whether we should enforce empty instances or force the frontend to deal with it
    for position in OfficerPosition.expected_positions():
        if position.to_string() not in officer_data:
            _logger.warning(
                f"Expected position={position.to_string()} in response current_executive_team."
            )
        elif (
            position.num_active is not None
            and len(officer_data[position.to_string()]) != position.num_active
        ):
            _logger.warning(
                f"Unexpected number of {position.to_string()} entries "
                f"({len(officer_data[position.to_string()])} entries) in current_executive_team response."
            )

    return officer_data

async def all_officer_terms(db_session: database.DBSession, include_private: bool) -> list[OfficerData]:
    """
    Orders officers recent first.

    This could be a lot of data, so be careful.

    TODO: optionally paginate data, so it's not so bad.
    """
    query = sqlalchemy.select(OfficerTerm)
    query = query.order_by(OfficerTerm.start_date.desc())
    officer_terms = (await db_session.scalars(query)).all()

    officer_data_list = []
    for term in officer_terms:
        officer_info_query = sqlalchemy.select(OfficerInfo)
        officer_info_query = officer_info_query.where(
            OfficerInfo.computing_id == term.computing_id
        )
        officer_info = (await db_session.scalars(officer_info_query)).first()

        officer_data_list += [
            OfficerData(
                is_active = (term.end_date is None) or (datetime.today() <= term.end_date),

                position = term.position,
                start_date = term.start_date,
                end_date = term.end_date,

                legal_name = officer_info.legal_name,
                nickname = term.nickname,
                discord_name = officer_info.discord_name,
                discord_nickname = officer_info.discord_nickname,

                favourite_course_0 = term.favourite_course_0,
                favourite_course_1 = term.favourite_course_1,
                favourite_language_0 = term.favourite_pl_0,
                favourite_language_1 = term.favourite_pl_1,

                csss_email = OfficerPosition.from_string(term.position).to_email(),
                biography = term.biography,
                photo_url = term.photo_url,

                private_data = OfficerPrivateData(
                    computing_id = term.computing_id,
                    phone_number = officer_info.phone_number,
                    github_username = officer_info.github_username,
                    google_drive_email = officer_info.google_drive_email,
                ) if include_private else None,
            )
        ]

    return officer_data_list

# TODO: do we ever expect to need to remove officer info? Probably not? Just updating it.
async def create_new_officer_info(db_session: database.DBSession, officer_info_data: OfficerInfoData) -> bool:
    """
    Return False if the officer already exists
    """
    query = sqlalchemy.select(OfficerInfo)
    query = query.where(OfficerInfo.computing_id == officer_info_data.computing_id)
    officer_info = (await db_session.scalar(query)).first()
    if officer_info is not None:
        return False

    # TODO: make this a class function
    is_filled_in = True
    for field in dataclasses.fields(officer_info_data):
        if getattr(officer_info_data, field.name) is None:
            is_filled_in = False
            break

    new_user_session = OfficerInfo.from_data(is_filled_in, officer_info_data)
    await db_session.add(new_user_session)

async def update_officer_info(db_session: database.DBSession, officer_info_data: OfficerInfoData) -> bool:
    """
    Return False if the officer doesn't exist yet
    """
    query = sqlalchemy.select(OfficerInfo)
    query = query.where(OfficerInfo.computing_id == officer_info_data.computing_id)
    officer_info = (await db_session.scalar(query)).first()
    if officer_info is None:
        return False

    is_filled_in = True
    for field in dataclasses.fields(officer_info_data):
        if getattr(officer_info_data, field.name) is None:
            is_filled_in = False
            break

    query = (
        sqlalchemy
        .update(OfficerInfo)
        .where(OfficerInfo.computing_id == officer_info.computing_id)
        .values(OfficerInfo.update_dict(is_filled_in, officer_info_data))
    )
    # TODO: do we need to handle the result?
    await db_session.execute(query)


def update_officer_term(
    db_session: database.DBSession,
    officer_term_data: OfficerTermData,
):
    """
    Creates an officer term entry
    """

    is_filled_in = True
    for field in dataclasses.fields(officer_term_data):
        # the photo doesn't have to be uploaded for the term to be filled.
        if field.name == "photo_url":
            continue

        if getattr(officer_term_data, field.name) is None:
            is_filled_in = False
            break

    new_officer_term = OfficerTerm(
        computing_id = officer_term_data.computing_id,
        is_filled_in = is_filled_in,

        position = officer_term_data.position,
        start_date = officer_term_data.start_date,
        end_date = officer_term_data.end_date,

        nickname = officer_term_data.nickname,
        favourite_course_0 = officer_term_data.favourite_course_0,
        favourite_course_1 = officer_term_data.favourite_course_1,
        favourite_pl_0 = officer_term_data.favourite_pl_0,
        favourite_pl_1 = officer_term_data.favourite_pl_1,
        biography = officer_term_data.biography,
        photo_url = officer_term_data.photo_url,
    )
    # TODO: check if an entry with this (computing_id, position, start_date) already exists, & update it
    # instead of adding a new entry
    db_session.add(new_officer_term)

def remove_officer_term():
    pass

