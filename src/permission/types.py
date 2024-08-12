from datetime import UTC, datetime, timezone

import database
import elections.crud
import officers.constants
import officers.crud
from data.semesters import current_semester_start, step_semesters


class OfficerPrivateInfo:
    @staticmethod
    async def has_permission(db_session: database.DBSession, computing_id: str) -> bool:
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

class ElectionOfficer:
    @staticmethod
    async def has_permission(db_session: database.DBSession, computing_id: str) -> bool:
        """
        An current elections officer has access to all elections, prior elections officers have no access.
        """
        officer_terms = await officers.crud.current_executive_team(db_session, True)
        current_election_officer = officer_terms.get(officers.constants.OfficerPosition.ElectionsOfficer.value)[0]
        if current_election_officer is not None:
            # no need to verify if position is election officer, we do so above
            if current_election_officer.private_data.computing_id == computing_id and current_election_officer.is_current_officer is True:
                return True

        return False
