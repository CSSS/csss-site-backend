from datetime import date
from typing import ClassVar

from fastapi import HTTPException

import database
import officers.constants
import officers.crud
import utils
from data.semesters import step_semesters
from officers.constants import OfficerPositionEnum

WEBSITE_ADMIN_POSITIONS: list[OfficerPositionEnum] = [
    OfficerPositionEnum.PRESIDENT,
    OfficerPositionEnum.VICE_PRESIDENT,
    OfficerPositionEnum.DIRECTOR_OF_ARCHIVES,
    OfficerPositionEnum.SYSTEM_ADMINISTRATOR,
    OfficerPositionEnum.WEBMASTER,
]


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
