from datetime import date
from typing import ClassVar

from fastapi import HTTPException

import database
import elections.crud
import officers.constants
import officers.crud
import utils
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

class ElectionOfficer:
    @staticmethod
    async def has_permission(db_session: database.DBSession, computing_id: str) -> bool:
        """
        An current elections officer has access to all elections, prior elections officers have no access.
        """
        officer_terms = await officers.crud.current_officers(db_session, True)
        current_election_officer = officer_terms.get(
            officers.constants.OfficerPosition.ELECTIONS_OFFICER
        )
        if current_election_officer is not None:
            for election_officer in current_election_officer[1]:
                if (
                    election_officer.private_data.computing_id == computing_id
                    and election_officer.is_current_officer
                ):
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
    async def has_permission_or_raise(
        db_session: database.DBSession,
        computing_id: str,
        errmsg:str = "must have website admin permissions"
    ) -> bool:
        if not await WebsiteAdmin.has_permission(db_session, computing_id):
            raise HTTPException(status_code=401, detail=errmsg)
