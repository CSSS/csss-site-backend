from datetime import date, datetime, timedelta, timezone

from enum import Enum
from typing import Any

from data.semesters import current_semester_start, step_semesters

import database

import officers.crud
#from officers.crud import latest_exec_term # TODO: figure out the function to import

class Permission:
    pass

# TODO: how to export this from __init__, but still place it in permission.py
class OfficerPrivateInfo(Permission):

    @staticmethod
    def user_has_permission(db_session: database.DBSession, computing_id: str) -> bool:
        """
        A user has access to private officer info if they've been an exec sometime in the past 5 semesters.
        A semester is defined in semester_start
        """

        # TODO: implement this crud function
        most_recent_exec_term = officers.crud.most_recent_exec_term(db_session, computing_id)
        if len(most_recent_exec_term) == 0:
            return False

        current_date = datetime.now(timezone.utc)
        semester_start = current_semester_start(current_date)
        NUM_SEMESTERS = 5
        cutoff_date = step_semesters(semester_start, -NUM_SEMESTERS)

        if most_recent_exec_term > cutoff_date:
            return True
        else:
            return False
