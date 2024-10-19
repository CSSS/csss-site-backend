import dataclasses
import logging
from datetime import datetime

import sqlalchemy
from fastapi import HTTPException

import database
import utils
from auth.tables import SiteUser
from data import semesters
from officers.constants import OfficerPosition
from officers.tables import OfficerInfo, OfficerTerm
from officers.types import (
    OfficerData,
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

async def current_officer_positions(db_session: database.DBSession, computing_id: str) -> list[str]:
    """
    Returns [] if the user is not currently an officer.

    Gets positions ordered most recent start date first.

    An officer can have multiple positions, such as Webmaster, Frosh chair, and DoEE.
    """
    query = sqlalchemy.select(OfficerTerm)
    query = query.where(OfficerTerm.computing_id == computing_id)
    query = query.order_by(OfficerTerm.start_date.desc())
    query = utils.is_active_officer(query)

    officer_term_list = (await db_session.scalars(query)).all()
    return [term.position for term in officer_term_list]

async def officer_info(db_session: database.DBSession, computing_id: str) -> OfficerInfo:
    query = (
        sqlalchemy
        .select(OfficerInfo)
        .where(OfficerInfo.computing_id == computing_id)
    )
    officer_term = await db_session.scalar(query)
    if officer_term is None:
        raise HTTPException(status_code=400, detail=f"officer_info for computing_id={computing_id} does not exist yet")
    return officer_term

async def officer_term(db_session: database.DBSession, term_id: int) -> OfficerTerm:
    query = (
        sqlalchemy
        .select(OfficerTerm)
        .where(OfficerTerm.id == term_id)
    )
    officer_term = await db_session.scalar(query)
    if officer_term is None:
        raise HTTPException(status_code=400, detail=f"Could not find officer_term with id={term_id}")
    return officer_term

# TODO: change to "get_officer_terms" naming convention (& all functions in this module)
async def officer_terms(
    db_session: database.DBSession,
    computing_id: str,
    max_terms: None | int,
    # will not include officer term info that has not been filled in yet.
    view_only_filled_in: bool,
) -> list[OfficerTerm]:
    query = sqlalchemy.select(OfficerTerm)
    query = query.where(OfficerTerm.computing_id == computing_id)
    # TODO: does active == filled_in ?
    if view_only_filled_in:
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
        query = OfficerTerm.sql_is_filled_in(query)
    query = query.order_by(OfficerTerm.start_date.desc())
    officer_terms = (await db_session.scalars(query)).all()

    officer_data_list = []
    for term in officer_terms:
        officer_info_query = sqlalchemy.select(OfficerInfo)
        officer_info_query = officer_info_query.where(
            OfficerInfo.computing_id == term.computing_id
        )
        officer_info = await db_session.scalar(officer_info_query)

        officer_data_list += [OfficerData.from_data(
            term,
            officer_info,
            include_private,
            utils.is_active_term(term)
        )]

    return officer_data_list

async def create_new_officer_info(db_session: database.DBSession, new_officer_info: OfficerInfo) -> bool:
    """
    Return False if the officer already exists
    """
    query = sqlalchemy.select(OfficerInfo)
    query = query.where(OfficerInfo.computing_id == new_officer_info.computing_id)
    stored_officer_info = await db_session.scalar(query)
    if stored_officer_info is not None:
        return False

    db_session.add(new_officer_info)
    return True

# TODO: implement this for patch term as well
async def create_new_officer_term(
    db_session: database.DBSession,
    new_officer_term: OfficerTerm
):
    if new_officer_term.position not in OfficerPosition.position_list():
        raise HTTPException(status_code=500)

    position_length = OfficerPosition.position_length_in_semesters(new_officer_term.position)
    if position_length is not None:
        new_officer_term.end_date = semesters.step_semesters(
            semesters.current_semester_start(new_officer_term.start_date),
            position_length,
        )
    db_session.add(new_officer_term)

async def update_officer_info(db_session: database.DBSession, new_officer_info: OfficerInfo) -> bool:
    """
    Return False if the officer doesn't exist yet
    """
    query = sqlalchemy.select(OfficerInfo)
    query = query.where(OfficerInfo.computing_id == new_officer_info.computing_id)
    officer_info = await db_session.scalar(query)
    if officer_info is None:
        return False

    # TODO: how to detect an entry insert error? For example, what happens if
    # we try to set our discord id to be the same as another executive's?
    query = (
        sqlalchemy
        .update(OfficerInfo)
        .where(OfficerInfo.computing_id == officer_info.computing_id)
        .values(new_officer_info.to_update_dict())
    )
    await db_session.execute(query)

    return True

async def update_officer_term(
    db_session: database.DBSession,
    new_officer_term: OfficerTerm,
):
    """
    Update based on the term id.

    Returns false if the above entry does not exist.
    """
    query = (
        sqlalchemy
        .select(OfficerTerm)
        .where(OfficerTerm.id == new_officer_term.id)
    )
    officer_term = await db_session.scalar(query)
    if officer_term is None:
        return False

    query = (
        sqlalchemy
        .update(OfficerTerm)
        .where(OfficerTerm.id == new_officer_term.id)
        .values(new_officer_term.to_update_dict())
    )
    await db_session.execute(query)
    return True

def remove_officer_term():
    pass
