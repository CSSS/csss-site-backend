import logging

import sqlalchemy
from fastapi import HTTPException

import database
import utils
from data import semesters
from officers.constants import OfficerPosition
from officers.tables import OfficerInfo, OfficerTerm
from officers.types import (
    OfficerData,
)

_logger = logging.getLogger(__name__)

async def most_recent_officer_term(db_session: database.DBSession, computing_id: str) -> OfficerTerm | None:
    """
    Returns the most recent OfficerTerm an exec has held
    """
    return await db_session.scalar(
        sqlalchemy
        .select(OfficerTerm)
        .where(OfficerTerm.computing_id == computing_id)
        .order_by(OfficerTerm.start_date.desc())
        .limit(1)
    )

async def current_officer_positions(db_session: database.DBSession, computing_id: str) -> list[str]:
    """
    Returns the list of officer positions a user currently has. Returns [] if the user is not currently an officer.

    An officer can have multiple positions at once, such as Webmaster, Frosh chair, and DoEE.
    """
    query = utils.is_active_officer(
        sqlalchemy
        .select(OfficerTerm)
        .where(OfficerTerm.computing_id == computing_id)
        # In order of most recent start date first
        .order_by(OfficerTerm.start_date.desc())
    )
    officer_term_list = (await db_session.scalars(query)).all()
    return [term.position for term in officer_term_list]

async def current_officers(
    db_session: database.DBSession,
    include_private: bool
) -> dict[str, list[OfficerData]]:
    """
    Get info about officers that are active. Go through all active & complete officer terms.

    Returns a mapping between officer position and officer terms
    """
    query = (
        sqlalchemy
        .select(OfficerTerm)
        .order_by(OfficerTerm.start_date.desc())
    )
    query = utils.is_active_officer(query)

    officer_terms = (await db_session.scalars(query)).all()
    officer_data = {}
    for term in officer_terms:
        officer_info_query = (
            sqlalchemy
            .select(OfficerInfo)
            .where(OfficerInfo.computing_id == term.computing_id)
        )
        officer_info = (await db_session.scalars(officer_info_query)).first()
        if officer_info is None:
            # TODO: make sure there are daily checks that this data actually exists
            continue
        elif term.position not in officer_data:
            officer_data[term.position] = []

        officer_data[term.position] += [
            OfficerData.from_data(term, officer_info, include_private, is_active=True)
        ]

    return officer_data

async def all_officers(
    db_session: database.DBSession,
    include_private_data: bool,
    include_future_terms: bool,
) -> list[OfficerData]:
    """
    This could be a lot of data, so be careful
    """
    # NOTE: paginate data if needed
    query = (
        sqlalchemy
        .select(OfficerTerm)
        # Ordered recent first
        .order_by(OfficerTerm.start_date.desc())
    )
    if not include_future_terms:
        query = utils.has_started_term(query)

    officer_data_list = []
    officer_terms = (await db_session.scalars(query)).all()
    for term in officer_terms:
        officer_info = await db_session.scalar(
            sqlalchemy
            .select(OfficerInfo)
            .where(OfficerInfo.computing_id == term.computing_id)
        )
        officer_data_list += [OfficerData.from_data(
            term,
            officer_info,
            include_private_data,
            utils.is_active_term(term)
        )]

    return officer_data_list

async def get_officer_info(db_session: database.DBSession, computing_id: str) -> OfficerInfo:
    officer_term = await db_session.scalar(
        sqlalchemy
        .select(OfficerInfo)
        .where(OfficerInfo.computing_id == computing_id)
    )
    if officer_term is None:
        raise HTTPException(status_code=400, detail=f"officer_info for computing_id={computing_id} does not exist yet")
    return officer_term

async def get_officer_terms(
    db_session: database.DBSession,
    computing_id: str,
    max_terms: None | int,
    include_future_terms: bool,
) -> list[OfficerTerm]:
    query = (
        sqlalchemy
        .select(OfficerTerm)
        .where(OfficerTerm.computing_id == computing_id)
        .order_by(OfficerTerm.start_date.desc())
    )
    if not include_future_terms:
        query = utils.has_started_term(query)

    if max_terms is not None:
        query.limit(max_terms)

    return (await db_session.scalars(query)).all()

async def get_officer_term_by_id(db_session: database.DBSession, term_id: int) -> OfficerTerm:
    query = (
        sqlalchemy
        .select(OfficerTerm)
        .where(OfficerTerm.id == term_id)
    )
    officer_term = await db_session.scalar(query)
    if officer_term is None:
        raise HTTPException(status_code=400, detail=f"Could not find officer_term with id={term_id}")
    return officer_term

async def create_new_officer_info(
    db_session: database.DBSession,
    new_officer_info: OfficerInfo
) -> bool:
    """
    Return False if the officer already exists
    """
    query = (
        sqlalchemy
        .select(OfficerInfo)
        .where(OfficerInfo.computing_id == new_officer_info.computing_id)
    )
    stored_officer_info = await db_session.scalar(query)
    if stored_officer_info is not None:
        return False

    db_session.add(new_officer_info)
    return True

async def create_new_officer_term(
    db_session: database.DBSession,
    new_officer_term: OfficerTerm
):
    # TODO: does this check need to be here?
    # if new_officer_term.position not in OfficerPosition.position_list():
    #     raise HTTPException(status_code=500)

    # when creating a new position, assign a default end date if one exists
    position_length = OfficerPosition.length_in_semesters(new_officer_term.position)
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
    query = (
        sqlalchemy
        .select(OfficerInfo)
        .where(OfficerInfo.computing_id == new_officer_info.computing_id)
    )
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

async def remove_officer_term():
    # TODO: implement this
    pass
