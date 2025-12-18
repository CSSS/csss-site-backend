import re
from datetime import date, datetime

from sqlalchemy import Select

# we can't use and/or in sql expressions, so we must use these functions
from sqlalchemy.sql.expression import and_, or_

from officers.models import OfficerTerm
from officers.tables import OfficerTermDB


def is_iso_format(date_str: str) -> bool:
    try:
        datetime.fromisoformat(date_str)
        return True
    except ValueError:
        return False


def is_active_officer(query: Select) -> Select:
    """
    An active officer is one who is currently part of the CSSS officer team.
    That is, they are not upcoming, or in the past.
    """
    return query.where(
        and_(
            # cannot be an officer who has not started yet
            OfficerTermDB.start_date <= date.today(),
            or_(
                # executives without a specified end_date are considered active
                OfficerTermDB.end_date.is_(None),
                # check that today's timestamp is before (smaller than) the term's end date
                date.today() <= OfficerTermDB.end_date,
            ),
        )
    )


def has_started_term(query: Select) -> Select[tuple[OfficerTermDB]]:
    return query.where(OfficerTermDB.start_date <= date.today())


def is_active_term(term: OfficerTermDB) -> bool:
    return (
        # cannot be an officer who has not started yet
        term.start_date <= date.today()
        and (
            # executives without a specified end_date are considered active
            term.end_date is None
            # check that today's timestamp is before (smaller than) the term's end date
            or date.today() <= term.end_date
        )
    )


def is_past_term(term: OfficerTermDB | OfficerTerm) -> bool:
    """Any term which has concluded"""
    return (
        # an officer with no end date is current
        term.end_date is not None
        # if today is past the end date, it's a past term
        and date.today() > term.end_date
    )


def is_valid_phone_number(phone_number: str) -> bool:
    return len(phone_number) == 10 and phone_number.isnumeric()


def is_valid_email(email: str):
    return re.match(r"^[^@]+@[^@]+\.[a-zA-Z]*$", email)
