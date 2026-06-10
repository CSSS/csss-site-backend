from collections.abc import Sequence

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

import candidates.crud
import nominees.crud
from candidates.tables import CandidateDB
from elections.models import ElectionNomineeSummary
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


async def get_all_nominees_by_election(
    db_session: AsyncSession,
    has_permission: bool,
) -> dict[str, list[ElectionNomineeSummary]]:
    """
    Fetches all nominees across all elections in a JOIN query.
    Returns a dict mapping election slug -> list of ElectionNomineeSummary.
    Only fetches contact fields (computing_id, linked_in, etc.) when has_permission is True.
    """
    if has_permission:
        query = sqlalchemy.select(
            CandidateDB.nominee_election,
            CandidateDB.position,
            CandidateDB.speech,
            NomineeInfoDB.full_name,
            NomineeInfoDB.computing_id,
            NomineeInfoDB.linked_in,
            NomineeInfoDB.instagram,
            NomineeInfoDB.email,
            NomineeInfoDB.discord_username,
        ).join(NomineeInfoDB, CandidateDB.computing_id == NomineeInfoDB.computing_id)
    else:
        query = sqlalchemy.select(
            CandidateDB.nominee_election,
            CandidateDB.position,
            CandidateDB.speech,
            NomineeInfoDB.full_name,
        ).join(NomineeInfoDB, CandidateDB.computing_id == NomineeInfoDB.computing_id)

    rows = (await db_session.execute(query)).all()

    nominees_by_election: dict[str, list[ElectionNomineeSummary]] = {}
    for row in rows:
        if has_permission:
            nominee = ElectionNomineeSummary(
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
            nominee = ElectionNomineeSummary(
                full_name=row.full_name,
                position=row.position,
                speech=row.speech or "No speech provided by this candidate",
            )
        if row.nominee_election not in nominees_by_election:
            nominees_by_election[row.nominee_election] = []
        nominees_by_election[row.nominee_election].append(nominee)

    return nominees_by_election


async def _get_election_nominees(
    db_session: AsyncSession,
    election_row: ElectionDB,
    has_permission: bool,
) -> list[ElectionNomineeSummary]:
    candidates_list = []
    all_nominations = await candidates.crud.get_all_candidates_in_election(db_session, election_row.slug)
    if not all_nominations:
        return []
    for nomination in all_nominations:
        # NOTE: if a nominee does not input their legal name, they are not considered a nominee
        nominee_info = await nominees.crud.get_nominee_info(db_session, nomination.computing_id)
        if nominee_info is None:
            continue

        if has_permission:
            candidate_entry = ElectionNomineeSummary(
                full_name=nominee_info.full_name,
                position=nomination.position,
                speech=nomination.speech or "No speech provided by this candidate",
                computing_id=nomination.computing_id,
                linked_in=nominee_info.linked_in,
                instagram=nominee_info.instagram,
                email=nominee_info.email,
                discord_username=nominee_info.discord_username,
            )
        else:
            candidate_entry = ElectionNomineeSummary(
                full_name=nominee_info.full_name,
                position=nomination.position,
                speech=nomination.speech or "No speech provided by this candidate",
            )
        candidates_list.append(candidate_entry)
    return candidates_list
