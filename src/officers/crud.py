import logging

import sqlalchemy

import database

from officers.models import OfficerTerm
from officers.constants import OfficerPosition
from officers.schemas import OfficerData, OfficerPrivateData

_logger = logging.getLogger(__name__)


async def most_recent_exec_term(db_session: database.DBSession, computing_id: str) -> OfficerTerm | None:
    """
    Returns the most recent OfficerTerm an exec has had
    """

    query = sqlalchemy.select(OfficerTerm)
    query = query.where(OfficerTerm.computing_id == computing_id)
    query = query.order_by(OfficerTerm.start_date.desc())
    query = query.limit(1)

    # TODO: can this be replaced with scalar to improve performance?
    return (await db_session.scalars(query)).first()

async def current_executive_team(db_session: database.DBSession, include_private: bool) -> dict[str, list[OfficerData]]:
    """
    Get info about officers that satisfy is_active. Go through all active & complete officer terms.
    """

    query = sqlalchemy.select(OfficerTerm)
    query = query.filter(OfficerTerm.is_active and OfficerTerm.is_complete)
    query = query.order_by(OfficerTerm.start_date.desc())

    officer_terms = (await db_session.scalars(query)).all()
    num_officers = {}
    officer_data = {}
    
    for term in officer_terms:
        if term.position not in [officer.value for officer in OfficerPosition]:
            _logger.warning(
                f"Unknown OfficerTerm.position={term.position} in database. Ignoring in request"
            )
            continue

        if term.position not in officer_data:
            num_officers[term.position] = 1
            officer_data[term.position] = []
        else:
            num_officers[term.position] += 1
            if num_officers[term.position] > OfficerPrivateData.from_string(term.position).num_active():
                # If there are more active positions than expected, log it to a file
                _logger.warning(
                    f"There are more active {term.position} positions in the OfficerTerm than expected "
                    f"({num_officers[term.position]} > {OfficerPrivateData.from_string(term.position).num_active()})"
                )

        officer_data[term.position] += [
            OfficerData(
                is_current_officer = True,

                position = term.position,
                start_date = term.start_date,
                end_date = term.end_date,

                legal_name = term.site_user.officer_info.legal_name,
                nickname = term.nickname,
                discord_name = term.site_user.officer_info.discord_name,
                discord_nickname = term.site_user.officer_info.discord_nickname,

                favourite_course_0 = term.favourite_course_0,
                favourite_course_1 = term.favourite_course_1,

                favourite_language_0 = term.favourite_pl_0,
                favourite_language_1 = term.favourite_pl_1,

                csss_email = OfficerPosition.from_string(term.position).to_email(),
                biography = term.biography,
                photo_url = term.photo_url,

                private_data = OfficerPrivateData(
                    computing_id = term.computing_id,
                    phone_number = term.site_user.officer_info.phone_number,
                    github_username = term.site_user.officer_info.github_username,
                    google_drive_email = term.site_user.officer_info.google_drive_email,
                ) if include_private else None,
            )
        ]

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


"""
# get info about which officers are private
def get_current_officers_info(db: Session, get_private: bool) -> list:
    query = db.query(Assignment)
    data = query.filter(Assignment.is_active).filter(Assignment.is_public).limit(50).all()
    return data  # TODO: what is the type of data?


# TODO: what do all these db functions do?
def create_new_assignment(db: Session, new_officer_data: schemas.NewOfficerData_Upload):
    # TODO: check if this officer already exists in the table by the computing_id
    # new_officer = Officer()

    new_assignment = Assignment(
        is_active=True,
        is_public=False,
        position=new_officer_data.position,
        start_date=new_officer_data.start_date,
        # position = new_officer_data.position,
        officer_id=-1,  # TODO: how to link to another table entry ???
    )
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)  # refresh the current db instance with updated data
    return new_assignment


# TODO: decide on data containers later, based on whatever makes the most sense.
def update_assignment(
    db: Session,
    personal_data: schemas.OfficerPersonalData_Upload,
    position_data: schemas.OfficerPositionData_Upload,
):
    pass


def create_personal_info():
    pass


def create_officer():
    pass
"""
