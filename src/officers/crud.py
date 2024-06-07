from typing import Optional

import sqlalchemy

from models import OfficerTerm

import database
# rom . import schemas

def most_recent_exec_term(
    db_session: database.DBSession, 
    computing_id: str
) -> Optional[OfficerTerm]:
    """
    Returns the most recent OfficerTerm an exec has had
    """

    query = db_session.query(OfficerTerm)
    query = query.filter(OfficerTerm.computing_id == computing_id)
    query = query.order_by(OfficerTerm.start_date.desc())
    
    # TODO: confirm that the result is an instance of OfficerTerm (or None)
    return query.first()

'''
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
'''