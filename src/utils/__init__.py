import re
from datetime import date, datetime

from sqlalchemy import Select

# we can't use and/or in sql expressions, so we must use these functions
from sqlalchemy.sql.expression import and_, or_

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


def is_active_term(
    term: OfficerTermDB | None = None, start_date: date | None = None, end_date: date | None = None
) -> bool:
    start = term.start_date if term is not None else start_date
    # TODO: Handle this error
    if start is None:
        return False
    end = term.end_date if term is not None else end_date
    return (
        # cannot be an officer who has not started yet
        start <= date.today()
        and (
            # executives without a specified end_date are considered active
            end is None
            # check that today's timestamp is before (smaller than) the term's end date
            or date.today() <= end
        )
    )


def is_past_term(term: OfficerTermDB) -> bool:
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
