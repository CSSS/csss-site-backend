import dataclasses
import logging
from datetime import datetime

import database
import sqlalchemy
import utils
from auth.tables import SiteUser

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

    return await db_session.scalar(query)

async def current_officer_position(db_session: database.DBSession, computing_id: str) -> str | None:
    """
    Returns None if the user is not currently an officer
    """
    query = sqlalchemy.select(OfficerTerm)
    query = query.where(OfficerTerm.computing_id == computing_id)
    query = utils.is_active_officer(query)
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
        query = utils.is_active_officer(query)

    query = query.order_by(OfficerTerm.start_date.desc())
    if max_terms is not None:
        query.limit(max_terms)

    return (await db_session.scalars(query)).all()

async def current_executive_team(db_session: database.DBSession, include_private: bool) -> dict[str, list[OfficerData]]:
    """
    Get info about officers that are active. Go through all active & complete officer terms.

    Returns a mapping between officer position and officer terms
    """

    query = sqlalchemy.select(OfficerTerm)
    query = utils.is_active_officer(query)
    query = query.order_by(OfficerTerm.start_date.desc())

    officer_terms = (await db_session.scalars(query)).all()
    num_officers = {}
    officer_data = {}

    for term in officer_terms:
        if term.position not in OfficerPosition.position_list():
            _logger.warning(
                f"Unknown OfficerTerm.position={term.position} in database. Ignoring in request."
            )
            continue

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
        if num_officers[term.position] > OfficerPosition.num_active(term.position):
            # If there are more active positions than expected, log it to a file
            _logger.warning(
                f"There are more active {term.position} positions in the OfficerTerm than expected "
                f"({num_officers[term.position]} > {OfficerPosition.num_active(term.position)})"
            )

        officer_data[term.position] += [OfficerData.from_data(term, officer_info, include_private, is_active=True)]

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

        is_active = (term.end_date is None) or (datetime.today() <= term.end_date)
        officer_data_list += [OfficerData.from_data(term, officer_info, include_private, is_active)]

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

    is_filled_in = officer_info_data.is_filled_in()

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

    is_filled_in = officer_info_data.is_filled_in()
    query = (
        sqlalchemy
        .update(OfficerInfo)
        .where(OfficerInfo.computing_id == officer_info.computing_id)
        .values(OfficerInfo.update_dict(is_filled_in, officer_info_data))
    )

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

    is_filled_in = officer_term_data.is_filled_in()

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
    # TODO: we should move towards using the term_id, so that the start_date can be updated if needed?
    query = (
        sqlalchemy
        .select(OfficerTerm)
        .where(OfficerTerm.computing_id == officer_term_data.computing_id)
        .where(OfficerTerm.position == officer_term_data.position)
        .where(OfficerTerm.start_date == officer_term_data.start_date)
    )
    officer_term = await db_session.scalar(query)
    if officer_term is None:
        return False

    is_filled_in = officer_term_data.is_filled_in()
    query = (
        sqlalchemy
        .update(OfficerTerm)
        .where(OfficerTerm.computing_id == officer_term_data.computing_id)
        .where(OfficerTerm.position == officer_term_data.position)
        .where(OfficerTerm.start_date == officer_term_data.start_date)
        .values(OfficerTerm.update_dict(is_filled_in, officer_term_data))
    )

    await db_session.execute(query)
    return True

def remove_officer_term():
    pass
