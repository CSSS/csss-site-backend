from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

from fastapi import HTTPException

import github
import utils
from constants import COMPUTING_ID_MAX
from discord import discord
from officers.constants import OfficerPosition
from officers.tables import OfficerInfo, OfficerTerm


class OfficerPositionEnum(StrEnum):
    PRESIDENT = "president"
    VICE_PRESIDENT = "vice-president"
    TREASURER = "treasurer"

    DIRECTOR_OF_RESOURCES = "director of resources"
    DIRECTOR_OF_EVENTS = "director of events"
    DIRECTOR_OF_EDUCATIONAL_EVENTS = "director of educational events"
    ASSISTANT_DIRECTOR_OF_EVENTS = "assistant director of events"
    DIRECTOR_OF_COMMUNICATIONS = "director of communications"
    #DIRECTOR_OF_OUTREACH = "director of outreach"
    DIRECTOR_OF_MULTIMEDIA = "director of multimedia"
    DIRECTOR_OF_ARCHIVES = "director of archives"
    EXECUTIVE_AT_LARGE = "executive at large"
    FIRST_YEAR_REPRESENTATIVE = "first year representative"

    ELECTIONS_OFFICER = "elections officer"
    SFSS_COUNCIL_REPRESENTATIVE = "sfss council representative"
    FROSH_WEEK_CHAIR = "frosh week chair"

    SYSTEM_ADMINISTRATOR = "system administrator"
    WEBMASTER = "webmaster"
    SOCIAL_MEDIA_MANAGER = "social media manager"

@dataclass
class InitialOfficerInfo:
    computing_id: str
    position: str
    start_date: date

    def valid_or_raise(self):
        if len(self.computing_id) > COMPUTING_ID_MAX:
            raise HTTPException(status_code=400, detail=f"computing_id={self.computing_id} is too large")
        elif self.computing_id == "":
            raise HTTPException(status_code=400, detail="computing_id cannot be empty")
        elif self.position not in OfficerPosition.position_list():
            raise HTTPException(status_code=400, detail=f"invalid position={self.position}")

@dataclass
class OfficerInfoUpload:
    # TODO (#71): compute this using SFU's API & remove from being uploaded
    legal_name: str
    phone_number: None | str = None
    discord_name: None | str = None
    github_username: None | str = None
    google_drive_email: None | str = None

    # TODO (#71): remove this once legal name is computed using SFU's API.
    def valid_or_raise(self):
        if self.legal_name is None or self.legal_name == "":
            raise HTTPException(status_code=400, detail="legal name must not be empty")

    def to_officer_info(self, computing_id: str, discord_id: str | None, discord_nickname: str | None) -> OfficerInfo:
        return OfficerInfo(
            computing_id = computing_id,
            legal_name = self.legal_name,

            discord_id = discord_id,
            discord_name = self.discord_name,
            discord_nickname = discord_nickname,

            phone_number = self.phone_number,
            github_username = self.github_username,
            google_drive_email = self.google_drive_email,
        )

    async def validate(self, computing_id: str, old_officer_info: OfficerInfo) -> tuple[list[str], OfficerInfo]:
        """
        Validate that the uploaded officer info is correct; if it's not, revert it to old_officer_info.
        """
        validation_failures = []
        corrected_officer_info = self.to_officer_info(
            computing_id=computing_id,
            discord_id=None,
            discord_nickname=None,
        )

        if self.phone_number is None or not utils.is_valid_phone_number(self.phone_number):
            validation_failures += [f"invalid phone number {self.phone_number}"]
            corrected_officer_info.phone_number = old_officer_info.phone_number

        if discord.is_active():
            if self.discord_name is None or self.discord_name == "":
                corrected_officer_info.discord_name = None
                corrected_officer_info.discord_id = None
                corrected_officer_info.discord_nickname = None
            else:
                discord_user_list = await discord.search_username(self.discord_name)
                if len(discord_user_list) != 1:
                    validation_failures += [
                        f"unable to find discord user with the name {self.discord_name}"
                        if len(discord_user_list) == 0
                        else f"too many discord users start with {self.discord_name}"
                    ]
                    corrected_officer_info.discord_name = old_officer_info.discord_name
                    corrected_officer_info.discord_id = old_officer_info.discord_id
                    corrected_officer_info.discord_nickname = old_officer_info.discord_nickname
                else:
                    discord_user = discord_user_list[0]
                    corrected_officer_info.discord_name = discord_user.username
                    corrected_officer_info.discord_id = discord_user.id
                    corrected_officer_info.discord_nickname = discord_user.global_name
        else:
            # TODO (#27): log that the module is inactive & send an email to csss_sysadmin@sfu.ca
            # (if local is false & we have the email permissions or smth)

            # if module is inactive, don't allow updates to discord username
            corrected_officer_info.discord_name = old_officer_info.discord_name
            corrected_officer_info.discord_id = old_officer_info.discord_id
            corrected_officer_info.discord_nickname = old_officer_info.discord_nickname
            validation_failures += ["discord module inactive"]

        # TODO (#82): validate google-email using google module, by trying to assign the user to a permission or something
        if not utils.is_valid_email(self.google_drive_email):
            validation_failures += [f"invalid email format {self.google_drive_email}"]
            corrected_officer_info.google_drive_email = old_officer_info.google_drive_email

        # validate that github user is real
        if github.is_active():
            if await github.internals.get_user_by_username(self.github_username) is None:
                validation_failures += [f"invalid github username {self.github_username}"]
                corrected_officer_info.github_username = old_officer_info.github_username
        else:
            # TODO (#27): log that the module is inactive & send an email to csss_sysadmin@sfu.ca
            # (if local is false & we have the email permissions or smth)
            corrected_officer_info.github_username = old_officer_info.github_username
            validation_failures += ["github module inactive"]

        # TODO (#93): add the following to the daily cronjob
        # TODO (#97): if github user exists, invite the github user to the org (or can we simply add them directly?)
        # -> do so outside this function. Also, detect if the github username is being changed & uninvite the old user

        return validation_failures, corrected_officer_info

@dataclass
class OfficerTermUpload:
    # only admins can change:
    computing_id: str
    position: str
    start_date: date
    end_date: None | date = None

    # officer should change:
    nickname: None | str = None
    favourite_course_0: None | str = None
    favourite_course_1: None | str = None
    favourite_pl_0: None | str = None
    favourite_pl_1: None | str = None
    biography: None | str = None

    # TODO (#39): we're going to need an endpoint for uploading images
    photo_url: None | str = None

    def valid_or_raise(self):
        if self.position not in OfficerPosition.position_list():
            raise HTTPException(status_code=400, detail=f"invalid new position={self.position}")
        elif self.end_date is not None and self.start_date > self.end_date:
            raise HTTPException(status_code=400, detail="end_date must be after start_date")

    def to_officer_term(self, term_id: str) -> OfficerTerm:
        return OfficerTerm(
            id = term_id,

            computing_id = self.computing_id,
            position = self.position,
            start_date = self.start_date,
            end_date = self.end_date,

            nickname = self.nickname,
            favourite_course_0 = self.favourite_course_0,
            favourite_course_1 = self.favourite_course_1,
            favourite_pl_0 = self.favourite_pl_0,
            favourite_pl_1 = self.favourite_pl_1,
            biography = self.biography,
            photo_url = self.photo_url,
        )

# -------------------------------------------- #

@dataclass
class OfficerPrivateData:
    computing_id: str | None
    phone_number: str | None
    github_username: str | None
    google_drive_email: str | None

@dataclass
class OfficerData:
    is_active: bool

    # an officer may have multiple positions, such as FroshWeekChair & DirectorOfEvents
    position: str
    start_date: date
    end_date: date | None

    legal_name: str  # some people have long names, you never know
    nickname: str | None
    discord_name: str | None
    discord_nickname: str | None

    favourite_course_0: str | None
    favourite_course_1: str | None
    favourite_language_0: str | None
    favourite_language_1: str | None

    csss_email: str | None
    biography: str | None
    photo_url: str | None

    private_data: OfficerPrivateData | None

    def serializable_dict(self):
        # we need to manually serialize datetime objects for some reason...
        new_self = asdict(self)
        new_self["start_date"] = new_self["start_date"].isoformat()
        if new_self["end_date"] is not None:
            new_self["end_date"] = new_self["end_date"].isoformat()
        return new_self

    @staticmethod
    def from_data(
        term: OfficerTerm,
        officer_info: OfficerInfo,
        include_private_data: bool,
        is_active: bool,
    ) -> OfficerData:
        return OfficerData(
            is_active = is_active,

            position = term.position,
            start_date = term.start_date,
            end_date = term.end_date,

            legal_name = officer_info.legal_name,
            nickname = term.nickname,
            discord_name = officer_info.discord_name,
            discord_nickname = officer_info.discord_nickname,

            favourite_course_0 = term.favourite_course_0,
            favourite_course_1 = term.favourite_course_1,
            favourite_language_0 = term.favourite_pl_0,
            favourite_language_1 = term.favourite_pl_1,

            csss_email = OfficerPosition.to_email(term.position),
            biography = term.biography,
            photo_url = term.photo_url,

            private_data = OfficerPrivateData(
                computing_id = term.computing_id,
                phone_number = officer_info.phone_number,
                github_username = officer_info.github_username,
                google_drive_email = officer_info.google_drive_email,
            ) if include_private_data else None,
        )
