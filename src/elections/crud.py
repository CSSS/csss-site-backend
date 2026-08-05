from collections.abc import Sequence
from datetime import datetime

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from candidates.tables import CandidateDB
from elections.models import ElectionNomineeSummary, ElectionResponse
from elections.tables import ElectionDB
from nominees.tables import NomineeInfoDB


async def get_all_elections(db_session: AsyncSession) -> Sequence[ElectionDB]:
    election_list = (await db_session.scalars(sqlalchemy.select(ElectionDB))).all()
    return election_list


async def get_election(db_session: AsyncSession, election_slug: str) -> ElectionDB | None:
    return await db_session.scalar(sqlalchemy.select(ElectionDB).where(ElectionDB.slug == election_slug))


async def create_election(db_session: AsyncSession, election: ElectionDB):
    """
    Creates a new election with given parameters.
    Does not validate if an election _already_ exists
    """
    db_session.add(election)


async def update_election(db_session: AsyncSession, new_election: ElectionDB):
    """
    Attempting to change slug will fail. Instead, you must create a new election.
    """
    await db_session.execute(
        sqlalchemy.update(ElectionDB).where(ElectionDB.slug == new_election.slug).values(new_election.to_update_dict())
    )


async def delete_election(db_session: AsyncSession, slug: str) -> None:
    """
    Deletes a given election by its slug. Does not validate if an election exists
    """
    await db_session.execute(sqlalchemy.delete(ElectionDB).where(ElectionDB.slug == slug))


async def get_all_elections_with_nominees(
    db_session: AsyncSession,
    at_time: datetime,
    has_permission: bool,
) -> list[ElectionResponse]:
    """
    Fetches all elections and their nominees in a single query.
    Returns a list of ElectionResponse with candidates embedded.
    """
    query = (
        sqlalchemy.select(ElectionDB, CandidateDB, NomineeInfoDB)
        .outerjoin(CandidateDB, ElectionDB.slug == CandidateDB.nominee_election)
        .outerjoin(NomineeInfoDB, CandidateDB.computing_id == NomineeInfoDB.computing_id)
    )

    rows = (await db_session.execute(query)).all()

    elections_by_slug = {}
    for election, candidate, nominee_info in rows:
        if election.slug not in elections_by_slug:
            elections_by_slug[election.slug] = ElectionResponse(
                slug=election.slug,
                name=election.name,
                type=election.type,
                datetime_start_nominations=election.datetime_start_nominations,
                datetime_start_voting=election.datetime_start_voting,
                datetime_end_voting=election.datetime_end_voting,
                available_positions=election.available_positions,
                status=election.status(at_time),
                survey_link=election.survey_link if has_permission else None,
                candidates=[],
            )

        if (candidate is None) or (nominee_info is None) or (nominee_info.full_name is None):
            continue

        if has_permission:
            nominee = ElectionNomineeSummary(
                full_name=nominee_info.full_name,
                position=candidate.position,
                speech=candidate.speech or "No speech provided by this candidate",
                computing_id=nominee_info.computing_id,
                linked_in=nominee_info.linked_in,
                instagram=nominee_info.instagram,
                email=nominee_info.email,
                discord_username=nominee_info.discord_username,
            )
        else:
            nominee = ElectionNomineeSummary(
                full_name=nominee_info.full_name,
                position=candidate.position,
                speech=candidate.speech or "No speech provided by this candidate",
            )
        elections_by_slug[election.slug].candidates.append(nominee)

    return list(elections_by_slug.values())


async def get_election_nominees(
    db_session: AsyncSession,
    election_slug: str,
    has_permission: bool,
) -> list[ElectionNomineeSummary]:
    """
    Fetches all nominees for a single election in one JOIN query.
    Only fetches contact fields when has_permission is True.
    """
    if has_permission:
        query = (
            sqlalchemy.select(
                CandidateDB.position,
                CandidateDB.speech,
                NomineeInfoDB.full_name,
                NomineeInfoDB.computing_id,
                NomineeInfoDB.linked_in,
                NomineeInfoDB.instagram,
                NomineeInfoDB.email,
                NomineeInfoDB.discord_username,
            )
            .outerjoin(NomineeInfoDB, CandidateDB.computing_id == NomineeInfoDB.computing_id)
            .where(CandidateDB.nominee_election == election_slug)
        )
    else:
        query = (
            sqlalchemy.select(
                CandidateDB.position,
                CandidateDB.speech,
                NomineeInfoDB.full_name,
            )
            .outerjoin(NomineeInfoDB, CandidateDB.computing_id == NomineeInfoDB.computing_id)
            .where(CandidateDB.nominee_election == election_slug)
        )

    rows = (await db_session.execute(query)).all()

    candidates_list = []
    for row in rows:
        if has_permission:
            candidate_entry = ElectionNomineeSummary(
                full_name=row.full_name,
                position=row.position,
                speech=row.speech or "No speech provided by this candidate",
                computing_id=row.computing_id,
                linked_in=row.linked_in,
                instagram=row.instagram,
                email=row.email,
                discord_username=row.discord_username,
            )
        else:
            candidate_entry = ElectionNomineeSummary(
                full_name=row.full_name,
                position=row.position,
                speech=row.speech or "No speech provided by this candidate",
            )
        candidates_list.append(candidate_entry)
    return candidates_list
