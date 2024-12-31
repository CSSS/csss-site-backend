from datetime import date
from typing import ClassVar

from fastapi import HTTPException, Request

import auth.crud
import database
import officers.crud
import utils
from auth.types import SessionType
from data.semesters import step_semesters
from officers.constants import OfficerPosition


class OfficerPrivateInfo:
    @staticmethod
    async def has_permission(db_session: database.DBSession, computing_id: str) -> bool:
        """
        A user has access to private officer info if they've been an exec sometime in the past 5 semesters.
        A semester is defined in semester_start
        """

        term_list = await officers.crud.get_officer_terms(db_session, computing_id, include_future_terms=False)
        for term in term_list:
            if utils.is_active_term(term):
                return True

            NUM_SEMESTERS = 5
            if date.today() <= step_semesters(term.end_date, NUM_SEMESTERS):
                return True

        return False

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
        A website admin has to be an active officer who has one of the above positions
        """
        for position in await officers.crud.current_officer_positions(db_session, computing_id):
            if position in WebsiteAdmin.WEBSITE_ADMIN_POSITIONS:
                return True
        return False

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

    @staticmethod
    async def has_permission_or_raise(
        db_session: database.DBSession,
        computing_id: str,
        errmsg: str = "must have website admin permissions"
    ) -> bool:
        if not await WebsiteAdmin.has_permission(db_session, computing_id):
            raise HTTPException(status_code=401, detail=errmsg)

class ExamBankAccess:
    @staticmethod
    async def has_permission(
        db_session: database.DBSession,
        request: Request,
    ) -> bool:
        session_id = request.cookies.get("session_id", None)
        if session_id is None:
            return False

        # TODO: allow CSSS officers to access the exam bank, in addition to faculty

        if await auth.crud.get_session_type(db_session, session_id) == SessionType.FACULTY:
           return True

        # the only non-faculty who can view exams are website admins
        computing_id = await auth.crud.get_computing_id(db_session, session_id)
        return await WebsiteAdmin.has_permission(db_session, computing_id)
