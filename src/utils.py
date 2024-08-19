from datetime import datetime

from officers.tables import OfficerInfo, OfficerTerm
from sqlalchemy import Select

# we can't use and/or in sql expressions, so we must use these functions
from sqlalchemy.sql.expression import and_, or_


def is_iso_format(date_str: str) -> bool:
    try:
        datetime.fromisoformat(date_str)
        return True
    except ValueError:
        return False


def is_active_officer(query: Select) -> Select:
    # TODO: assert this constraint at the SQL level, so that we don't even have to check it?
    return query.where(
        and_(
            OfficerTerm.is_filled_in,
            or_(
                # executives without a specified end_date are considered active
                OfficerTerm.end_date.is_(None),
                # check that today's timestamp is before (smaller than) the term's end date
                datetime.today() <= OfficerTerm.end_date
            )
        )
    )
