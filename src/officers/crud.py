from collections.abc import Sequence
from datetime import date, datetime

import sqlalchemy
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import auth.crud
import auth.tables
import database
import utils
from data import semesters
from officers.constants import OfficerPosition
from officers.models import OfficerInfoResponse, OfficerTermCreate
from officers.tables import OfficerInfo, OfficerTerm

# NOTE: this module should not do any data validation; that should be done in the urls.py or higher layer


async def current_officers(
    db_session: database.DBSession,
) -> list[OfficerInfoResponse]:
    """
    Get info about officers that are active. Go through all active & complete officer terms.

    Returns a mapping between officer position and officer terms
    """
    curr_time = date.today()
    query = (
        sqlalchemy.select(OfficerTerm, OfficerInfo)
        .join(OfficerInfo, OfficerTerm.computing_id == OfficerInfo.computing_id)
        .where((OfficerTerm.start_date <= curr_time) & (OfficerTerm.end_date >= curr_time))
        .order_by(OfficerTerm.start_date.desc())
    )

    result: Sequence[sqlalchemy.Row[tuple[OfficerTerm, OfficerInfo]]] = (await db_session.execute(query)).all()
    officer_list = []
    for term, officer in result:
        officer_list.append(
            OfficerInfoResponse(
                legal_name=officer.legal_name,
                is_active=True,
                position=term.position,
                start_date=term.start_date,
                end_date=term.end_date,
                biography=term.biography,
                csss_email=OfficerPosition.to_email(term.position),
                discord_id=officer.discord_id,
                discord_name=officer.discord_name,
                discord_nickname=officer.discord_nickname,
                computing_id=officer.computing_id,
                phone_number=officer.phone_number,
                github_username=officer.github_username,
                google_drive_email=officer.google_drive_email,
                photo_url=term.photo_url,
            )
        )

    return officer_list


async def all_officers(db_session: AsyncSession, include_future_terms: bool) -> list[OfficerInfoResponse]:
    """
    This could be a lot of data, so be careful
    """
    # NOTE: paginate data if needed
    query = (
        sqlalchemy.select(OfficerTerm, OfficerInfo)
        .join(OfficerInfo, OfficerTerm.computing_id == OfficerInfo.computing_id)
        .order_by(OfficerTerm.start_date.desc())
    )

    if not include_future_terms:
        query = utils.has_started_term(query)
    result: Sequence[sqlalchemy.Row[tuple[OfficerTerm, OfficerInfo]]] = (await db_session.execute(query)).all()
    officer_list = []
    for term, officer in result:
        officer_list.append(
            OfficerInfoResponse(
                legal_name=officer.legal_name,
                is_active=utils.is_active_term(term),
                position=term.position,
                start_date=term.start_date,
                end_date=term.end_date,
                biography=term.biography,
                csss_email=OfficerPosition.to_email(term.position),
                discord_id=officer.discord_id,
                discord_name=officer.discord_name,
                discord_nickname=officer.discord_nickname,
                computing_id=officer.computing_id,
                phone_number=officer.phone_number,
                github_username=officer.github_username,
                google_drive_email=officer.google_drive_email,
                photo_url=term.photo_url,
            )
        )

    return officer_list


async def get_officer_info_or_raise(db_session: database.DBSession, computing_id: str) -> OfficerInfo:
    officer_term = await db_session.scalar(
        sqlalchemy.select(OfficerInfo).where(OfficerInfo.computing_id == computing_id)
    )
    if officer_term is None:
        raise HTTPException(status_code=404, detail=f"officer_info for computing_id={computing_id} does not exist yet")
    return officer_term


async def get_new_officer_info_or_raise(db_session: database.DBSession, computing_id: str) -> OfficerInfo:
    """
    This check is for after a create/update
    """
    officer_term = await db_session.scalar(
        sqlalchemy.select(OfficerInfo).where(OfficerInfo.computing_id == computing_id)
    )
    if officer_term is None:
        raise HTTPException(status_code=500, detail=f"failed to fetch {computing_id} after update")
    return officer_term


async def get_officer_terms(
    db_session: database.DBSession,
    computing_id: str,
    include_future_terms: bool,
) -> list[OfficerTerm]:
    query = (
        sqlalchemy.select(OfficerTerm)
        .where(OfficerTerm.computing_id == computing_id)
        # In order of most recent start date first
        .order_by(OfficerTerm.start_date.desc())
    )
    if not include_future_terms:
        query = utils.has_started_term(query)

    return (await db_session.scalars(query)).all()


async def get_active_officer_terms(db_session: database.DBSession, computing_id: str) -> list[OfficerTerm]:
    """
    Returns the list of active officer terms for a user. Returns [] if the user is not currently an officer.
    An officer can have multiple positions at once, such as Webmaster, Frosh chair, and DoEE.
    """
    query = (
        sqlalchemy.select(OfficerTerm)
        .where(OfficerTerm.computing_id == computing_id)
        # In order of most recent start date first
        .order_by(OfficerTerm.start_date.desc())
    )
    query = utils.is_active_officer(query)

    officer_term_list = (await db_session.scalars(query)).all()
    return officer_term_list


async def current_officer_positions(db_session: database.DBSession, computing_id: str) -> list[str]:
    """
    Returns the list of officer positions a user currently has. [] if not currently an officer.
    """
    officer_term_list = await get_active_officer_terms(db_session, computing_id)
    return [term.position for term in officer_term_list]


async def get_officer_term_by_id_or_raise(
    db_session: database.DBSession, term_id: int, is_new: bool = False
) -> OfficerTerm:
    officer_term = await db_session.scalar(sqlalchemy.select(OfficerTerm).where(OfficerTerm.id == term_id))
    if officer_term is None:
        if is_new:
            raise HTTPException(status_code=500, detail=f"could not find new officer_term with id={term_id}")
        else:
            raise HTTPException(status_code=404, detail=f"could not find officer_term with id={term_id}")
    return officer_term


async def create_new_officer_info(db_session: database.DBSession, new_officer_info: OfficerInfo) -> bool:
    """Return False if the officer already exists & don't do anything."""
    if not await auth.crud.site_user_exists(db_session, new_officer_info.computing_id):
        # if computing_id has not been created as a site_user yet, add them
        db_session.add(
            auth.tables.SiteUser(computing_id=new_officer_info.computing_id, first_logged_in=None, last_logged_in=None)
        )

    existing_officer_info = await db_session.scalar(
        sqlalchemy.select(OfficerInfo).where(OfficerInfo.computing_id == new_officer_info.computing_id)
    )
    if existing_officer_info is not None:
        return False

    db_session.add(new_officer_info)
    return True


async def create_new_officer_term(db_session: database.DBSession, new_officer_term: OfficerTerm):
    position_length = OfficerPosition.length_in_semesters(new_officer_term.position)
    if position_length is not None:
        # when creating a new position, assign a default end date if one exists
        new_officer_term.end_date = semesters.step_semesters(
            semesters.current_semester_start(new_officer_term.start_date),
            position_length,
        )
    db_session.add(new_officer_term)


async def update_officer_info(db_session: database.DBSession, new_officer_info: OfficerInfo) -> bool:
    """
    Return False if the officer doesn't exist yet
    """
    officer_info = await db_session.scalar(
        sqlalchemy.select(OfficerInfo).where(OfficerInfo.computing_id == new_officer_info.computing_id)
    )
    if officer_info is None:
        return False

    # NOTE: if there's ever an insert entry error, it will raise SQLAlchemyError
    # see: https://stackoverflow.com/questions/2136739/how-to-check-and-handle-errors-in-sqlalchemy
    await db_session.execute(
        sqlalchemy.update(OfficerInfo)
        .where(OfficerInfo.computing_id == officer_info.computing_id)
        .values(new_officer_info.to_update_dict())
    )
    return True


async def update_officer_term(
    db_session: database.DBSession,
    new_officer_term: OfficerTerm,
) -> bool:
    """
    Update all officer term data in `new_officer_term` based on the term id.
    Returns false if the above entry does not exist.
    """
    officer_term = await db_session.scalar(sqlalchemy.select(OfficerTerm).where(OfficerTerm.id == new_officer_term.id))
    if officer_term is None:
        return False

    await db_session.execute(
        sqlalchemy.update(OfficerTerm)
        .where(OfficerTerm.id == new_officer_term.id)
        .values(new_officer_term.to_update_dict())
    )
    return True


async def delete_officer_term_by_id(db_session: database.DBSession, term_id: int):
    await db_session.execute(sqlalchemy.delete(OfficerTerm).where(OfficerTerm.id == term_id))
