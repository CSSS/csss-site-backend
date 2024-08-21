from datetime import UTC, datetime, timezone
from typing import ClassVar

import auth.crud
import database
import officers.crud
from auth.types import SessionType
from data.semesters import current_semester_start, step_semesters
from fastapi import HTTPException, Request
from officers.constants import OfficerPosition


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
        elif most_recent_exec_term.end_date is None:
            # considered an active exec if no end_date
            return True

        current_date = datetime.now(UTC)
        semester_start = current_semester_start(current_date)
        NUM_SEMESTERS = 5
        cutoff_date = step_semesters(semester_start, -NUM_SEMESTERS)

        return most_recent_exec_term.end_date > cutoff_date

class WebsiteAdmin:
    WEBSITE_ADMIN_POSITIONS: ClassVar[list[OfficerPosition]] = [
        OfficerPosition.PRESIDENT,
        OfficerPosition.VICE_PRESIDENT,
        OfficerPosition.DIRECTOR_OF_ARCHIVES,
        OfficerPosition.SYSTEM_ADMINISTRATOR,
        OfficerPosition.WEBMASTER,
    ]

    @staticmethod
    async def has_permission(db_session: database.DBSession, computing_id: str) -> bool:
        """
        A website admin has to be one of the following positions, and
        """
        position = await officers.crud.current_officer_position(db_session, computing_id)
        if position is None:
            return False

        return position in WebsiteAdmin.WEBSITE_ADMIN_POSITIONS

    @staticmethod
    async def validate_request(db_session: database.DBSession, request: Request) -> bool:
        """
        Checks if the provided request satisfies these permissions, and raises the neccessary
        exceptions if not
        """
        # TODO: does this function return bool???
        session_id = request.cookies.get("session_id", None)
        if session_id is None:
            raise HTTPException(status_code=401, detail="must be logged in")
        else:
            computing_id = await auth.crud.get_computing_id(db_session, session_id)
            if not await WebsiteAdmin.has_permission(db_session, computing_id):
                raise HTTPException(status_code=401, detail="must have website admin permissions")

class ExamBankAccess:
    @staticmethod
    async def has_permission(
        db_session: database.DBSession,
        request: Request,
    ) -> bool:
        session_id = request.cookies.get("session_id", None)
        if session_id is None:
            return False

        if await auth.crud.get_session_type(db_session, session_id) == SessionType.FACULTY:
           return True

        # the only non-faculty who can view exams are website admins
        computing_id = await auth.crud.get_computing_id(db_session, session_id)
        return await WebsiteAdmin.has_permission(db_session, computing_id)


