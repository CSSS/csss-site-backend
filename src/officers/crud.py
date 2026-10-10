from datetime import date, datetime

from sqlalchemy import Select, Tuple, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

import auth.crud
import database
import utils
from auth.tables import SiteUserDB
from constants import TZ_INFO
from data import semesters
from officers.models import OfficerCreate
from officers.tables import OfficerInfoDB, OfficerPositionVersionDB, OfficerTermDB


def get_officer_term_query():
    return (
        select(OfficerTermDB)
        .options(
            joinedload(OfficerTermDB.officer),
            joinedload(OfficerTermDB.position_version).joinedload(OfficerPositionVersionDB.position),
        )
        .order_by(OfficerTermDB.start_date.desc())
    )


async def get_officer_terms(
    db_session: AsyncSession,
    include_future_terms: bool,
) -> list[OfficerTermDB]:
    query = get_officer_term_query()

    if not include_future_terms:
        query = query.where(OfficerTermDB.start_date <= datetime.now(TZ_INFO).date())

    return list((await db_session.scalars(query)).all())


async def get_officer_info(db_session: AsyncSession, computing_id: str) -> OfficerInfoDB | None:
    return await db_session.scalar(select(OfficerInfoDB).where(OfficerInfoDB.computing_id == computing_id))


async def get_officer_term_by_id(db_session: AsyncSession, term_id: int) -> OfficerTermDB | None:
    query = (
        select(OfficerTermDB)
        .options(
            joinedload(OfficerTermDB.officer),
        )
        .where(OfficerTermDB.id == term_id)
    )

    return await db_session.scalar(query)


async def get_active_officer_terms(
    db_session: AsyncSession,
) -> list[OfficerTermDB]:
    """
    Returns a list of all active officer terms.
    Active means that the current date is between the start and end dates of the term, or if the end date is None (indicating an ongoing term).
    """
    today = datetime.now(tz=TZ_INFO).date()

    query = get_officer_term_query().where(
        OfficerTermDB.start_date <= today, or_(OfficerTermDB.end_date.is_(None), OfficerTermDB.end_date >= today)
    )

    return list((await db_session.scalars(query)).all())


async def create_multiple_officers(db_session: AsyncSession, new_officers: list[OfficerCreate]):
    computing_ids = {term.computing_id for term in new_officers}

    # Prepare new officer info
    # If it's someone's first time being added as an officer, we need to create their Officer Info entry first
    existing_officer_infos = {
        info.computing_id: info
        for info in (
            await db_session.scalars(select(OfficerInfoDB).where(OfficerInfoDB.computing_id.in_(computing_ids)))
        ).all()
    }
    new_officer_infos = []
    for off in new_officers:
        if off.computing_id not in existing_officer_infos:
            info = OfficerInfoDB(
                computing_id=off.computing_id,
                legal_name=off.legal_name,
                preferred_name=off.preferred_name,
                phone_number=off.phone_number,
                discord_id=off.discord_id,
                google_drive_email=off.google_drive_email,
                github_username=off.github_username,
            )
            existing_officer_infos[off.computing_id] = info
            new_officer_infos.append(info)

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

    db_session.add_all(new_site_users)
    db_session.add_all(new_officer_infos)
    await db_session.flush()  # Flush to get IDs for new entries

    new_officer_terms: list[OfficerTermDB] = []
    for off in new_officers:
        new_officer_terms.append(
            OfficerTermDB(
                officer=existing_officer_infos[off.computing_id],
                position_version_id=off.position_version_id,
                start_date=off.start_date,
                end_date=off.end_date,
                photo_url=off.photo_url,
            )
        )

    db_session.add_all(new_officer_terms)
    await db_session.flush()

    return new_officer_terms


async def delete_officer_term_by_id(db_session: AsyncSession, term_id: int):
    await db_session.execute(delete(OfficerTermDB).where(OfficerTermDB.id == term_id))


async def get_officer_positions(db_session: AsyncSession, active_only: bool = False) -> list[OfficerPositionVersionDB]:
    latest_versions = select(
        OfficerPositionVersionDB.position_id,
        func.max(OfficerPositionVersionDB.id).label("version_id"),
    ).group_by(OfficerPositionVersionDB.position_id)
    if active_only:
        today = datetime.now(tz=TZ_INFO).date()
        latest_versions = latest_versions.where(
            OfficerPositionVersionDB.effective_from <= today,
            or_(OfficerPositionVersionDB.effective_to.is_(None), OfficerPositionVersionDB.effective_to >= today),
        )
    latest_versions = latest_versions.subquery()
    query = (
        select(OfficerPositionVersionDB)
        .join(latest_versions, OfficerPositionVersionDB.id == latest_versions.c.version_id)
        .options(joinedload(OfficerPositionVersionDB.position))
        .order_by(OfficerPositionVersionDB.position_id)
    )

    return list((await db_session.scalars(query)).all())


async def get_latest_officer_position_version(
    db_session: AsyncSession,
    position_id: int,
) -> OfficerPositionVersionDB | None:
    query = (
        select(OfficerPositionVersionDB)
        .options(joinedload(OfficerPositionVersionDB.position))
        .order_by(OfficerPositionVersionDB.id.desc())
        .limit(1)
    )

    return await db_session.scalar(query)


async def get_active_officer_position_version(
    db_session: AsyncSession,
    position_id: int,
) -> OfficerPositionVersionDB | None:
    query = (
        select(OfficerPositionVersionDB)
        .where(
            OfficerPositionVersionDB.position_id == position_id,
            OfficerPositionVersionDB.effective_from <= datetime.now(TZ_INFO).date(),
            or_(
                OfficerPositionVersionDB.effective_to.is_(None),
                OfficerPositionVersionDB.effective_to >= datetime.now(TZ_INFO).date(),
            ),
        )
        .options(joinedload(OfficerPositionVersionDB.position))
        .order_by(OfficerPositionVersionDB.id.desc())
        .limit(1)
    )

    return await db_session.scalar(query)
