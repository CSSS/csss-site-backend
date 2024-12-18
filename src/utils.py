import re
from datetime import datetime

from sqlalchemy import Select

# we can't use and/or in sql expressions, so we must use these functions
from sqlalchemy.sql.expression import and_, or_

from officers.tables import OfficerInfo, OfficerTerm


def is_iso_format(date_str: str) -> bool:
    try:
        datetime.fromisoformat(date_str)
        return True
    except ValueError:
        return False

def is_active_officer(query: Select) -> Select:
    query = query.where(
        and_(
            # cannot be an officer who has not started yet
            OfficerTerm.start_date <= datetime.today(),
            or_(
                # executives without a specified end_date are considered active
                OfficerTerm.end_date.is_(None),
                # check that today's timestamp is before (smaller than) the term's end date
                datetime.today() <= OfficerTerm.end_date,
            )
        )
    )
    return OfficerTerm.sql_is_filled_in(query)

def is_active_term(term: OfficerTerm) -> bool:
    return (
        # cannot be an officer who has not started yet
        term.start_date <= datetime.today()
        and (
            # executives without a specified end_date are considered active
            term.end_date is None
            # check that today's timestamp is before (smaller than) the term's end date
            or datetime.today() <= term.end_date
        )
    )

def is_past_term(term: OfficerTerm) -> bool:
    """Any term which has concluded"""
    return (
        # an officer with no end date is current
        term.end_date is not None
        # if today is past the end date, it's a past term
        and datetime.today() > term.end_date
    )

def is_valid_phone_number(phone_number: str) -> bool:
    return (
        len(phone_number) == 10
        and phone_number.isnumeric()
    )

def is_valid_email(email: str):
    return re.match(r"^[^@]+@[^@]+\.[a-zA-Z]*$", email)
