from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date, datetime

from fastapi import HTTPException

import github
import utils
from discord import discord
from officers.constants import OfficerPosition
from officers.tables import OfficerInfo, OfficerTerm


@dataclass
class OfficerInfoUpload:
    # TODO: compute this using SFU's API; if unable, use a default value
    legal_name: str
    phone_number: None | str = None
    discord_name: None | str = None
    github_username: None | str = None
    google_drive_email: None | str = None

    # TODO: why are valid_or_raise and validate separate?
    def valid_or_raise(self):
        # TODO: more checks
        if self.legal_name is not None and self.legal_name == "":
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

        # TODO: validate google-email using google module, by trying to assign the user to a permission or something
        if not utils.is_valid_email(self.google_drive_email):
            validation_failures += [f"invalid email format {self.google_drive_email}"]
            corrected_officer_info.google_drive_email = old_officer_info.google_drive_email

        # validate that github user is real
        if await github.internals.get_user_by_username(self.github_username) is None:
            validation_failures += [f"invalid github username {self.github_username}"]
            corrected_officer_info.github_username = old_officer_info.github_username

        # TODO: invite github user
        # TODO: detect if changing github username & uninvite old user

        return validation_failures, corrected_officer_info

@dataclass
class OfficerTermUpload:
    # only admins can change:
    position: str
    start_date: date
    end_date: None | date = None

    # officer should change
    nickname: None | str = None
    favourite_course_0: None | str = None
    favourite_course_1: None | str = None
    favourite_pl_0: None | str = None
    favourite_pl_1: None | str = None
    biography: None | str = None

    # TODO: we're going to need an API call to upload images
    # NOTE: changing the name of this variable without changing all instances is breaking
    photo_url: None | str = None

    def valid_or_raise(self):
        # NOTE: An officer can change their own data for terms that are ongoing.
        if self.position not in OfficerPosition.position_list():
            raise HTTPException(status_code=400, detail=f"invalid new position={self.position}")
        elif self.end_date is not None and self.start_date > self.end_date:
            raise HTTPException(status_code=400, detail="end_date must be after start_date")

    def to_officer_term(self, term_id: str, computing_id:str) -> OfficerTerm:
        return OfficerTerm(
            id = term_id,
            computing_id = computing_id,

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
    start_date: datetime
    end_date: datetime | None

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
