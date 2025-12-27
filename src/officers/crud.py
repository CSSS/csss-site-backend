from datetime import date

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

import auth.crud
import database
import utils
from auth.tables import SiteUserDB
from data import semesters
from officers.constants import OfficerPosition, OfficerPositionEnum
from officers.models import Officer, OfficerCreate
from officers.tables import OfficerInfoDB, OfficerTermDB

# NOTE: this module should not do any data validation; that should be done in the urls.py or higher layer


async def current_officers(db_session: database.DBSession, include_private: bool = False) -> list[Officer]:
    """
    Get info about officers that are active. Go through all active & complete officer terms.
    """
    curr_time = date.today()
    query = (
        select(OfficerTermDB, OfficerInfoDB)
        .join(OfficerInfoDB, OfficerTermDB.computing_id == OfficerInfoDB.computing_id)
        .where((OfficerTermDB.start_date <= curr_time) & (OfficerTermDB.end_date >= curr_time))
        .order_by(OfficerTermDB.start_date.desc())
    )

    result = (await db_session.execute(query)).all()
    officer_list = []
    if include_private:
        for term, officer in result:
            officer_list.append(
                Officer(
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
    else:
        for term, officer in result:
            officer_list.append(Officer.public_fields(term, officer))

    return officer_list


async def get_current_terms_by_position(
    db_session: database.DBSession, position: OfficerPositionEnum, computing_id: str | None = None
) -> list[OfficerTermDB]:
    """
    Get current officer that holds a position
    """
    curr_time = date.today()
    query = (
        select(OfficerTermDB)
        .where(
            (OfficerTermDB.start_date <= curr_time)
            & (OfficerTermDB.end_date >= curr_time)
            & (OfficerTermDB.position == position)
        )
        .order_by(OfficerTermDB.start_date.desc())
    )
    if computing_id:
        query.where(OfficerTermDB.computing_id == computing_id)

    result = list((await db_session.scalars(query)).all())

    return result


async def get_all_officers(
    db_session: AsyncSession, include_future_terms: bool, include_private: bool
) -> list[Officer]:
    """
    This could be a lot of data, so be careful
    """
    query = (
        select(OfficerTermDB, OfficerInfoDB)
        .join(OfficerInfoDB, OfficerTermDB.computing_id == OfficerInfoDB.computing_id)
        .order_by(OfficerTermDB.start_date.desc())
    )
    if not include_future_terms:
        query = utils.has_started_term(query)
    officer_list = []
    # NOTE: paginate data if needed
    result = (await db_session.execute(query)).all()

    if include_private:
        for term, officer in result:
            officer_list.append(
                Officer(
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
    else:
        for term, officer in result:
            officer_list.append(Officer.public_fields(term, officer))

    return officer_list


async def get_officer_info_or_raise(db_session: database.DBSession, computing_id: str) -> OfficerInfoDB:
    officer_term = await db_session.scalar(select(OfficerInfoDB).where(OfficerInfoDB.computing_id == computing_id))
    if officer_term is None:
        raise HTTPException(status_code=404, detail=f"officer_info for computing_id={computing_id} does not exist yet")
    return officer_term


async def get_new_officer_info_or_raise(db_session: database.DBSession, computing_id: str) -> OfficerInfoDB:
    """
    This check is for after a create/update
    """
    officer_term = await db_session.scalar(select(OfficerInfoDB).where(OfficerInfoDB.computing_id == computing_id))
    if officer_term is None:
        raise HTTPException(status_code=500, detail=f"failed to fetch {computing_id} after update")
    return officer_term


async def get_officer_terms(
    db_session: database.DBSession,
    computing_id: str,
    include_future_terms: bool,
) -> list[OfficerTermDB]:
    query = (
        select(OfficerTermDB)
        .where(OfficerTermDB.computing_id == computing_id)
        # In order of most recent start date first
        .order_by(OfficerTermDB.start_date.desc())
    )
    if not include_future_terms:
        query = utils.has_started_term(query)

    return list((await db_session.scalars(query)).all())


async def get_active_officer_terms(
    db_session: database.DBSession, computing_id: str, positions: list[OfficerPositionEnum] | None = None
) -> list[OfficerTermDB]:
    """
    Returns the list of active officer terms for a user. Returns [] if the user is not currently an officer.
    An officer can have multiple positions at once, such as Webmaster, Frosh chair, and DoEE.
    """
    query = (
        select(OfficerTermDB)
        .where(OfficerTermDB.computing_id == computing_id)
        # In order of most recent start date first
        .order_by(OfficerTermDB.start_date.desc())
    )
    query = utils.is_active_officer(query)
    if positions:
        query.where(OfficerTermDB.position.in_(positions))

    return list((await db_session.scalars(query)).all())


async def current_officer_positions(
    db_session: database.DBSession, computing_id: str, positions: list[OfficerPositionEnum] | None = None
) -> list[str]:
    """
    Returns the list of officer positions a user currently has. [] if not currently an officer.
    """
    officer_term_list = await get_active_officer_terms(db_session, computing_id, positions)
    return [term.position for term in officer_term_list]


async def get_officer_term_by_id_or_raise(
    db_session: database.DBSession, term_id: int, is_new: bool = False
) -> OfficerTermDB:
    officer_term = await db_session.scalar(select(OfficerTermDB).where(OfficerTermDB.id == term_id))
    if officer_term is None:
        if is_new:
            raise HTTPException(status_code=500, detail=f"could not find new officer_term with id={term_id}")
        else:
            raise HTTPException(status_code=404, detail=f"could not find officer_term with id={term_id}")
    return officer_term


async def create_new_officer_info(db_session: database.DBSession, new_officer_info: OfficerInfoDB) -> bool:
    """Return False if the officer already exists & don't do anything."""
    if not await auth.crud.site_user_exists(db_session, new_officer_info.computing_id):
        # if computing_id has not been created as a site_user yet, add them
        db_session.add(
            SiteUserDB(computing_id=new_officer_info.computing_id, first_logged_in=None, last_logged_in=None)
        )

    existing_officer_info = await db_session.scalar(
        select(OfficerInfoDB).where(OfficerInfoDB.computing_id == new_officer_info.computing_id)
    )
    if existing_officer_info is not None:
        return False

    db_session.add(new_officer_info)
    return True


async def create_new_officer_term(db_session: database.DBSession, new_officer_term: OfficerTermDB):
    position_length = OfficerPosition.length_in_semesters(new_officer_term.position)
    if position_length is not None:
        # when creating a new position, assign a default end date if one exists
        new_officer_term.end_date = semesters.step_semesters(
            semesters.current_semester_start(new_officer_term.start_date),
            position_length,
        )
    db_session.add(new_officer_term)


async def create_multiple_officers(db_session: database.DBSession, new_officers: list[OfficerCreate]):
    computing_ids = {term.computing_id for term in new_officers}

    # Prepare new officer info
    # If it's someone's first time being added as an officer, we need to create their Officer Info entry first
    existing_officer_infos = set(
        (
            await db_session.scalars(
                select(OfficerInfoDB.computing_id).where(OfficerInfoDB.computing_id.in_(computing_ids))
            )
        ).all()
    )

    new_officer_infos = []
    seen_computing_ids: set[str] = set()  # Just in case duplicate slips through
    for off in new_officers:
        if off.computing_id not in existing_officer_infos and off.computing_id not in seen_computing_ids:
            new_officer_infos.append(
                OfficerInfoDB(
                    computing_id=off.computing_id,
                    legal_name=off.legal_name,
                    phone_number=off.phone_number,
                    discord_id=off.discord_id,
                    discord_name=off.discord_name,
                    discord_nickname=off.discord_nickname,
                    google_drive_email=off.google_drive_email,
                    github_username=off.github_username,
                )
            )
            seen_computing_ids.add(off.computing_id)

    # Get existing site users and create ones that are missing
    existing_site_users = set(
        (
            await db_session.scalars(select(SiteUserDB.computing_id).where(SiteUserDB.computing_id.in_(computing_ids)))
        ).all()
    )
    new_site_users = [
        SiteUserDB(computing_id=cid, first_logged_in=None, last_logged_in=None)
        for cid in computing_ids
        if cid not in existing_site_users
    ]

    # Prepare officer terms with computed end dates
    new_officer_terms: list[OfficerTermDB] = []
    for off in new_officers:
        end_date = off.end_date
        if end_date is None:
            position_length = OfficerPosition.length_in_semesters(off.position)
            if position_length is not None:
                end_date = semesters.step_semesters(
                    semesters.current_semester_start(off.start_date),
                    position_length,
                )
        new_officer_terms.append(
            OfficerTermDB(
                computing_id=off.computing_id,
                position=off.position,
                start_date=off.start_date,
                end_date=end_date,
                nickname=off.nickname,
                favourite_course_0=off.favourite_course_0,
                favourite_course_1=off.favourite_course_1,
                favourite_pl_0=off.favourite_pl_0,
                favourite_pl_1=off.favourite_pl_1,
                biography=off.biography,
                photo_url=off.photo_url,
            )
        )

    # Create all the new entries
    if new_site_users:
        db_session.add_all(new_site_users)
    if new_officer_infos:
        db_session.add_all(new_officer_infos)
    db_session.add_all(new_officer_terms)

    # Flush gets the generated IDs, but does not commit
    await db_session.flush()

    # Refresh each term to ensure all attributes are loaded for Pydantic validation
    for term in new_officer_terms:
        await db_session.refresh(term)

    return new_officer_terms


async def update_officer_info(db_session: database.DBSession, new_officer_info: OfficerInfoDB) -> bool:
    """
    Return False if the officer doesn't exist yet
    """
    officer_info = await db_session.scalar(
        select(OfficerInfoDB).where(OfficerInfoDB.computing_id == new_officer_info.computing_id)
    )
    if officer_info is None:
        return False

    # NOTE: if there's ever an insert entry error, it will raise SQLAlchemyError
    # see: https://stackoverflow.com/questions/2136739/how-to-check-and-handle-errors-in-sqlalchemy
    await db_session.execute(
        update(OfficerInfoDB)
        .where(OfficerInfoDB.computing_id == officer_info.computing_id)
        .values(new_officer_info.to_update_dict())
    )
    return True


async def update_officer_term(
    db_session: database.DBSession,
    new_officer_term: OfficerTermDB,
) -> bool:
    """
    Update all officer term data in `new_officer_term` based on the term id.
    Returns false if the above entry does not exist.
    """
    officer_term = await db_session.scalar(select(OfficerTermDB).where(OfficerTermDB.id == new_officer_term.id))
    if officer_term is None:
        return False

    await db_session.execute(
        update(OfficerTermDB).where(OfficerTermDB.id == new_officer_term.id).values(new_officer_term.to_update_dict())
    )
    return True


async def delete_officer_term_by_id(db_session: database.DBSession, term_id: int):
    await db_session.execute(delete(OfficerTermDB).where(OfficerTermDB.id == term_id))
