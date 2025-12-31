import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

import candidates.crud
import database
import elections.crud
import nominees.crud
from candidates.models import (
    Candidate,
    CandidateCreate,
    CandidateUpdate,
)
from candidates.tables import CandidateDB
from dependencies import logged_in_user, perm_election
from elections.models import (
    ElectionStatusEnum,
)
from officers.constants import OfficerPositionEnum
from utils.shared_models import DetailModel, SuccessResponse
from utils.urls import slugify

router = APIRouter(
    prefix="/candidate",
    tags=["candidate"],
)


@router.get(
    "",
    description="get all candidates across all elections",
    response_model=list[Candidate],
    operation_id="get_candidates",
)
async def get_all_candidates(
    db_session: database.DBSession,
):
    return await candidates.crud.get_all_candidates(db_session)


@router.get(
    "/{election_name}",
    description="get all the candidates of a single election",
    response_model=list[Candidate],
    responses={
        401: {"description": "Not logged in", "model": DetailModel},
        404: {"description": "Election with slug does not exist", "model": DetailModel},
    },
    operation_id="get_election_candidates",
    dependencies=[Depends(logged_in_user)],
)
async def get_election_candidates(db_session: database.DBSession, election_name: str):
    slugified_name = slugify(election_name)
    if await elections.crud.get_election(db_session, slugified_name) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"election with slug {slugified_name} does not exist"
        )

    candidate_list = await candidates.crud.get_all_candidates_in_election(db_session, slugified_name)
    return [item.serialize() for item in candidate_list]


@router.post(
    "/{election_name}",
    description="Register for a specific position in this election, but doesn't set a speech. Returns the created entry.",
    response_model=Candidate,
    responses={
        400: {"description": "Bad request", "model": DetailModel},
        401: {"description": "Not logged in", "model": DetailModel},
        403: {"description": "Not an admin", "model": DetailModel},
        404: {"description": "No election found", "model": DetailModel},
    },
    operation_id="register",
    dependencies=[Depends(perm_election)],
)
async def register_candidate(db_session: database.DBSession, body: CandidateCreate, election_name: str):
    if body.position not in [o.value for o in OfficerPositionEnum]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid position {body.position}")

    if await nominees.crud.get_nominee_info(db_session, body.computing_id) is None:
        # ensure that the user has a nominee info entry before allowing registration to occur.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="must have submitted nominee info before registering"
        )

    slugified_name = slugify(election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"election with slug {slugified_name} does not exist"
        )

    if body.position not in election.available_positions:
        # NOTE: We only restrict creating a registration for a position that doesn't exist,
        # not updating or deleting one
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{body.position} is not available to register for in this election",
        )

    if election.status(datetime.datetime.now(datetime.UTC)) != ElectionStatusEnum.NOMINATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="registrations can only be made during the nomination period",
        )

    if await candidates.crud.get_all_registrations_of_candidate(db_session, body.computing_id, slugified_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="person is already registered in this election"
        )

    # TODO: associate specific election officers with specific election, then don't
    # allow any election officer running an election to register for it
    await candidates.crud.add_candidate(
        db_session,
        CandidateDB(
            computing_id=body.computing_id, nominee_election=slugified_name, position=body.position, speech=None
        ),
    )
    await db_session.commit()

    registrant = await candidates.crud.get_one_candidate_in_election(
        db_session, body.computing_id, slugified_name, body.position
    )
    if not registrant:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="failed to find new registrant")
    return registrant


@router.patch(
    "/{election_name}/{position}/{computing_id}",
    description="update the application of a specific registrant and return the changed entry",
    response_model=Candidate,
    responses={
        400: {"description": "Bad request", "model": DetailModel},
        401: {"description": "Not logged in", "model": DetailModel},
        403: {"description": "Not an admin", "model": DetailModel},
        404: {"description": "No election found", "model": DetailModel},
    },
    operation_id="update_candidate",
    dependencies=[Depends(perm_election)],
)
async def update_candidate(
    db_session: database.DBSession,
    body: CandidateUpdate,
    election_name: str,
    computing_id: str,
    position: OfficerPositionEnum,
):
    if body.position and body.position not in [o.value for o in OfficerPositionEnum]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid position {body.position}")

    slugified_name = slugify(election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"election with slug {slugified_name} does not exist"
        )

    # self updates can only be done during nomination period. Admin updates can be done whenever
    if election.status(datetime.datetime.now(datetime.UTC)) != ElectionStatusEnum.NOMINATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="speeches can only be updated during the nomination period"
        )

    candidate = await candidates.crud.get_one_candidate_in_election(db_session, computing_id, slugified_name, position)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no candidate record found")

    candidate.update_from_params(body)

    await candidates.crud.update_candidate(db_session, candidate)

    await db_session.commit()
    await db_session.refresh(candidate)
    return candidate


@router.delete(
    "/{election_name}/{position}/{computing_id}",
    description="delete the registration of a person",
    response_model=SuccessResponse,
    responses={
        400: {"description": "Bad request", "model": DetailModel},
        401: {"description": "Not logged in", "model": DetailModel},
        403: {"description": "Not an admin", "model": DetailModel},
        404: {"description": "No election or registrant found", "model": DetailModel},
    },
    operation_id="delete_candidate",
    dependencies=[Depends(perm_election)],
)
async def delete_candidate(
    db_session: database.DBSession,
    election_name: str,
    position: OfficerPositionEnum,
    computing_id: str,
):
    slugified_name = slugify(election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"election with slug {slugified_name} does not exist"
        )

    if election.status(datetime.datetime.now(datetime.UTC)) != ElectionStatusEnum.NOMINATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="candidate can only be revoked during the nomination period",
        )

    if not await candidates.crud.get_one_candidate_in_election(db_session, computing_id, slugified_name, position):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{computing_id} was not registered in election {slugified_name} for {position}",
        )

    await candidates.crud.delete_candidate(db_session, computing_id, slugified_name, position)
    await db_session.commit()
    old_election = await candidates.crud.get_one_candidate_in_election(
        db_session, computing_id, slugified_name, position
    )
    return JSONResponse({"success": old_election is None})
