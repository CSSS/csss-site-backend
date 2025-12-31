from collections.abc import Sequence

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from candidates.tables import CandidateDB
from officers.constants import OfficerPositionEnum


async def get_all_candidates(db_session: AsyncSession) -> Sequence[CandidateDB]:
    candidates = (await db_session.scalars(sqlalchemy.select(CandidateDB))).all()
    return candidates


async def get_all_registrations_of_candidate(
    db_session: AsyncSession, computing_id: str, election_slug: str
) -> Sequence[CandidateDB] | None:
    candidates = (
        await db_session.scalars(
            sqlalchemy.select(CandidateDB).where(
                (CandidateDB.computing_id == computing_id) & (CandidateDB.nominee_election == election_slug)
            )
        )
    ).all()
    return candidates


async def get_one_candidate_in_election(
    db_session: AsyncSession,
    computing_id: str,
    election_slug: str,
    position: OfficerPositionEnum,
) -> CandidateDB | None:
    registration = await db_session.scalar(
        sqlalchemy.select(CandidateDB).where(
            CandidateDB.computing_id == computing_id,
            CandidateDB.nominee_election == election_slug,
            CandidateDB.position == position,
        )
    )
    return registration


async def get_all_candidates_in_election(
    db_session: AsyncSession,
    election_slug: str,
) -> list[CandidateDB]:
    candidates = (
        await db_session.scalars(sqlalchemy.select(CandidateDB).where(CandidateDB.nominee_election == election_slug))
    ).all()
    return list(candidates)


async def add_candidate(db_session: AsyncSession, initial_application: CandidateDB):
    db_session.add(initial_application)


async def update_candidate(db_session: AsyncSession, initial_application: CandidateDB):
    await db_session.execute(
        sqlalchemy.update(CandidateDB)
        .where(
            (CandidateDB.computing_id == initial_application.computing_id)
            & (CandidateDB.nominee_election == initial_application.nominee_election)
            & (CandidateDB.position == initial_application.position)
        )
        .values(initial_application.serialize())
    )


async def delete_candidate(
    db_session: AsyncSession, computing_id: str, election_slug: str, position: OfficerPositionEnum
):
    await db_session.execute(
        sqlalchemy.delete(CandidateDB).where(
            (CandidateDB.computing_id == computing_id)
            & (CandidateDB.nominee_election == election_slug)
            & (CandidateDB.position == position)
        )
    )
