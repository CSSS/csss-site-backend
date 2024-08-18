import dataclasses
import logging
from datetime import datetime

import database
import sqlalchemy
from auth.tables import SiteUser

# we can't use and/or in sql expressions, so we must use these functions
from sqlalchemy.sql.expression import and_, or_

from officers.constants import OfficerPosition
from officers.tables import OfficerInfo, OfficerTerm
from officers.types import (
    OfficerData,
    OfficerInfoData,
    OfficerPrivateData,
    OfficerTermData,
)

_logger = logging.getLogger(__name__)


# TODO:
# - make sure that no functions assume that the computing_id exists in SiteUser

async def most_recent_exec_term(db_session: database.DBSession, computing_id: str) -> OfficerTerm | None:
    """
    Returns the most recent OfficerTerm an exec has had
    """

    query = sqlalchemy.select(OfficerTerm)
    query = query.where(OfficerTerm.computing_id == computing_id)
    query = query.order_by(OfficerTerm.start_date.desc())
    query = query.limit(1)

    return await db_session.scalar(query)

async def current_officer_position(db_session: database.DBSession, computing_id: str) -> str | None:
    """
    Returns None if the user is not currently an officer
    """
    query = sqlalchemy.select(OfficerTerm)
    query = query.where(OfficerTerm.computing_id == computing_id)
    # TODO: assert this constraint at the SQL level, so that we don't even have to check it?
    query = query.where(
        # TODO: turn this query into a utility function, so it can be reused
        and_(
            OfficerTerm.is_filled_in,
            or_(
                # executives without a specified end_date are considered active
                OfficerTerm.end_date.is_(None),
                # check that today's timestamp is before (smaller than) the term's end date
                datetime.today() <= OfficerTerm.end_date
            )
        )
    )
    query = query.limit(1)

    officer_term = await db_session.scalar(query)
    if officer_term is None:
        return None
    else:
        return officer_term.position

async def officer_terms(
    db_session: database.DBSession,
    computing_id: str,
    max_terms: None | int,
    # will not include officer term info that has not been filled in yet.
    hide_filled_in: bool
) -> list[OfficerTerm]:
    query = sqlalchemy.select(OfficerTerm)
    query = query.where(OfficerTerm.computing_id == computing_id)
    if hide_filled_in:
        query = query.where(
        # TODO: turn this query into a utility function, so it can be reused
        and_(
            OfficerTerm.is_filled_in,
            or_(
                # executives without a specified end_date are considered active
                OfficerTerm.end_date.is_(None),
                # check that today's timestamp is before (smaller than) the term's end date
                datetime.today() <= OfficerTerm.end_date
            )
        )
    )

    query = query.order_by(OfficerTerm.start_date.desc())
    if max_terms is not None:
        query.limit(max_terms)

    # TODO: is this a list by default?
    return (await db_session.scalars(query)).all()

async def current_executive_team(db_session: database.DBSession, include_private: bool) -> dict[str, list[OfficerData]]:
    """
    Get info about officers that are active. Go through all active & complete officer terms.

    Returns a mapping between officer position and officer terms
    """

    query = sqlalchemy.select(OfficerTerm)
    query = query.where(
        # TODO: turn this query into a utility function, so it can be reused
        and_(
            OfficerTerm.is_filled_in,
            or_(
                # executives without a specified end_date are considered active
                OfficerTerm.end_date.is_(None),
                # check that today's timestamp is before (smaller than) the term's end date
                datetime.today() <= OfficerTerm.end_date
            )
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
        # TODO: move this to a ~~daily cronjob~~ SQL model checking
        if num_officers[term.position] > OfficerPosition.from_string(term.position).num_active():
            # If there are more active positions than expected, log it to a file
            _logger.warning(
                f"There are more active {term.position} positions in the OfficerTerm than expected "
                f"({num_officers[term.position]} > {OfficerPosition.from_string(term.position).num_active()})"
            )

        officer_data[term.position] += [
            # TODO: turn this into a util function
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

async def all_officer_terms(
    db_session: database.DBSession,
    include_private: bool,
    view_only_filled_in: bool,
) -> list[OfficerData]:
    """
    Orders officers recent first.

    This could be a lot of data, so be careful.

    TODO: optionally paginate data, so it's not so bad.
    """
    query = sqlalchemy.select(OfficerTerm)
    if view_only_filled_in:
        query = query.where(OfficerTerm.is_filled_in)
    query = query.order_by(OfficerTerm.start_date.desc())
    officer_terms = (await db_session.scalars(query)).all()

    officer_data_list = []
    for term in officer_terms:
        officer_info_query = sqlalchemy.select(OfficerInfo)
        officer_info_query = officer_info_query.where(
            OfficerInfo.computing_id == term.computing_id
        )
        officer_info = await db_session.scalar(officer_info_query)

        officer_data_list += [
            # TODO: also turn this into a util function
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

async def create_new_officer_info(db_session: database.DBSession, officer_info_data: OfficerInfoData) -> bool:
    """
    Return False if the officer already exists
    """
    query = sqlalchemy.select(OfficerInfo)
    query = query.where(OfficerInfo.computing_id == officer_info_data.computing_id)
    officer_info = await db_session.scalar(query)
    if officer_info is not None:
        return False

    # TODO: make this a class function
    is_filled_in = True
    for field in dataclasses.fields(officer_info_data):
        if getattr(officer_info_data, field.name) is None:
            is_filled_in = False
            break

    new_user_session = OfficerInfo.from_data(is_filled_in, officer_info_data)
    db_session.add(new_user_session)
    return True

async def update_officer_info(db_session: database.DBSession, officer_info_data: OfficerInfoData) -> bool:
    """
    Return False if the officer doesn't exist yet
    """
    query = sqlalchemy.select(OfficerInfo)
    query = query.where(OfficerInfo.computing_id == officer_info_data.computing_id)
    officer_info = await db_session.scalar(query)
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
    return True

async def create_new_officer_term(
    db_session: database.DBSession,
    officer_term_data: OfficerTermData
) -> bool:
    query = sqlalchemy.select(OfficerTerm)
    query = query.where(OfficerTerm.computing_id == officer_term_data.computing_id)
    query = query.where(OfficerTerm.start_date == officer_term_data.start_date)
    query = query.where(OfficerTerm.position == officer_term_data.position)
    officer_data = await db_session.scalar(query)
    if officer_data is not None:
        # if an entry with this (computing_id, position, start_date) already exists, do nothing
        return False

    # TODO: turn this into a function
    is_filled_in = True
    for field in dataclasses.fields(officer_term_data):
        if field.name == "photo_url" or field.name == "end_date":
            # photo doesn't have to be uploaded for the term to be filled.
            continue
        elif getattr(officer_term_data, field.name) is None:
            is_filled_in = False
            print(f"NOT FILLED IN: {officer_term_data}")
            break

    db_session.add(OfficerTerm.from_data(is_filled_in, officer_term_data))
    return True

async def update_officer_term(
    db_session: database.DBSession,
    officer_term_data: OfficerTermData,
):
    """
    If there's an existing entry with the same computing_id, start_date, and position,
    update the data of that term.

    Returns false if the above entry does not exist.
    """
    # TODO: turn these into a compound key so we know it's unique !
    # TODO: or actually, just use a term_id?
    query = (
        sqlalchemy
        .select(OfficerTerm)
        .where(OfficerTerm.computing_id == officer_term_data.computing_id)
        .where(OfficerTerm.position == officer_term_data.position)
        .where(OfficerTerm.start_date == officer_term_data.start_date)
    )
    print(officer_term_data)
    officer_term = await db_session.scalar(query)
    if officer_term is None:
        return False

    # TODO: turn this into a function
    is_filled_in = True
    for field in dataclasses.fields(officer_term_data):
        # the photo doesn't have to be uploaded for the term to be filled.
        if field.name == "photo_url" or field.name == "end_date":
            continue

        if getattr(officer_term_data, field.name) is None:
            is_filled_in = False
            break

    query = (
        sqlalchemy
        .update(OfficerTerm)
        .where(OfficerTerm.computing_id == officer_term_data.computing_id)
        .where(OfficerTerm.position == officer_term_data.position)
        .where(OfficerTerm.start_date == officer_term_data.start_date)
        .values(OfficerTerm.update_dict(is_filled_in, officer_term_data))
    )
    print(OfficerTerm.update_dict(is_filled_in, officer_term_data))
    # TODO: do we need to handle the result?
    await db_session.execute(query)
    return True

def remove_officer_term():
    pass
