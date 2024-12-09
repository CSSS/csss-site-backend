from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime

from fastapi import HTTPException

from constants import COMPUTING_ID_MAX
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

    def validate(self) -> None | HTTPException:
        if self.legal_name is not None and self.legal_name == "":
            return HTTPException(status_code=400, detail="legal name must not be empty")
        # TODO: more checks
        else:
            return None

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

    def validate(self):
        """input validation"""
        # NOTE: An officer can change their own data for terms that are ongoing.
        if self.position not in OfficerPosition.position_list():
            raise HTTPException(status_code=400, detail=f"invalid new position={self.position}")
        elif self.end_date is not None and self.start_date > self.end_date:
            raise HTTPException(status_code=400, detail="end_date must be after start_date")

    def to_officer_term(self, term_id: str, computing_id:str) -> OfficerTerm:
        # TODO: many positions have a length; if the length is defined, fill it in right here
        # (end date is 1st of month, 12 months after start date's month).
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
    photo_url: str | None  # some urls get big...

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
        include_private: bool,
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
            ) if include_private else None,
        )
