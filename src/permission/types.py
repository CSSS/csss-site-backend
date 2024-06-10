from datetime import UTC, datetime, timezone

import database
import officers.crud
from data.semesters import current_semester_start, step_semesters


class OfficerPrivateInfo:
    @staticmethod
    async def user_has_permission(db_session: database.DBSession, computing_id: str) -> bool:
        """
        A user has access to private officer info if they've been an exec sometime in the past 5 semesters.
        A semester is defined in semester_start
        """

        most_recent_exec_term = await officers.crud.most_recent_exec_term(db_session, computing_id)
        if most_recent_exec_term is None:
            return False

        current_date = datetime.now(UTC)
        semester_start = current_semester_start(current_date)
        NUM_SEMESTERS = 5
        cutoff_date = step_semesters(semester_start, -NUM_SEMESTERS)

        return most_recent_exec_term > cutoff_date
